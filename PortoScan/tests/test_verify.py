import asyncio
import os

from portoscan.verify import (
    confirm_exposure,
    confirm_terrapin,
    parse_kexinit,
    redact_evidence,
    terrapin_verdict,
)


def test_redact_masks_values_keeps_keys():
    body = b"AWS_ACCESS_KEY_ID=AKIAEXAMPLE\nDB_PASSWORD=sup3rs3cret\nDEBUG=1\n"
    ev = redact_evidence("env file", body)
    assert "AWS_ACCESS_KEY_ID" in ev and "DB_PASSWORD" in ev
    assert "AKIAEXAMPLE" not in ev and "sup3rs3cret" not in ev
    assert "redacted" in ev and "sha256" in ev


def test_terrapin_verdicts():
    base = [["curve25519-sha256"], ["ssh-ed25519"]]
    vuln = base + [["chacha20-poly1305@openssh.com"]] * 2 + [["hmac-sha2-256"]] * 2
    assert terrapin_verdict(vuln)[0] is True
    patched = [["curve25519-sha256", "kex-strict-s-v00@openssh.com"], ["ssh-ed25519"]] \
        + [["chacha20-poly1305@openssh.com"]] * 2 + [["hmac-sha2-256"]] * 2
    assert terrapin_verdict(patched)[0] is False
    safe = base + [["aes256-gcm@openssh.com"]] * 2 + [["hmac-sha2-256"]] * 2
    assert terrapin_verdict(safe)[0] is False
    cbc_etm = base + [["aes256-cbc"]] * 2 + [["hmac-sha2-256-etm@openssh.com"]] * 2
    assert terrapin_verdict(cbc_etm)[0] is True


def _namelist(items):
    b = ",".join(items).encode()
    return len(b).to_bytes(4, "big") + b


def _kexinit_packet(kex, enc, mac):
    payload = bytes([20]) + os.urandom(16)
    payload += _namelist(kex) + _namelist(["ssh-ed25519"])
    payload += _namelist(enc) + _namelist(enc) + _namelist(mac) + _namelist(mac)
    payload += _namelist(["none"]) + _namelist(["none"]) + _namelist([]) + _namelist([])
    payload += b"\x00" + b"\x00\x00\x00\x00"
    pad = 8 - ((len(payload) + 5) % 8)
    if pad < 4:
        pad += 8
    packet = bytes([pad]) + payload + os.urandom(pad)
    return len(packet).to_bytes(4, "big") + packet


def test_parse_kexinit_roundtrip():
    payload = _kexinit_packet(["curve25519-sha256"], ["chacha20-poly1305@openssh.com"],
                              ["hmac-sha2-256"])
    # strip the 4-byte length + 1-byte padding to get the payload the parser wants
    length = int.from_bytes(payload[:4], "big")
    chunk = payload[4:4 + length]
    pad = chunk[0]
    parsed = parse_kexinit(chunk[1:len(chunk) - pad])
    assert parsed[0] == ["curve25519-sha256"]
    assert parsed[2] == ["chacha20-poly1305@openssh.com"]


async def _fake_ssh(kex, enc, mac):
    async def handler(reader, writer):
        writer.write(b"SSH-2.0-FakeSSH_1.0\r\n")
        writer.write(_kexinit_packet(kex, enc, mac))
        await writer.drain()
        await asyncio.sleep(0.05)
        writer.close()
    return await asyncio.start_server(handler, "127.0.0.1", 0)


async def test_confirm_terrapin_live_vulnerable():
    server = await _fake_ssh(["curve25519-sha256"],
                             ["chacha20-poly1305@openssh.com"], ["hmac-sha2-256"])
    port = server.sockets[0].getsockname()[1]
    async with server:
        finding = await confirm_terrapin("127.0.0.1", port, timeout=2.0)
    assert finding is not None and finding.confirmed
    assert "CONFIRMED" in finding.message and finding.severity == "medium"


async def test_confirm_terrapin_live_patched():
    server = await _fake_ssh(["curve25519-sha256", "kex-strict-s-v00@openssh.com"],
                             ["chacha20-poly1305@openssh.com"], ["hmac-sha2-256"])
    port = server.sockets[0].getsockname()[1]
    async with server:
        finding = await confirm_terrapin("127.0.0.1", port, timeout=2.0)
    assert finding is not None and finding.confirmed
    assert "not exploitable" in finding.message and finding.severity == "low"


async def test_confirm_exposure_confirms_and_redacts():
    async def handler(reader, writer):
        await reader.read(1024)
        writer.write(b"HTTP/1.0 200 OK\r\n\r\nAPI_KEY=live-secret-xyz\nDB_PASSWORD=p@ss\n")
        await writer.drain()
        writer.close()
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    async with server:
        conf = await confirm_exposure("127.0.0.1", port, "/.env", "env file", "high",
                                      tls=False, timeout=2.0)
    assert conf.confirmed is True
    assert "API_KEY" in conf.evidence
    assert "live-secret-xyz" not in conf.evidence and "p@ss" not in conf.evidence


async def test_confirm_exposure_rejects_spa_200():
    async def handler(reader, writer):
        await reader.read(1024)
        writer.write(b"HTTP/1.0 200 OK\r\n\r\n<!doctype html><html>app</html>")
        await writer.drain()
        writer.close()
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    async with server:
        conf = await confirm_exposure("127.0.0.1", port, "/.env", "env file", "high",
                                      tls=False, timeout=2.0)
    assert conf.confirmed is False
    assert "not confirmed" in conf.evidence
