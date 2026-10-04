"""The PortoScan application.

Authorized-use TCP port scanner: it scans targets the operator supplies (an
uploaded .txt, pasted entries, or hosts expanded from CIDR/dotted ranges they
own). It has no random or by-country public-IP target generation by design.
"""

from __future__ import annotations

import logging
from pathlib import Path

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, HorizontalGroup, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Label,
    Select,
    TextArea,
)

from portoscan.authorization import classify
from portoscan.icons import glyphs
from portoscan.paths import Paths, resource_path
from portoscan.ports import PROFILE_BY_KEY, PROFILES, parse_ports
from portoscan.scan import PRESET_BY_KEY, PRESETS, Progress, Result, scan
from portoscan.screens import AuthorizeScreen, Confirm, SettingsScreen
from portoscan.storage import Settings, save_scan
from portoscan.targets import expand
from portoscan.themes import ALL_THEMES
from portoscan.widgets import ScanMeter, ScopeBanner

log = logging.getLogger(__name__)
STATE_ORDER = {"open": 0, "filtered": 1, "error": 2, "closed": 3}


class PortoScan(App[int]):
    TITLE = "PortoScan"
    SUB_TITLE = "authorized-use port scanner"
    CSS_PATH = [resource_path("styles/base.tcss")]
    HORIZONTAL_BREAKPOINTS = [(0, "-narrow"), (100, "-normal")]
    BINDINGS = [
        Binding("s", "scan", "Scan", id="scan"),
        Binding("x", "stop", "Stop", id="stop"),
        Binding("slash", "focus('#filter')", "Filter", id="filter"),
        Binding("e", "export", "Export", id="export"),
        Binding("comma", "settings", "Settings", id="settings"),
        Binding("ctrl+t", "cycle_theme", "Theme", id="theme"),
        Binding("f1", "show_help_panel", "Help", id="help"),
    ]
    HELP = """
    ## PortoScan
    Scan only systems you own or are authorized to test.
    - `s` scan, `x` stop, `/` filter results, `e` export
    - `,` settings, `ctrl+t` theme, `ctrl+p` command palette
    """

    scanning: reactive[bool] = reactive(False)

    def __init__(self, *, targets: str = "") -> None:
        super().__init__()
        self.paths = Paths.resolve().ensure()
        self.settings = Settings.load(self.paths.settings_file)
        self._initial_targets = targets
        self._glyphs = glyphs(self.settings.icons)
        self._results: list[Result] = []
        self._cancel = False

    # ---------------------------------------------------------------- compose
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, icon="*")
        yield ScopeBanner(id="scope")
        with Horizontal(id="body"):
            with VerticalScroll(id="targets"):
                yield Label("Targets (IP / host / CIDR / a.b.c.d-e)", classes="section")
                yield TextArea(self._initial_targets, id="target-input",
                               soft_wrap=False)
                with HorizontalGroup():
                    yield Button("Open .txt", id="open", compact=True)
                    yield Button("Preview", id="preview", compact=True)
                yield Label("Ports", classes="section")
                yield Select([(p.label, p.key) for p in PROFILES],
                             value=self.settings.port_profile, allow_blank=False,
                             id="profile")
                yield TextArea("", id="port-spec", soft_wrap=True,
                               tooltip="Custom: 22,80,443,8000-8100 (overrides profile)")
                yield Label("Rate preset", classes="section")
                yield Select([(p.label, p.key) for p in PRESETS],
                             value=self.settings.rate_preset, allow_blank=False,
                             id="rate")
                with HorizontalGroup(id="scan-row"):
                    yield Button("Scan", id="scan", variant="primary")
                    yield Button("Stop", id="stop", variant="error", disabled=True)
            with VerticalScroll(id="results-pane"):
                yield Label("", id="filter")  # placeholder; real Input mounted on demand
                yield DataTable(id="results", cursor_type="row", zebra_stripes=True)
        with HorizontalGroup(id="statusbar"):
            yield Label("idle", id="status")
            yield ScanMeter(id="meter")
        yield Footer()

    def on_mount(self) -> None:
        for theme in ALL_THEMES:
            self.register_theme(theme)
        if self.settings.theme in self.available_themes:
            self.theme = self.settings.theme
        table = self.query_one("#results", DataTable)
        table.add_column("Host", key="host", width=20)
        table.add_column("Port", key="port", width=7)
        table.add_column("State", key="state", width=10)
        table.add_column("Service", key="service", width=12)
        table.add_column("ms", key="latency", width=7)
        table.add_column("Banner", key="banner")
        self._refresh_scope()
        if not self.settings.authorized_ack:
            self._prompt_authorization()

    @work
    async def _prompt_authorization(self) -> None:
        ok = await self.push_screen_wait(AuthorizeScreen())
        if not ok:
            self.exit(2)
            return
        self.settings.authorized_ack = True
        self._persist()

    # --------------------------------------------------------------- targets
    def _target_text(self) -> str:
        return self.query_one("#target-input", TextArea).text

    def _selected_ports(self) -> list[int]:
        spec = self.query_one("#port-spec", TextArea).text.strip()
        if spec:
            return parse_ports(spec)
        key = str(self.query_one("#profile", Select).value)
        return list(PROFILE_BY_KEY[key].ports)

    def _refresh_scope(self) -> None:
        parsed = expand(self._target_text())
        try:
            ports = self._selected_ports()
        except ValueError:
            ports = []
        report = classify(parsed.hosts)
        preset = PRESET_BY_KEY[str(self.query_one("#rate", Select).value)].label
        self.query_one("#scope", ScopeBanner).show(report, len(ports), preset)

    @on(TextArea.Changed, "#target-input")
    @on(TextArea.Changed, "#port-spec")
    @on(Select.Changed, "#profile")
    @on(Select.Changed, "#rate")
    def _inputs_changed(self) -> None:
        self._refresh_scope()

    @on(Button.Pressed, "#open")
    @work
    async def _open(self) -> None:
        from textual_fspicker import FileOpen, Filters

        path = await self.push_screen_wait(
            FileOpen(Path.cwd(), title="Open a targets .txt",
                     filters=Filters(("Text", lambda p: p.suffix.lower() == ".txt"),
                                     ("Any", lambda _: True)))
        )
        if path is None:
            return
        try:
            text = Path(path).read_text("utf-8", "replace")
        except OSError as error:
            self.notify(f"Could not read file: {error}", severity="error")
            return
        self.query_one("#target-input", TextArea).text = text
        self.settings.remember_file(str(path))
        self._persist()
        self._refresh_scope()

    @on(Button.Pressed, "#preview")
    def _preview(self) -> None:
        parsed = expand(self._target_text())
        try:
            ports = self._selected_ports()
        except ValueError as error:
            self.notify(f"Bad port spec: {error}", severity="error")
            return
        total = len(parsed.hosts) * len(ports)
        extra = " (truncated)" if parsed.truncated else ""
        errs = f"; {len(parsed.errors)} errors" if parsed.errors else ""
        self.notify(f"{len(parsed.hosts)} hosts x {len(ports)} ports "
                    f"= {total} connections{extra}{errs}")

    # ----------------------------------------------------------------- scan
    def action_scan(self) -> None:
        self._start_scan()

    @on(Button.Pressed, "#scan")
    def _scan_button(self) -> None:
        self._start_scan()

    @work
    async def _start_scan(self) -> None:
        if self.scanning:
            return
        parsed = expand(self._target_text())
        if not parsed.hosts:
            self.notify("No targets", severity="warning")
            return
        try:
            ports = self._selected_ports()
        except ValueError as error:
            self.notify(f"Bad port spec: {error}", severity="error")
            return
        profile_key = str(self.query_one("#profile", Select).value)
        using_profile = self.query_one("#port-spec", TextArea).text.strip() == ""
        if using_profile and PROFILE_BY_KEY[profile_key].warn and not await self.push_screen_wait(
            Confirm(f"A full 1-65535 scan of {len(parsed.hosts)} host(s) is "
                    f"{len(parsed.hosts) * len(ports)} connections. Continue?", ok="Scan")
        ):
            return
        self._run_scan(parsed.hosts, ports)

    @work(exclusive=True, group="scan")
    async def _run_scan(self, hosts: list[str], ports: list[int]) -> None:
        self._cancel = False
        self.scanning = True
        self._results = []
        preset = PRESET_BY_KEY[str(self.query_one("#rate", Select).value)]
        table = self.query_one("#results", DataTable)
        table.clear()
        meter = self.query_one("#meter", ScanMeter)
        status = self.query_one("#status", Label)

        def on_result(result: Result, progress: Progress) -> None:
            self._add_row(table, result)

        def on_progress(progress: Progress) -> None:
            meter.fraction = progress.done / progress.total if progress.total else 0
            status.update(f"{progress.done}/{progress.total}  "
                          f"{progress.open} open  {progress.rate:.0f}/s  "
                          f"ETA {progress.eta:.0f}s")

        results = await scan(
            hosts, ports,
            concurrency=preset.concurrency, timeout=preset.timeout,
            grab=self.settings.grab_banners,
            on_result=on_result, on_progress=on_progress,
            should_cancel=lambda: self._cancel,
        )
        self._results = results
        self.scanning = False
        opened = sum(1 for r in results if r.state == "open")
        status.update(f"done: {len(results)} scanned, {opened} open"
                      + (" (stopped)" if self._cancel else ""))
        self._persist_history(hosts, ports, results)

    def _add_row(self, table: DataTable, result: Result) -> None:
        glyph = self._glyphs.get(result.state, "")
        state_text = Text(f"{glyph} {result.state}")
        state_text.stylize({
            "open": "bold green", "filtered": "yellow",
            "error": "bold red", "closed": "dim",
        }.get(result.state, ""))
        table.add_row(
            result.host, str(result.port), state_text, result.service,
            f"{result.latency_ms:.0f}", result.banner,
        )

    def watch_scanning(self, scanning: bool) -> None:
        with self.app.batch_update():
            try:
                self.query_one("#scan", Button).disabled = scanning
                self.query_one("#stop", Button).disabled = not scanning
            except Exception:  # not yet mounted
                pass

    def action_stop(self) -> None:
        self._cancel = True

    @on(Button.Pressed, "#stop")
    def _stop_button(self) -> None:
        self._cancel = True

    def _persist_history(self, hosts, ports, results) -> None:
        try:
            scope = f"{len(hosts)} hosts x {len(ports)} ports"
            save_scan(self.paths.database, scope=scope, hosts=len(hosts),
                      ports=len(ports), results=results)
        except Exception:  # history is best-effort
            log.exception("failed to save scan history")

    # ---------------------------------------------------------------- export
    @work
    async def action_export(self) -> None:
        if not self._results:
            self.notify("Nothing to export yet", severity="warning")
            return
        from textual_fspicker import FileSave

        from portoscan import export

        path = await self.push_screen_wait(
            FileSave(Path.cwd(), default_file="portoscan-results.csv"))
        if path is None:
            return
        target = Path(path)
        text = export.to_json(self._results) if target.suffix.lower() == ".json" \
            else export.to_csv(self._results)
        try:
            target.write_text(text, encoding="utf-8")
        except OSError as error:
            self.notify(f"Export failed: {error}", severity="error")
            return
        self.notify(f"Wrote {len(self._results)} rows to {target.name}")

    # -------------------------------------------------------------- settings
    @work
    async def action_settings(self) -> None:
        updated = await self.push_screen_wait(
            SettingsScreen(self.settings, list(self.available_themes)))
        if updated is None:
            return
        self.settings = updated
        self.theme = updated.theme
        self._glyphs = glyphs(updated.icons)
        self.query_one("#profile", Select).value = updated.port_profile
        self.query_one("#rate", Select).value = updated.rate_preset
        self._persist()
        self._refresh_scope()

    def action_cycle_theme(self) -> None:
        names = list(self.available_themes)
        self.theme = names[(names.index(self.theme) + 1) % len(names)]
        self.settings.theme = self.theme
        self._persist()

    def _persist(self) -> None:
        try:
            self.settings.save(self.paths.settings_file)
        except OSError:
            log.warning("could not save settings")

    def on_unmount(self) -> None:
        self._persist()
