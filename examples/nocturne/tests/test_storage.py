"""Storage tests: atomic writes, migration, corruption tolerance, SQLite."""

import json

import pytest

from nocturne.paths import Paths
from nocturne.storage import Settings, SingleInstance, atomic_write_text, connect


def test_paths_honour_the_env_override():
    paths = Paths.resolve().ensure()
    for directory in (paths.config, paths.data, paths.cache, paths.state, paths.logs):
        assert directory.is_dir()


def test_atomic_write_leaves_no_temp_files():
    paths = Paths.resolve().ensure()
    target = paths.config / "x.json"
    atomic_write_text(target, '{"a": 1}')
    assert json.loads(target.read_text()) == {"a": 1}
    assert not list(paths.config.glob("*.tmp"))


def test_v1_settings_migrate_to_v2():
    paths = Paths.resolve().ensure()
    atomic_write_text(
        paths.settings_file,
        json.dumps({"schema_version": 1, "fancy": False, "theme": "nord", "junk": 1}),
    )
    settings = Settings.load(paths.settings_file)
    assert settings.schema_version == 2
    assert settings.animations == "none"
    assert settings.theme == "nord"
    assert not hasattr(settings, "junk")


def test_corrupt_settings_fall_back_to_defaults():
    paths = Paths.resolve().ensure()
    paths.settings_file.write_text("{ not json")
    assert Settings.load(paths.settings_file).theme == Settings().theme


def test_settings_round_trip():
    paths = Paths.resolve().ensure()
    settings = Settings()
    settings.push_recent(paths.config / "a.log")
    settings.push_recent(paths.config / "b.log")
    settings.push_recent(paths.config / "a.log")
    settings.save(paths.settings_file)
    reloaded = Settings.load(paths.settings_file)
    assert reloaded.recent[0].endswith("a.log")
    assert len(reloaded.recent) == 2


def test_sqlite_is_in_wal_mode():
    paths = Paths.resolve().ensure()
    with connect(paths.database) as conn:
        conn.execute("INSERT INTO entry(at, level, message) VALUES (?,?,?)",
                     ("2026-01-01T00:00:00Z", "info", "hello"))
        row = conn.execute("SELECT level, message FROM entry").fetchone()
        assert row["level"] == "info" and row["message"] == "hello"
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_single_instance_is_exclusive():
    paths = Paths.resolve().ensure()
    with SingleInstance(paths.lock_file), pytest.raises(RuntimeError), SingleInstance(
        paths.lock_file
    ):
        pass
    with SingleInstance(paths.lock_file):
        pass
