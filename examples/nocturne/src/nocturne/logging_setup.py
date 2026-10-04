"""File-only logging. A StreamHandler would corrupt the rendered screen."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_dir: Path, *, level: int = logging.INFO, debug: bool = False) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        log_dir / "nocturne.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else level)
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
