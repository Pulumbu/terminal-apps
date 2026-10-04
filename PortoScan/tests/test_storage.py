import json

from portoscan.paths import Paths
from portoscan.scan import Result
from portoscan.storage import Settings, recent_scans, save_scan


def test_settings_round_trip_and_corruption():
    paths = Paths.resolve().ensure()
    settings = Settings()
    settings.theme = "amber-crt"
    settings.remember_file("/tmp/a.txt")
    settings.remember_file("/tmp/b.txt")
    settings.remember_file("/tmp/a.txt")
    settings.save(paths.settings_file)
    loaded = Settings.load(paths.settings_file)
    assert loaded.theme == "amber-crt"
    assert loaded.recent_files == ["/tmp/a.txt", "/tmp/b.txt"]

    paths.settings_file.write_text("{ broken")
    assert Settings.load(paths.settings_file).theme == Settings().theme


def test_unknown_keys_dropped():
    paths = Paths.resolve().ensure()
    paths.settings_file.write_text(json.dumps({"theme": "midnight", "mystery": 1}))
    loaded = Settings.load(paths.settings_file)
    assert loaded.theme == "midnight" and not hasattr(loaded, "mystery")


def test_history_persists_and_reads_back():
    paths = Paths.resolve().ensure()
    results = [
        Result("127.0.0.1", 80, "open", 1.0, "http", ""),
        Result("127.0.0.1", 81, "closed", 1.0, "", ""),
    ]
    scan_id = save_scan(paths.database, scope="1 hosts x 2 ports",
                        hosts=1, ports=2, results=results)
    assert scan_id >= 1
    scans = recent_scans(paths.database)
    assert scans[0]["open_count"] == 1 and scans[0]["hosts"] == 1


def test_load_scan_round_trip():
    from portoscan.storage import load_scan, save_scan
    paths = Paths.resolve().ensure()
    saved = [
        Result("127.0.0.1", 80, "open", 1.0, "http", "b"),
        Result("127.0.0.1", 81, "filtered", 300.0, "", ""),
    ]
    scan_id = save_scan(paths.database, scope="1 hosts x 2 ports",
                        hosts=1, ports=2, results=saved)
    loaded = load_scan(paths.database, scan_id)
    assert len(loaded) == 2
    assert loaded[0].host == "127.0.0.1" and loaded[0].state == "open"
    assert loaded[1].state == "filtered"
