"""Fast CLI front end; imports the TUI lazily."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="portoscan",
        description="Authorized-use TCP port scanner. Scan only systems you own "
                    "or are authorized to test.",
    )
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--paths", action="store_true", help="print app-data paths")
    parser.add_argument("--theme", default=None)
    parser.add_argument("targets", nargs="?",
                        help="a targets .txt file to preload (optional)")

    headless = parser.add_argument_group(
        "headless scan (no TUI)",
        "Run a scan from the command line and write a 'PortoScan Result' folder.")
    headless.add_argument("--scan", action="store_true",
                          help="run a headless scan instead of the TUI")
    headless.add_argument("--targets", dest="targets_inline", metavar="LIST",
                          help="inline targets (IPs/hosts/CIDR/ranges, space/comma/newline)")
    headless.add_argument("--profile", metavar="KEYS",
                          help="port profile(s): top100,web,db,admin,mail,full")
    headless.add_argument("--ports", metavar="SPEC",
                          help="custom ports, e.g. 22,80,443,8000-8100")
    headless.add_argument("--rate", default="lan",
                          choices=["localhost", "lan", "internet"])
    headless.add_argument("--udp", action="store_true", help="UDP scan")
    headless.add_argument("--no-grab", action="store_true", help="skip banner grab")
    headless.add_argument("--no-resolve", action="store_true",
                          help="do not pre-resolve hostnames")
    headless.add_argument("--out", metavar="DIR",
                          help="base directory for the result folder")
    headless.add_argument("--format", default="txt", choices=["txt", "csv", "json"],
                          help="split-file format (report.html is always written)")
    headless.add_argument("--authorize", action="store_true",
                          help="confirm you are authorized to scan public addresses")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.version:
        from portoscan import __version__
        print(__version__)
        return 0

    from portoscan.logging_setup import setup_logging
    from portoscan.paths import Paths

    paths = Paths.resolve().ensure()
    setup_logging(paths.logs)

    if args.paths:
        for name in ("config", "data", "cache", "state", "logs"):
            print(f"{name:7}: {getattr(paths, name)}")
        return 0

    if args.scan or args.targets_inline or args.profile or args.ports:
        from portoscan import headless
        ns = argparse.Namespace(
            targets_file=args.targets, targets=args.targets_inline,
            profile=args.profile, ports=args.ports, rate=args.rate, udp=args.udp,
            no_grab=args.no_grab, no_resolve=args.no_resolve, out=args.out,
            format=args.format, authorize=args.authorize)
        return headless.run(ns, paths)

    targets = ""
    if args.targets:
        try:
            targets = Path(args.targets).read_text("utf-8", "replace")
        except OSError as error:
            print(f"could not read {args.targets}: {error}", file=sys.stderr)
            return 1

    from portoscan.app import PortoScan

    app = PortoScan(targets=targets)
    if args.theme:
        app.settings.theme = args.theme

    if os.environ.get("PORTOSCAN_SMOKE"):
        return _smoke(app)

    return app.run() or 0


def _smoke(app) -> int:
    from textual.widgets import DataTable

    app.settings.authorized_ack = True  # headless self-test; no modal
    async def run() -> None:
        async with app.run_test(size=(120, 36)) as pilot:
            await pilot.pause(0.3)
            assert app.query_one("#results", DataTable) is not None

    try:
        asyncio.run(run())
    except Exception:
        logging.getLogger(__name__).exception("smoke failed")
        raise
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
