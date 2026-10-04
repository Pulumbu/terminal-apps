import pytest

from portoscan.ports import PROFILE_BY_KEY, TOP_100, parse_ports


def test_top_100_length_and_head():
    assert len(TOP_100) == 100
    assert TOP_100[:3] == (80, 23, 443)


def test_profiles_present():
    assert set(PROFILE_BY_KEY) >= {"top100", "web", "db", "admin", "mail", "full"}
    assert len(PROFILE_BY_KEY["full"].ports) == 65535


def test_parse_list_and_range():
    assert parse_ports("22,80,443") == [22, 80, 443]
    assert parse_ports("8000-8003") == [8000, 8001, 8002, 8003]
    assert parse_ports("443,80,80,443") == [80, 443]


def test_parse_rejects_out_of_range():
    with pytest.raises(ValueError):
        parse_ports("70000")
    with pytest.raises(ValueError):
        parse_ports("0")


def test_parse_rejects_reversed_range():
    with pytest.raises(ValueError):
        parse_ports("100-10")
