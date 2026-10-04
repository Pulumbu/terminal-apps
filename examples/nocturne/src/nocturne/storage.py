"""Atomic writes, typed settings with migration, and the SQLite connection."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Write ``text`` to ``path`` so that readers never see a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        if os.name != "nt":
            dir_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


CURRENT_SCHEMA_VERSION = 2


def migrate(raw: dict[str, Any]) -> dict[str, Any]:
    version = int(raw.get("schema_version", 1))
    if version < 2:
        raw["animations"] = "full" if raw.pop("fancy", True) else "none"
        raw["schema_version"] = 2
    return raw


@dataclass
class Settings:
    schema_version: int = CURRENT_SCHEMA_VERSION
    theme: str = "arctic"
    page_size: int = 50
    animations: str = "full"          # full | basic | none
    icons: str = "auto"               # auto | ascii | unicode | nerd
    recent: list[str] = field(default_factory=list)
    keymap: dict[str, str] = field(default_factory=dict)
    flags: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> Settings:
        try:
            raw = json.loads(path.read_text("utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        raw = migrate(raw)
        known = {f.name for f in fields(cls)}
        return cls(**{key: value for key, value in raw.items() if key in known})

    def save(self, path: Path) -> None:
        atomic_write_text(path, json.dumps(asdict(self), indent=2, sort_keys=True) + "\n")

    def push_recent(self, path: Path, limit: int = 10) -> None:
        resolved = str(path.resolve())
        recent = [item for item in self.recent if item != resolved]
        recent.insert(0, resolved)
        self.recent = recent[:limit]


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS entry (
    id      INTEGER PRIMARY KEY,
    at      TEXT    NOT NULL,
    level   TEXT    NOT NULL,
    message TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS entry_level ON entry(level);
"""


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    """A WAL-mode connection safe to hand to a worker thread."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5.0, isolation_level=None,
                           check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
    finally:
        conn.close()


class SingleInstance:
    """Advisory, cross-platform single-instance lock."""

    def __init__(self, lock_path: Path) -> None:
        self.lock_path = lock_path
        self._handle = None

    def __enter__(self) -> SingleInstance:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = open(self.lock_path, "a+b")
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self._handle.close()
            self._handle = None
            raise RuntimeError("another instance is already running") from error
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
