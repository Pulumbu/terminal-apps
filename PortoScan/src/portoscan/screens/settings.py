from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import HorizontalGroup, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Select, Switch

from portoscan.ports import PROFILES
from portoscan.scan import PRESETS
from portoscan.storage import Settings


class SettingsScreen(ModalScreen[Settings | None]):
    CSS = """
    SettingsScreen { align: center middle; background: $background 60%; }
    #form { width: 70; height: auto; padding: 1 2; border: round $primary; background: $surface; }
    .row { height: auto; }
    .row > Label { width: 18; content-align-vertical: middle; }
    .row > Select { width: 1fr; }
    #buttons { align-horizontal: right; height: auto; padding-top: 1; }
    """

    def __init__(self, settings: Settings, themes: list[str]) -> None:
        super().__init__()
        self.settings = settings
        self.themes = themes

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="form"):
            yield from self._select("theme", "Theme",
                                    [(t, t) for t in self.themes], self.settings.theme)
            yield from self._select("rate", "Rate preset",
                                    [(p.label, p.key) for p in PRESETS],
                                    self.settings.rate_preset)
            yield from self._select("profile", "Default ports",
                                    [(p.label, p.key) for p in PROFILES],
                                    self.settings.port_profile)
            yield from self._select("anim", "Animations",
                                    [(x, x) for x in ("full", "basic", "none")],
                                    self.settings.animations)
            yield from self._select("icons", "Icons",
                                    [(x, x) for x in ("auto", "unicode", "ascii", "nerd")],
                                    self.settings.icons)
            with HorizontalGroup(classes="row"):
                yield Label("Grab banners")
                yield Switch(self.settings.grab_banners, id="grab")
            with HorizontalGroup(id="buttons"):
                yield Button("Cancel", id="cancel", compact=True)
                yield Button("Save", id="save", variant="primary", compact=True)

    def _select(self, ident, label, options, value):
        with HorizontalGroup(classes="row"):
            yield Label(label)
            yield Select(options, value=value, allow_blank=False, id=ident)

    @on(Button.Pressed, "#save")
    def _save(self) -> None:
        self.settings.theme = str(self.query_one("#theme", Select).value)
        self.settings.rate_preset = str(self.query_one("#rate", Select).value)
        self.settings.port_profile = str(self.query_one("#profile", Select).value)
        self.settings.animations = str(self.query_one("#anim", Select).value)
        self.settings.icons = str(self.query_one("#icons", Select).value)
        self.settings.grab_banners = self.query_one("#grab", Switch).value
        self.dismiss(self.settings)

    @on(Button.Pressed, "#cancel")
    def _cancel(self) -> None:
        self.dismiss(None)
