from portoscan.scan import Result
from portoscan.stats import counts_by_state, open_pairs, per_host_open, top_services


def r(host, port, state, service=""):
    return Result(host, port, state, 1.0, service, "")


RESULTS = [
    r("10.0.0.1", 22, "open", "ssh"),
    r("10.0.0.1", 80, "open", "http"),
    r("10.0.0.2", 80, "open", "http"),
    r("10.0.0.2", 443, "closed", "https"),
    r("10.0.0.3", 3389, "filtered", "ms-wbt-server"),
]


def test_counts_by_state():
    counts = counts_by_state(RESULTS)
    assert counts == {"open": 3, "closed": 1, "filtered": 1, "error": 0}


def test_top_services_counts_only_open():
    services = dict(top_services(RESULTS))
    assert services == {"http": 2, "ssh": 1}  # https was closed -> excluded


def test_per_host_open():
    hosts = dict(per_host_open(RESULTS))
    assert hosts == {"10.0.0.1": 2, "10.0.0.2": 1}


def test_open_pairs_are_sorted_unique():
    pairs = open_pairs(RESULTS)
    assert pairs == [("10.0.0.1", 22), ("10.0.0.1", 80), ("10.0.0.2", 80)]
