"""Resource and application-data path resolution.

Three-tier resolution, so the same binary works as a portable install, under a
test harness, and as a normal OS-conventional install:

    1. portable  -- a ``portable.txt`` next to the executable
    2. override  -- ``$NOCTURNE_HOME``
    3. OS        -- platformdirs
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "Nocturne"
APP_AUTHOR = "Acme"
DIRS = PlatformDirs(appname=APP_NAME, appauthor=APP_AUTHOR, roaming=True)


def is_frozen() -> bool:
    """True when running from a PyInstaller (or similar) bundle."""
    return bool(getattr(sys, "frozen", False))


def resource_path(relative: str | os.PathLike[str]) -> Path:
    """Locate a read-only shipped asset, frozen or not.

    Never write to the result: under ``--onefile`` it lives in a temporary
    directory that is deleted when the process exits.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = Path(__file__).resolve().parent
    return Path(base) / relative


def portable_root() -> Path | None:
    if not is_frozen():
        return None
    exe_dir = Path(sys.executable).resolve().parent
    return exe_dir if (exe_dir / "portable.txt").exists() else None


@dataclass(frozen=True)
class Paths:
    config: Path
    data: Path
    cache: Path
    state: Path
    logs: Path

    @classmethod
    def resolve(cls) -> Paths:
        root = portable_root()
        if root is not None:
            base = root / "userdata"
            return cls(base / "config", base / "data", base / "cache",
                       base / "state", base / "logs")

        override = os.environ.get(f"{APP_NAME.upper()}_HOME")
        if override:
            base = Path(override).expanduser()
            return cls(base / "config", base / "data", base / "cache",
                       base / "state", base / "logs")

        return cls(
            Path(DIRS.user_config_dir),
            Path(DIRS.user_data_dir),
            Path(DIRS.user_cache_dir),
            Path(DIRS.user_state_dir),
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
        return self.data / "nocturne.sqlite3"

    @property
    def lock_file(self) -> Path:
        return self.state / "nocturne.lock"
