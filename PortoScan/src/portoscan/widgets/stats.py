"""A live stats panel: open-ports sparkline, top services, per-host open counts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, Sparkline, Static

from portoscan.stats import counts_by_state, per_host_open, top_services

if TYPE_CHECKING:
    from collections.abc import Sequence

    from portoscan.scan import Result


class StatsPanel(Vertical):
    DEFAULT_CSS = """
    StatsPanel {
        width: 32;
        border-left: vkey $primary-muted;
        padding: 0 1;
    }
    StatsPanel Label.section { text-style: bold; color: $text-primary; margin-top: 1; }
    StatsPanel Sparkline {
        height: 3;
        & > .sparkline--max-color { color: $success; }
        & > .sparkline--min-color { color: $primary; }
    }
    StatsPanel Static { height: auto; }
    """

    def compose(self) -> ComposeResult:
        yield Label("Open ports over time", classes="section")
        yield Sparkline([0], id="stats-spark")
        yield Label("By state", classes="section")
        yield Static("", id="stats-state")
        yield Label("Top services", classes="section")
        yield Static("", id="stats-services")
        yield Label("Top hosts (open)", classes="section")
        yield Static("", id="stats-hosts")

    def set_series(self, series: Sequence[int]) -> None:
        self.query_one("#stats-spark", Sparkline).data = list(series) or [0]

    def set_rollups(self, results: Sequence[Result]) -> None:
        states = counts_by_state(results)
        self.query_one("#stats-state", Static).update(
            "  ".join(f"{name[0].upper()}:{states[name]}"
                      for name in ("open", "closed", "filtered", "error")))
        self.query_one("#stats-services", Static).update(
            self._rows(top_services(results)) or "[dim]none[/]")
        self.query_one("#stats-hosts", Static).update(
            self._rows(per_host_open(results)) or "[dim]none[/]")

    @staticmethod
    def _rows(pairs: list[tuple[str, int]]) -> str:
        return "\n".join(f"{name[:20]:<20} {count:>4}" for name, count in pairs)
