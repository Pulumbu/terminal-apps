from portoscan.compliance import check, summarize
from portoscan.report import render_report
from portoscan.scan import Result


def r(host, port, state, service=""):
    return Result(host, port, state, 1.0, service, "")


def test_flags_open_risky_ports_only():
    results = [
        r("10.0.0.1", 23, "open", "telnet"),      # high
        r("10.0.0.1", 3389, "open", "rdp"),        # medium
        r("10.0.0.2", 3306, "open", "mysql"),      # high (exposed db)
        r("10.0.0.2", 443, "open", "https"),       # not risky
        r("10.0.0.3", 23, "closed", "telnet"),     # closed -> ignored
    ]
    findings = check(results)
    flagged = {(f.host, f.port, f.severity) for f in findings}
    assert ("10.0.0.1", 23, "high") in flagged
    assert ("10.0.0.2", 3306, "high") in flagged
    assert ("10.0.0.1", 3389, "medium") in flagged
    assert all(f.port != 443 for f in findings)
    assert all(not (f.port == 23 and f.host == "10.0.0.3") for f in findings)


def test_sorted_high_first():
    results = [r("h", 3389, "open"), r("h", 23, "open")]
    findings = check(results)
    assert findings[0].severity == "high"       # telnet before rdp


def test_summary_empty():
    assert "No policy findings" in summarize([])


def test_report_html_includes_findings_and_escapes():
    html = render_report(
        [r("10.0.0.1", 23, "open", "telnet"),
         Result("10.0.0.1", 80, "open", 1.0, "http", "<script>x</script>")],
        scope="demo")
    assert "<!doctype html>" in html.lower()
    assert "Telnet" in html
    assert "&lt;script&gt;" in html   # banner escaped, not raw
    assert "demo" in html
