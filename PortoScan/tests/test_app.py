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
        from textual.widgets import SelectionList
        app.screen.query_one("#profiles", SelectionList).deselect_all()
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


async def test_port_selection_unions_categories_and_custom():
    from textual.widgets import SelectionList
    app = PortoScan()
    app.settings.authorized_ack = True
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        profiles = app.screen.query_one("#profiles", SelectionList)
        # tick Web + Remote admin together
        profiles.deselect_all()
        profiles.select("web")
        profiles.select("admin")
        await pilot.pause(0.1)
        ports = set(app._selected_ports())
        assert {80, 443, 8443} <= ports        # web
        assert {22, 3389, 5900} <= ports       # remote admin (RDP, VNC)
        # custom box ADDS extra ports on top of the ticked categories
        app.screen.query_one("#port-spec", TextArea).text = "9999"
        await pilot.pause(0.1)
        ports2 = set(app._selected_ports())
        assert 9999 in ports2 and {80, 22} <= ports2
        # untick everything -> only the custom ports remain
        profiles.deselect_all()
        await pilot.pause(0.1)
        assert app._selected_ports() == [9999]


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
        from textual.widgets import SelectionList
        app.screen.query_one("#profiles", SelectionList).deselect_all()
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


async def test_header_click_sorts_results():
    from portoscan.scan import Result
    app = PortoScan()
    app.settings.authorized_ack = True
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app._results = [
            Result("10.0.0.1", 80, "closed", 5.0, "http", ""),
            Result("10.0.0.1", 22, "open", 1.0, "ssh", ""),
            Result("10.0.0.1", 443, "filtered", 9.0, "https", ""),
        ]
        app._rerender()
        # sort by state: open first, then filtered, then closed (STATE_ORDER)
        app._sort_col = "state"
        app._sort_reverse = False
        assert [x.state for x in app._sorted_results()] == ["open", "filtered", "closed"]
        app._sort_col = "port"
        assert [x.port for x in app._sorted_results()] == [22, 80, 443]
        app._sort_reverse = True
        assert [x.port for x in app._sorted_results()] == [443, 80, 22]


async def test_state_filter_select():
    from textual.widgets import DataTable, Select

    from portoscan.scan import Result
    app = PortoScan()
    app.settings.authorized_ack = True
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app._results = [
            Result("10.0.0.1", 22, "open", 1.0, "", ""),
            Result("10.0.0.1", 80, "closed", 1.0, "", ""),
            Result("10.0.0.1", 443, "filtered", 1.0, "", ""),
        ]
        app._rerender()
        table = app.screen.query_one("#results", DataTable)
        assert table.row_count == 3
        app.screen.query_one("#state-filter", Select).value = "open"
        await pilot.pause(0.1)
        assert table.row_count == 1
        app.screen.query_one("#state-filter", Select).value = "notclosed"
        await pilot.pause(0.1)
        assert table.row_count == 2


async def test_save_and_load_preset():
    from textual.widgets import Input, Select, SelectionList, TextArea
    app = PortoScan()
    app.settings.authorized_ack = True
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app.screen.query_one("#target-input", TextArea).text = "10.0.0.0/30"
        profiles = app.screen.query_one("#profiles", SelectionList)
        profiles.deselect_all()
        profiles.select("web")
        profiles.select("db")
        app.screen.query_one("#port-spec", TextArea).text = "9999"
        app.screen.query_one("#rate", Select).value = "internet"
        await pilot.pause(0.1)
        # save
        app.action_save_preset()
        await pilot.pause(0.2)
        app.screen.query_one("#value", Input).value = "my-preset"
        await pilot.press("enter")
        await pilot.pause(0.2)
        assert any(p["name"] == "my-preset" for p in app.settings.presets)
        # change everything, then load it back
        app.screen.query_one("#target-input", TextArea).text = ""
        profiles.deselect_all()
        app.screen.query_one("#port-spec", TextArea).text = ""
        await pilot.pause(0.1)
        preset = next(p for p in app.settings.presets if p["name"] == "my-preset")
        app._apply_preset(preset)
        await pilot.pause(0.1)
        assert app.screen.query_one("#target-input", TextArea).text == "10.0.0.0/30"
        assert set(profiles.selected) == {"web", "db"}
        assert app.screen.query_one("#port-spec", TextArea).text == "9999"
        assert str(app.screen.query_one("#rate", Select).value) == "internet"


