from portoscan.diff import diff_scans
from portoscan.scan import Result


def r(host, port, state):
    return Result(host, port, state, 1.0, "", "")


def test_newly_open_and_closed():
    baseline = [r("10.0.0.1", 22, "open"), r("10.0.0.1", 80, "closed")]
    current = [r("10.0.0.1", 22, "closed"), r("10.0.0.1", 80, "open")]
    report = diff_scans(baseline, current)
    assert [(c.host, c.port) for c in report.newly_open] == [("10.0.0.1", 80)]
    assert [(c.host, c.port) for c in report.newly_closed] == [("10.0.0.1", 22)]


def test_still_open_not_flagged():
    base = [r("10.0.0.1", 443, "open")]
    cur = [r("10.0.0.1", 443, "open")]
    report = diff_scans(base, cur)
    assert not report.newly_open and not report.newly_closed
    assert len(report.still_open) == 1


def test_appeared_and_disappeared():
    base = [r("10.0.0.1", 22, "open")]
    cur = [r("10.0.0.2", 22, "open")]
    report = diff_scans(base, cur)
    assert [(c.host, c.port) for c in report.disappeared] == [("10.0.0.1", 22)]
    assert [(c.host, c.port) for c in report.appeared] == [("10.0.0.2", 22)]
    # a new endpoint that is open also counts as newly open
    assert [(c.host, c.port) for c in report.newly_open] == [("10.0.0.2", 22)]


def test_filtered_to_open_is_newly_open():
    report = diff_scans([r("10.0.0.1", 8080, "filtered")], [r("10.0.0.1", 8080, "open")])
    assert len(report.newly_open) == 1


def test_summary_string():
    report = diff_scans([r("10.0.0.1", 22, "open")], [r("10.0.0.1", 22, "closed")])
    assert "open" in report.summary and "closed" in report.summary
