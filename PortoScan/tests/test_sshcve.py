from portoscan.scan import Result
from portoscan.sshcve import check_banner, parse_openssh, scan


def test_parse_variants():
    assert parse_openssh("SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13") == (9, 6, 1)
    assert parse_openssh("SSH-2.0-OpenSSH_7.4") == (7, 4, 0)
    assert parse_openssh("SSH-2.0-Dropbear_2020.81") is None


def test_regresshion_range():
    assert any(c.cve == "CVE-2024-6387" for c in check_banner("OpenSSH_8.9p1"))
    assert not any(c.cve == "CVE-2024-6387" for c in check_banner("OpenSSH_9.8p1"))
    assert not any(c.cve == "CVE-2024-6387" for c in check_banner("OpenSSH_4.3"))


def test_terrapin_fixed_in_9_6():
    assert any(c.cve == "CVE-2023-48795" for c in check_banner("OpenSSH_9.5p1"))
    assert not any(c.cve == "CVE-2023-48795" for c in check_banner("OpenSSH_9.6p1"))


def test_scan_only_open_openssh():
    results = [
        Result("10.0.0.1", 22, "open", 1.0, "ssh", "SSH-2.0-OpenSSH_8.9p1 Ubuntu"),
        Result("10.0.0.2", 22, "closed", 1.0, "ssh", "SSH-2.0-OpenSSH_8.9p1"),
        Result("10.0.0.3", 22, "open", 1.0, "ssh", "SSH-2.0-Dropbear_2020.81"),
    ]
    findings = scan(results)
    assert findings and all(f.host == "10.0.0.1" for f in findings)
    assert any("CVE-2024-6387" in f.message for f in findings)
