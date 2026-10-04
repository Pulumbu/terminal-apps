"""Deterministic harness for snapshotting FilterableMultiSelect."""

from textual.app import App, ComposeResult

from nocturne.widgets import FilterableMultiSelect

ITEMS = {
    "unit": "Unit tests",
    "integration": "Integration tests",
    "e2e": "End-to-end tests",
    "smoke": "Smoke tests",
    "perf": "Performance tests",
}


class MultiSelectHarness(App[None]):
    CSS = "Screen { padding: 1 2; } FilterableMultiSelect { width: 46; }"

    def compose(self) -> ComposeResult:
        yield FilterableMultiSelect(ITEMS, id="levels")


if __name__ == "__main__":
    MultiSelectHarness().run()
