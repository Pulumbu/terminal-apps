"""The async TCP-connect scan engine. Pure asyncio; imports no Textual.

Design and verification: see PORTOSCAN.md section 4. This is a TCP *connect*
scan (no raw sockets, no privileges), which is correct and cross-platform: a
completed handshake unambiguously means the port is open.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
import ssl
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

State = str  # "open" | "closed" | "filtered" | "error"


@dataclass(frozen=True, slots=True)
class Result:
    host: str
    port: int
    state: State
    latency_ms: float
    service: str
    banner: str


@dataclass(frozen=True, slots=True)
class RatePreset:
    key: str
    label: str
    concurrency: int
    timeout: float


PRESETS: tuple[RatePreset, ...] = (
    RatePreset("localhost", "Localhost", 1000, 0.3),
    RatePreset("lan", "LAN", 500, 1.0),
    RatePreset("internet", "Internet (authorized)", 200, 2.5),
)
PRESET_BY_KEY = {preset.key: preset for preset in PRESETS}

_HTTP_PORTS = {80, 591, 8000, 8008, 8080, 8888, 5000, 3000}
_TLS_PORTS = {443, 465, 563, 636, 989, 990, 993, 995, 8443, 9443, 5986}


def service_name(port: int, protocol: str = "tcp") -> str:
    try:
        return socket.getservbyport(port, protocol)
    except OSError:
        return ""


@dataclass
class Progress:
    total: int
    done: int = 0
    open: int = 0
    closed: int = 0
    filtered: int = 0
    errors: int = 0
    inflight: int = 0           # connections in progress right now
    concurrency: int = 0        # current auto-tuned limit
    started: float = field(default_factory=time.monotonic)

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started

    @property
    def rate(self) -> float:
        elapsed = self.elapsed
        return self.done / elapsed if elapsed > 0 else 0.0

    @property
    def eta(self) -> float:
        rate = self.rate
        return (self.total - self.done) / rate if rate > 0 else 0.0

    def record(self, state: State) -> None:
        self.done += 1
        if hasattr(self, state):
            setattr(self, state, getattr(self, state) + 1)


async def _scan_tcp(
    host: str, port: int, *, timeout: float, grab: bool
) -> Result:
    start = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
    except asyncio.TimeoutError:
        return Result(host, port, "filtered", timeout * 1000, service_name(port), "")
    except (ConnectionRefusedError, ConnectionResetError):
        return Result(host, port, "closed", (time.perf_counter() - start) * 1000,
                      service_name(port), "")
    except OSError as error:
        # unreachable host, DNS failure, etc. -- report, don't guess "closed"
        state = "closed" if error.errno in (111,) else "error"
        return Result(host, port, state, (time.perf_counter() - start) * 1000,
                      service_name(port), "")

    banner = ""
    if grab:
        banner = await _grab(reader, writer, host, port, timeout)
    writer.close()
    with contextlib.suppress(OSError):
        await writer.wait_closed()
    return Result(host, port, "open", (time.perf_counter() - start) * 1000,
                  service_name(port), banner)


async def _grab(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                host: str, port: int, timeout: float) -> str:
    """Return a short service/version hint for an open TCP port."""
    if port in _TLS_PORTS:
        return await _tls_probe(host, port, timeout)
    try:
        if port in _HTTP_PORTS:
            writer.write(f"HEAD / HTTP/1.0\r\nHost: {host}\r\n\r\n".encode())
            await writer.drain()
        data = await asyncio.wait_for(reader.read(512), timeout=min(0.8, timeout))
    except (asyncio.TimeoutError, OSError):
        return ""
    if not data:
        return ""
    text = data.decode("utf-8", "replace")
    if port in _HTTP_PORTS:
        return _http_hint(text)
    return text.strip().splitlines()[0][:200] if text.strip() else ""


def _http_hint(text: str) -> str:
    server = ""
    status = ""
    for line in text.splitlines():
        low = line.lower()
        if low.startswith("server:"):
            server = line.split(":", 1)[1].strip()
        elif line.startswith("HTTP/") and not status:
            status = line.strip()
    if server:
        return f"HTTP {server}"[:200]
    return status[:200]


async def _tls_probe(host: str, port: int, timeout: float) -> str:
    """Open a TLS connection and report protocol + cipher (+ cert CN if possible).

    Does NOT validate the certificate -- the point is to fingerprint an unknown
    service, not to trust it.
    """
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=context,
                                    server_hostname=host if _is_name(host) else None),
            timeout=timeout,
        )
    except (asyncio.TimeoutError, ssl.SSLError, OSError):
        return "TLS"
    parts = ["TLS"]
    ssl_object = writer.get_extra_info("ssl_object")
    if ssl_object is not None:
        version = ssl_object.version()
        if version:
            parts.append(version)
        cipher = ssl_object.cipher()
        if cipher:
            parts.append(cipher[0])
        cn = _cert_cn(ssl_object)
        if cn:
            parts.append(f"CN={cn}")
    writer.close()
    with contextlib.suppress(OSError, ssl.SSLError):
        await writer.wait_closed()
    return " ".join(parts)[:200]


def _is_name(host: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET, host)
        return False
    except OSError:
        pass
    try:
        socket.inet_pton(socket.AF_INET6, host)
        return False
    except OSError:
        return True


def _cert_cn(ssl_object: ssl.SSLObject) -> str:
    """Best-effort certificate common name, if a parser is available."""
    try:
        der = ssl_object.getpeercert(binary_form=True)
    except (ValueError, ssl.SSLError):
        return ""
    if not der:
        return ""
    try:
        from cryptography import x509  # optional dependency
        from cryptography.x509.oid import NameOID
        cert = x509.load_der_x509_certificate(der)
        attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        return attrs[0].value if attrs else ""
    except Exception:
        return ""


async def _scan_udp(host: str, port: int, *, timeout: float) -> Result:
    """A connectionless UDP probe.

    open          -> a datagram came back
    closed        -> the OS reported ICMP port-unreachable (ConnectionRefused)
    filtered      -> no response at all (this is nmap's 'open|filtered')
    """
    loop = asyncio.get_running_loop()
    start = time.perf_counter()

    class _Proto(asyncio.DatagramProtocol):
        def __init__(self) -> None:
            self.data: bytes | None = None
            self.error: Exception | None = None

        def datagram_received(self, data: bytes, addr: object) -> None:
            self.data = data

        def error_received(self, exc: Exception) -> None:
            self.error = exc

    try:
        transport, proto = await loop.create_datagram_endpoint(
            _Proto, remote_addr=(host, port))
    except OSError as error:
        return Result(host, port, "error", 0.0, service_name(port, "udp"), str(error)[:80])
    try:
        transport.sendto(b"\x00")
        await asyncio.sleep(timeout)
    finally:
        transport.close()
    latency = (time.perf_counter() - start) * 1000
    if proto.data is not None:
        return Result(host, port, "open", latency, service_name(port, "udp"),
                      proto.data[:60].decode("utf-8", "replace").strip())
    if isinstance(proto.error, ConnectionRefusedError):
        return Result(host, port, "closed", latency, service_name(port, "udp"), "")
    return Result(host, port, "filtered", latency, service_name(port, "udp"),
                  "open|filtered")


async def scan(
    hosts: Sequence[str],
    ports: Sequence[int],
    *,
    concurrency: int = 500,
    timeout: float = 1.0,
    grab: bool = True,
    rate: float = 0.0,
    on_result: Callable[[Result, Progress], None] | None = None,
    on_progress: Callable[[Progress], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    adaptive: bool = True,
    pairs: Sequence[tuple[str, int]] | None = None,
    protocol: str = "tcp",
) -> list[Result]:
    """Scan ``hosts`` x ``ports``.

    ``on_result`` / ``on_progress`` are called from this coroutine's loop as the
    scan runs -- in a Textual app, call them via ``call_from_thread`` or run the
    scan as an async worker so they land on the UI loop.

    ``should_cancel`` is polled cooperatively; when it returns True the scan
    stops promptly and returns the results gathered so far.

    ``adaptive`` applies nmap-style backoff: when the recent filtered-rate climbs
    the effective concurrency is cut, and it recovers when things clear up.

    ``pairs`` scans an explicit list of (host, port) tuples instead of the
    ``hosts`` x ``ports`` cross product -- used by "re-scan open" to re-check
    exactly the endpoints that were open.
    """
    scan_pairs = list(pairs) if pairs is not None else [
        (host, port) for host in hosts for port in ports
    ]
    ceiling = max(1, concurrency)
    progress = Progress(total=len(scan_pairs), concurrency=ceiling)
    results: list[Result] = []
    delay = (1.0 / rate) if rate > 0 else 0.0

    # Deadlock-free dynamic concurrency: a Condition gate admits a worker only
    # while `inflight < target`. Auto-tune lowers `target` when the recent
    # filtered-rate climbs (be polite, avoid false negatives) and raises it back
    # toward the ceiling when things clear up. `target` is surfaced live as
    # Progress.concurrency so the UI can show it.
    cond = asyncio.Condition()
    gate = {"target": ceiling, "inflight": 0}
    window: list[bool] = []

    async def adjust(was_filtered: bool) -> None:
        window.append(was_filtered)
        if len(window) < 40:
            return
        filtered_rate = sum(window) / len(window)
        window.clear()
        async with cond:
            if adaptive and filtered_rate > 0.5:
                gate["target"] = max(1, gate["target"] // 2)
            elif adaptive and filtered_rate < 0.1 and gate["target"] < ceiling:
                gate["target"] = min(ceiling, gate["target"] + max(1, ceiling // 10))
            progress.concurrency = gate["target"]
            cond.notify_all()

    async def run(host: str, port: int) -> None:
        if should_cancel is not None and should_cancel():
            return
        async with cond:
            await cond.wait_for(
                lambda: gate["inflight"] < gate["target"]
                or (should_cancel is not None and should_cancel()))
            if should_cancel is not None and should_cancel():
                return
            gate["inflight"] += 1
            progress.inflight = gate["inflight"]
        try:
            if delay:
                await asyncio.sleep(delay)
            if protocol == "udp":
                result = await _scan_udp(host, port, timeout=timeout)
            else:
                result = await _scan_tcp(host, port, timeout=timeout, grab=grab)
        finally:
            async with cond:
                gate["inflight"] -= 1
                progress.inflight = gate["inflight"]
                cond.notify(1)
        results.append(result)
        progress.record(result.state)
        await adjust(result.state == "filtered")
        if on_result is not None:
            on_result(result, progress)
        if on_progress is not None:
            on_progress(progress)

    tasks = [asyncio.create_task(run(host, port)) for host, port in scan_pairs]
    try:
        for coro in asyncio.as_completed(tasks):
            await coro
            if should_cancel is not None and should_cancel():
                break
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    return results


def preview(hosts: Iterable[str], ports: Sequence[int]) -> tuple[int, int, int]:
    """Return (host_count, port_count, total_connections) for a dry run."""
    host_count = sum(1 for _ in hosts)
    return host_count, len(ports), host_count * len(ports)
