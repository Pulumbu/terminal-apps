"""Scope classification and the authorized-use gate.

PortoScan scans only what the operator supplies. This module classifies a set
of targets so the UI can keep private/loopback scopes frictionless while asking
for an explicit acknowledgment the first time, and reminding (never silently)
when a scope reaches public addresses.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable
from dataclasses import dataclass

ACK_TEXT = (
    "I will use PortoScan only against systems I own or have explicit, "
    "written authorization to test."
)


@dataclass(frozen=True, slots=True)
class ScopeReport:
    total: int
    private: int
    loopback: int
    public: int
    hostnames: int

    @property
    def has_public(self) -> bool:
        return self.public > 0 or self.hostnames > 0

    @property
    def all_local(self) -> bool:
        return self.total > 0 and not self.has_public


def classify(targets: Iterable[str]) -> ScopeReport:
    private = loopback = public = hostnames = total = 0
    for target in targets:
        total += 1
        try:
            address = ipaddress.ip_address(target)
        except ValueError:
            hostnames += 1  # a hostname can resolve anywhere -> treat as non-local
            continue
        if address.is_loopback:
            loopback += 1
        elif address.is_private or address.is_link_local:
            private += 1
        else:
            public += 1
    return ScopeReport(total, private, loopback, public, hostnames)
