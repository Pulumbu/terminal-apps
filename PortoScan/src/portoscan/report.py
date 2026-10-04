"""Render a standalone HTML scan report. Pure; imports no Textual."""

from __future__ import annotations

import html
from datetime import datetime
from typing import TYPE_CHECKING

from portoscan.compliance import Finding, check, summarize
from portoscan.stats import counts_by_state, per_host_open, top_services

if TYPE_CHECKING:
    from collections.abc import Sequence

    from portoscan.scan import Result

_STATE_COLOR = {
    "open": "#2e7d32", "closed": "#757575",
    "filtered": "#b8860b", "error": "#c62828",
}
_SEV_COLOR = {"high": "#c62828", "medium": "#b8860b", "low": "#757575"}


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_report(results: Sequence[Result], *, scope: str = "",
                  when: datetime | None = None,
                  extra_findings: Sequence[Finding] | None = None) -> str:
    when = when or datetime.now()
    states = counts_by_state(results)
    findings = list(check(results))
    if extra_findings:
        seen = {(f.severity, f.host, f.port, f.message) for f in findings}
        for f in extra_findings:
            key = (f.severity, f.host, f.port, f.message)
            if key not in seen:
                seen.add(key)
                findings.append(f)
        from portoscan.compliance import SEVERITY_ORDER
        findings.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.host, f.port))
    rows = sorted(results, key=lambda r: (r.host, r.port))

    def chips() -> str:
        return "".join(
            f'<span class="chip" style="--c:{_STATE_COLOR[s]}">{s}: {states[s]}</span>'
            for s in ("open", "closed", "filtered", "error"))

    def result_rows() -> str:
        out = []
        for r in rows:
            color = _STATE_COLOR.get(r.state, "#000")
            out.append(
                f"<tr><td>{_esc(r.host)}</td><td class='num'>{r.port}</td>"
                f"<td style='color:{color};font-weight:600'>{_esc(r.state)}</td>"
                f"<td>{_esc(r.service)}</td><td class='num'>{r.latency_ms:.0f}</td>"
                f"<td>{_esc(r.banner)}</td></tr>")
        return "\n".join(out)

    def finding_rows(items: Sequence[Finding]) -> str:
        if not items:
            return "<tr><td colspan='4' class='muted'>No policy findings.</td></tr>"
        out = []
        for f in items:
            color = _SEV_COLOR.get(f.severity, "#000")
            out.append(
                f"<tr><td style='color:{color};font-weight:700'>{_esc(f.severity)}</td>"
                f"<td>{_esc(f.host)}</td><td class='num'>{f.port}</td>"
                f"<td>{_esc(f.message)}</td></tr>")
        return "\n".join(out)

    def rollup(title: str, pairs: list[tuple[str, int]]) -> str:
        if not pairs:
            return ""
        lis = "".join(f"<li><span>{_esc(n)}</span><b>{c}</b></li>" for n, c in pairs)
        return f"<div class='card'><h3>{title}</h3><ul class='bars'>{lis}</ul></div>"

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PortoScan report {_esc(when.strftime('%Y-%m-%d %H:%M'))}</title>
<style>
  :root {{ color-scheme: light dark; --bg:#f6f7f9; --fg:#1a1c23; --card:#fff;
           --line:#e3e6ea; --muted:#6b7280; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg:#14161f; --fg:#d7dae0;
           --card:#1c1f2b; --line:#2a2e3d; --muted:#9aa0ac; }} }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:24px; background:var(--bg); color:var(--fg);
          font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }}
  h1 {{ font-size:20px; margin:0 0 4px; }}
  .sub {{ color:var(--muted); margin-bottom:16px; }}
  .chips {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:16px; }}
  .chip {{ padding:2px 10px; border-radius:999px; border:1px solid var(--c);
           color:var(--c); font-weight:600; font-size:12px; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
           gap:12px; margin-bottom:16px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:10px;
           padding:12px 14px; }}
  .card h3 {{ margin:0 0 8px; font-size:13px; color:var(--muted);
              text-transform:uppercase; letter-spacing:.04em; }}
  ul.bars {{ list-style:none; margin:0; padding:0; }}
  ul.bars li {{ display:flex; justify-content:space-between; padding:2px 0;
                border-bottom:1px dashed var(--line); }}
  table {{ width:100%; border-collapse:collapse; background:var(--card);
           border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
  th,td {{ text-align:left; padding:7px 10px; border-bottom:1px solid var(--line); }}
  th {{ background:rgba(127,127,127,.08); font-size:12px; text-transform:uppercase;
        letter-spacing:.03em; color:var(--muted); }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .muted {{ color:var(--muted); }}
  footer {{ margin-top:20px; color:var(--muted); font-size:12px; }}
</style></head>
<body>
  <h1>PortoScan report</h1>
  <div class="sub">{_esc(when.strftime('%Y-%m-%d %H:%M:%S'))} &middot; {_esc(scope)}
       &middot; {len(results)} result(s)</div>
  <div class="chips">{chips()}</div>
  <div class="grid">
    {rollup('Top services (open)', top_services(results))}
    {rollup('Top hosts (open)', per_host_open(results))}
    <div class="card"><h3>Policy check</h3><div>{_esc(summarize(findings))}</div></div>
  </div>
  <h3>Policy findings</h3>
  <table><thead><tr><th>Severity</th><th>Host</th><th>Port</th><th>Finding</th></tr>
    </thead><tbody>{finding_rows(findings)}</tbody></table>
  <h3 style="margin-top:20px">Results</h3>
  <table><thead><tr><th>Host</th><th>Port</th><th>State</th><th>Service</th>
    <th>ms</th><th>Banner</th></tr></thead><tbody>{result_rows()}</tbody></table>
  <footer>Generated by PortoScan &middot; authorized-use scanning only.</footer>
</body></html>
"""
