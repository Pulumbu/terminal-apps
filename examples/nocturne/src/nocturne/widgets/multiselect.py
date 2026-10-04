"""A searchable, filterable multi-select.

The control real apps need and no framework ships. The important subtlety is
that selection state lives in this component, not in the ``SelectionList``:
filtering destroys and rebuilds the options, so a widget-held selection would
be silently lost.
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.fuzzy import Matcher
from textual.widgets import Input, Label, SelectionList
from textual.widgets.selection_list import Selection


class FilterableMultiSelect(Vertical):
    DEFAULT_CSS = """
    FilterableMultiSelect {
        height: auto; border: round $primary; padding: 0 1;
        & > Input { border: none; padding: 0; height: 1; }
        & > SelectionList { height: auto; max-height: 12; }
        & > #fms-count { color: $text-muted; height: 1; }
        &:focus-within { border: round $accent; }
    }
    """
    BINDINGS = [
        Binding("ctrl+a", "select_all", "All", show=False),
        Binding("ctrl+d", "clear_all", "None", show=False),
    ]

    def __init__(self, items: dict[str, str], *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._items = items
        self._selected: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Input(placeholder="type to filter…", id="fms-search")
        yield SelectionList[str](id="fms-list")
        yield Label("0 selected", id="fms-count")

    def on_mount(self) -> None:
        self._repopulate("")

    @property
    def selected(self) -> set[str]:
        return set(self._selected)

    def _repopulate(self, query: str) -> None:
        listing = self.query_one("#fms-list", SelectionList)
        matcher = Matcher(query) if query else None
        rows: list[tuple[float, Selection[str]]] = []
        for value, label in self._items.items():
            if matcher is None:
                rows.append((0.0, Selection(label, value, value in self._selected)))
                continue
            score = matcher.match(label)
            if score > 0:
                rows.append((score, Selection(matcher.highlight(label), value,
                                              value in self._selected)))
        rows.sort(key=lambda pair: -pair[0])
        listing.clear_options()
        if rows:
            listing.add_options([selection for _score, selection in rows])
        self._refresh_count()

    def _refresh_count(self) -> None:
        total = len(self._items)
        self.query_one("#fms-count", Label).update(f"{len(self._selected)} of {total} selected")

    @on(Input.Changed, "#fms-search")
    def _filter(self, event: Input.Changed) -> None:
        event.stop()
        self._repopulate(event.value)

    @on(SelectionList.SelectedChanged, "#fms-list")
    def _sync(self, event: SelectionList.SelectedChanged) -> None:
        event.stop()
        visible = {
            option.value
            for option in (event.selection_list.get_option_at_index(index)
                           for index in range(event.selection_list.option_count))
        }
        chosen = set(event.selection_list.selected)
        self._selected -= (visible - chosen)
        self._selected |= chosen
        self._refresh_count()

    def add_selection(self, value: str) -> None:
        """Select one value programmatically, preserving the current filter."""
        self._selected.add(value)
        self._repopulate(self.query_one("#fms-search", Input).value)

    def action_select_all(self) -> None:
        self._selected |= set(self._items)
        self._repopulate(self.query_one("#fms-search", Input).value)

    def action_clear_all(self) -> None:
        self._selected.clear()
        self._repopulate(self.query_one("#fms-search", Input).value)
