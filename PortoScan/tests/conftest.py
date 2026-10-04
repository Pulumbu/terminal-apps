import tempfile

import pytest


@pytest.fixture(autouse=True)
def isolated_home(monkeypatch):
    home = tempfile.mkdtemp()
    monkeypatch.setenv("PORTOSCAN_HOME", home)
    monkeypatch.setenv("TEXTUAL_ANIMATIONS", "none")
    # Run each test from a throwaway cwd so any auto-saved "PortoScan Result/"
    # folder lands in a temp dir, never in the project tree.
    monkeypatch.chdir(tempfile.mkdtemp())
    yield
