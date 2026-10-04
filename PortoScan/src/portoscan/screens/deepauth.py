"""A stronger authorization gate for active verification."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import HorizontalGroup, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

ACK = ("I am a licensed penetration tester or the system owner, and I am "
       "authorized to ACTIVELY probe these hosts (fetch sensitive paths and "
       "negotiate the SSH transport). This is for my own or contracted sites.")


class DeepAuthorizeScreen(ModalScreen[bool]):
    CSS = """
    DeepAuthorizeScreen { align: center middle; background: $background 75%; }
    #box { width: 74; height: auto; padding: 1 2; border: thick $error; background: $surface; }
    #title { text-style: bold; color: $text-error; }
    #ack { padding: 1 0; }
    #row { height: auto; align-horizontal: right; padding-top: 1; }
    """
    BINDINGS = [("escape", "dismiss(False)", "Decline")]

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label("Active verification — highly authorized use only", id="title")
            yield Static(
                "Verification sends real requests to the targets: it fetches "
                "sensitive paths and speaks the SSH protocol to confirm findings. "
                "Only run this against systems you own or are contracted to test.",
                id="ack")
            yield Static(f"[b]{ACK}[/b]")
            with HorizontalGroup(id="row"):
                yield Button("Cancel", id="no", compact=True)
                yield Button("I am authorized — verify", id="yes",
                             variant="error", compact=True)

    @on(Button.Pressed, "#yes")
    def _yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#no")
    def _no(self) -> None:
        self.dismiss(False)