async def test_diff_action_shows_screen():
    from portoscan.scan import Result
    from portoscan.screens import DiffScreen
    from portoscan.storage import save_scan
    app = PortoScan()
    app.settings.authorized_ack = True
    save_scan(app.paths.database, scope="s", hosts=1, ports=1,
              results=[Result("10.0.0.1", 22, "open", 1.0, "", "")])
    save_scan(app.paths.database, scope="s", hosts=1, ports=1,
              results=[Result("10.0.0.1", 22, "closed", 1.0, "", "")])
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app.action_diff()
        await pilot.pause(0.3)
        from portoscan.screens import HistoryScreen
        assert isinstance(app.screen, HistoryScreen)
        await pilot.press("enter")          # pick baseline (newest)
        await pilot.pause(0.2)
        await pilot.press("down", "enter")  # pick the other
        await pilot.pause(0.2)
        assert isinstance(app.screen, DiffScreen)


async def test_stats_panel_toggle_and_rollups():
    from portoscan.scan import Result
    app = PortoScan()
    app.settings.authorized_ack = True
    async with app.run_test(size=(140, 36)) as pilot:
        await pilot.pause(0.2)
        stats = app.screen.query_one("#stats")
        assert not stats.has_class("-show")          # hidden by default
        app.action_toggle_stats()
        await pilot.pause(0.1)
        assert stats.has_class("-show")
        app._results = [
            Result("10.0.0.1", 22, "open", 1.0, "ssh", ""),
            Result("10.0.0.1", 80, "open", 1.0, "http", ""),
            Result("10.0.0.2", 443, "closed", 1.0, "https", ""),
        ]
        app._rerender()
        from textual.widgets import Static
        services = str(app.screen.query_one("#stats-services", Static).content)
        assert "ssh" in services and "http" in services


async def test_rescan_open_rescans_only_open_pairs():
    import asyncio

    from textual.widgets import Select, SelectionList, TextArea

    async def handle(reader, writer):
        writer.close()
    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    open_port = server.sockets[0].getsockname()[1]
    closed_port = open_port + 1

    app = PortoScan()
    app.settings.authorized_ack = True
    app.settings.auto_save = False
    async with server, app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app.screen.query_one("#profiles", SelectionList).deselect_all()
        app.screen.query_one("#target-input", TextArea).text = "127.0.0.1"
        app.screen.query_one("#port-spec", TextArea).text = f"{open_port},{closed_port}"
        app.screen.query_one("#rate", Select).value = "localhost"
        await pilot.pause(0.1)
        app.action_scan()
        for _ in range(100):
            await pilot.pause(0.05)
            if not app.scanning and app._results:
                break
        assert len(app._results) == 2
        # now re-scan open: should scan exactly the 1 open endpoint
        app.action_rescan_open()
        for _ in range(100):
            await pilot.pause(0.05)
            if not app.scanning and app._results:
                break
        assert len(app._results) == 1
        assert app._results[0].state == "open"
        assert app._results[0].port == open_port


async def test_scan_resolves_hostname_before_scanning():
    import asyncio

    from textual.widgets import Select, SelectionList, TextArea

    async def handler(reader, writer):
        writer.close()
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    app = PortoScan()
    app.settings.authorized_ack = True
    app.settings.auto_save = False
    app.settings.resolve_first = True
    async with server, app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app.screen.query_one("#profiles", SelectionList).deselect_all()
        app.screen.query_one("#target-input", TextArea).text = "localhost"
        app.screen.query_one("#port-spec", TextArea).text = str(port)
        app.screen.query_one("#rate", Select).value = "localhost"
        await pilot.pause(0.1)
        app.action_scan()
        for _ in range(100):
            await pilot.pause(0.05)
            if not app.scanning and app._results:
                break
        # the hostname was resolved to a loopback literal before scanning
        assert app._results and app._results[0].host in ("127.0.0.1", "::1")
        assert app._results[0].state in ("open", "closed")


