# PortoScan — Design & Feature Specification

> A fast, friendly, **authorized-use** TCP port scanner with a modern terminal UI.
> You supply the targets; PortoScan scans them beautifully.

**Status:** design spec, written 2026-10-04.
**Companion:** this document applies the patterns in
[`../docs/ADVANCED-TERMINAL-APPS-PYTHON.md`](../docs/ADVANCED-TERMINAL-APPS-PYTHON.md)
(the advanced-terminal-apps handbook) to a concrete application. Where a technique is
described in full there, this spec references the section rather than repeating it.
**Verified:** the scan engine, target expansion, service-name lookup, timeout handling and
open/closed/filtered detection in §4 were prototyped and executed against this project's own
loopback before this spec was written.

---

## 0. Scope and authorization (read first)

PortoScan is built on one rule, and the rule shapes every feature below:

> **You scan only systems you own or have explicit, written authorization to test.**

### What PortoScan does

- Scans targets **you supply**: an uploaded `.txt` list, pasted entries, or hosts
  **expanded from CIDR ranges and dotted ranges you provide**.
- Expanding `10.0.0.0/24` into its 254 hosts is a convenience for scanning *your own*
  network — it is the legitimate meaning of "generate the IPs to scan".

### What PortoScan does not do — by design, not by configuration

- It does **not** generate random public IP addresses.
- It does **not** generate IP addresses by country or geography.
- It has **no** "pick a region and find hosts to scan" mode.

Generating real, routable IPs you have no relationship with and scanning their ports is
unauthorized scanning of third parties. Every major scanner — nmap, masscan, RustScan —
works the same way PortoScan does: *the operator supplies the scope.* None of them ship a
random/by-country public-IP target generator, and neither does this one.

### Why this matters (the research, briefly)

