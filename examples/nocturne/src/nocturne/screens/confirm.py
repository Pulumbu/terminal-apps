"""A modal that returns a value."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import HorizontalGroup, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class Confirm(ModalScreen[bool]):
    CSS = """
    Confirm { align: center middle; background: $background 60%; }
    #box {
        width: 52; height: auto; padding: 1 2;
        border: round $primary; background: $surface;
    }
    #row { height: auto; align-horizontal: right; padding-top: 1; }
    """
    BINDINGS = [
        ("escape", "dismiss(False)", "Cancel"),
        ("enter", "dismiss(True)", "OK"),
    ]

    def __init__(self, question: str, *, danger: bool = False) -> None:
        super().__init__()
        self.question = question
        self.danger = danger

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label(self.question)
            with HorizontalGroup(id="row"):
                yield Button("Cancel", id="no", compact=True)
                yield Button(
                    "Delete" if self.danger else "OK",
                    id="yes",
                    variant="error" if self.danger else "primary",
                    compact=True,
                )

    @on(Button.Pressed, "#yes")
    def _yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#no")
    def _no(self) -> None:
        self.dismiss(False)
