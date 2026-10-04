"""Pure logic. Imports no Textual. Fully unit-testable without an event loop."""

from __future__ import annotations

import random
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

LEVELS = ("debug", "info", "warning", "error")


@dataclass(frozen=True, slots=True)
class Entry:
    at: datetime
    level: str
    message: str

    @property
    def row(self) -> tuple[str, str, str]:
        return (self.at.strftime("%H:%M:%S"), self.level, self.message)


def generate(count: int, *, seed: int = 0) -> list[Entry]:
    """Deterministic sample data, so tests and snapshots are stable."""
    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    words = ("connect", "retry", "timeout", "flush", "commit", "rollback",
             "resolve", "handshake", "upstream", "cache")
    entries: list[Entry] = []
    for index in range(count):
        entries.append(Entry(
            at=start + timedelta(seconds=index * 7),
            level=rng.choice(LEVELS),
            message=f"{rng.choice(words)} {rng.choice(words)} #{index}",
        ))
    return entries


def filter_entries(
    entries: Sequence[Entry], query: str = "", levels: Iterable[str] | None = None
) -> list[Entry]:
    """Case-insensitive substring filter plus a level whitelist."""
    needle = query.strip().lower()
    allowed = set(levels) if levels is not None else None
    return [
        entry
        for entry in entries
        if (allowed is None or entry.level in allowed)
        and (not needle or needle in entry.message.lower() or needle in entry.level)
    ]


def level_counts(entries: Sequence[Entry]) -> dict[str, int]:
    counts = dict.fromkeys(LEVELS, 0)
    for entry in entries:
        counts[entry.level] = counts.get(entry.level, 0) + 1
    return counts


def chunked(items: Sequence[Entry], size: int) -> Iterator[list[Entry]]:
    for start in range(0, len(items), size):
        yield list(items[start:start + size])
