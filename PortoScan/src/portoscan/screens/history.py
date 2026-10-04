"""Re-open a past scan stored in the history database."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option


class HistoryScreen(ModalScreen[int | None]):
    """Dismisses with the chosen scan id, or None."""

    CSS = """
    HistoryScreen { align: center middle; background: $background 60%; }
    #box { width: 80; height: 24; padding: 1 2; border: round $primary; background: $surface; }
    #title { text-style: bold; color: $text-primary; }
    OptionList { height: 1fr; }
    #empty { color: $text-muted; padding: 1 0; }
    """
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, scans: list[dict]) -> None:
        super().__init__()
        self.scans = scans

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label("Scan history", id="title")
            if not self.scans:
                yield Label("No past scans yet.", id="empty")
                return
            options = [
                Option(
                    f"#{row['id']}  {row['started_at']}  |  {row['scope']}  |  "
                    f"{row['open_count']} open",
                    id=str(row["id"]),
                )
                for row in self.scans
            ]
            yield OptionList(*options, id="scan-list")

    def on_mount(self) -> None:
        if self.scans:
            self.query_one("#scan-list", OptionList).focus()

    @on(OptionList.OptionSelected, "#scan-list")
    def _chosen(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(int(event.option.id))

    def action_dismiss(self) -> None:
        self.dismiss(None)
