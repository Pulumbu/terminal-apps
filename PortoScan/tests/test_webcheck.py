import asyncio

from portoscan.scan import Result
from portoscan.webcheck import PROBES, check_endpoint, scan, web_endpoints


async def _server(routes):
    async def handler(reader, writer):
        req = await reader.read(1024)
        try:
            path = req.split(b"\r\n", 1)[0].split()[1].decode()
        except IndexError:
            path = "/"
        body = routes.get(path)
        if body is None:
            writer.write(b"HTTP/1.0 404 Not Found\r\n\r\nnope")
        else:
            writer.write(b"HTTP/1.0 200 OK\r\n\r\n" + body)
        await writer.drain()
        writer.close()
    return await asyncio.start_server(handler, "127.0.0.1", 0)


async def test_detects_exposed_env_and_git_only_presence():
    server = await _server({
        "/.env": b"SECRET_KEY=abc\nDB_PASSWORD=hunter2\n",
        "/.git/config": b"[core]\n\trepositoryformatversion = 0\n",
    })
    port = server.sockets[0].getsockname()[1]
    async with server:
        findings = await check_endpoint("127.0.0.1", port, tls=False, timeout=1.0)
    paths = {f.message.split()[0] for f in findings}
    assert "/.env" in paths and "/.git/config" in paths
    # the finding carries only a classification, never the secret body
    for f in findings:
        assert "hunter2" not in f.message
        assert "SECRET_KEY" not in f.message
        assert "looks like" in f.message


async def test_200_without_signature_is_not_flagged():
    # an SPA that returns 200 + HTML for every path must NOT be flagged
    server = await _server({p.path: b"<!doctype html><html>app</html>" for p in PROBES})
    port = server.sockets[0].getsockname()[1]
    async with server:
        findings = await check_endpoint("127.0.0.1", port, tls=False, timeout=1.0)
    assert findings == []


def test_web_endpoints_filters_open_web_ports():
    results = [
        Result("10.0.0.1", 80, "open", 1.0, "http", ""),
        Result("10.0.0.1", 22, "open", 1.0, "ssh", ""),        # not web
        Result("10.0.0.2", 443, "open", 1.0, "https", ""),     # tls
        Result("10.0.0.3", 8080, "closed", 1.0, "http", ""),   # closed
    ]
    endpoints = web_endpoints(results)
    assert ("10.0.0.1", 80, False) in endpoints
    assert ("10.0.0.2", 443, True) in endpoints
    assert all(host != "10.0.0.3" for host, _, _ in endpoints)
    assert all(port != 22 for _, port, _ in endpoints)


async def test_scan_over_results():
    server = await _server({"/.env": b"API_KEY=zzz\n"})
    port = server.sockets[0].getsockname()[1]
    async with server:
        findings = await scan([Result("127.0.0.1", port, "open", 1.0, "http", "")],
                              timeout=1.0)
    assert len(findings) == 1 and findings[0].severity == "high"
