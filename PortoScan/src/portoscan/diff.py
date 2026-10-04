"""Compare two scans. Pure; imports no Textual.

Keyed on (host, port), this reports how port states changed between a baseline
scan and a later one -- the useful signal being ports that newly opened or
newly closed, which is the basis of change monitoring on your own infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from portoscan.scan import Result


@dataclass(frozen=True, slots=True)
class Change:
    host: str
    port: int
    old_state: str      # "" when the endpoint was absent from the baseline
    new_state: str      # "" when the endpoint is absent from the current scan


@dataclass
class DiffReport:
    newly_open: list[Change] = field(default_factory=list)
    newly_closed: list[Change] = field(default_factory=list)
    changed: list[Change] = field(default_factory=list)   # any other state change
    still_open: list[Change] = field(default_factory=list)
    appeared: list[Change] = field(default_factory=list)   # in current, not baseline
    disappeared: list[Change] = field(default_factory=list)  # in baseline, not current

    @property
    def summary(self) -> str:
        return (f"+{len(self.newly_open)} open  "
                f"-{len(self.newly_closed)} closed  "
                f"~{len(self.changed)} changed")


def _index(results: Sequence[Result]) -> dict[tuple[str, int], str]:
    # last state wins if duplicated
    return {(r.host, r.port): r.state for r in results}


def diff_scans(baseline: Sequence[Result], current: Sequence[Result]) -> DiffReport:
    old = _index(baseline)
    new = _index(current)
    report = DiffReport()

    for key in sorted(new.keys() | old.keys()):
        host, port = key
        old_state = old.get(key, "")
        new_state = new.get(key, "")

        if old_state and not new_state:
            report.disappeared.append(Change(host, port, old_state, ""))
            continue
        if new_state and not old_state:
            report.appeared.append(Change(host, port, "", new_state))
            if new_state == "open":
                report.newly_open.append(Change(host, port, "", new_state))
            continue

        if old_state == new_state:
            if new_state == "open":
                report.still_open.append(Change(host, port, old_state, new_state))
            continue

        change = Change(host, port, old_state, new_state)
        if new_state == "open":
            report.newly_open.append(change)
        elif old_state == "open":
            report.newly_closed.append(change)
        else:
            report.changed.append(change)

    return report
