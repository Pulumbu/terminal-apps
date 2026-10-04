"""SVG snapshot tests.

Record or refresh with:   pytest --snapshot-update
Assert with:              pytest

Two rules learned the hard way:

1. ``snap_compare`` resolves its path relative to the *test file*, not the
   working directory -- build the path from ``__file__``.
2. A snapshot must be deterministic. Anything time-dependent (a clock in the
   header, a running animation, random data) makes the SVG differ on every
   run. Snapshot small deterministic harness apps rather than the whole
   application, or freeze the moving parts in ``run_before``.
"""

from pathlib import Path

HARNESS = Path(__file__).parent / "snapshot_apps"


def test_multiselect(snap_compare):
    assert snap_compare(str(HARNESS / "multiselect_app.py"), terminal_size=(60, 16))


def test_multiselect_filtered(snap_compare):
    assert snap_compare(
        str(HARNESS / "multiselect_app.py"),
        terminal_size=(60, 16),
        press=["t", "e", "s"],
    )


def test_settings_form(snap_compare):
    assert snap_compare(str(HARNESS / "settings_app.py"), terminal_size=(80, 24))
