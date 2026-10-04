"""Map an SSH banner to known OpenSSH CVEs. Pure; no network.

This is *informational* version matching against the banner the scan already
grabbed. Banners can be back-patched by distributions, so a match is a prompt
to verify, not proof of vulnerability. No exploitation is performed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from portoscan.compliance import Finding

if TYPE_CHECKING:
    from collections.abc import Sequence

    from portoscan.scan import Result

_OPENSSH_RE = re.compile(r"OpenSSH[_-](\d+)\.(\d+)(?:p(\d+))?", re.IGNORECASE)


def parse_openssh(banner: str) -> tuple[int, int, int] | None:
    """'SSH-2.0-OpenSSH_9.6p1 Ubuntu' -> (9, 6, 1); None if not OpenSSH."""
    match = _OPENSSH_RE.search(banner or "")
    if not match:
        return None
    major, minor, patch = match.group(1), match.group(2), match.group(3)
    return (int(major), int(minor), int(patch) if patch else 0)


@dataclass(frozen=True, slots=True)
class CVE:
    cve: str
    severity: str
    low: tuple[int, int, int]    # inclusive
    high: tuple[int, int, int]   # exclusive (fixed-in version)
    summary: str

    def applies(self, version: tuple[int, int, int]) -> bool:
        return self.low <= version < self.high


# A small, notable set. Ranges are approximate (fixed-in as the upper bound).
KNOWN_CVES: tuple[CVE, ...] = (
    CVE("CVE-2024-6387", "high", (8, 5, 1), (9, 8, 1),
        "regreSSHion: sshd signal-handler race (glibc Linux) -> potential RCE"),
    CVE("CVE-2023-48795", "medium", (0, 0, 0), (9, 6, 1),
        "Terrapin: SSH transport prefix-truncation downgrade"),
    CVE("CVE-2023-38408", "high", (0, 0, 0), (9, 3, 2),
        "ssh-agent PKCS#11 forwarding -> remote code execution"),
    CVE("CVE-2021-41617", "medium", (6, 2, 0), (8, 8, 1),
        "sshd AuthorizedKeysCommand/AuthorizedPrincipalsCommand privilege handling"),
    CVE("CVE-2020-15778", "medium", (0, 0, 0), (8, 4, 1),
        "scp: command injection via crafted path (legacy scp protocol)"),
    CVE("CVE-2018-15473", "medium", (0, 0, 0), (7, 7, 1),
        "Username enumeration via auth timing/response differences"),
    CVE("CVE-2016-0777", "medium", (5, 4, 0), (7, 1, 2),
        "Client roaming: private-key information leak"),
)


def check_banner(banner: str) -> list[CVE]:
    version = parse_openssh(banner)
    if version is None:
        return []
    return [cve for cve in KNOWN_CVES if cve.applies(version)]


def scan(results: Sequence[Result]) -> list[Finding]:
    """Return informational CVE findings for open SSH ports in `results`."""
    findings: list[Finding] = []
    for result in results:
        if result.state != "open":
            continue
        if "openssh" not in (result.banner or "").lower():
            continue
        version = parse_openssh(result.banner)
        vtext = (f"{version[0]}.{version[1]}p{version[2]}" if version else "?")
        for cve in check_banner(result.banner):
            findings.append(Finding(
                cve.severity, result.host, result.port,
                result.service or "ssh",
                f"{cve.cve} (OpenSSH {vtext}, informational): {cve.summary}"))
    return findings