async def test_compliance_screen_lists_findings():
    from portoscan.scan import Result
    from portoscan.screens import ComplianceScreen
    app = PortoScan()
    app.settings.authorized_ack = True
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app._results = [
            Result("10.0.0.1", 23, "open", 1.0, "telnet", ""),
            Result("10.0.0.1", 443, "open", 1.0, "https", ""),
        ]
        app.action_compliance()
        await pilot.pause(0.3)
        assert isinstance(app.screen, ComplianceScreen)
        assert len(app.screen.findings) == 1   # only telnet flagged
        assert app.screen.findings[0].port == 23


async def test_vuln_checks_action_combines_ssh_and_web():
    import asyncio

    from portoscan.scan import Result
    from portoscan.screens import ComplianceScreen

    async def handler(reader, writer):
        req = await reader.read(1024)
        path = req.split(b"\r\n", 1)[0].split()[1].decode()
        if path == "/.env":
            writer.write(b"HTTP/1.0 200 OK\r\n\r\nSECRET_KEY=abc\nDB_PASSWORD=x\n")
        else:
            writer.write(b"HTTP/1.0 404 Not Found\r\n\r\nx")
        await writer.drain()
        writer.close()
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    app = PortoScan()
    app.settings.authorized_ack = True
    async with server, app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app._results = [
            Result("127.0.0.1", port, "open", 1.0, "http", ""),
            Result("127.0.0.1", 22, "open", 1.0, "ssh", "SSH-2.0-OpenSSH_8.9p1"),
        ]
        app.action_vuln_checks()
        await pilot.pause(0.6)
        assert isinstance(app.screen, ComplianceScreen)
        messages = " ".join(f.message for f in app.screen.findings)
        assert "/.env" in messages            # exposed path
        assert "CVE-2024-6387" in messages    # ssh cve
        assert "DB_PASSWORD" not in messages   # no secret captured


async def test_verify_action_gate_confirm_and_save(tmp_path):
    import asyncio

    from portoscan.scan import Result
    from portoscan.screens import DeepAuthorizeScreen, VerifyScreen

    async def handler(reader, writer):
        req = await reader.read(1024)
        path = req.split(b"\r\n", 1)[0].split()[1].decode()
        if path == "/.env":
            writer.write(b"HTTP/1.0 200 OK\r\n\r\nAPI_KEY=live-xyz\nDB_PASSWORD=p\n")
        else:
            writer.write(b"HTTP/1.0 404 Not Found\r\n\r\nx")
        await writer.drain()
        writer.close()
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    app = PortoScan()
    app.settings.authorized_ack = True
    app.settings.auto_save_dir = str(tmp_path)
    app.settings.output_format = "txt"
    async with server, app.run_test(size=(120, 36)) as pilot:
        await pilot.pause(0.2)
        app._results = [Result("127.0.0.1", port, "open", 1.0, "http", "")]
        app.action_verify()
        await pilot.pause(0.3)
        # first run hits the strong-auth gate
        assert isinstance(app.screen, DeepAuthorizeScreen)
        await pilot.click("#yes")
        # wait for the verification pass + save
        for _ in range(100):
            await pilot.pause(0.05)
            if isinstance(app.screen, VerifyScreen):
                break
        assert isinstance(app.screen, VerifyScreen)
        findings = app.screen.findings
        assert any(f.confirmed and "/.env" in f.message for f in findings)
        # evidence must not contain the secret value
        joined = " ".join(f.evidence for f in findings)
        assert "live-xyz" not in joined
        # a -verify result folder was written with findings.txt
        from portoscan.results_io import RESULT_DIR_NAME
        verify_dirs = [d for d in (tmp_path / RESULT_DIR_NAME).iterdir()
                       if d.name.endswith("-verify")]
        assert verify_dirs and (verify_dirs[0] / "findings.txt").exists()
        text = (verify_dirs[0] / "findings.txt").read_text()
        assert "CONFIRMED" in text and "live-xyz" not in text
