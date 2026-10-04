"""Check web ports for *exposed* sensitive paths. Reporting-only.

PRIVACY GUARANTEE: this probes a fixed list of well-known sensitive paths and
reports only (path, HTTP status, a yes/no "looks like <kind>" classification).
It NEVER stores, logs, returns, or writes the response body. The point is to
tell the owner "you have leaked this" -- not to collect the secret.

Only runs against the open ports of hosts already in the user's scan scope.
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import ssl
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from portoscan.compliance import Finding

if TYPE_CHECKING:
    from portoscan.scan import Result

_WEB_PORTS = {80, 443, 591, 3000, 5000, 8000, 8008, 8080, 8443, 8888, 9443}
_TLS_PORTS = {443, 8443, 9443, 5986}


def _looks_env(head: bytes) -> bool:
    text = head[:512].decode("utf-8", "replace")
    return bool(re.search(r"(?m)^[A-Z][A-Z0-9_]{2,}=", text)) or \
        any(k in text for k in ("SECRET", "API_KEY", "PASSWORD", "TOKEN", "DB_"))


def _looks_git(head: bytes) -> bool:
    text = head[:256].decode("utf-8", "replace")
    return "[core]" in text or "repositoryformatversion" in text


def _looks_aws(head: bytes) -> bool:
    return b"aws_access_key_id" in head[:256].lower()


def _looks_apache_status(head: bytes) -> bool:
    return b"Apache Server Status" in head[:512]


def _looks_htpasswd(head: bytes) -> bool:
    return bool(re.search(rb"(?m)^[A-Za-z0-9_.-]+:\$?[0-9a-zA-Z$./]+", head[:256]))


@dataclass(frozen=True, slots=True)
class _Probe:
    path: str
    kind: str
    severity: str
    signature: Callable[[bytes], bool]


PROBES: tuple[_Probe, ...] = (
    _Probe("/.env", "env file", "high", _looks_env),
    _Probe("/.git/config", "git config", "high", _looks_git),
    _Probe("/.aws/credentials", "AWS credentials", "high", _looks_aws),
    _Probe("/.htpasswd", "htpasswd", "high", _looks_htpasswd),
    _Probe("/server-status", "Apache status", "medium", _looks_apache_status),
    _Probe("/config.php.bak", "PHP config backup", "high",
           lambda h: b"<?php" in h[:256]),
    _Probe("/.env.local", "env file", "high", _looks_env),
)


async def _fetch_head(host: str, port: int, path: str, *, tls: bool,
                      timeout: float) -> tuple[int, bytes] | None:
    """Return (status_code, first<=1KB of body) or None. The body is used only
    to classify and is discarded by the caller -- never persisted."""
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
        raw = await asyncio.wait_for(reader.read(2048), timeout=timeout)
    except (OSError, ssl.SSLError, asyncio.TimeoutError):
        return None
    finally:
        writer.close()
        with contextlib.suppress(OSError, ssl.SSLError):
            await writer.wait_closed()
    if not raw:
        return None
    head, _, body = raw.partition(b"\r\n\r\n")
    status_line = head.split(b"\r\n", 1)[0]
    try:
        status = int(status_line.split()[1])
    except (ValueError, IndexError):
        return None
    return status, body


async def check_endpoint(host: str, port: int, *, tls: bool,
                         timeout: float = 3.0) -> list[Finding]:
    findings: list[Finding] = []
    for probe in PROBES:
        result = await _fetch_head(host, port, probe.path, tls=tls, timeout=timeout)
        if result is None:
            continue
        status, body = result
        # Only a 200 whose content matches the signature counts as "exposed".
        if status == 200 and probe.signature(body):
            findings.append(Finding(
                probe.severity, host, port, "http",
                f"{probe.path} exposed (HTTP 200, looks like {probe.kind})"))
        # body is discarded here; nothing is stored or logged.
    return findings


def web_endpoints(results: Sequence[Result]) -> list[tuple[str, int, bool]]:
    """Distinct (host, port, tls) open web endpoints worth probing."""
    seen: set[tuple[str, int, bool]] = set()
    out: list[tuple[str, int, bool]] = []
    for r in results:
        if r.state != "open":
            continue
        service = (r.service or "").lower()
        is_web = r.port in _WEB_PORTS or "http" in service
        if not is_web:
            continue
        key = (r.host, r.port, r.port in _TLS_PORTS or "https" in service)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


async def scan(results: Sequence[Result], *, timeout: float = 3.0,
               concurrency: int = 20) -> list[Finding]:
    endpoints = web_endpoints(results)
    sem = asyncio.Semaphore(concurrency)
    findings: list[Finding] = []

    async def run(host: str, port: int, tls: bool) -> None:
        async with sem:
            findings.extend(await check_endpoint(host, port, tls=tls, timeout=timeout))

    await asyncio.gather(*(run(h, p, tls) for h, p, tls in endpoints))
    findings.sort(key=lambda f: (f.severity, f.host, f.port))
    return findings
