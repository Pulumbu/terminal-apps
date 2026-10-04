"""CSV / JSON export of scan results. Pure; imports no Textual."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from portoscan.scan import Result

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
