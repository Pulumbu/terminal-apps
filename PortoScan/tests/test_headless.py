from argparse import Namespace

from portoscan.headless import resolve_ports, run
from portoscan.paths import Paths
from portoscan.results_io import RESULT_DIR_NAME


def _args(**kw):
    base = {"targets_file": None, "targets": "127.0.0.1", "profile": None,
            "ports": "22,80", "rate": "localhost", "udp": False, "no_grab": True,
            "no_resolve": True, "out": None, "format": "txt", "authorize": False}
    base.update(kw)
    return Namespace(**base)


def test_resolve_ports_profile_and_spec():
    assert resolve_ports("web", None)        # profile expands
    assert resolve_ports(None, "22,80,443") == [22, 80, 443]
    assert resolve_ports("web,admin", "9999")  # union of two profiles + custom


def test_resolve_ports_unknown_profile():
    import pytest
    with pytest.raises(ValueError):
        resolve_ports("nope", None)


def test_headless_local_scan_writes_folder(tmp_path):
    paths = Paths.resolve().ensure()
    rc = run(_args(out=str(tmp_path)), paths)
    assert rc == 0
    runs = list((tmp_path / RESULT_DIR_NAME).iterdir())
    assert len(runs) == 1
    assert (runs[0] / "all.txt").exists()
    assert (runs[0] / "report.html").exists()
    assert (runs[0] / "compliance.txt").exists()


def test_headless_refuses_public_without_authorize(tmp_path, capsys):
    paths = Paths.resolve().ensure()
    rc = run(_args(targets="8.8.8.8", ports="53", rate="internet",
                   out=str(tmp_path)), paths)
    assert rc == 3
    assert "authorize" in capsys.readouterr().err.lower()
    assert not (tmp_path / RESULT_DIR_NAME).exists()
