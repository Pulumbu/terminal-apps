"""Headless (no-TUI) scan: same engine, written to a result folder.

Intended for cron / CI against hosts you own. Refuses to scan public addresses
unless --authorize is passed, mirroring the TUI's first-run acknowledgment.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
from argparse import Namespace

from portoscan.authorization import classify
from portoscan.compliance import check as compliance_check
from portoscan.compliance import summarize as compliance_summary
from portoscan.ports import PROFILE_BY_KEY, parse_ports
from portoscan.resolve import resolve_all
from portoscan.scan import PRESET_BY_KEY, Progress, scan
from portoscan.storage import save_scan
from portoscan.targets import expand


def resolve_ports(profile: str | None, spec: str | None) -> list[int]:
    ports: set[int] = set()
    for key in (profile or "").replace(",", " ").split():
        if key not in PROFILE_BY_KEY:
            raise ValueError(f"unknown profile '{key}'")
        ports.update(PROFILE_BY_KEY[key].ports)
    if spec:
        ports.update(parse_ports(spec))
    if not ports:
        ports.update(PROFILE_BY_KEY["top100"].ports)
    return sorted(ports)


def run(args: Namespace, paths) -> int:
    text = ""
    if args.targets_file:
        from pathlib import Path
        text = Path(args.targets_file).read_text("utf-8", "replace")
    if args.targets:
        text += "\n" + args.targets
    parsed = expand(text)
    if not parsed.hosts:
        print("portoscan: no targets", file=sys.stderr)
        return 2

    try:
        ports = resolve_ports(args.profile, args.ports)
    except ValueError as error:
        print(f"portoscan: {error}", file=sys.stderr)
        return 2

    hosts = parsed.hosts
    if not args.no_resolve:
        report = resolve_all(hosts)
        for name in report.failed:
            print(f"portoscan: could not resolve {name}", file=sys.stderr)
        hosts = report.ips
        if not hosts:
            print("portoscan: no targets resolved", file=sys.stderr)
            return 2

    scope_report = classify(hosts)
    if scope_report.has_public and not args.authorize:
        print("portoscan: scope includes public addresses. Re-run with --authorize "
              "to confirm you are authorized to scan them.", file=sys.stderr)
        return 3

    preset = PRESET_BY_KEY.get(args.rate, PRESET_BY_KEY["lan"])
    protocol = "udp" if args.udp else "tcp"
    total = len(hosts) * len(ports)
    print(f"portoscan: scanning {len(hosts)} host(s) x {len(ports)} port(s) "
          f"= {total} ({protocol}, {preset.label})", file=sys.stderr)

    last = [0.0]

    def on_progress(progress: Progress) -> None:
        import time
        now = time.monotonic()
        if now - last[0] >= 0.5 or progress.done == progress.total:
            last[0] = now
            print(f"\r  {progress.done}/{progress.total}  {progress.open} open  "
                  f"{progress.rate:.0f}/s", end="", file=sys.stderr, flush=True)

    results = asyncio.run(scan(
        hosts, ports, concurrency=preset.concurrency, timeout=preset.timeout,
        grab=not args.no_grab and protocol == "tcp",
        on_progress=on_progress, protocol=protocol))
    print("", file=sys.stderr)

    scope = f"{len(hosts)} hosts x {len(ports)} ports"
    from portoscan import results_io
    base = results_io.resolve_base(args.out or None,
                                   fallbacks=[paths.documents, paths.data])
    output = results_io.write_run(base, results, scope=scope, fmt=args.format)

    with contextlib.suppress(Exception):  # history is best-effort
        save_scan(paths.database, scope=scope, hosts=len(hosts),
                  ports=len(ports), results=results)

    opened = sum(1 for r in results if r.state == "open")
    findings = compliance_check(results)
    print(f"done: {len(results)} scanned, {opened} open")
    print(f"saved: {output.folder}")
    print(f"policy: {compliance_summary(findings)}")
    return 0
