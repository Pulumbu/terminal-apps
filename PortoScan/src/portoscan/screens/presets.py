"""Pick (or delete) a saved scan preset."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList
from textual.widgets.option_list import Option


class PresetsScreen(ModalScreen[tuple[str, str] | None]):
    """Dismisses with ("load"|"delete", preset_name), or None."""

    CSS = """
    PresetsScreen { align: center middle; background: $background 60%; }
    #box { width: 64; height: 22; padding: 1 2; border: round $primary; background: $surface; }
    #title { text-style: bold; color: $text-primary; }
    OptionList { height: 1fr; }
    #hint { color: $text-muted; }
    #empty { color: $text-muted; padding: 1 0; }
    """
    BINDINGS = [
        ("escape", "close", "Close"),
        ("delete,d", "delete", "Delete"),
    ]

    def __init__(self, names: list[str]) -> None:
        super().__init__()
        self.names = names

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label("Saved presets", id="title")
            if not self.names:
                yield Label("No presets yet. Save one with ctrl+s.", id="empty")
                return
            yield OptionList(*(Option(name, id=name) for name in self.names),
                             id="preset-list")
            yield Label("enter: load   |   d / delete: remove", id="hint")

    def on_mount(self) -> None:
        if self.names:
            self.query_one("#preset-list", OptionList).focus()

    @on(OptionList.OptionSelected, "#preset-list")
    def _load(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(("load", event.option.id or ""))

    def action_delete(self) -> None:
        if not self.names:
            return
        option_list = self.query_one("#preset-list", OptionList)
        if option_list.highlighted is None:
            return
        name = option_list.get_option_at_index(option_list.highlighted).id or ""
        self.dismiss(("delete", name))

    def action_close(self) -> None:
        self.dismiss(None)
