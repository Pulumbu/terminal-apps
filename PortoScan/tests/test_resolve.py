from portoscan.resolve import resolve_all, resolve_host


def test_literal_ips_pass_through_and_dedupe():
    report = resolve_all(["10.0.0.1", "10.0.0.1", "::1"])
    assert report.ips == ["10.0.0.1", "::1"]
    assert report.literal == 3 and not report.failed and not report.resolved


def test_localhost_resolves():
    addresses = resolve_host("localhost")
    assert "127.0.0.1" in addresses or "::1" in addresses


def test_failed_names_reported_not_raised():
    report = resolve_all(["definitely-not-real.invalid"])
    assert report.failed == ["definitely-not-real.invalid"] and report.ips == []


def test_dedupe_name_and_literal_same_ip():
    report = resolve_all(["127.0.0.1", "localhost"])
    # localhost -> 127.0.0.1, already present as a literal -> one unique IP
    assert report.ips.count("127.0.0.1") == 1
    assert "localhost" in report.resolved
