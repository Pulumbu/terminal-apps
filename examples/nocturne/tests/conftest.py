import tempfile

import pytest


@pytest.fixture(autouse=True)
def isolated_home(monkeypatch):
    """Never touch the developer's real config while testing."""
    monkeypatch.setenv("NOCTURNE_HOME", tempfile.mkdtemp())
    monkeypatch.setenv("TEXTUAL_ANIMATIONS", "none")
    yield
