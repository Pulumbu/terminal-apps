# Nocturne

The reference application for
[the advanced terminal apps handbook](../../docs/ADVANCED-TERMINAL-APPS-PYTHON.md).

It is a small log explorer, but the point is the scaffolding: every pattern the handbook
recommends is implemented here and covered by tests.

## Run it

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,syntax]"

nocturne                      # the app
nocturne --count 20000        # more sample data
nocturne --theme high-contrast
nocturne --inline             # under the shell prompt, no alt-screen
nocturne --paths              # where config/data/cache/state/logs resolve to
nocturne --version
```

Keys: `/` search · `,` settings · `ctrl+r` reload · `ctrl+t` cycle theme ·
`ctrl+d` delete · `ctrl+p` command palette · `f1` help · `ctrl+q` quit.

## Develop

```bash
# terminal 1 — devtools log console
textual console
# terminal 2 — the app, with live CSS reload
textual run --dev src/nocturne/app.py
```

Edit `src/nocturne/styles/base.tcss` while it runs and the app restyles instantly.

## Test

```bash
pytest                      # 31 tests
pytest --snapshot-update    # re-record the SVG snapshots
```

| File | Layer |
|---|---|
| `tests/test_domain.py` | pure logic, no event loop |
| `tests/test_storage.py` | atomic writes, migration, corruption, SQLite WAL, instance lock |
| `tests/test_concurrency.py` | bounded fan-out, streaming completion, debounce, backpressure, cancellation, process pool |
| `tests/test_app.py` | behaviour through `Pilot`: loading, debounced search, multi-select across filtering, animation, theming, modal validation, breakpoints |
| `tests/test_snapshots.py` | SVG snapshots of deterministic harness apps |

## Build

```bash
./tools/build.sh
```

That script creates a **clean** virtualenv (so unrelated installed packages are not
vacuumed into the bundle), generates the icons, runs PyInstaller against
[`nocturne.spec`](nocturne.spec), prints the bundle size, and then runs the frozen binary's
own smoke test. Measured on Linux x86-64: **30 MB** `--onedir`.

The spec file is the interesting part — it carries the three things a Textual app needs and
PyInstaller will not infer:

```python
datas += collect_data_files("textual")        # the tree-sitter *.scm highlight queries
hiddenimports = ["tree_sitter", "tree_sitter_python", ...]   # imported by language name
console=True                                  # a TUI is a console app, never --windowed
```

## Layout

```
src/nocturne/
├── __main__.py        # freeze_support() first, then the CLI
├── cli.py             # argparse; imports the TUI lazily; NOCTURNE_SMOKE self-test
├── app.py             # the App: layout, workers, actions, crash reports
├── paths.py           # resource_path() + Paths.resolve()
├── storage.py         # atomic writes, Settings + migration, SQLite, SingleInstance
├── concurrency.py     # pools, debounce, bounded fan-out, pipelines
├── domain.py          # pure logic — imports no Textual
├── icons.py           # nerd → unicode → ascii tiering
├── themes.py          # arctic + high-contrast
├── commands.py        # command-palette provider
├── logging_setup.py   # rotating file logs (never a StreamHandler)
├── styles/base.tcss   # hot-reloaded stylesheet
├── widgets/           # WaveMeter (line API), FilterableMultiSelect
└── screens/           # Confirm (returns bool), SettingsScreen (returns Settings)
```
