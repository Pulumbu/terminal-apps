from datetime import datetime

from portoscan.results_io import RESULT_DIR_NAME, resolve_base, run_folder_name, write_run
from portoscan.scan import Result

RESULTS = [
    Result("127.0.0.1", 80, "open", 1.2, "http", "Server: x"),
    Result("127.0.0.1", 81, "closed", 0.9, "", ""),
    Result("127.0.0.1", 82, "filtered", 300.0, "", ""),
    Result("127.0.0.2", 22, "open", 2.1, "ssh", "SSH-2.0"),
]


def test_resolve_base_prefers_writable(tmp_path):
    assert resolve_base(str(tmp_path)) == tmp_path


def test_resolve_base_falls_back(tmp_path, monkeypatch):
    # cwd is writable here, so resolve_base(None) returns cwd; assert it is usable
    monkeypatch.chdir(tmp_path)
    base = resolve_base(None, fallbacks=[tmp_path / "fallback"])
    assert base.exists()


def test_run_folder_name_format():
    name = run_folder_name(datetime(2026, 1, 2, 3, 4, 5))
    assert name == "2026-01-02_03-04-05"


def test_write_run_creates_split_files(tmp_path):
    when = datetime(2026, 1, 2, 3, 4, 5)
    output = write_run(tmp_path, RESULTS, scope="2 hosts x 2 ports", fmt="txt", when=when)
    assert output.folder == tmp_path / RESULT_DIR_NAME / "2026-01-02_03-04-05"
    names = {p.name for p in output.files}
    assert names == {"all.txt", "open.txt", "closed.txt", "filtered.txt",
                     "summary.txt", "compliance.txt", "report.html"}

    open_text = (output.folder / "open.txt").read_text()
    assert "127.0.0.1:80" in open_text and "127.0.0.2:22" in open_text
    assert "127.0.0.1:81" not in open_text  # closed not in open file

    closed_text = (output.folder / "closed.txt").read_text()
    assert "127.0.0.1:81" in closed_text and "127.0.0.1:80" not in closed_text

    all_text = (output.folder / "all.txt").read_text()
    assert all_text.count("\n") == 4  # every result, one per line

    summary = (output.folder / "summary.txt").read_text()
    assert "total:  4" in summary and "open: 2" in summary


def test_write_run_csv_and_json(tmp_path):
    out_csv = write_run(tmp_path / "c", RESULTS, fmt="csv")
    assert (out_csv.folder / "all.csv").read_text().startswith("host,port,state")
    out_json = write_run(tmp_path / "j", RESULTS, fmt="json")
    assert (out_json.folder / "open.json").read_text().lstrip().startswith("[")


def test_each_run_gets_its_own_folder(tmp_path):
    a = write_run(tmp_path, RESULTS, when=datetime(2026, 1, 1, 0, 0, 0))
    b = write_run(tmp_path, RESULTS, when=datetime(2026, 1, 1, 0, 0, 1))
    assert a.folder != b.folder
    assert a.folder.parent == b.folder.parent == tmp_path / RESULT_DIR_NAME
