"""Resource and application-data path resolution (handbook sections 22, 23)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "PortoScan"
APP_AUTHOR = "PortoScan"
DIRS = PlatformDirs(appname=APP_NAME, appauthor=APP_AUTHOR, roaming=True)


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_path(relative: str | os.PathLike[str]) -> Path:
    """Locate a read-only shipped asset, frozen or not. Never write here."""
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = Path(__file__).resolve().parent
    return Path(base) / relative


@dataclass(frozen=True)
class Paths:
    config: Path
    data: Path
    cache: Path
    state: Path
    logs: Path

    @classmethod
    def resolve(cls) -> Paths:
        override = os.environ.get("PORTOSCAN_HOME")
        if override:
            base = Path(override).expanduser()
            return cls(base / "config", base / "data", base / "cache",
                       base / "state", base / "logs")
        return cls(
            Path(DIRS.user_config_dir), Path(DIRS.user_data_dir),
            Path(DIRS.user_cache_dir), Path(DIRS.user_state_dir),
            Path(DIRS.user_log_dir),
        )

    def ensure(self) -> Paths:
        for path in (self.config, self.data, self.cache, self.state, self.logs):
            path.mkdir(parents=True, exist_ok=True)
        return self

    @property
    def settings_file(self) -> Path:
        return self.config / "settings.json"

    @property
    def database(self) -> Path:
        return self.data / "portoscan.sqlite3"
