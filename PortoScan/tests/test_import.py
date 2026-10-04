from portoscan import export
from portoscan.scan import Result

RESULTS = [
    Result("10.0.0.1", 80, "open", 1.0, "http", "banner, with comma"),
    Result("10.0.0.1", 443, "closed", 2.0, "https", ""),
]


def test_csv_round_trip():
    text = export.to_csv(RESULTS)
    back = export.from_csv(text)
    assert [(r.host, r.port, r.state, r.service) for r in back] == \
           [(r.host, r.port, r.state, r.service) for r in RESULTS]
    assert back[0].banner == "banner, with comma"


def test_json_round_trip():
    text = export.to_json(RESULTS)
    back = export.from_json(text)
    assert back[1].port == 443 and back[1].state == "closed"


def test_load_file_by_extension(tmp_path):
    csv_path = tmp_path / "r.csv"
    csv_path.write_text(export.to_csv(RESULTS))
    json_path = tmp_path / "r.json"
    json_path.write_text(export.to_json(RESULTS))
    assert len(export.load_file(csv_path)) == 2
    assert len(export.load_file(json_path)) == 2


def test_from_json_rejects_non_list():
    import pytest
    with pytest.raises(ValueError):
        export.from_json('{"not": "a list"}')


def test_from_csv_skips_blank_rows():
    text = "host,port,state,service,latency_ms,banner\n,,,,,\n10.0.0.1,22,open,ssh,1.0,\n"
    back = export.from_csv(text)
    assert len(back) == 1 and back[0].port == 22
