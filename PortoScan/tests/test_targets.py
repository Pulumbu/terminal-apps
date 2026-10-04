from portoscan.targets import expand


def test_plain_ip():
    r = expand("10.0.0.5")
    assert r.hosts == ["10.0.0.5"] and not r.errors


def test_cidr_expansion():
    r = expand("10.0.0.0/24")
    assert r.hosts[0] == "10.0.0.1"
    assert r.hosts[-1] == "10.0.0.254"
    assert len(r.hosts) == 254


def test_small_cidr_includes_both_hosts():
    r = expand("192.168.1.0/31")
    assert r.hosts == ["192.168.1.0", "192.168.1.1"]


def test_dotted_range():
    r = expand("192.168.1.10-12")
    assert r.hosts == ["192.168.1.10", "192.168.1.11", "192.168.1.12"]


def test_dedup_and_comments():
    r = expand("10.0.0.1\n10.0.0.1  # dup\n# comment\n\n10.0.0.2")
    assert r.hosts == ["10.0.0.1", "10.0.0.2"]


def test_hostname_accepted():
    r = expand("scanme.example.internal")
    assert r.hosts == ["scanme.example.internal"]


def test_bad_token_reported_not_raised():
    r = expand("bad_host!!")   # underscore + punctuation: not a valid label
    assert r.errors and r.hosts == []


def test_host_cap_truncates():
    r = expand("10.0.0.0/16", max_hosts=100)
    assert r.truncated and len(r.hosts) == 100


def test_commas_and_spaces():
    r = expand("10.0.0.1, 10.0.0.2 10.0.0.3")
    assert r.hosts == ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
