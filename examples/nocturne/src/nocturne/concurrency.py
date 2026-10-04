from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")

CPU_WORKERS = max(1, (os.cpu_count() or 2) - 1)


# --- 1. bounded async fan-out -------------------------------------------------
async def gather_bounded(
    tasks: Sequence[Callable[[], Awaitable[R]]], limit: int = 8
) -> list[R | BaseException]:
    sem = asyncio.Semaphore(limit)

    async def run(factory: Callable[[], Awaitable[R]]) -> R:
        async with sem:
            return await factory()

    return await asyncio.gather(*(run(t) for t in tasks), return_exceptions=True)


# --- 2. streaming results as they complete ------------------------------------
async def as_completed_stream(
    coros: Iterable[Awaitable[R]],
) -> AsyncIterator[R | BaseException]:
    pending = {asyncio.ensure_future(c) for c in coros}
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            try:
                yield task.result()
            except BaseException as error:
                yield error


# --- 3. CPU work off the event loop -------------------------------------------
_process_pool: ProcessPoolExecutor | None = None


def process_pool() -> ProcessPoolExecutor:
    global _process_pool
    if _process_pool is None:
        _process_pool = ProcessPoolExecutor(max_workers=CPU_WORKERS)
    return _process_pool


def shutdown_process_pool() -> None:
    global _process_pool
    if _process_pool is not None:
        _process_pool.shutdown(cancel_futures=True)
        _process_pool = None


async def run_cpu(fn: Callable[..., R], *args: object) -> R:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(process_pool(), fn, *args)


# --- 4. coalescing / debounce -------------------------------------------------
class Debouncer:
    """Collapse rapid calls into one, after `delay` seconds of quiet."""

    def __init__(self, delay: float) -> None:
        self.delay = delay
        self._handle: asyncio.TimerHandle | None = None

    def __call__(self, fn: Callable[[], None]) -> None:
        if self._handle is not None:
            self._handle.cancel()
        loop = asyncio.get_running_loop()
        self._handle = loop.call_later(self.delay, fn)

    def cancel(self) -> None:
        if self._handle is not None:
            self._handle.cancel()
            self._handle = None


# --- 5. cancellable, cooperative thread work ----------------------------------
@dataclass
class Cancellation:
    event: threading.Event

    def __bool__(self) -> bool:
        return self.event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.event.is_set():
            raise asyncio.CancelledError


def chunked_scan(root: str, cancel: Cancellation, chunk: int = 256) -> Iterable[list[str]]:
    batch: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        cancel.raise_if_cancelled()
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            batch.append(os.path.join(dirpath, name))
            if len(batch) >= chunk:
                yield batch
                batch = []
    if batch:
        yield batch


# --- 6. backpressured producer/consumer ---------------------------------------
async def pipeline(
    produce: Callable[[asyncio.Queue[T | None]], Awaitable[None]],
    consume: Callable[[T], Awaitable[None]],
    *,
    maxsize: int = 64,
    workers: int = 4,
) -> None:
    queue: asyncio.Queue[T | None] = asyncio.Queue(maxsize=maxsize)

    async def worker() -> None:
        while True:
            item = await queue.get()
            try:
                if item is None:
                    return
                await consume(item)
            finally:
                queue.task_done()

    consumers = [asyncio.create_task(worker()) for _ in range(workers)]
    try:
        await produce(queue)
        for _ in consumers:
            await queue.put(None)
        await asyncio.gather(*consumers)
    finally:
        for task in consumers:
            task.cancel()


# --- 7. single-instance lock --------------------------------------------------
class SingleInstance:
    def __init__(self, lock_path: str) -> None:
        self.lock_path = lock_path
        self._handle = None

    def __enter__(self) -> SingleInstance:
        self._handle = open(self.lock_path, "a+b")
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self._handle.close()
            self._handle = None
            raise RuntimeError("another instance is already running") from error
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None


def fib(n: int) -> int:
    return n if n < 2 else fib(n - 1) + fib(n - 2)
