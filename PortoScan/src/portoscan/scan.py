"""The async TCP-connect scan engine. Pure asyncio; imports no Textual.

Design and verification: see PORTOSCAN.md section 4. This is a TCP *connect*
scan (no raw sockets, no privileges), which is correct and cross-platform: a
completed handshake unambiguously means the port is open.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
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

_HTTP_PORTS = {80, 591, 8000, 8008, 8080, 8888}


def service_name(port: int) -> str:
    try:
        return socket.getservbyport(port, "tcp")
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
        setattr(self, state, getattr(self, state) + 1)


async def _scan_one(
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
        banner = await _grab(reader, writer, port)
    writer.close()
    with contextlib.suppress(OSError):
        await writer.wait_closed()
    return Result(host, port, "open", (time.perf_counter() - start) * 1000,
                  service_name(port), banner)


async def _grab(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                port: int) -> str:
    try:
        if port in _HTTP_PORTS:
            writer.write(b"HEAD / HTTP/1.0\r\n\r\n")
            await writer.drain()
        data = await asyncio.wait_for(reader.read(256), timeout=0.6)
    except (asyncio.TimeoutError, OSError):
        return ""
    if not data:
        return ""
    text = data.decode("utf-8", "replace").strip()
    return text.splitlines()[0][:200] if text else ""


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
) -> list[Result]:
    """Scan ``hosts`` x ``ports``.

    ``on_result`` / ``on_progress`` are called from this coroutine's loop as the
    scan runs -- in a Textual app, call them via ``call_from_thread`` or run the
    scan as an async worker so they land on the UI loop.

    ``should_cancel`` is polled cooperatively; when it returns True the scan
    stops promptly and returns the results gathered so far.

    ``adaptive`` applies nmap-style backoff: when the recent filtered-rate climbs
    the effective concurrency is cut, and it recovers when things clear up.
    """
    progress = Progress(total=len(hosts) * len(ports))
    results: list[Result] = []
    sem = asyncio.Semaphore(max(1, concurrency))

    # Adaptive backoff adjusts the inter-connection delay rather than resizing
    # the semaphore: when the recent filtered-rate climbs we slow down (be
    # polite / avoid false negatives), and speed back up when it clears. This
    # cannot deadlock -- unlike dynamically shrinking a semaphore.
    base_delay = (1.0 / rate) if rate > 0 else 0.0
    state = {"delay": base_delay}
    window: list[bool] = []

    def adjust(was_filtered: bool) -> None:
        window.append(was_filtered)
        if len(window) < 50:
            return
        filtered_rate = sum(window) / len(window)
        window.clear()
        if filtered_rate > 0.5:
            state["delay"] = min(max(state["delay"] * 2, 0.01), 0.5)
        elif filtered_rate < 0.1:
            state["delay"] = base_delay if state["delay"] <= 0.01 else state["delay"] / 2

    async def run(host: str, port: int) -> None:
        if should_cancel is not None and should_cancel():
            return
        async with sem:
            if should_cancel is not None and should_cancel():
                return
            if state["delay"]:
                await asyncio.sleep(state["delay"])
            result = await _scan_one(host, port, timeout=timeout, grab=grab)
        results.append(result)
        progress.record(result.state)
        if adaptive:
            adjust(result.state == "filtered")
        if on_result is not None:
            on_result(result, progress)
        if on_progress is not None:
            on_progress(progress)

    tasks = [
        asyncio.create_task(run(host, port))
        for host in hosts
        for port in ports
    ]
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
