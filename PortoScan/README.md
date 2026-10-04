# PortoScan

An **authorized-use** TCP port scanner with a modern Textual UI. You supply the
targets; PortoScan scans them — fast, polite, and legible.

See [`PORTOSCAN.md`](PORTOSCAN.md) for the full design & feature spec. This README is the
quick start.

## Authorized use only

PortoScan scans the targets **you** supply: an uploaded `.txt`, pasted entries, or hosts
expanded from **CIDR / dotted ranges you own**. It has **no** random or by-country public-IP
target generation — generating strangers' IPs and scanning them is unauthorized scanning of
third parties. Scan only systems you own or have explicit, written authorization to test.
On first run it asks you to acknowledge this; private/loopback scopes are frictionless.

## Install & run

```bash
cd PortoScan
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

portoscan                       # launch the TUI
portoscan targets.txt           # preload a targets file
portoscan --paths               # show app-data locations
portoscan --version
```

Keys: `s` scan · `x` stop · `/` filter · `e` export · `i` import · `h` history ·
`d` diff · `r` re-scan open · `ctrl+r` re-scan host · `t` stats · `ctrl+s` save preset ·
`ctrl+l` presets · `,` settings · `ctrl+t` theme · `ctrl+p` command palette · `ctrl+q` quit.

## What it does

- **Targets you supply**: upload `.txt`, paste, or expand `10.0.0.0/24` / `192.168.1.10-20`
- **Ports**: tick any combination of categories (Top 100, Web, Databases, Remote admin,
  Mail, Full) — they're **unioned** into one scan — and the custom box adds extra ports on
  top, e.g. `22,80,443,8000-8100`. Untick everything to scan only the custom ports.
- **Scan**: async **TCP connect** or **UDP** (clearly labelled, slower), bounded concurrency,
  adaptive backoff, honest states (open / closed / filtered; UDP filtered = open|filtered),
  per-environment rate presets, cancellable. **IPv6** targets, CIDR and classification are
  supported end-to-end alongside IPv4.
- **Service/version hints**: open ports are fingerprinted lightly — TLS version + cipher
  (+ certificate CN when `cryptography` is installed) on TLS ports, the HTTP `Server` header,
  and the first banner line otherwise. Reporting only; no exploitation.
- **Results**: live table with a **filter box** (type text, or a state like `open`), a
  **state-filter dropdown** (All / Open only / Not closed / Open+Filtered), and
  **click-to-sort** column headers. CSV/JSON **export** and **import**, plus a **history**
  screen to re-open past scans from the SQLite database.
- **Diff**: pick two past scans and see newly-open / newly-closed / changed ports — change
  monitoring for your own infrastructure (`d`).
- **Presets**: save a (targets + categories + custom ports + rate) combo by name and reload
  it later (`ctrl+s` to save, `ctrl+l` to pick/delete).
- **Re-scan**: `r` re-scans only the endpoints that were open (a fast verification pass);
  `ctrl+r` re-scans the highlighted row's host across the current port selection.
- **Live stats panel** (`t`): open-ports sparkline over time, by-state counts, a top-services
  histogram and the top hosts by open-port count — updating as the scan runs.
- **Auto-save**: every run creates `PortoScan Result/<timestamp>/` in the launch directory
  (falling back to Documents, then app-data, if that is not writable) containing
  `open`, `closed`, `filtered`, `all` and `summary` files. Default format is **txt**;
  switch to CSV or JSON in Settings
- **UX**: two themes + high-contrast, `NO_COLOR` support, scope banner, progress meter,
  command palette, responsive layout

## Develop & test

```bash
pytest                          # 33 tests (domain, engine, storage, Pilot)
textual run --dev src/portoscan/app.py   # live CSS reload + devtools
ruff check src tests
```

Tests scan only `127.0.0.1` against listeners they start themselves.

## Layout

```
src/portoscan/
├── __main__.py / cli.py     # entry points (freeze_support, lazy TUI import)
├── app.py                   # the Textual App
├── scan.py                  # async TCP-connect engine (no Textual)
├── targets.py               # CIDR/range/hostname expansion (no Textual)
├── ports.py                 # profiles + nmap top-100 (no Textual)
├── authorization.py         # scope classification + ack text (no Textual)
├── export.py                # CSV/JSON (no Textual)
├── storage.py paths.py      # settings, SQLite history, app-data
├── themes.py icons.py       # midnight / amber-crt / high-contrast, glyph tiers
├── widgets/                 # ScopeBanner, ScanMeter (line API)
├── screens/                 # Authorize, Confirm, Settings
└── styles/base.tcss
```

The engine, parsing and export import **no Textual** and are unit-tested without an event
loop. Built on the techniques in
[`../docs/ADVANCED-TERMINAL-APPS-PYTHON.md`](../docs/ADVANCED-TERMINAL-APPS-PYTHON.md).

## Not built, by design

Random public-IP generation · country/geography target generation · raw-socket/SYN scanning ·
vulnerability detection or exploitation. PortoScan scans what you point it at, and helps you
point it only at what you're allowed to.
