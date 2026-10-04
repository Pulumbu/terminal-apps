import tempfile

import pytest


@pytest.fixture(autouse=True)
def isolated_home(monkeypatch):
    monkeypatch.setenv("PORTOSCAN_HOME", tempfile.mkdtemp())
    monkeypatch.setenv("TEXTUAL_ANIMATIONS", "none")
    yield
