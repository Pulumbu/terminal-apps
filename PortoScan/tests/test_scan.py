import asyncio

from portoscan.export import to_csv, to_json
from portoscan.scan import Progress, Result, scan, service_name


async def _free_port() -> int:
    server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()
    return port


async def test_open_detection_and_banner():
    async def handle(reader, writer):
        writer.write(b"PortoScan-Test/1.0\r\n")
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    async with server:
        results = await scan(["127.0.0.1"], [port], timeout=0.5, grab=True)
    assert results[0].state == "open"
    assert "PortoScan-Test" in results[0].banner


async def test_closed_detection():
    port = await _free_port()  # nothing is listening here now
    results = await scan(["127.0.0.1"], [port], timeout=0.5, grab=False)
    assert results[0].state == "closed"


async def test_filtered_on_timeout():
    # 10.255.255.1 is non-routable in most environments -> connect times out.
    results = await scan(["10.255.255.1"], [9], timeout=0.2, grab=False, adaptive=False)
    assert results[0].state in ("filtered", "error")


async def test_concurrency_never_exceeds_limit():
    peak = 0
    live = 0
    lock = asyncio.Lock()

    import portoscan.scan as scan_mod
    original = scan_mod._scan_tcp

    async def tracked(host, port, *, timeout, grab):
        nonlocal peak, live
        async with lock:
            live += 1
            peak = max(peak, live)
        await asyncio.sleep(0.01)
        async with lock:
            live -= 1
        return Result(host, port, "closed", 1.0, "", "")

    scan_mod._scan_tcp = tracked
    try:
        await scan(["127.0.0.1"], list(range(2000, 2100)), concurrency=10,
                   grab=False, adaptive=False)
    finally:
        scan_mod._scan_tcp = original
    assert peak <= 10


async def test_cancellation_stops_early():
    flag = {"cancel": False}
    import portoscan.scan as scan_mod
    original = scan_mod._scan_tcp

    async def slow(host, port, *, timeout, grab):
        await asyncio.sleep(0.02)
        flag["cancel"] = True  # cancel after the first result returns
        return Result(host, port, "closed", 1.0, "", "")

    scan_mod._scan_tcp = slow
    try:
        results = await scan(["127.0.0.1"], list(range(3000, 3200)),
                             concurrency=1, grab=False,
                             should_cancel=lambda: flag["cancel"], adaptive=False)
    finally:
        scan_mod._scan_tcp = original
    assert len(results) < 200


def test_progress_accounting():
    progress = Progress(total=3)
    progress.record("open")
    progress.record("closed")
    progress.record("filtered")
    assert progress.done == 3 and progress.open == 1 and progress.filtered == 1


def test_service_name_known_port():
    assert service_name(443) == "https"


def test_export_round_trips():
    results = [Result("127.0.0.1", 80, "open", 1.2, "http", "Server: x")]
    csv_text = to_csv(results)
    assert "127.0.0.1,80,open,http,1.2,Server: x" in csv_text
    import json
    rows = json.loads(to_json(results))
    assert rows[0]["port"] == 80 and rows[0]["state"] == "open"


async def test_autotune_lowers_concurrency_under_high_filtered_rate():
    import asyncio

    import portoscan.scan as scan_mod
    from portoscan.scan import Result, scan

    original = scan_mod._scan_tcp

    async def all_filtered(host, port, *, timeout, grab):
        await asyncio.sleep(0)
        return Result(host, port, "filtered", 1.0, "", "")

    scan_mod._scan_tcp = all_filtered
    seen_min = [10_000]

    def on_progress(progress):
        seen_min[0] = min(seen_min[0], progress.concurrency)

    try:
        await scan(["127.0.0.1"], list(range(1, 301)), concurrency=100,
                   grab=False, adaptive=True, on_progress=on_progress)
    finally:
        scan_mod._scan_tcp = original
    assert seen_min[0] < 100  # auto-tune backed the limit off


async def test_progress_exposes_inflight_and_concurrency():
    from portoscan.scan import scan
    captured = {}

    def on_progress(progress):
        captured["concurrency"] = progress.concurrency
        captured["inflight"] = progress.inflight

    await scan(["127.0.0.1"], [40000, 40001], concurrency=50, grab=False,
               adaptive=False, on_progress=on_progress)
    assert captured["concurrency"] == 50
    assert captured["inflight"] >= 0
