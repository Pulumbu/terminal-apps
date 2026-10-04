"""Resolve hostnames to IPs up front. Pure (blocking); call from a worker thread.

Resolving before the scan lets PortoScan report which names failed, and
de-duplicate targets that point at the same address.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass
class ResolveReport:
    ips: list[str] = field(default_factory=list)        # final, de-duplicated
    resolved: dict[str, list[str]] = field(default_factory=dict)  # name -> ips
    failed: list[str] = field(default_factory=list)     # names that did not resolve
    literal: int = 0                                    # inputs already IP literals


def _is_ip(token: str) -> bool:
    try:
        ipaddress.ip_address(token)
        return True
    except ValueError:
        return False


def resolve_host(name: str) -> list[str]:
    """Return every distinct A/AAAA address for ``name`` (may be empty)."""
    try:
        infos = socket.getaddrinfo(name, None, proto=socket.IPPROTO_TCP)
    except (OSError, UnicodeError):
        return []
    seen: list[str] = []
    for info in infos:
        address = info[4][0]
        if address not in seen:
            seen.append(address)
    return seen


def resolve_all(hosts: Sequence[str]) -> ResolveReport:
    report = ResolveReport()
    order: list[str] = []
    seen: set[str] = set()

    def add_ip(ip: str) -> None:
        if ip not in seen:
            seen.add(ip)
            order.append(ip)

    for host in hosts:
        if _is_ip(host):
            report.literal += 1
            add_ip(host)
            continue
        addresses = resolve_host(host)
        if not addresses:
            report.failed.append(host)
            continue
        report.resolved[host] = addresses
        for address in addresses:
            add_ip(address)

    report.ips = order
    return report
