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
    Input,
    Label,
    Select,
    SelectionList,
    TextArea,
)
from textual.widgets.selection_list import Selection

from portoscan import export, results_io
from portoscan.authorization import classify
from portoscan.diff import diff_scans
from portoscan.icons import glyphs
from portoscan.paths import Paths, resource_path
from portoscan.ports import PROFILE_BY_KEY, PROFILES, parse_ports
from portoscan.scan import PRESET_BY_KEY, PRESETS, Progress, Result, scan
from portoscan.screens import (
    AuthorizeScreen,
    Confirm,
    DiffScreen,
    HistoryScreen,
    PresetsScreen,
    PromptScreen,
    SettingsScreen,
)
from portoscan.stats import open_pairs
from portoscan.storage import Settings, load_scan, recent_scans, save_scan
from portoscan.targets import expand
from portoscan.themes import ALL_THEMES
from portoscan.widgets import ScanMeter, ScopeBanner, StatsPanel

log = logging.getLogger(__name__)
STATE_ORDER = {"open": 0, "filtered": 1, "error": 2, "closed": 3}

SORT_KEYS = {
    "host": lambda r: (r.host, r.port),
    "port": lambda r: (r.port, r.host),
    "state": lambda r: (STATE_ORDER.get(r.state, 9), r.host, r.port),
    "service": lambda r: (r.service, r.host, r.port),
    "latency": lambda r: (r.latency_ms, r.host, r.port),
    "banner": lambda r: (r.banner, r.host, r.port),
}
STATE_FILTERS = {
    "all": {"open", "closed", "filtered", "error"},
    "open": {"open"},
    "notclosed": {"open", "filtered", "error"},
    "openfiltered": {"open", "filtered"},
}


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
        Binding("i", "import_results", "Import", id="import"),
        Binding("h", "history", "History", id="history"),
        Binding("d", "diff", "Diff", id="diff"),
        Binding("r", "rescan_open", "Re-scan open", id="rescan-open"),
        Binding("ctrl+r", "rescan_host", "Re-scan host", id="rescan-host"),
        Binding("t", "toggle_stats", "Stats", id="stats"),
        Binding("ctrl+s", "save_preset", "Save preset", id="save-preset"),
        Binding("ctrl+l", "load_preset", "Presets", id="load-preset"),
        Binding("comma", "settings", "Settings", id="settings"),
        Binding("ctrl+t", "cycle_theme", "Theme", id="theme"),
        Binding("f1", "show_help_panel", "Help", id="help"),
    ]
    HELP = """
    ## PortoScan
    Scan only systems you own or are authorized to test.
    - `s` scan, `x` stop, `/` filter results, click a header to sort
    - `e` export, `i` import, `h` history, `d` diff two scans
    - `r` re-scan open, `ctrl+r` re-scan highlighted host, `t` stats panel
    - `ctrl+s` save preset, `ctrl+l` presets, `,` settings, `ctrl+t` theme
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
        self._filter_text = ""
        self._sort_col: str | None = None
        self._sort_reverse = False
        self._visible_states = STATE_FILTERS["all"]
        self._open_series: list[int] = []

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
                yield Label("Ports (tick any; combined)", classes="section")
                yield SelectionList[str](
                    *[Selection(p.label, p.key, p.key == self.settings.port_profile)
                      for p in PROFILES],
                    id="profiles",
                )
                yield TextArea("", id="port-spec", soft_wrap=True,
                               tooltip="Extra ports, added to the ticked categories: "
                                       "22,80,443,8000-8100")
                yield Label("Rate preset", classes="section")
                yield Select([(p.label, p.key) for p in PRESETS],
                             value=self.settings.rate_preset, allow_blank=False,
                             id="rate")
                yield Label("Protocol", classes="section")
                yield Select([("TCP connect", "tcp"), ("UDP (slow)", "udp")],
                             value=self.settings.protocol, allow_blank=False,
                             id="protocol")
                with HorizontalGroup(id="scan-row"):
                    yield Button("Scan", id="scan", variant="primary")
                    yield Button("Stop", id="stop", variant="error", disabled=True)
            with VerticalScroll(id="results-pane"):
                with HorizontalGroup(id="results-tools"):
                    yield Input(placeholder="filter: text, or a state like 'open'",
                                id="filter")
                    yield Select(
                        [("All states", "all"), ("Open only", "open"),
                         ("Not closed", "notclosed"), ("Open+Filtered", "openfiltered")],
                        value="all", allow_blank=False, id="state-filter")
                yield DataTable(id="results", cursor_type="row", zebra_stripes=True)
            yield StatsPanel(id="stats")
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
        table.add_column("Host", key="host", width=30)
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

    def _ticked_profiles(self) -> list[str]:
        return list(self.query_one("#profiles", SelectionList).selected)

    def _selected_ports(self) -> list[int]:
        """Union of every ticked category plus any ports in the custom box."""
        ports: set[int] = set()
        for key in self._ticked_profiles():
            ports.update(PROFILE_BY_KEY[key].ports)
        spec = self.query_one("#port-spec", TextArea).text.strip()
        if spec:
            ports.update(parse_ports(spec))
        return sorted(ports)

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
    @on(SelectionList.SelectedChanged, "#profiles")
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
        if not ports:
            self.notify("No ports selected", severity="warning")
            return
        warns = any(PROFILE_BY_KEY[k].warn for k in self._ticked_profiles())
        if (warns or len(ports) > 10000) and not await self.push_screen_wait(
            Confirm(f"This scans {len(parsed.hosts)} host(s) x {len(ports)} ports "
                    f"= {len(parsed.hosts) * len(ports)} connections. Continue?", ok="Scan")
        ):
            return
        self._run_scan(parsed.hosts, ports)

    @work(exclusive=True, group="scan")
    async def _run_scan(self, hosts: list[str], ports: list[int], *,
                        pairs: list[tuple[str, int]] | None = None) -> None:
        self._cancel = False
        self.scanning = True
        self._results = []
        self._open_series = []
        preset = PRESET_BY_KEY[str(self.query_one("#rate", Select).value)]
        protocol = str(self.query_one("#protocol", Select).value)
        table = self.query_one("#results", DataTable)
        table.clear()
        meter = self.query_one("#meter", ScanMeter)
        status = self.query_one("#status", Label)
        stats = self.query_one("#stats", StatsPanel)

        def on_result(result: Result, progress: Progress) -> None:
            self._add_row(table, result)

        def on_progress(progress: Progress) -> None:
            meter.fraction = progress.done / progress.total if progress.total else 0
            status.update(f"{progress.done}/{progress.total}  "
                          f"{progress.open} open  {progress.rate:.0f}/s  "
                          f"ETA {progress.eta:.0f}s")
            self._open_series.append(progress.open)
            if len(self._open_series) > 120:
                self._open_series = self._open_series[-120:]
            stats.set_series(self._open_series)

        results = await scan(
            hosts, ports,
            concurrency=preset.concurrency, timeout=preset.timeout,
            grab=self.settings.grab_banners and protocol == "tcp",
            on_result=on_result, on_progress=on_progress,
            should_cancel=lambda: self._cancel, pairs=pairs, protocol=protocol,
        )
        self._results = results
        self.scanning = False
        opened = sum(1 for r in results if r.state == "open")
        host_n = len({h for h, _ in pairs}) if pairs is not None else len(hosts)
        port_n = len({p for _, p in pairs}) if pairs is not None else len(ports)
        scope = f"{host_n} hosts x {port_n} ports"
        status.update(f"done: {len(results)} scanned, {opened} open"
                      + (" (stopped)" if self._cancel else ""))
        self._update_stats()
        self._persist_history([*{h for h, _ in pairs}] if pairs else hosts,
                              list(range(port_n)) if pairs else ports, results)
        if self.settings.auto_save and results:
            self._auto_save(results, scope)

    def _matches(self, result: Result) -> bool:
        if result.state not in self._visible_states:
            return False
        query = self._filter_text.strip().lower()
        if not query:
            return True
        haystack = (f"{result.host} {result.port} {result.state} "
                    f"{result.service} {result.banner}").lower()
        return all(term in haystack for term in query.split())

    def _sorted_results(self) -> list[Result]:
        if self._sort_col is None:
            return self._results
        return sorted(self._results, key=SORT_KEYS[self._sort_col],
                      reverse=self._sort_reverse)

    def _add_row(self, table: DataTable, result: Result) -> None:
        if not self._matches(result):
            return
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

    def _rerender(self) -> None:
        table = self.query_one("#results", DataTable)
        with self.app.batch_update():
            table.clear()
            shown = 0
            for result in self._sorted_results():
                if self._matches(result):
                    self._add_row(table, result)
                    shown += 1
        if self._results:
            self.query_one("#status", Label).update(
                f"{shown}/{len(self._results)} shown"
                + (f"  (filter: {self._filter_text})" if self._filter_text else ""))
        self._update_stats()

    def _update_stats(self) -> None:
        try:
            stats = self.query_one("#stats", StatsPanel)
        except Exception:  # panel not mounted yet
            return
        stats.set_rollups(self._results)
        if not self.scanning:
            opened = sum(1 for r in self._results if r.state == "open")
            stats.set_series(self._open_series or [opened])

    def action_toggle_stats(self) -> None:
        panel = self.query_one("#stats", StatsPanel)
        panel.toggle_class("-show")
        if panel.has_class("-show"):
            self._update_stats()

    def _highlighted_host(self) -> str | None:
        table = self.query_one("#results", DataTable)
        if table.row_count == 0 or table.cursor_row is None:
            return None
        try:
            return str(table.get_row_at(table.cursor_row)[0])
        except Exception:
            return None

    def action_rescan_open(self) -> None:
        if self.scanning:
            return
        pairs = open_pairs(self._results)
        if not pairs:
            self.notify("No open ports to re-scan", severity="warning")
            return
        hosts = sorted({h for h, _ in pairs})
        ports = sorted({p for _, p in pairs})
        self.notify(f"Re-scanning {len(pairs)} open endpoint(s)")
        self._run_scan(hosts, ports, pairs=pairs)

    def action_rescan_host(self) -> None:
        if self.scanning:
            return
        host = self._highlighted_host()
        if host is None:
            self.notify("Highlight a result row first", severity="warning")
            return
        try:
            ports = self._selected_ports()
        except ValueError as error:
            self.notify(f"Bad port spec: {error}", severity="error")
            return
        if not ports:
            self.notify("No ports selected", severity="warning")
            return
        self.notify(f"Re-scanning {host} x {len(ports)} ports")
        self._run_scan([host], ports)

    @on(Input.Changed, "#filter")
    def _filter_changed(self, event: Input.Changed) -> None:
        self._filter_text = event.value
        self._rerender()

    @on(Select.Changed, "#state-filter")
    def _state_filter_changed(self, event: Select.Changed) -> None:
        self._visible_states = STATE_FILTERS[str(event.value)]
        self._rerender()

    @on(DataTable.HeaderSelected, "#results")
    def _sort_by_header(self, event: DataTable.HeaderSelected) -> None:
        key = str(event.column_key.value)
        if key not in SORT_KEYS:
            return
        self._sort_reverse = (not self._sort_reverse) if key == self._sort_col else False
        self._sort_col = key
        self._rerender()

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

    # ------------------------------------------------------------ auto-save
    def _output_base(self):
        return results_io.resolve_base(
            self.settings.auto_save_dir or None,
            fallbacks=[self.paths.documents, self.paths.data],
        )

    def _auto_save(self, results, scope: str) -> None:
        try:
            output = results_io.write_run(
                self._output_base(), results, scope=scope,
                fmt=self.settings.output_format,
            )
            self.notify(f"Saved {len(results)} results to {output.folder}")
        except OSError as error:
            log.warning("auto-save failed: %s", error)
            self.notify(f"Could not auto-save results: {error}", severity="error")

    # ---------------------------------------------------------------- import
    @work
    async def action_import_results(self) -> None:
        from textual_fspicker import FileOpen, Filters

        path = await self.push_screen_wait(
            FileOpen(Path.cwd(), title="Import results (.csv / .json)",
                     filters=Filters(
                         ("Results", lambda p: p.suffix.lower() in {".csv", ".json"}),
                         ("Any", lambda _: True))))
        if path is None:
            return
        try:
            results = export.load_file(path)
        except (OSError, ValueError) as error:
            self.notify(f"Import failed: {error}", severity="error")
            return
        self._results = results
        self._rerender()
        self.notify(f"Imported {len(results)} results from {Path(path).name}")

    # --------------------------------------------------------------- history
    @work
    async def action_history(self) -> None:
        scans = recent_scans(self.paths.database)
        scan_id = await self.push_screen_wait(HistoryScreen(scans))
        if scan_id is None:
            return
        results = load_scan(self.paths.database, scan_id)
        self._results = results
        self._rerender()
        self.notify(f"Loaded scan #{scan_id}: {len(results)} results")

    # ------------------------------------------------------------------ diff
    @work
    async def action_diff(self) -> None:
        scans = recent_scans(self.paths.database)
        if len(scans) < 2:
            self.notify("Need at least two saved scans to diff", severity="warning")
            return
        baseline = await self.push_screen_wait(HistoryScreen(scans))
        if baseline is None:
            return
        current = await self.push_screen_wait(HistoryScreen(scans))
        if current is None:
            return
        report = diff_scans(
            load_scan(self.paths.database, baseline),
            load_scan(self.paths.database, current),
        )
        await self.push_screen_wait(
            DiffScreen(report, baseline=str(baseline), current=str(current)))

    # --------------------------------------------------------------- presets
    @work
    async def action_save_preset(self) -> None:
        name = await self.push_screen_wait(PromptScreen("Name this preset:"))
        if not name:
            return
        preset = {
            "name": name,
            "targets": self._target_text(),
            "profiles": self._ticked_profiles(),
            "custom_ports": self.query_one("#port-spec", TextArea).text.strip(),
            "rate": str(self.query_one("#rate", Select).value),
        }
        self.settings.presets = [p for p in self.settings.presets
                                 if p.get("name") != name] + [preset]
        self._persist()
        self.notify(f"Saved preset '{name}'")

    @work
    async def action_load_preset(self) -> None:
        names = [p.get("name", "") for p in self.settings.presets]
        choice = await self.push_screen_wait(PresetsScreen(names))
        if choice is None:
            return
        action, name = choice
        if action == "delete":
            self.settings.presets = [p for p in self.settings.presets
                                     if p.get("name") != name]
            self._persist()
            self.notify(f"Deleted preset '{name}'")
            return
        preset = next((p for p in self.settings.presets if p.get("name") == name), None)
        if preset is None:
            return
        self._apply_preset(preset)
        self.notify(f"Loaded preset '{name}'")

    def _apply_preset(self, preset: dict) -> None:
        self.query_one("#target-input", TextArea).text = preset.get("targets", "")
        self.query_one("#port-spec", TextArea).text = preset.get("custom_ports", "")
        profiles = self.query_one("#profiles", SelectionList)
        profiles.deselect_all()
        for key in preset.get("profiles", []):
            if key in PROFILE_BY_KEY:
                profiles.select(key)
        rate = preset.get("rate", "lan")
        if rate in PRESET_BY_KEY:
            self.query_one("#rate", Select).value = rate
        self._refresh_scope()

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
        profiles = self.query_one("#profiles", SelectionList)
        profiles.deselect_all()
        profiles.select(updated.port_profile)
        self.query_one("#rate", Select).value = updated.rate_preset
        self.query_one("#protocol", Select).value = updated.protocol
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
