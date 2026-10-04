"""Concurrency tests: bounds, cancellation, debounce, backpressure."""

import asyncio
import os
import sys
import threading

import pytest

from nocturne.concurrency import (
    Cancellation,
    Debouncer,
    as_completed_stream,
    chunked_scan,
    fib,
    gather_bounded,
    pipeline,
    run_cpu,
    shutdown_process_pool,
)


async def test_gather_bounded_respects_the_limit():
    live = peak = 0
    lock = asyncio.Lock()

    async def job(index: int) -> int:
        nonlocal live, peak
        async with lock:
            live += 1
            peak = max(peak, live)
        await asyncio.sleep(0.01)
        async with lock:
            live -= 1
        return index * 2

    results = await gather_bounded([lambda i=i: job(i) for i in range(20)], limit=4)
    assert results == [i * 2 for i in range(20)]
    assert peak <= 4


async def test_as_completed_stream_yields_in_completion_order():
    async def slow(n: int) -> int:
        await asyncio.sleep(n / 100)
        if n == 2:
            raise ValueError("boom")
        return n

    seen = [item async for item in as_completed_stream([slow(3), slow(1), slow(2)])]
    assert [item for item in seen if not isinstance(item, BaseException)] == [1, 3]
    assert any(isinstance(item, ValueError) for item in seen)


async def test_debouncer_collapses_a_burst():
    calls: list[int] = []
    debounce = Debouncer(0.05)
    for _ in range(10):
        debounce(lambda: calls.append(1))
        await asyncio.sleep(0.005)
    await asyncio.sleep(0.12)
    assert calls == [1]


async def test_pipeline_applies_backpressure_and_loses_nothing():
    consumed: list[int] = []

    async def produce(queue):
        for index in range(100):
            await queue.put(index)

    async def consume(item):
        await asyncio.sleep(0)
        consumed.append(item)

    await pipeline(produce, consume, maxsize=8, workers=5)
    assert sorted(consumed) == list(range(100))


def test_chunked_scan_is_cancellable():
    cancel = Cancellation(threading.Event())
    for index, _batch in enumerate(
        chunked_scan(os.path.dirname(sys.executable), cancel, chunk=4)
    ):
        if index == 1:
            cancel.event.set()
            break
    with pytest.raises(asyncio.CancelledError):
        list(chunked_scan(os.path.dirname(sys.executable), cancel, chunk=4))


async def test_cpu_work_runs_in_a_process_pool():
    try:
        results = await asyncio.gather(*(run_cpu(fib, 20) for _ in range(3)))
        assert results == [6765] * 3
    finally:
        shutdown_process_pool()
