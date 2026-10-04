"""A tiny modal that asks for a single line of text."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label


class PromptScreen(ModalScreen[str | None]):
    CSS = """
    PromptScreen { align: center middle; background: $background 60%; }
    #box { width: 56; height: auto; padding: 1 2; border: round $primary; background: $surface; }
    """

    def __init__(self, question: str, *, default: str = "") -> None:
        super().__init__()
        self.question = question
        self.default = default

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label(self.question)
            yield Input(self.default, id="value")

    def on_mount(self) -> None:
        self.query_one("#value", Input).focus()

    @on(Input.Submitted, "#value")
    def _submit(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        self.dismiss(value or None)

    def key_escape(self) -> None:
        self.dismiss(None)
