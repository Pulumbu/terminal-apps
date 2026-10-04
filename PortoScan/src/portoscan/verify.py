"""Active verification of findings, for highly-authorized use only.

Two confirmations that go beyond inference, while never exfiltrating secrets:

* Exposed sensitive paths -- reads the body to CONFIRM it is genuinely
  sensitive (not just an HTTP 200), then reports REDACTED evidence: the key
  *names* present (values masked), counts, byte size and a short content hash.
  The raw body is discarded; no secret value is ever stored, logged or returned.

* SSH Terrapin (CVE-2023-48795) -- negotiates the SSH transport read-only and
  parses the server KEXINIT to determine whether an affected cipher is offered
  and whether the strict-KEX countermeasure is advertised. No authentication,
  no exploitation.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import re
import ssl
from dataclasses import dataclass

from portoscan.compliance import Finding
from portoscan.webcheck import PROBES

_ENV_KEY_RE = re.compile(rb"(?m)^[ \t]*(?:export[ \t]+)?([A-Za-z][A-Za-z0-9_]{1,64})[ \t]*=")


# --------------------------------------------------------------- redaction
def _short_hash(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()[:12]


def redact_evidence(kind: str, body: bytes) -> str:
    """A human-readable, REDACTED summary of a confirmed exposure. No values."""
    size = len(body)
    digest = _short_hash(body)
    if kind in ("env file",):
        keys: list[str] = []
        for match in _ENV_KEY_RE.finditer(body[:16384]):
            name = match.group(1).decode("ascii", "replace")
            if name not in keys:
                keys.append(name)
        shown = ", ".join(keys[:8])
        more = "" if len(keys) <= 8 else f" +{len(keys) - 8} more"
        return (f"{len(keys)} key(s) [{shown}{more}] (values redacted), "
                f"{size} B, sha256 {digest}")
    if kind == "git config":
        remotes = body[:16384].count(b"url =") + body[:16384].count(b"url=")
        return f"valid git config, {remotes} remote URL(s) (redacted), {size} B, sha256 {digest}"
    if kind == "AWS credentials":
        n = body[:16384].lower().count(b"aws_access_key_id")
        return f"{n} AWS key id(s) present (redacted), {size} B, sha256 {digest}"
    return f"confirmed, {size} B, sha256 {digest}"


# ------------------------------------------------------ exposure confirmation
@dataclass(frozen=True, slots=True)
class Confirmation:
    path: str
    kind: str
    severity: str
    status: int
    confirmed: bool
    evidence: str


async def _fetch_body(host: str, port: int, path: str, *, tls: bool,
                      timeout: float, limit: int = 65536) -> tuple[int, bytes] | None:
    context = None
    if tls:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=context), timeout=timeout)
    except (OSError, ssl.SSLError, asyncio.TimeoutError):
        return None
    try:
        request = (f"GET {path} HTTP/1.0\r\nHost: {host}\r\n"
                   f"User-Agent: PortoScan\r\nAccept: */*\r\nConnection: close\r\n\r\n")
        writer.write(request.encode("latin-1", "replace"))
        await writer.drain()
        raw = await asyncio.wait_for(reader.readexactly(limit), timeout=timeout)
    except asyncio.IncompleteReadError as partial:
        raw = partial.partial
    except (OSError, ssl.SSLError, asyncio.TimeoutError):
        return None
    finally:
        writer.close()
        with contextlib.suppress(OSError, ssl.SSLError):
            await writer.wait_closed()
    if not raw:
        return None
    head, _, body = raw.partition(b"\r\n\r\n")
    try:
        status = int(head.split(b"\r\n", 1)[0].split()[1])
    except (ValueError, IndexError):
        return None
    return status, body


async def confirm_exposure(host: str, port: int, path: str, kind: str,
                           severity: str, *, tls: bool,
                           timeout: float = 4.0) -> Confirmation:
    result = await _fetch_body(host, port, path, tls=tls, timeout=timeout)
    if result is None:
        return Confirmation(path, kind, severity, 0, False, "no response")
    status, body = result
    probe = next((p for p in PROBES if p.path == path and p.kind == kind), None)
    matched = status == 200 and probe is not None and probe.signature(body)
    evidence = redact_evidence(kind, body) if matched else (
        f"HTTP {status}, content does not match {kind} (not confirmed)")
    # body is discarded here; only the redacted evidence survives.
    return Confirmation(path, kind, severity, status, matched, evidence)


# ---------------------------------------------------------- SSH Terrapin
def parse_kexinit(payload: bytes) -> list[list[str]]:
    """Return the ten name-lists from an SSH_MSG_KEXINIT payload (type 20)."""
    if not payload or payload[0] != 20:
        return []
    pos = 17  # 1 byte type + 16 byte cookie
    lists: list[list[str]] = []
    for _ in range(10):
        if pos + 4 > len(payload):
            break
        length = int.from_bytes(payload[pos:pos + 4], "big")
        pos += 4
        chunk = payload[pos:pos + length].decode("ascii", "replace")
        pos += length
        lists.append(chunk.split(",") if chunk else [])
    return lists


def terrapin_verdict(lists: list[list[str]]) -> tuple[bool, str]:
    """(vulnerable, explanation) from parsed KEXINIT name-lists."""
    if len(lists) < 6:
        return False, "could not parse KEXINIT"
    kex, enc_c2s, enc_s2c = lists[0], lists[2], lists[3]
    mac_c2s, mac_s2c = lists[4], lists[5]
    if "kex-strict-s-v00@openssh.com" in kex:
        return False, "strict KEX supported (patched against Terrapin)"
    ciphers = enc_c2s + enc_s2c
    macs = mac_c2s + mac_s2c
    chacha = any("chacha20-poly1305" in c for c in ciphers)
    cbc_etm = any(c.endswith("-cbc") for c in ciphers) and \
        any(m.endswith("-etm@openssh.com") for m in macs)
    if chacha or cbc_etm:
        reason = "ChaCha20-Poly1305" if chacha else "CBC-EtM"
        return True, f"affected cipher offered ({reason}), no strict KEX"
    return False, "no affected cipher offered"


async def _read_kexinit(host: str, port: int, timeout: float) -> bytes | None:
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout)
    except (OSError, asyncio.TimeoutError):
        return None
    try:
        writer.write(b"SSH-2.0-PortoScan_verify\r\n")
        await writer.drain()
        # consume banner/ident line(s) until the server's SSH- identification
        for _ in range(5):
            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
            if not line:
                return None
            if line.startswith(b"SSH-"):
                break
        # read binary packets until SSH_MSG_KEXINIT (type 20)
        for _ in range(4):
            header = await asyncio.wait_for(reader.readexactly(4), timeout=timeout)
            packet_len = int.from_bytes(header, "big")
            if not 1 <= packet_len <= 35000:
                return None
            chunk = await asyncio.wait_for(reader.readexactly(packet_len), timeout=timeout)
            padding = chunk[0]
            payload = chunk[1:len(chunk) - padding]
            if payload and payload[0] == 20:
                return payload
    except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError):
        return None
    finally:
        writer.close()
        with contextlib.suppress(OSError):
            await writer.wait_closed()
    return None


async def confirm_terrapin(host: str, port: int,
                           timeout: float = 4.0) -> Finding | None:
    payload = await _read_kexinit(host, port, timeout)
    if payload is None:
        return None
    lists = parse_kexinit(payload)
    vulnerable, reason = terrapin_verdict(lists)
    if vulnerable:
        return Finding("medium", host, port, "ssh",
                       f"CVE-2023-48795 Terrapin CONFIRMED: {reason}",
                       evidence=reason, confirmed=True)
    return Finding("low", host, port, "ssh",
                   f"CVE-2023-48795 Terrapin not exploitable: {reason}",
                   evidence=reason, confirmed=True)
