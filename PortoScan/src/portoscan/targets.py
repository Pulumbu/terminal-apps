"""Parse and expand user-supplied scan targets.

Accepted tokens (one per line or comma-separated):
    * a hostname            example.internal
    * an IPv4/IPv6 address  10.0.0.5, ::1
    * a CIDR range you own   10.0.0.0/24
    * an inclusive dotted range  192.168.1.10-20

Blank lines and ``#`` comments are ignored. Expansion is capped so a wide
CIDR cannot blow up memory or launch an unbounded scan by accident.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass

DEFAULT_MAX_HOSTS = 65536
_RANGE_RE = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){3})-(\d{1,3})$")


@dataclass(frozen=True, slots=True)
class ParseResult:
    hosts: list[str]
    errors: list[str]
    truncated: bool


def _tokens(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        line = line.split("#", 1)[0]
        for token in line.replace(",", " ").split():
            out.append(token.strip())
    return [t for t in out if t]


def expand(text: str, *, max_hosts: int = DEFAULT_MAX_HOSTS) -> ParseResult:
    hosts: list[str] = []
    seen: set[str] = set()
    errors: list[str] = []
    truncated = False

    def add(value: str) -> bool:
        if value in seen:
            return True
        if len(hosts) >= max_hosts:
            return False
        seen.add(value)
        hosts.append(value)
        return True

    for token in _tokens(text):
        if truncated:
            break
        try:
            if "/" in token:
                network = ipaddress.ip_network(token, strict=False)
                iterator = network.hosts() if network.num_addresses > 2 else iter(network)
                for address in iterator:
                    if not add(str(address)):
                        truncated = True
                        break
                continue

            match = _RANGE_RE.match(token)
            if match:
                base, last = match.group(1), int(match.group(2))
                first = ipaddress.ip_address(base)
                prefix = base.rsplit(".", 1)[0]
                end = ipaddress.ip_address(f"{prefix}.{last}")
                if int(end) < int(first):
                    errors.append(f"{token}: range end is before start")
                    continue
                current = int(first)
                while current <= int(end):
                    if not add(str(ipaddress.ip_address(current))):
                        truncated = True
                        break
                    current += 1
                continue

            # plain IP (validate) or hostname (accept as-is)
            try:
                ipaddress.ip_address(token)
            except ValueError:
                if not _looks_like_hostname(token):
                    errors.append(f"{token}: not an IP, CIDR, range or hostname")
                    continue
            add(token)
        except ValueError as error:
            errors.append(f"{token}: {error}")

    return ParseResult(hosts=hosts, errors=errors, truncated=truncated)


def _looks_like_hostname(token: str) -> bool:
    if len(token) > 253 or not token:
        return False
    labels = token.rstrip(".").split(".")
    allowed = re.compile(r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$")
    return all(allowed.match(label) for label in labels)
