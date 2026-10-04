"""Fast CLI front end. Imports the TUI only when the TUI is wanted."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nocturne", description="Terminal log explorer")
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    parser.add_argument("--theme", default=None, help="start with this theme")
    parser.add_argument("--count", type=int, default=2000, help="how many sample entries")
    parser.add_argument("--debug", action="store_true", help="verbose file logging")
    parser.add_argument("--inline", action="store_true", help="render under the shell prompt")
    parser.add_argument("--paths", action="store_true", help="print resolved app paths")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.version:
        from nocturne import __version__

        print(__version__)
        return 0

    from nocturne.logging_setup import setup_logging
    from nocturne.paths import Paths, is_frozen

    paths = Paths.resolve().ensure()
    setup_logging(paths.logs, debug=args.debug)

    if args.paths:
        print(f"frozen:  {is_frozen()}")
        for name in ("config", "data", "cache", "state", "logs"):
            print(f"{name:7}: {getattr(paths, name)}")
        return 0

    from nocturne.app import Nocturne

    app = Nocturne(count=args.count, theme_override=args.theme)

    if os.environ.get("NOCTURNE_SMOKE"):
        return _smoke(app)

    return app.run(inline=args.inline) or 0


def _smoke(app) -> int:
    """Headless self-test: proves a built bundle actually runs."""
    from textual.widgets import DataTable

    async def run() -> None:
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.5)
            table = app.screen.query_one("#rows", DataTable)
            assert table.row_count > 0, "no rows were loaded"
            await pilot.press("ctrl+t")
            await pilot.pause(0.2)
            svg = app.export_screenshot()
            assert "<svg" in svg

    try:
        asyncio.run(run())
    except Exception:
        logging.getLogger(__name__).exception("smoke test failed")
        raise
    print(f"SMOKE OK  frozen={getattr(sys, 'frozen', False)}  theme={app.theme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
