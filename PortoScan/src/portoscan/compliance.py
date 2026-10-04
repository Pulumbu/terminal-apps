"""A simple rules pass over scan results. Pure; imports no Textual.

Flags open ports that expose risky / legacy / plaintext services -- a quick
hygiene check for your own infrastructure, not a vulnerability scanner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from portoscan.scan import Result

# port -> (label, severity)  severity in {"high", "medium", "low"}
RISKY_PORTS: dict[int, tuple[str, str]] = {
    21: ("FTP (plaintext)", "high"),
    23: ("Telnet (plaintext)", "high"),
    512: ("rexec", "high"),
    513: ("rlogin", "high"),
    514: ("rsh", "high"),
    69: ("TFTP", "high"),
    135: ("MSRPC", "medium"),
    139: ("NetBIOS", "medium"),
    445: ("SMB", "medium"),
    3389: ("RDP", "medium"),
    5900: ("VNC", "high"),
    1433: ("MSSQL (exposed DB)", "high"),
    1521: ("Oracle (exposed DB)", "high"),
    3306: ("MySQL (exposed DB)", "high"),
    5432: ("PostgreSQL (exposed DB)", "high"),
    6379: ("Redis (often no auth)", "high"),
    9200: ("Elasticsearch (exposed)", "high"),
    11211: ("Memcached (often no auth)", "high"),
    27017: ("MongoDB (exposed DB)", "high"),
}

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True, slots=True)
class Finding:
    severity: str
    host: str
    port: int
    service: str
    message: str
    evidence: str = ""        # redacted, human-readable; never raw secret values
    confirmed: bool = False   # True when actively verified (body/transport), not inferred


def check(results: Sequence[Result],
          rules: dict[int, tuple[str, str]] | None = None) -> list[Finding]:
    rules = rules if rules is not None else RISKY_PORTS
    findings: list[Finding] = []
    for result in results:
        if result.state != "open":
            continue
        rule = rules.get(result.port)
        if rule is None:
            continue
        label, severity = rule
        findings.append(Finding(
            severity, result.host, result.port, result.service or label,
            f"{label} exposed on {result.host}:{result.port}"))
    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.host, f.port))
    return findings


def summarize(findings: Sequence[Finding]) -> str:
    if not findings:
        return "No policy findings."
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    parts = [f"{counts.get(s, 0)} {s}" for s in ("high", "medium", "low") if counts.get(s)]
    return f"{len(findings)} finding(s): " + ", ".join(parts)
