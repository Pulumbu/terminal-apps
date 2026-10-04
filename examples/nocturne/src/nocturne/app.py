"""The Nocturne application.

Demonstrates, in one place: layout and breakpoints, theming, a custom line-API
widget, a filterable multi-select, a virtualised DataTable, thread and async
workers with cancellation, debounced search, modal screens returning values, a
command-palette provider, atomic settings persistence and animation levels.
"""

from __future__ import annotations

import asyncio
import logging
import platform
import sys
import traceback
from contextlib import suppress
from datetime import datetime, timezone

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Sparkline,
    Static,
)
from textual.worker import Worker, WorkerState, get_current_worker

from nocturne import __version__
from nocturne.commands import NocturneCommands
from nocturne.concurrency import Debouncer, shutdown_process_pool
from nocturne.domain import Entry, filter_entries, generate, level_counts
from nocturne.icons import pick_icons
from nocturne.paths import Paths, resource_path
from nocturne.screens import Confirm, SettingsScreen
from nocturne.storage import Settings
from nocturne.themes import ALL_THEMES
from nocturne.widgets import FilterableMultiSelect, WaveMeter

log = logging.getLogger(__name__)

LEVEL_STYLE = {
    "debug": "dim",
    "info": "",
    "warning": "bold $text-warning",
    "error": "bold $text-error",
}


