"""First-run authorized-use acknowledgment."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import HorizontalGroup, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from portoscan.authorization import ACK_TEXT


class AuthorizeScreen(ModalScreen[bool]):
    CSS = """
    AuthorizeScreen { align: center middle; background: $background 70%; }
    #box { width: 70; height: auto; padding: 1 2; border: round $warning; background: $surface; }
    #title { text-style: bold; color: $text-warning; }
    #ack { padding: 1 0; }
    #row { height: auto; align-horizontal: right; padding-top: 1; }
    """
    BINDINGS = [("escape", "dismiss(False)", "Decline")]

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label("Authorized use only", id="title")
            yield Static(
                "PortoScan scans only the targets you supply. Scanning systems "
                "you do not own or are not authorized to test may be illegal.",
                id="ack",
            )
            yield Static(f"[b]{ACK_TEXT}[/b]")
            with HorizontalGroup(id="row"):
                yield Button("Decline (quit)", id="no", compact=True)
                yield Button("I understand", id="yes", variant="primary", compact=True)

    @on(Button.Pressed, "#yes")
    def _yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#no")
    def _no(self) -> None:
        self.dismiss(False)
