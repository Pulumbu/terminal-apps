"""CSV / JSON export of scan results. Pure; imports no Textual."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from portoscan.scan import Result

__all__ = ["FIELDS", "from_csv", "from_json", "load_file", "to_csv", "to_json"]

FIELDS = ("host", "port", "state", "service", "latency_ms", "banner")


def to_csv(results: Sequence[Result]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(FIELDS)
    for result in results:
        writer.writerow([
            result.host, result.port, result.state, result.service,
            f"{result.latency_ms:.1f}", result.banner,
        ])
    return buffer.getvalue()


def to_json(results: Sequence[Result]) -> str:
    rows = [
        {
            "host": r.host, "port": r.port, "state": r.state,
            "service": r.service, "latency_ms": round(r.latency_ms, 1),
            "banner": r.banner,
        }
        for r in results
    ]
    return json.dumps(rows, indent=2) + "\n"


def _coerce(host, port, state, service, latency, banner) -> Result:
    from portoscan.scan import Result
    try:
        port_int = int(port)
    except (TypeError, ValueError) as error:
        raise ValueError(f"bad port {port!r}") from error
    if state not in ("open", "closed", "filtered", "error"):
        raise ValueError(f"bad state {state!r}")
    try:
        latency_f = float(latency) if latency not in (None, "") else 0.0
    except (TypeError, ValueError):
        latency_f = 0.0
    return Result(str(host), port_int, str(state), latency_f,
                  str(service or ""), str(banner or ""))


def from_csv(text: str) -> list[Result]:
    reader = csv.DictReader(io.StringIO(text))
    results: list[Result] = []
    for row in reader:
        if not row.get("host") and not row.get("port"):
            continue
        results.append(_coerce(
            row.get("host"), row.get("port"), row.get("state"),
            row.get("service"), row.get("latency_ms"), row.get("banner"),
        ))
    return results


def from_json(text: str) -> list[Result]:
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("JSON must be a list of result objects")
    results: list[Result] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("each JSON entry must be an object")
        results.append(_coerce(
            item.get("host"), item.get("port"), item.get("state"),
            item.get("service"), item.get("latency_ms"), item.get("banner"),
        ))
    return results


def load_file(path) -> list[Result]:
    """Import results from a .csv or .json file written by PortoScan."""
    from pathlib import Path
    p = Path(path)
    text = p.read_text("utf-8")
    if p.suffix.lower() == ".json":
        return from_json(text)
    return from_csv(text)