class Nocturne(App[int]):
    TITLE = "Nocturne"
    CSS_PATH = [resource_path("styles/base.tcss")]
    COMMANDS = App.COMMANDS | {NocturneCommands}
    HORIZONTAL_BREAKPOINTS = [(0, "-narrow"), (100, "-normal"), (150, "-wide")]
    BINDINGS = [
        Binding("ctrl+r", "reload", "Reload", id="app.reload", priority=True),
        Binding("slash", "focus('#search')", "Search", id="app.search"),
        Binding("comma", "settings", "Settings", id="app.settings"),
        Binding("ctrl+t", "cycle_theme", "Theme", id="app.theme"),
        Binding("ctrl+d", "confirm_delete", "Delete", id="app.delete"),
        Binding("f1", "show_help_panel", "Help", id="app.help"),
    ]
    HELP = """
    ## Nocturne
    - `/` focus search, `,` settings, `ctrl+r` reload
    - `ctrl+t` cycle theme, `ctrl+p` command palette
    - `ctrl+d` delete the highlighted entry
    """

    status: reactive[str] = reactive("starting")
    entries: reactive[list[Entry]] = reactive(list)

    def __init__(self, *, count: int = 2000, theme_override: str | None = None) -> None:
        super().__init__()
        self.paths = Paths.resolve().ensure()
        self.settings = Settings.load(self.paths.settings_file)
        if theme_override:
            self.settings.theme = theme_override
        self.icons = pick_icons(self.settings.icons)
        self._count = count
        self._level_filter: str | None = None
        self._search_debounce: Debouncer | None = None

    # ---------------------------------------------------------------- compose

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, icon=self.icons.folder)
        with Horizontal(id="body"):
            with VerticalScroll(id="sidebar"):
                yield Input(placeholder="search entries...", id="search")
                yield Static(id="facets")
                yield FilterableMultiSelect(
                    {level: level for level in ("debug", "info", "warning", "error")},
                    id="levels",
                )
                yield Sparkline([0], id="spark")
                yield WaveMeter(id="meter")
            with VerticalScroll(id="content"):
                yield DataTable(id="rows", cursor_type="row")
        yield Label(id="statusbar")
        yield Footer()

    def on_mount(self) -> None:
        for theme in ALL_THEMES:
            self.register_theme(theme)
        if self.settings.theme in self.available_themes:
            self.theme = self.settings.theme
        self.set_keymap(self.settings.keymap)

        self.query_one("#facets", Static).border_title = "Levels"
        table = self.query_one("#rows", DataTable)
        table.zebra_stripes = self.settings.flags.get("zebra", True)
        table.add_column("When", key="at", width=10)
        table.add_column("Level", key="level", width=9)
        table.add_column("Message", key="message")

        self._search_debounce = Debouncer(0.2)
        self.load_entries()

    # ----------------------------------------------------------- reactivity

    def watch_status(self, status: str) -> None:
        self.sub_title = status
        with suppress(NoMatches):  # the status bar may not be mounted yet
            self.query_one("#statusbar", Label).update(
                f"{self.icons.info} {status}   v{__version__}"
            )

    def watch_entries(self, entries: list[Entry]) -> None:
        counts = level_counts(entries)
        self.query_one("#facets", Static).update(
            "\n".join(f"{level:<9}{count:>6}" for level, count in counts.items())
        )
        self.query_one("#spark", Sparkline).data = (
            [counts[level] for level in ("debug", "info", "warning", "error")] or [0]
        )
        meter = self.query_one("#meter", WaveMeter)
        target = min(1.0, len(entries) / max(1, self._count))
        meter.animate("value", target, duration=0.4, easing="out_cubic",
                      level="full")

    # -------------------------------------------------------------- workers

    @work(exclusive=True, group="io", thread=True, exit_on_error=False)
    def load_entries(self) -> int:
        """Blocking data load, on a thread, cancellable, batched into the UI."""
        worker = get_current_worker()
        produced: list[Entry] = []
        for chunk_start in range(0, self._count, 500):
            if worker.is_cancelled:
                return len(produced)
            batch = generate(500, seed=chunk_start)
            produced.extend(batch)
            self.call_from_thread(self._merge, list(produced))
        return len(produced)

    def _merge(self, entries: list[Entry]) -> None:
        self._all = entries
        self.entries = entries
        self._render_rows(entries)

    def _render_rows(self, entries: list[Entry]) -> None:
        table = self.query_one("#rows", DataTable)
        with self.batch_update():
            table.clear()
            page = entries[: self.settings.page_size]
            for entry in page:
                table.add_row(*entry.row, key=f"{entry.at.isoformat()}|{entry.message}",
                              height=1)
        shown = min(len(entries), self.settings.page_size)
        self.status = f"{len(entries)} entries, showing {shown}"

    @work(exclusive=True, group="query")
    async def run_search(self, query: str) -> None:
        await asyncio.sleep(0)  # yield a frame so typing stays smooth
        levels = self.query_one("#levels", FilterableMultiSelect).selected or None
        filtered = filter_entries(getattr(self, "_all", []), query, levels)
        self._render_rows(filtered)

    @on(Worker.StateChanged)
    def _worker_state(self, event: Worker.StateChanged) -> None:
        if event.state is WorkerState.ERROR:
            log.exception("worker %s failed", event.worker.name)
            self.notify(f"{event.worker.name} failed", severity="error")

    # ------------------------------------------------------------- handlers

    @on(Input.Changed, "#search")
    def _typed(self, event: Input.Changed) -> None:
        assert self._search_debounce is not None
        value = event.value
        self._search_debounce(lambda: self.run_search(value))

    @on(Input.Submitted, "#search")
    def _submitted(self, event: Input.Submitted) -> None:
        self.run_search(event.value)

    # -------------------------------------------------------------- actions

    def filter_to_level(self, level: str | None) -> None:
        self._level_filter = level
        selector = self.query_one("#levels", FilterableMultiSelect)
        selector.action_clear_all()
        if level is not None:
            selector.add_selection(level)
        self.run_search(self.query_one("#search", Input).value)

    def action_reload(self) -> None:
        self.load_entries()

    def action_cycle_theme(self) -> None:
        names = list(self.available_themes)
        self.theme = names[(names.index(self.theme) + 1) % len(names)]
        self.settings.theme = self.theme
        self._persist()

    @work
    async def action_settings(self) -> None:
        updated = await self.push_screen_wait(
            SettingsScreen(self.settings, list(self.available_themes))
        )
        if updated is None:
            return
        self.settings = updated
        self.theme = updated.theme
        self.icons = pick_icons(updated.icons)
        self.query_one("#rows", DataTable).zebra_stripes = updated.flags.get("zebra", True)
        self._render_rows(getattr(self, "_all", []))
        self._persist()
        self.notify("Settings saved")

    @work
    async def action_confirm_delete(self) -> None:
        table = self.query_one("#rows", DataTable)
        if table.row_count == 0:
            self.notify("Nothing to delete", severity="warning")
            return
        if await self.push_screen_wait(Confirm("Delete the highlighted entry?", danger=True)):
            table.remove_row(table.coordinate_to_cell_key(table.cursor_coordinate).row_key)
            self.status = f"{table.row_count} entries"

    def action_clear_cache(self) -> None:
        removed = 0
        for path in self.paths.cache.rglob("*"):
            if path.is_file():
                path.unlink(missing_ok=True)
                removed += 1
        self.notify(f"Cleared {removed} cached files")

    # ------------------------------------------------------------ lifecycle

    def _persist(self) -> None:
        try:
            self.settings.save(self.paths.settings_file)
        except OSError as error:
            log.warning("could not save settings: %s", error)

    def on_unmount(self) -> None:
        self._persist()
        shutdown_process_pool()

    def _handle_exception(self, error: Exception) -> None:
        try:
            self._write_crash_report(error)
        finally:
            super()._handle_exception(error)

    def _write_crash_report(self, error: Exception) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report = self.paths.logs / f"crash-{stamp}.log"
        try:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(
                "\n".join(
                    [
                        f"version: {__version__}",
                        f"python: {sys.version}",
                        f"platform: {platform.platform()}",
                        f"frozen: {getattr(sys, 'frozen', False)}",
                        f"size: {self.size}",
                        f"theme: {self.theme}",
                        "",
                        "".join(traceback.format_exception(error)),
                    ]
                ),
                encoding="utf-8",
            )
        except OSError:
            pass
