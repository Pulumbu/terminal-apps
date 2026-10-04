"""File-only logging (handbook section 22.8). Never a StreamHandler in a TUI."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_dir: Path, *, debug: bool = False) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        log_dir / "portoscan.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
