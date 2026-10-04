"""Behavioural tests through Pilot. Scans only 127.0.0.1 (this machine)."""

import asyncio

from textual.widgets import DataTable, Select, TextArea

from portoscan.app import PortoScan


async def _free_local_port() -> int:
    server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()
    return port


async def test_app_starts_and_builds_table():
    app = PortoScan()
    app.settings.authorized_ack = True
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        table = app.screen.query_one("#results", DataTable)
        assert table.columns  # columns were added


async def test_scope_banner_marks_public():
    app = PortoScan()
    app.settings.authorized_ack = True
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app.screen.query_one("#target-input", TextArea).text = "8.8.8.8"
        await pilot.pause(0.1)
        assert app.screen.query_one("#scope").has_class("-public")
        app.screen.query_one("#target-input", TextArea).text = "127.0.0.1\n10.0.0.1"
        await pilot.pause(0.1)
        assert not app.screen.query_one("#scope").has_class("-public")


async def test_scan_localhost_fills_table():
    # a listener we control, on loopback
    async def handle(reader, writer):
        writer.write(b"hello\r\n")
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    open_port = server.sockets[0].getsockname()[1]
    closed_port = await _free_local_port()

    app = PortoScan()
    app.settings.authorized_ack = True
    async with server, app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app.screen.query_one("#target-input", TextArea).text = "127.0.0.1"
        app.screen.query_one("#port-spec", TextArea).text = f"{open_port},{closed_port}"
        app.screen.query_one("#rate", Select).value = "localhost"
        await pilot.pause(0.1)
        app.action_scan()
        # wait for the scan worker to finish
        for _ in range(100):
            await pilot.pause(0.05)
            if not app.scanning and app._results:
                break
        states = {r.port: r.state for r in app._results}
        assert states.get(open_port) == "open", states
        assert states.get(closed_port) == "closed", states
        assert app.screen.query_one("#results", DataTable).row_count == 2


async def test_custom_port_spec_overrides_profile():
    app = PortoScan()
    app.settings.authorized_ack = True
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app.screen.query_one("#port-spec", TextArea).text = "22,80,443"
        assert app._selected_ports() == [22, 80, 443]
        app.screen.query_one("#port-spec", TextArea).text = ""
        app.screen.query_one("#profile", Select).value = "web"
        assert 8443 in app._selected_ports()


async def test_stop_sets_cancel_flag():
    app = PortoScan()
    app.settings.authorized_ack = True
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app.action_stop()
        assert app._cancel is True
