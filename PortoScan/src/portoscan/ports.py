"""Port profiles and custom port-spec parsing. Pure; imports no Textual."""

from __future__ import annotations

from dataclasses import dataclass

# nmap's real top-100 TCP ports, in popularity order
# (github.com/HeckerBirb/top-nmap-ports-csv).
TOP_100: tuple[int, ...] = (
    80, 23, 443, 21, 22, 25, 3389, 110, 445, 139, 143, 53, 135, 3306, 8080,
    1723, 111, 995, 993, 5900, 1025, 587, 8888, 199, 1720, 465, 548, 113, 81, 6001,
    10000, 514, 5060, 179, 1026, 2000, 8443, 8000, 32768, 554, 26, 1433, 49152, 2001, 515,
    8008, 49154, 1027, 5666, 646, 5000, 5631, 631, 49153, 8081, 2049, 88, 79, 5800, 106,
    2121, 1110, 49155, 6000, 513, 990, 5357, 427, 49156, 543, 544, 5101, 144, 7, 389,
    8009, 3128, 444, 9999, 5009, 7070, 5190, 3000, 5432, 1900, 3986, 13, 1029, 9, 5051,
    6646, 49157, 1028, 873, 1755, 2717, 4899, 9100, 119, 37,
)

WEB = (80, 443, 3000, 5000, 8000, 8008, 8080, 8443, 8888)
DATABASES = (1433, 1521, 3306, 5432, 6379, 9200, 11211, 27017)
REMOTE_ADMIN = (22, 23, 3389, 5900, 5985, 5986)
MAIL = (25, 110, 143, 465, 587, 993, 995)


@dataclass(frozen=True, slots=True)
class Profile:
    key: str
    label: str
    ports: tuple[int, ...]
    warn: bool = False


PROFILES: tuple[Profile, ...] = (
    Profile("top100", "Top 100 (fast)", TOP_100),
    Profile("web", "Web", WEB),
    Profile("db", "Databases", DATABASES),
    Profile("admin", "Remote admin", REMOTE_ADMIN),
    Profile("mail", "Mail", MAIL),
    Profile("full", "Full 1-65535 (slow)", tuple(range(1, 65536)), warn=True),
)
PROFILE_BY_KEY = {profile.key: profile for profile in PROFILES}


def parse_ports(spec: str) -> list[int]:
    """Parse ``22,80,443,8000-8100`` into a sorted, de-duplicated port list.

    Raises ``ValueError`` on anything out of 1-65535 or malformed.
    """
    ports: set[int] = set()
    for raw in spec.replace(",", " ").split():
        token = raw.strip()
        if not token:
            continue
        if "-" in token:
            start_text, _, end_text = token.partition("-")
            start, end = _port(start_text), _port(end_text)
            if end < start:
                raise ValueError(f"{token}: range end before start")
            ports.update(range(start, end + 1))
        else:
            ports.add(_port(token))
    return sorted(ports)


def _port(text: str) -> int:
    try:
        value = int(text)
    except ValueError as error:
        raise ValueError(f"{text!r} is not a port number") from error
    if not 1 <= value <= 65535:
        raise ValueError(f"{value} is outside 1-65535")
    return value
