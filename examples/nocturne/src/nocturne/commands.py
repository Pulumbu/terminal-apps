"""A command-palette provider."""

from __future__ import annotations

from functools import partial

from textual.command import DiscoveryHit, Hit, Hits, Provider

from nocturne.domain import LEVELS


class NocturneCommands(Provider):
    """Expose level filters and app actions in the command palette."""

    async def startup(self) -> None:
        self._commands: list[tuple[str, object, str]] = [
            (f"Filter: {level}", partial(self.app.filter_to_level, level),
             f"Show only {level} entries")
            for level in LEVELS
        ]
        self._commands += [
            ("Filter: all levels", partial(self.app.filter_to_level, None), "Clear the filter"),
            ("Reload entries", self.app.action_reload, "Re-read the data source"),
            ("Settings", self.app.action_settings, "Open the settings form"),
            ("Clear cache", self.app.action_clear_cache, "Delete derived files"),
        ]

    async def discover(self) -> Hits:
        for display, command, help_text in self._commands[:5]:
            yield DiscoveryHit(display, command, help=help_text)

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for display, command, help_text in self._commands:
            score = matcher.match(display)
            if score > 0:
                yield Hit(score, matcher.highlight(display), command, help=help_text)
