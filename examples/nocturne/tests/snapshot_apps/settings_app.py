"""Deterministic harness for snapshotting the settings form."""

from textual.app import App, ComposeResult

from nocturne.screens import SettingsScreen
from nocturne.storage import Settings
from nocturne.themes import ALL_THEMES


class SettingsHarness(App[None]):
    def compose(self) -> ComposeResult:
        return iter(())

    def on_mount(self) -> None:
        for theme in ALL_THEMES:
            self.register_theme(theme)
        self.theme = "arctic"
        self.push_screen(SettingsScreen(Settings(), ["arctic", "high-contrast", "nord"]))


if __name__ == "__main__":
    SettingsHarness().run()
