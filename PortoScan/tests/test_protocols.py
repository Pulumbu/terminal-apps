"""TCP service hints, UDP scanning, and IPv6 handling."""

import asyncio
import socket

import pytest

from portoscan.authorization import classify
from portoscan.scan import scan, service_name
from portoscan.targets import expand


# --- service / version hints (feature 6) ------------------------------------
async def test_http_server_header_hint():
    async def handler(reader, writer):
        await reader.read(256)
        writer.write(b"HTTP/1.0 200 OK\r\nServer: PortoScan-nginx/9.9\r\n\r\n")
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handler, "127.0.0.1", 8080)
    async with server:
        results = await scan(["127.0.0.1"], [8080], grab=True, timeout=0.6,
                             adaptive=False)
    assert results[0].state == "open"
    assert results[0].banner == "HTTP PortoScan-nginx/9.9"


async def test_generic_banner_first_line():
    async def handler(reader, writer):
        writer.write(b"SSH-2.0-PortoScanSSH\r\nmore\r\n")
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    async with server:
        results = await scan(["127.0.0.1"], [port], grab=True, timeout=0.6,
                             adaptive=False)
    assert results[0].banner == "SSH-2.0-PortoScanSSH"


# --- UDP (feature 7) ---------------------------------------------------------
async def test_udp_closed_port():
    # Nothing listening -> ICMP port-unreachable -> closed (Linux loopback).
    results = await scan(["127.0.0.1"], [54999], protocol="udp", timeout=0.5,
                         adaptive=False)
    assert results[0].state in ("closed", "filtered")  # closed on Linux


async def test_udp_open_with_responder():
    class Echo(asyncio.DatagramProtocol):
        def connection_made(self, transport):
            self.transport = transport

        def datagram_received(self, data, addr):
            self.transport.sendto(b"pong", addr)

    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(Echo, local_addr=("127.0.0.1", 0))
    port = transport.get_extra_info("socket").getsockname()[1]
    try:
        results = await scan(["127.0.0.1"], [port], protocol="udp", timeout=0.6,
                             adaptive=False)
    finally:
        transport.close()
    assert results[0].state == "open"
    assert results[0].banner == "pong"


def test_udp_service_name():
    assert service_name(53, "udp") == "domain"


# --- IPv6 end-to-end (feature 8) --------------------------------------------
def test_ipv6_address_parsed():
    result = expand("::1\n2001:db8::1")
    assert result.hosts == ["::1", "2001:db8::1"] and not result.errors


def test_ipv6_cidr_expansion_and_cap():
    result = expand("2001:db8::/120", max_hosts=10)
    assert result.truncated and len(result.hosts) == 10
    # IPv6 .hosts() starts at ::1 (the all-zeros anycast address is excluded)
    assert result.hosts[0] == "2001:db8::1"


def test_ipv6_classification():
    # 2606:4700:4700::1111 is a genuine global address; 2001:db8:: is a
    # documentation prefix Python treats as private, so use the former here.
    report = classify(["::1", "fe80::1", "2606:4700:4700::1111", "fd00::1"])
    assert report.loopback == 1          # ::1
    assert report.private >= 2           # fe80:: (link-local) + fd00:: (ULA)
    assert report.public == 1            # 2606:4700:4700::1111 (global)


_HAS_V6 = False
try:
    _s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    _s.bind(("::1", 0))
    _s.close()
    _HAS_V6 = True
except OSError:
    pass


@pytest.mark.skipif(not _HAS_V6, reason="no IPv6 loopback in this environment")
async def test_ipv6_tcp_scan():
    async def handler(reader, writer):
        writer.close()

    server = await asyncio.start_server(handler, "::1", 0)
    port = server.sockets[0].getsockname()[1]
    async with server:
        results = await scan(["::1"], [port], grab=False, timeout=0.6, adaptive=False)
    assert results[0].state == "open"