- Most regulators treat probing third-party systems without authorization as unlawful access
  even when non-invasive; in the US the **Computer Fraud and Abuse Act** has been applied to
  port probes, and courts have read "sending packets to probe services" as *accessing* the
  system. ([StationX](https://www.stationx.net/is-port-scanning-legal/),
  [Calyptix](https://www.calyptix.com/technical-insights/port-scanning-legal-answers-companies/))
- Authorization should be **written and signed by both parties**; verbal permission has been
  found insufficient in real cases.
- A **highly aggressive, high-speed scan can itself be treated as a denial-of-service attack**,
  which is independently illegal — so politeness and rate limiting are safety features, not
  just performance knobs.

PortoScan therefore makes the responsible path the easy path: an authorization acknowledgment
on first run, private/loopback ranges as the default scope, conservative default rates, and a
visible, logged scope for every scan.

---

## 1. Product vision

A security engineer, sysadmin or student opens PortoScan, points it at hosts they are
responsible for — by dropping in a `.txt`, pasting a CIDR, or typing an address — and within
seconds has a live, sortable, exportable map of which ports are open, what services answer,
and how fast. It should feel like a well-made desktop app: themed, animated, keyboard-first,
mouse-friendly, and genuinely pleasant — the opposite of squinting at raw `nmap` output.

**Design goals**

1. **Safe by default** — the responsible choice requires no configuration.
2. **Fast but polite** — async concurrency with adaptive, bounded rate limiting.
3. **Legible** — results are a live table, not a scrolling wall of text.
4. **Honest** — open/closed/filtered are distinguished and never guessed at.
5. **Portable** — one themed binary with an icon; runs in a terminal, inline, or over SSH.

**Non-goals**

- Not a raw-socket SYN scanner (no root/raw sockets; TCP connect only — see §4.1).
- Not a vulnerability scanner or exploit tool — it reports open ports and banners, nothing more.
- Not an internet-wide survey tool, and never a target generator for hosts you don't control.

---

## 2. Feature set

### 2.1 Targets (input)

| Feature | Detail |
|---|---|
| **Upload `.txt`** | File picker (`textual-fspicker`, handbook §13.3); one target per line, `,`-separated also accepted; `#` comments and blanks ignored |
| **Paste / type** | A `TextArea` for ad-hoc entry, validated live |
| **CIDR expansion** | `10.0.0.0/24` → its usable hosts, using the stdlib `ipaddress` module |
| **Dotted range** | `192.168.1.10-20` → the 11 hosts in that inclusive range |
| **Hostnames** | Accepted and resolved at scan time (DNS on a worker thread) |
| **De-duplication** | Repeated/overlapping targets are collapsed |
| **Expansion cap** | Hard ceiling (default 65,536 hosts) so a wide CIDR cannot launch an unbounded scan by accident; UI shows "truncated" when hit |
| **Recent lists** | Last-used target files remembered (app-data, handbook §22) |
| **Scope guard** | First-run authorization acknowledgment; private/loopback ranges are the default and are never gated |

> There is deliberately **no** "random" or "by country" target source. See §0.

### 2.2 Port selection

Curated profiles plus custom input. The **top-100** profile uses nmap's real popularity
ranking ([HeckerBirb top-ports](https://github.com/HeckerBirb/top-nmap-ports-csv)):

```
80,23,443,21,22,25,3389,110,445,139,143,53,135,3306,8080,1723,111,995,993,5900,
1025,587,8888,199,1720,465,548,113,81,6001,10000,514,5060,179,1026,2000,8443,8000,
32768,554,26,1433,49152,2001,515,8008,49154,1027,5666,646,5000,5631,631,49153,8081,
2049,88,79,5800,106,2121,1110,49155,6000,513,990,5357,427,49156,543,544,5101,144,7,
389,8009,3128,444,9999,5009,7070,5190,3000,5432,1900,3986,13,1029,9,5051,6646,49157,
1028,873,1755,2717,4899,9100
```

| Profile | Contents |
|---|---|
| **Top 100** | the list above (fast first pass) |
| **Top 1000** | nmap's default set (bundled as data) |
| **Web** | 80, 443, 8000, 8008, 8080, 8443, 8888, 3000, 5000 |
| **Databases** | 1433, 1521, 3306, 5432, 6379, 9200, 11211, 27017 |
| **Remote admin** | 22, 23, 3389, 5900, 5985, 5986 |
| **Mail** | 25, 110, 143, 465, 587, 993, 995 |
| **Custom** | free-form: `22,80,443,8000-8100` (ranges and lists) |
| **Full** | 1–65535 (explicit opt-in; a warning explains the cost) |

Each open result shows the IANA service name via `socket.getservbyport` (verified working).

### 2.3 Scan engine

| Feature | Detail |
|---|---|
| **TCP connect scan** | `asyncio.open_connection` + `wait_for` timeout (handbook §21, research-backed) |
| **Three honest states** | `open` (connected), `closed` (refused), `filtered` (timed out) — never guessed |
| **Bounded concurrency** | `asyncio.Semaphore`; default 500, configurable |
| **Adaptive rate** | token-bucket cap + congestion backoff on timeouts (§4.2), modeled on nmap's congestion-window idea |
| **Per-environment presets** | Localhost / LAN / Internet presets pick sane rate + timeout (research: ~5–10k pps localhost, 2–5k LAN, 500–1k internet) |
| **Latency** | per-port connect time in ms |
| **Banner grab (optional)** | passive read of up to 256 B; `HEAD` probe on HTTP ports; UTF-8 with `errors="replace"` |
| **Cancellable** | `@work(exclusive=True)` + cooperative `is_cancelled`; one keypress stops it cleanly |
| **Progress** | live done/total, open-count, rate, ETA |
| **DNS** | hostname resolution on a thread, cached |

### 2.4 Results

- Live virtualised `DataTable` (handbook §11): host, port, state, service, latency, banner.
- Sort by any column; filter by state/text; group by host.
- Colour + glyph per state (never colour alone — handbook §25).
- Export **CSV** and **JSON**; copy a row or the whole scope to clipboard (OSC 52).
- Persist scan history to **SQLite** (WAL mode, handbook §22.5); re-open a past scan.

### 2.5 UX niceties

- Command palette for every action (handbook §20).
- Saved target lists and port profiles.
- Dry-run / preview: shows exactly how many hosts × ports will be scanned before you start.
- A always-visible **scope banner**: what will be scanned and the active rate preset.
- Crash reports and rotating file logs (handbook §22.8, §24.7).

---

## 3. Architecture

Mirrors the handbook's layout (§4) so the domain layer is pure and testable without an event
loop. Already scaffolded under `PortoScan/`.

```
PortoScan/
├── PORTOSCAN.md                 # this document
├── pyproject.toml
├── nocturne.spec  → portoscan.spec
├── assets/                      # logo.ico/.png, top-1000 ports data, app.tcss
├── src/portoscan/
│   ├── __init__.py              # version + the scope statement (written)
│   ├── __main__.py              # freeze_support(); CLI entry
│   ├── cli.py                   # argparse; scriptable + --paths + smoke hook
│   ├── app.py                   # the App
│   ├── targets.py               # parse/expand targets (written, verified)
│   ├── scan.py                  # the async engine (prototype verified)
│   ├── ports.py                 # profiles + the nmap top lists
│   ├── authorization.py         # first-run ack, scope classification
│   ├── storage.py               # settings, history (SQLite), atomic writes
│   ├── paths.py                 # resource_path + app-data (handbook §22/§23)
│   ├── export.py                # CSV/JSON writers
│   ├── themes.py                # PortoScan themes
│   ├── widgets/                 # scope banner, port picker, stat row, meter
│   ├── screens/                 # targets, scanning, settings, confirm
│   └── styles/                  # TCSS
├── tests/                       # domain, targets, scan, Pilot, snapshots
└── tools/                       # make_icons.py, build.sh
```

**The one rule (handbook §4.1):** `targets.py`, `scan.py`, `ports.py`, `authorization.py`
import **no Textual**. They are unit-tested directly. The `screens/` and `widgets/` layers
translate their results into UI.

---

## 4. The scan engine (verified design)

### 4.1 Why TCP connect, not SYN

A raw SYN scan needs raw sockets and root/admin, is brittle across platforms, and is exactly
the capability that turns a tool aggressive. A **TCP connect** scan uses the OS's normal
`connect()` via `asyncio.open_connection`, needs no privileges, behaves identically on
Linux/macOS/Windows, and is correct: a completed handshake is unambiguously an open port.
The trade-off — it is more visible to the target and a touch slower — is the right one for a
tool whose entire thesis is "scan only what you're allowed to."

### 4.2 Concurrency, timeout and adaptive rate

Verified prototype behaviour (executed against this container's loopback):

```python
import asyncio, time

async def scan_one(host, port, *, timeout, grab):
    start = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout)
    except asyncio.TimeoutError:
        return Result(host, port, "filtered", timeout * 1000, service(port), "")
    except (ConnectionRefusedError, OSError):
        return Result(host, port, "closed", (time.perf_counter()-start)*1000, service(port), "")
    banner = await maybe_grab(reader, writer, port) if grab else ""
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass
    return Result(host, port, "open", (time.perf_counter()-start)*1000, service(port), banner)
```

- **Semaphore** bounds in-flight connections (handbook §21.7). Default 500.
- **`wait_for` timeout** is what separates `filtered` from `closed` — and is the main source
  of false negatives: if RTT exceeds the timeout, an open port reads as filtered. So the
  timeout is tuned per environment, not fixed.
- **Adaptive backoff** (modeled on nmap's congestion window, per
  [nmap's algorithms](https://nmap.org/book/port-scanning-algorithms.html)): when the
  timeout/`filtered` rate over a window climbs, concurrency is cut and retried once; when it
  falls, concurrency recovers. This keeps the scan fast on a quiet LAN and *polite* — not
  DoS-like — on anything slower.
- **Rate presets** (from the research):

  | Preset | Concurrency | Timeout | Notes |
  |---|---|---|---|
  | Localhost | 1000 | 0.3 s | nothing to congest |
  | LAN | 500 | 1.0 s | default |
  | Internet (authorized) | 200 | 2.5 s | gentle; avoids DoS/false-negatives |

- **Streaming results** via `as_completed` (handbook §21.7) so the table fills as the scan
  runs — it feels instant even on large scopes.

### 4.3 Target expansion (verified)

`src/portoscan/targets.py` (already written and unit-tested in design): expands CIDR with
`ipaddress.ip_network(...).hosts()`, dotted ranges `a.b.c.d-e`, validates bare IPs, accepts
hostnames, de-duplicates, and enforces the host cap with a `truncated` flag. Verified cases:
`10.0.0.0/24 → 10.0.0.1 …`, `192.168.1.10-12 → 3 hosts`, duplicates collapsed.

---

## 5. User experience & UI

All of this is the handbook made concrete. Section references point at the technique.

### 5.1 Information architecture (modes — handbook §19.3)

```
┌ Header (clock, icon, title) ───────────────────────────────┐
│ Scope banner:  12 hosts × 100 ports · LAN preset · authorized │
├───────────────┬────────────────────────────────────────────┤
│  Targets pane │  Results                                    │
│  ───────────  │  ─────────────────────────────────────────  │
│  file picker  │  DataTable: host · port · state · service · │
│  paste area   │             latency · banner                │
│  port profile │                                             │
│  rate preset  │  (fills live as the scan runs)              │
│  [Preview]    │                                             │
│  [ Scan ]     │                                             │
├───────────────┴────────────────────────────────────────────┤
│ Status: 842/1200 · 37 open · 410 pps · ETA 3s   ▁▂▄▆█ meter │
├─────────────────────────────────────────────────────────────┤
│ Footer: / search · s scan · x stop · e export · ? help · ^P │
└─────────────────────────────────────────────────────────────┘
```

Three modes: **Targets** (compose the scope), **Results** (live + historical), **Settings**.

### 5.2 Layout (handbook §6)

- `Horizontal` split: a docked left **Targets** panel (`width: 34`, a `split: left` draggable
  divider) and a `1fr` **Results** area.
- Responsive breakpoints (handbook §6.6): below 100 cols the Targets panel collapses behind a
  key; below 80 the banner shortens.
- The scope banner is `dock: top`; the status bar and footer `dock: bottom`.

### 5.3 Colour & theme (handbook §7, §8)

Two bundled themes, all colour via tokens (no hard-coded hex):

- **Midnight** (default, dark): deep indigo surface, cyan primary, violet accent.
- **Amber CRT** (dark, high-visibility): black surface, amber primary — a nod to old
  terminals, and highly legible.
- Plus a registered **high-contrast** theme and full `NO_COLOR` / `:nocolor` support
  (handbook §25).

State colours are semantic tokens **and** carry a glyph, so they survive `NO_COLOR` and
colour-blindness:

| State | Token | Glyph (unicode / ascii) |
|---|---|---|
| open | `$success` | `●` / `[+]` |
| closed | `$text-muted` | `·` / `[-]` |
| filtered | `$warning` | `▲` / `[?]` |
| error | `$error` | `✗` / `[x]` |

Icons degrade nerd → unicode → ascii via the handbook's tiered `IconSet` (§9.2).

### 5.4 Widgets (handbook §10–§12, §18)

| Widget | Role |
|---|---|
| `DataTable` | results, virtualised, sortable, zebra, row cursor (§11) |
| `FilterableMultiSelect` (custom, §12.6) | pick ports/profiles, or filter results by state |
| `Select` | rate preset, port profile |
| `RadioSet` | target source (file / paste / range) |
| file picker (`textual-fspicker`) | upload `.txt` (§13.3) |
| `TextArea` | paste/type targets, live-validated |
| `ProgressBar` + custom `ScanMeter` (line-API, §18.3) | progress with gradient + a live open-rate wave |
| `Sparkline` | open-ports-over-time |
| `Digits` | big live open-count |
| scope banner (custom `Static`) | always-visible scope + preset |
| toasts | scan done, export written, errors (§10.5) |
| command palette provider | every action (§20) |

### 5.5 Animation (handbook §17)

- Results **stream in** rather than appearing at once; new rows get a one-frame
  `background-tint` flash that fades (`transition`, §17.3).
- The scan meter animates the open-rate; the progress bar uses a gradient.
- Panel transitions use `out_cubic` ~180 ms; everything passes `level=` and honours
  `TEXTUAL_ANIMATIONS` and a Settings toggle (§17.6).
- A spinner (braille frames, §9.3/§17.5) on the status bar while scanning; 12 fps.

### 5.6 Keyboard & discoverability (handbook §20)

| Key | Action |
|---|---|
| `s` | start scan |
| `x` | stop scan |
| `/` | focus results filter |
| `o` | file-open targets |
| `p` | port profile picker |
| `e` | export |
| `r` | rate preset |
| `,` | settings |
| `ctrl+t` | cycle theme |
| `ctrl+p` | command palette |
| `?` / `F1` | help panel |
| `ctrl+q` | quit |

Footer always shows live bindings; every destructive/expensive action (Full-range scan,
clear history) confirms via a modal (§19.2). All binding ids are remappable (§20.5).

### 5.7 First-run authorization

On first launch, a modal states the authorized-use rule and asks the user to acknowledge that
they will scan only systems they own or are authorized to test. The acknowledgment and
timestamp are stored in app-data. Private/loopback scopes never prompt again; a scope that
includes public addresses shows a non-blocking reminder banner and logs the scope.

---

## 6. Data & persistence (handbook §22)

- **Settings** (`user_config_dir/settings.json`): theme, rate preset, animation level, icon
  tier, default port profile, authorization-ack flag — typed dataclass, schema-versioned,
  atomic writes, corrupt-file tolerant.
- **History** (`user_data_dir/portoscan.sqlite3`, WAL): one row per scan (scope summary,
  started/finished, counts) + per-result rows; re-open any past scan.
- **Target lists & custom profiles**: saved under app-data, listed in the command palette.
- **Logs** (`user_log_dir`): rotating file logs; crash reports with redaction (no banners or
  target contents beyond counts). Never a `StreamHandler` (§22.8).
- **Exports**: CSV/JSON, written atomically, delivered via `deliver_binary` so the same code
  works under `textual serve` (§10.6).

---

## 7. Packaging (handbook §23)

- `resource_path()` for the bundled `top-1000` port data and TCSS; **never** written to.
- PyInstaller spec with `--collect-data textual`, `--add-data` for `assets/`, `console=True`,
  `multiprocessing.freeze_support()` first.
- Multi-size `.ico`/`.icns`/PNG from one master via `tools/make_icons.py`; `.desktop` with
  `Terminal=true`.
- Clean-venv build + a `PORTOSCAN_SMOKE=1` self-test the CI matrix runs against the frozen
  bundle (§23.10).

---

## 8. Testing (handbook §24)

- **Domain**: `targets.expand` (CIDR/range/hostname/dedup/cap), `ports` profiles, `export`
  round-trips — no event loop.
- **Engine**: start an `asyncio` listener on an ephemeral localhost port, assert `open` +
  banner; assert `closed` on a dead port; assert `filtered` on a `wait_for` timeout; assert
  concurrency never exceeds the semaphore; assert cancellation stops promptly. (All of these
  were already proven in the prototype.)
- **Behaviour (Pilot)**: upload a fixture list → scan localhost → table fills → export writes
  a file → stop mid-scan cancels.
- **Snapshots**: deterministic harness apps for the port picker and results table (fixed
  data, no clock/animation — handbook §24.3).
- Lint clean (ruff), typed, headless CI.

---

## 9. Build order

1. `ports.py` + `export.py` (pure, trivial to test).
2. `scan.py` — promote the verified prototype; add adaptive rate + presets; test against a
   local listener.
3. `authorization.py` + `storage.py` + `paths.py`.
4. `app.py` + screens/widgets/styles — the UI.
5. Tests (domain → engine → Pilot → snapshots), then packaging (spec, icons, build script).

`__init__.py` (scope statement) and `targets.py` (verified) are already written.

---

## 10. Explicitly out of scope

- Random public-IP generation.
- Country/geography-based target generation.
- Raw-socket / SYN / stealth scanning.
- OS fingerprinting, vuln detection, exploitation.
- Any feature whose primary purpose is scanning hosts the operator does not control.

PortoScan scans what you point it at, and helps you point it only at what you're allowed to.

---

## Sources

- [`../docs/ADVANCED-TERMINAL-APPS-PYTHON.md`](../docs/ADVANCED-TERMINAL-APPS-PYTHON.md) — the terminal-app techniques this spec builds on
- Scan engine, target expansion, service lookup, states — **prototyped and executed** for this spec
- [nmap: Port Scanning Algorithms](https://nmap.org/book/port-scanning-algorithms.html) — congestion window, backoff, timeout/false-negatives
- [nmap: Port Scanning Overview](https://nmap.org/book/port-scanning.html)
- [HeckerBirb/top-nmap-ports-csv](https://github.com/HeckerBirb/top-nmap-ports-csv) — the real top-ports popularity ranking
- [RustScan](https://github.com/RustScan/RustScan) and [rscan](https://github.com/dotMuny/rscan) — async batching and adaptive congestion control
- [superfastpython: asyncio port scanner](https://superfastpython.com/asyncio-port-scanner/) — `open_connection` + `wait_for` + semaphore patterns
- [StationX: Is Port Scanning Legal?](https://www.stationx.net/is-port-scanning-legal/) and [Calyptix](https://www.calyptix.com/technical-insights/port-scanning-legal-answers-companies/) — authorization, written permission, CFAA, DoS risk of aggressive scans
