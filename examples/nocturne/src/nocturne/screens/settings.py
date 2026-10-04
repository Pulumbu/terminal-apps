"""A settings form: validation, disabled submit, per-field errors."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalScroll
from textual.screen import ModalScreen
from textual.validation import Integer, ValidationResult
from textual.widgets import Button, Input, Label, Select, Switch

from nocturne.storage import Settings


class SettingsScreen(ModalScreen[Settings | None]):
    AUTO_FOCUS = "#page-size"
    CSS = """
    SettingsScreen { align: center middle; background: $background 60%; }
    #form {
        width: 68; height: auto; padding: 1 2;
        border: round $primary; background: $surface;
    }
    .row { height: auto; }
    .row > Label { width: 16; content-align-vertical: middle; }
    .row > Input, .row > Select { width: 1fr; }
    .field-error { color: $text-error; height: auto; padding-left: 16; }
    #buttons { align-horizontal: right; height: auto; padding-top: 1; }
    """

    def __init__(self, settings: Settings, themes: list[str]) -> None:
        super().__init__()
        self.settings = settings
        self.themes = themes

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="form"):
            with HorizontalGroup(classes="row"):
                yield Label("Page size")
                yield Input(
                    str(self.settings.page_size),
                    id="page-size",
                    type="integer",
                    validators=[Integer(1, 1000, failure_description="1-1000")],
                    validate_on=["changed"],
                )
            yield Label("", id="page-size-error", classes="field-error")

            with HorizontalGroup(classes="row"):
                yield Label("Theme")
                yield Select(
                    [(name, name) for name in self.themes],
                    value=self.settings.theme if self.settings.theme in self.themes else None,
                    allow_blank=False,
                    id="theme",
                )
            with HorizontalGroup(classes="row"):
                yield Label("Animations")
                yield Select(
                    [(name, name) for name in ("full", "basic", "none")],
                    value=self.settings.animations,
                    allow_blank=False,
                    id="animations",
                )
            with HorizontalGroup(classes="row"):
                yield Label("Icons")
                yield Select(
                    [(name, name) for name in ("auto", "unicode", "ascii", "nerd")],
                    value=self.settings.icons,
                    allow_blank=False,
                    id="icons",
                )
            with HorizontalGroup(classes="row"):
                yield Label("Zebra stripes")
                yield Switch(self.settings.flags.get("zebra", True), id="zebra")

            with HorizontalGroup(id="buttons"):
                yield Button("Cancel", id="cancel", compact=True)
                yield Button("Save", id="save", variant="primary", compact=True)

    def _valid(self) -> bool:
        return all(
            (widget.validate(widget.value) or ValidationResult.success()).is_valid
            for widget in self.query(Input)
        )

    @on(Input.Changed, "#page-size")
    def _revalidate(self, event: Input.Changed) -> None:
        bad = event.validation_result is not None and not event.validation_result.is_valid
        event.input.set_class(bad, "-invalid")
        self.query_one("#page-size-error", Label).update(
            "" if not bad else ", ".join(event.validation_result.failure_descriptions)
        )
        self.query_one("#save", Button).disabled = not self._valid()

    @on(Button.Pressed, "#save")
    def _save(self) -> None:
        if not self._valid():
            return
        self.settings.page_size = int(self.query_one("#page-size", Input).value)
        self.settings.theme = str(self.query_one("#theme", Select).value)
        self.settings.animations = str(self.query_one("#animations", Select).value)
        self.settings.icons = str(self.query_one("#icons", Select).value)
        self.settings.flags["zebra"] = self.query_one("#zebra", Switch).value
        self.dismiss(self.settings)

    @on(Button.Pressed, "#cancel")
    def _cancel(self) -> None:
        self.dismiss(None)
