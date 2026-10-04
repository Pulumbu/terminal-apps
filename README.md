# terminal-apps

A deep, verified handbook on building desktop-class terminal applications in Python —
plus a reference application that proves every claim in it.

## Contents

| Path | What it is |
|---|---|
| [`docs/ADVANCED-TERMINAL-APPS-PYTHON.md`](docs/ADVANCED-TERMINAL-APPS-PYTHON.md) | The handbook: ~5,600 lines covering widgets, layout, styling, colour, icons, animation, tables, file pickers, single/multi selectors, custom widgets, threading and concurrency scaling, app-data storage, PyInstaller packaging with `resource_path` and `.ico` logos, testing, accessibility and performance |
| [`examples/nocturne/`](examples/nocturne/) | **Nocturne** — a complete, tested, buildable reference app that implements the handbook's patterns |

## Why this is different from a tutorial

Everything in the handbook was checked against the packages themselves, in a clean
virtualenv on Python 3.11, and every non-trivial listing was executed:

- API signatures, CSS properties, design tokens, easing names, themes, events, key names
  and component classes were introspected from **Textual 8.2.8** (not recalled from docs).
- Interactive code was run headlessly through Textual's `run_test`/`Pilot`.
- The packaging section is built on **four real PyInstaller builds** that were launched and
  smoke-tested — including the two that *fail*, with their exact error messages.
- Sizes and startup times are measured numbers, not estimates.
- Breaking changes and library incompatibilities are reported as observed (e.g.
  `Select.BLANK` silently resolving to `False` on 8.x; `textual-pandas` downgrading
  Textual to 3.7.1).

## The reference application

```bash
cd examples/nocturne
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,syntax]"

nocturne                    # run it
nocturne --paths            # show resolved app-data locations
python -m nocturne --inline # render under the shell prompt

pytest                      # 31 tests: domain, storage, concurrency, Pilot, snapshots
pytest --snapshot-update    # re-record SVG snapshots
textual run --dev src/nocturne/app.py   # with live CSS reload + devtools

./tools/build.sh            # clean-venv PyInstaller build + frozen smoke test
```

What Nocturne demonstrates, end to end:

- a `domain/` layer with **no Textual imports**, unit-tested without an event loop
- `resource_path()` + three-tier app-data resolution (portable → `$NOCTURNE_HOME` → OS)
- atomic settings writes, schema migration, corruption tolerance, SQLite in WAL mode,
  a cross-platform single-instance lock
- a custom line-API widget (`render_line` → `Strip`) with sub-cell precision
- a searchable, filterable **multi-select** that keeps its selection across filtering
- thread and async workers with cooperative cancellation and `call_from_thread`
- a debouncer, a bounded fan-out helper, a backpressured pipeline, a process pool
- modal screens that return values, a settings form with live validation
- a command-palette provider, a keymap, responsive breakpoints, two themes
- a `--paths` flag, crash reports, file-only logging
- a PyInstaller spec that actually works, icon generation from one master, and a
  `NOCTURNE_SMOKE=1` self-test the CI matrix runs against the built bundle

## Verified environment

Python 3.11.15 · textual 8.2.8 · rich 15.0.0 · platformdirs 4.12.3 · pyinstaller 6.22.3 ·
pillow 12.3.0 · prompt_toolkit 3.0.53 · questionary 2.1.1 · textual-dev 1.8.0 ·
textual-fspicker 1.0.1 · textual-autocomplete 4.0.6 · textual-plotext 1.0.1 ·
textual-image 0.12.0 · textual-slider 0.2.0 · rich-pixels 3.0.1

Written 2026-10-04.
