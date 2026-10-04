"""Show the result of diffing two scans."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, RichLog

from portoscan.diff import DiffReport


class DiffScreen(ModalScreen[None]):
    CSS = """
    DiffScreen { align: center middle; background: $background 60%; }
    #box { width: 80; height: 28; padding: 1 2; border: round $primary; background: $surface; }
    #title { text-style: bold; color: $text-primary; }
    RichLog { height: 1fr; }
    """
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, report: DiffReport, *, baseline: str, current: str) -> None:
        super().__init__()
        self.report = report
        self.baseline = baseline
        self.current = current

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label(f"Diff: #{self.baseline}  ->  #{self.current}", id="title")
            yield Label(self.report.summary)
            yield RichLog(id="log", markup=True, highlight=False)

    def on_mount(self) -> None:
        log = self.query_one("#log", RichLog)
        self._section(log, "[b green]Newly open[/]", self.report.newly_open, "green")
        self._section(log, "[b red]Newly closed[/]", self.report.newly_closed, "red")
        self._section(log, "[b yellow]Other changes[/]", self.report.changed, "yellow")
        self._section(log, "[dim]Appeared (new endpoints)[/]", self.report.appeared, "dim")
        self._section(log, "[dim]Disappeared[/]", self.report.disappeared, "dim")
        if not any((self.report.newly_open, self.report.newly_closed,
                    self.report.changed, self.report.appeared, self.report.disappeared)):
            log.write("[dim]No differences.[/]")

    def _section(self, log: RichLog, heading: str, changes, style: str) -> None:
        if not changes:
            return
        log.write(heading)
        for change in changes:
            old = change.old_state or "-"
            new = change.new_state or "-"
            log.write(f"  [{style}]{change.host}:{change.port}[/]  {old} -> {new}")

    def action_dismiss(self) -> None:
        self.dismiss(None)
