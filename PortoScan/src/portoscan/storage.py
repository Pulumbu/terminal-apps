"""Settings, scan history (SQLite/WAL) and atomic writes (handbook section 22)."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from portoscan.scan import Result

CURRENT_SCHEMA_VERSION = 1


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
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


@dataclass
class Settings:
    schema_version: int = CURRENT_SCHEMA_VERSION
    theme: str = "midnight"
    rate_preset: str = "lan"
    port_profile: str = "top100"
    animations: str = "full"       # full | basic | none
    icons: str = "auto"            # auto | unicode | ascii | nerd
    grab_banners: bool = True
    authorized_ack: bool = False
    recent_files: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> Settings:
        try:
            raw = json.loads(path.read_text("utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return cls()
        if not isinstance(raw, dict):
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{key: value for key, value in raw.items() if key in known})

    def save(self, path: Path) -> None:
        atomic_write_text(path, json.dumps(asdict(self), indent=2, sort_keys=True) + "\n")

    def remember_file(self, file_path: str, limit: int = 10) -> None:
        self.recent_files = [file_path, *[f for f in self.recent_files if f != file_path]][:limit]


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS scan (
    id         INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL,
    scope      TEXT NOT NULL,
    hosts      INTEGER NOT NULL,
    ports      INTEGER NOT NULL,
    open_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS result (
    scan_id    INTEGER NOT NULL REFERENCES scan(id) ON DELETE CASCADE,
    host       TEXT NOT NULL,
    port       INTEGER NOT NULL,
    state      TEXT NOT NULL,
    service    TEXT NOT NULL DEFAULT '',
    latency_ms REAL NOT NULL DEFAULT 0,
    banner     TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS result_scan ON result(scan_id);
"""


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5.0, isolation_level=None,
                           check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
    finally:
        conn.close()


def save_scan(path: Path, *, scope: str, hosts: int, ports: int,
              results: Sequence[Result]) -> int:
    open_count = sum(1 for r in results if r.state == "open")
    with connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO scan(started_at, scope, hosts, ports, open_count) "
            "VALUES (?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"),
             scope, hosts, ports, open_count),
        )
        scan_id = int(cur.lastrowid)
        conn.executemany(
            "INSERT INTO result(scan_id, host, port, state, service, latency_ms, banner) "
            "VALUES (?,?,?,?,?,?,?)",
            [(scan_id, r.host, r.port, r.state, r.service, r.latency_ms, r.banner)
             for r in results],
        )
    return scan_id


def recent_scans(path: Path, limit: int = 20) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT id, started_at, scope, hosts, ports, open_count "
            "FROM scan ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
