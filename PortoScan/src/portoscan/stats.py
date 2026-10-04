"""Rollups for the live stats panel. Pure; imports no Textual."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from portoscan.scan import Result


def counts_by_state(results: Sequence[Result]) -> dict[str, int]:
    counter: Counter[str] = Counter(r.state for r in results)
    return {state: counter.get(state, 0)
            for state in ("open", "closed", "filtered", "error")}


def top_services(results: Sequence[Result], limit: int = 6) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter(
        (r.service or "?") for r in results if r.state == "open")
    return counter.most_common(limit)


def per_host_open(results: Sequence[Result], limit: int = 6) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter(r.host for r in results if r.state == "open")
    return counter.most_common(limit)


def open_pairs(results: Sequence[Result]) -> list[tuple[str, int]]:
    """The (host, port) pairs that were open -- used by 're-scan open'."""
    return sorted({(r.host, r.port) for r in results if r.state == "open"})
