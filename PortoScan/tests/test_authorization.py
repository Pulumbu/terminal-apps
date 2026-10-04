from portoscan.authorization import classify


def test_all_local():
    report = classify(["127.0.0.1", "10.0.0.5", "192.168.1.1"])
    assert report.all_local and not report.has_public


def test_public_detected():
    report = classify(["10.0.0.1", "8.8.8.8"])
    assert report.public == 1 and report.has_public and not report.all_local


def test_hostname_is_nonlocal():
    report = classify(["example.com"])
    assert report.hostnames == 1 and report.has_public
