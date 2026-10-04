"""Write each scan run to its own 'PortoScan Result/<run>' folder, and resolve a
writable base directory on any user's system. Pure; imports no Textual.

Layout produced per run (default format .txt):

    <base>/PortoScan Result/<YYYY-MM-DD_HH-MM-SS>/
        all.txt         every result
        open.txt        only open ports
        closed.txt      only closed ports
        filtered.txt    only filtered ports
        summary.txt     scope + counts
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from portoscan import export

if TYPE_CHECKING:
    from collections.abc import Sequence

    from portoscan.scan import Result

RESULT_DIR_NAME = "PortoScan Result"
STATES = ("open", "closed", "filtered")
FORMATS = ("txt", "csv", "json")


@dataclass(frozen=True, slots=True)
class RunOutput:
    folder: Path
    files: list[Path]


def _writable(directory: Path) -> bool:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / ".portoscan-write-test"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def resolve_base(preferred: str | os.PathLike[str] | None,
                 fallbacks: Sequence[Path] = ()) -> Path:
    """Pick a writable directory to hold 'PortoScan Result'.

    Order: an explicit preferred dir, the current working directory, then each
    fallback (e.g. the user's Documents, then app-data). Guarantees a usable,
    writable location on any system.
    """
    candidates: list[Path] = []
    if preferred:
        candidates.append(Path(preferred).expanduser())
    candidates.append(Path.cwd())
    candidates.extend(fallbacks)
    for candidate in candidates:
        if _writable(candidate):
            return candidate
    # last resort: a temp dir is always writable
    import tempfile
    return Path(tempfile.gettempdir())


def run_folder_name(when: datetime | None = None) -> str:
    return (when or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")


def _txt_line(result: Result) -> str:
    banner = f"  {result.banner}" if result.banner else ""
    service = result.service or "-"
    return (f"{result.host}:{result.port}\t{result.state}\t{service}"
            f"\t{result.latency_ms:.0f}ms{banner}")


def _render_txt(results: Sequence[Result]) -> str:
    rows = sorted(results, key=lambda r: (r.host, r.port))
    return "".join(_txt_line(r) + "\n" for r in rows)


def _render(results: Sequence[Result], fmt: str) -> str:
    if fmt == "csv":
        return export.to_csv(results)
    if fmt == "json":
        return export.to_json(results)
    return _render_txt(results)


def _summary(results: Sequence[Result], scope: str, when: datetime) -> str:
    counts = dict.fromkeys((*STATES, "error"), 0)
    for result in results:
        counts[result.state] = counts.get(result.state, 0) + 1
    lines = [
        "PortoScan run summary",
        f"when:   {when.isoformat(timespec='seconds')}",
        f"scope:  {scope}",
        f"total:  {len(results)}",
        *(f"{state}: {counts.get(state, 0)}" for state in (*STATES, "error")),
    ]
    return "\n".join(lines) + "\n"


def write_run(
    base: str | os.PathLike[str],
    results: Sequence[Result],
    *,
    scope: str = "",
    fmt: str = "txt",
    when: datetime | None = None,
) -> RunOutput:
    """Create '<base>/PortoScan Result/<run>' and write the split result files."""
    if fmt not in FORMATS:
        fmt = "txt"
    when = when or datetime.now()
    folder = Path(base) / RESULT_DIR_NAME / run_folder_name(when)
    folder.mkdir(parents=True, exist_ok=True)
    ext = fmt
    written: list[Path] = []

    all_path = folder / f"all.{ext}"
    all_path.write_text(_render(results, fmt), encoding="utf-8")
    written.append(all_path)

    for state in STATES:
        subset = [r for r in results if r.state == state]
        path = folder / f"{state}.{ext}"
        path.write_text(_render(subset, fmt), encoding="utf-8")
        written.append(path)

    summary_path = folder / "summary.txt"
    summary_path.write_text(_summary(results, scope, when), encoding="utf-8")
    written.append(summary_path)

    return RunOutput(folder=folder, files=written)
