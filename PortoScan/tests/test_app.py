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


async def test_filter_box_filters_table():
    from textual.widgets import Input

    from portoscan.scan import Result
    app = PortoScan()
    app.settings.authorized_ack = True
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app._results = [
            Result("127.0.0.1", 80, "open", 1.0, "http", ""),
            Result("127.0.0.1", 81, "closed", 1.0, "", ""),
            Result("127.0.0.2", 22, "open", 1.0, "ssh", ""),
        ]
        app._rerender()
        table = app.screen.query_one("#results", DataTable)
        assert table.row_count == 3
        app.screen.query_one("#filter", Input).value = "open"
        await pilot.pause(0.1)
        assert table.row_count == 2
        app.screen.query_one("#filter", Input).value = "ssh"
        await pilot.pause(0.1)
        assert table.row_count == 1
        app.screen.query_one("#filter", Input).value = ""
        await pilot.pause(0.1)
        assert table.row_count == 3


async def test_auto_save_writes_run_folder(tmp_path, monkeypatch):
    import asyncio

    from textual.widgets import Select, TextArea

    from portoscan.results_io import RESULT_DIR_NAME

    async def handle(reader, writer):
        writer.close()
    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    app = PortoScan()
    app.settings.authorized_ack = True
    app.settings.auto_save = True
    app.settings.auto_save_dir = str(tmp_path)
    app.settings.output_format = "txt"
    async with server, app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app.screen.query_one("#target-input", TextArea).text = "127.0.0.1"
        app.screen.query_one("#port-spec", TextArea).text = str(port)
        app.screen.query_one("#rate", Select).value = "localhost"
        await pilot.pause(0.1)
        app.action_scan()
        for _ in range(100):
            await pilot.pause(0.05)
            if not app.scanning and app._results:
                break
    run_root = tmp_path / RESULT_DIR_NAME
    assert run_root.exists()
    runs = list(run_root.iterdir())
    assert len(runs) == 1
    assert (runs[0] / "all.txt").exists()
    assert (runs[0] / "open.txt").exists()
    assert (runs[0] / "summary.txt").exists()


async def test_history_round_trip_loads_results():
    from portoscan.scan import Result
    from portoscan.storage import save_scan
    app = PortoScan()
    app.settings.authorized_ack = True
    saved = [Result("127.0.0.1", 80, "open", 1.0, "http", "")]
    save_scan(app.paths.database, scope="1 hosts x 1 ports",
              hosts=1, ports=1, results=saved)
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app.action_history()
        await pilot.pause(0.3)
        from portoscan.screens import HistoryScreen
        assert isinstance(app.screen, HistoryScreen)
        from textual.widgets import OptionList
        app.screen.query_one("#scan-list", OptionList).action_first()
        await pilot.press("enter")
        await pilot.pause(0.3)
        assert len(app._results) == 1 and app._results[0].port == 80
