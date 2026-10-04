# Advanced Terminal Applications in Python — The Complete Handbook

> A deep, practical reference for building desktop-class TUI (terminal user interface)
> applications in Python: widgets, layout, styling, colour, icons, animation, tables,
> file pickers, single/multi selectors, threading and concurrency scaling, app-data
> storage, PyInstaller packaging with `resource_path`, `.ico` logos, testing, and the
> hard-won details beyond.

**Document status:** written 2026-10-04. Every version number, API signature, CSS rule,
design token, easing name and build command in this document was checked against the
packages actually installed in a clean virtualenv on Python 3.11, and every non-trivial
code listing was executed headlessly (Textual's `run_test` / `Pilot`, PyInstaller builds
run and launched). Where a thing was *measured*, the number is given. Where something is
genuinely version-sensitive, the version is stated inline.

### Verified environment

| Package | Version tested | Notes |
|---|---|---|
| Python | 3.11.15 | 3.10+ required for Textual's `syntax` extra |
| `textual` | 8.2.8 | latest at time of writing (released 2026-06-30) |
| `rich` | 15.0.0 | Textual requires `rich>=14.2.0` |
| `textual-dev` | 1.8.0 | `textual console`, `run --dev`, `borders`, `colors`, `easing`, `keys`, `diagnose`, `serve` |
| `pytest-textual-snapshot` | current | SVG snapshot testing |
| `prompt_toolkit` | 3.0.53 | line-editor / REPL stack |
| `questionary` | 2.1.1 | quick prompt flows on top of prompt_toolkit |
| `platformdirs` | 4.12.3 | app-data path resolution |
| `pyinstaller` | 6.22.3 | with `pyinstaller-hooks-contrib` 2026.8 |
| `pillow` | 12.3.0 | `.ico` generation, image widgets |
| `textual-fspicker` | 1.0.1 | modal file/dir pickers |
| `textual-autocomplete` | 4.0.6 | dropdown + path autocomplete |
| `textual-plotext` | 1.0.1 | charts |
| `textual-image` | 0.12.0 | Kitty graphics / Sixel / half-cell / unicode images |
| `textual-slider` | 0.2.0 | slider widget |
| `rich-pixels` | 3.0.1 | image → cells renderable |

---

## Table of contents

1. [What "advanced" means in a terminal](#1-what-advanced-means-in-a-terminal)
2. [Choosing the stack](#2-choosing-the-stack)
3. [The terminal as a rendering target](#3-the-terminal-as-a-rendering-target)
4. [Project architecture](#4-project-architecture)
5. [Textual's core model](#5-textuals-core-model)
6. [Layout](#6-layout)
7. [Styling, theming and design tokens](#7-styling-theming-and-design-tokens)
8. [Colour](#8-colour)
9. [Typography, glyphs and icons](#9-typography-glyphs-and-icons)
10. [The complete built-in widget catalogue](#10-the-complete-built-in-widget-catalogue)
11. [Tables and data grids](#11-tables-and-data-grids)
12. [Selectors: single, multiple, searchable](#12-selectors-single-multiple-searchable)
13. [Trees, file pickers and filesystem UX](#13-trees-file-pickers-and-filesystem-ux)
14. [Forms, inputs and validation](#14-forms-inputs-and-validation)
15. [Text editing and syntax highlighting](#15-text-editing-and-syntax-highlighting)
16. [Charts, graphics and images](#16-charts-graphics-and-images)
17. [Animation and motion design](#17-animation-and-motion-design)
18. [Building custom widgets](#18-building-custom-widgets)
19. [Screens, modals, modes and navigation](#19-screens-modals-modes-and-navigation)
20. [Command palette, keymaps and discoverability](#20-command-palette-keymaps-and-discoverability)
21. [Threading, concurrency and scaling](#21-threading-concurrency-and-scaling)
22. [Application data, config and storage](#22-application-data-config-and-storage)
23. [Packaging: `resource_path`, PyInstaller, icons](#23-packaging-resource_path-pyinstaller-icons)
24. [Testing, debugging and observability](#24-testing-debugging-and-observability)
25. [Accessibility, i18n and UX polish](#25-accessibility-i18n-and-ux-polish)
26. [Performance playbook](#26-performance-playbook)
27. [Beyond the terminal: web, SSH, inline and embedded](#27-beyond-the-terminal-web-ssh-inline-and-embedded)
28. [Appendices](#28-appendices)

---

## 1. What "advanced" means in a terminal

A terminal gives you a grid of character cells. That is the whole hardware budget. Each
cell holds one grapheme plus a style (foreground colour, background colour, bold, italic,
underline, strike, reverse, dim, blink, and in some terminals underline colour and curly
underlines). A "desktop-class" terminal app is one that behaves like a GUI *despite* that
budget:

- **It is never blocked.** Every I/O operation is off the render loop. Scrolling at 60 fps
  while a network call is in flight is table stakes.
- **It is laid out, not printed.** Widgets occupy regions that reflow on resize; there is
  no `print()` anywhere near the UI.
- **It is themed.** A single token change restyles everything; light/dark and
  high-contrast are first-class.
- **It is discoverable.** A footer shows live keybindings, a command palette fuzzy-finds
  every action, and a help panel exists.
- **It is mouse-aware.** Click, drag, hover, scroll-wheel, text selection and even
  pointer-shape changes.
- **It is virtualised.** 1,000,000 rows renders as fast as 100 because only the visible
  strips are built.
- **It remembers.** Window-ish state, recent files, themes and sizes persist in the OS's
  proper app-data location.
- **It ships.** A single binary with an icon, signed, that starts in under a second.

Everything below is in service of those eight properties.

---

## 2. Choosing the stack

### 2.1 The landscape (2026)

| Library | Model | Use it when | Avoid when |
|---|---|---|---|
| **Textual** | Retained-mode widget DOM + CSS + asyncio event loop | You are building an *application*: multiple screens, widgets, mouse, themes | You just need a progress bar in a script |
| **Rich** | Immediate-mode renderables (print / `Live`) | Console output, logs, reports, progress, tables in CLIs | You need focus, input routing, screens |
| **prompt_toolkit** | Full-screen app + best-in-class line editor | REPLs, shells, sophisticated single-line/multi-line input (`IPython`, `pgcli` use it) | You want CSS-ish styling and a widget library |
| **questionary** | Thin prompt flows over prompt_toolkit | Wizards, installers, `git`-style interactive prompts | Persistent UI |
| **urwid** | Canvas widget tree, mature, synchronous-ish | Long-lived legacy apps already using it | New projects (small ecosystem, dated API) |
| **curses / `windows-curses`** | Raw terminal | You need zero dependencies or extreme control | Almost always — you will rebuild Textual badly |

**Default recommendation:** Textual for the app, Rich for anything that prints outside the
app (CLI subcommands, `--help`, crash dumps), prompt_toolkit only if you need a serious
line editor embedded. These compose: Textual *is* built on Rich primitives, and
`App.suspend()` lets you drop out to a prompt_toolkit session and come back.

### 2.2 Why Textual specifically

- 42 built-in widgets (exact list in §10), a 100+ property CSS dialect, 21 built-in
  themes, 33 easing functions, a worker/concurrency API, a command palette, snapshot
  testing, and a web/SSH server.
- One codebase runs in a terminal, inline under your shell prompt, in a browser
  (`textual serve`), and over SSH.
- The render pipeline is strip-based and compositing-aware: a widget that does not change
  is not re-rendered, and updates are wrapped in synchronized-output escapes (`CSI ?2026h`)
  so modern terminals do not tear.

### 2.3 Mixing paradigms safely

```python
# Dropping out of the TUI to run something that owns the terminal (an editor, a pager,
# a prompt_toolkit session) and coming back cleanly.
with app.suspend():
    subprocess.run([os.environ.get("EDITOR", "vi"), str(path)])
```

`App.suspend()` restores the normal screen buffer, disables mouse tracking, and re-enables
everything on exit. Never shell out to a full-screen program without it.

---

## 3. The terminal as a rendering target

You do not need to write escape sequences by hand — but you must know what exists, because
your design choices are bounded by them, and your bug reports will be about them.

### 3.1 The cell model

- A cell is one column wide for most characters, **two columns** for East Asian wide
  characters and most emoji, and **zero** for combining marks. Width is computed from
  Unicode's East Asian Width property plus emoji presentation rules. Rich/Textual do this
  for you via cell-length measurement; if you compute `len(text)` for layout you *will*
  misalign tables.
- Zero-width joiner sequences (👩‍🚀) are a single grapheme that many terminals render at
  width 2 and some at width 4. Avoid them in fixed-width columns.
- A "line" in Textual is a `Strip`: a list of styled segments with a known cell width.

### 3.2 Colour depth

| Env signal | Meaning |
|---|---|
| `COLORTERM=truecolor` or `24bit` | 16.7M colours (`CSI 38;2;r;g;b m`) |
| `TERM=*-256color` | 256-colour palette |
| `TERM=xterm`, `vt100` | 8/16 ANSI colours |
| `NO_COLOR` set (any value) | **Disable colour.** Honour this; it is a de-facto standard |
| `FORCE_COLOR` | Force colour on in non-TTY contexts (CI logs) |
| `TEXTUAL_COLOR_SYSTEM` | `auto` (default), `standard`, `256`, `truecolor` |

Textual targets truecolor and degrades. For an app that must look right on a 16-colour
`TERM`, use the `ansi-dark`/`ansi-light` themes (added in 8.2.5) or `App.ansi_color = True`,
which makes the app use the terminal's own palette and the `:ansi` pseudo-class for
style overrides.

### 3.3 Escape sequences that matter

| Sequence | Purpose | Who supports it |
|---|---|---|
| `CSI ?1049h/l` | Alternate screen buffer | Everything |
| `CSI ?25l/h` | Hide/show cursor | Everything |
| `CSI ?1003h` + `?1006h` | Any-event mouse tracking, SGR extended coordinates | Everything modern |
| `CSI ?2026h/l` | **Synchronized output** — atomic frame; kills tearing | Kitty, WezTerm, Ghostty, foot, iTerm2, Windows Terminal, Alacritty |
| `CSI > 1 u` family | Kitty keyboard protocol — real key-up/down, modifiers, disambiguated keys | Kitty, Ghostty, WezTerm, foot |
| `OSC 8 ;; uri ST` | Hyperlinks in text | Most modern terminals |
| `OSC 52` | Clipboard write (works over SSH/tmux) | Kitty, WezTerm, iTerm2, Ghostty, Windows Terminal |
| `OSC 777` / `OSC 9` | Desktop notification | Kitty, WezTerm, iTerm2 |
| `DCS q` (Sixel) | Raster images | WezTerm, foot, Windows Terminal (1.22+), xterm, mlterm, Contour |
| `APC G` (Kitty graphics) | Raster images, GPU-accelerated, animation | Kitty, Ghostty, WezTerm, Konsole |

Textual uses the first five itself. Items 6–10 you reach via `App.copy_to_clipboard()`,
the `Link` widget, `textual-image`, or raw writes.

**Keyboard protocol caveat (real, current):** Textual 8.2.7 added "report all keys" support
for the Kitty protocol, which finally makes `ctrl+i` distinguishable from `tab` and gives
you separate modifier-key events — but only on terminals that implement it. If a user
reports that a binding does something odd, have them set `TEXTUAL_DISABLE_KITTY_KEY=1` to
confirm. Design your primary bindings to work without it.

### 3.4 Capability detection, practically

```python
import os, sys

def terminal_profile() -> dict[str, object]:
    """Cheap, no-escape-sequence capability guesses. Use for defaults, not gates."""
    term = os.environ.get("TERM", "")
    program = os.environ.get("TERM_PROGRAM", "")
    return {
        "tty": sys.stdout.isatty(),
        "truecolor": os.environ.get("COLORTERM") in ("truecolor", "24bit"),
        "no_color": "NO_COLOR" in os.environ,
        "ssh": bool(os.environ.get("SSH_CONNECTION")),
        "tmux": term.startswith("screen") or term.startswith("tmux") or "TMUX" in os.environ,
        "ci": any(k in os.environ for k in ("CI", "GITHUB_ACTIONS", "BUILDKITE")),
        "program": program or os.environ.get("TERMINAL_EMULATOR", "unknown"),
        "kitty_graphics": program == "ghostty" or term.startswith("xterm-kitty"),
        "wide_unicode": "UTF-8" in (os.environ.get("LC_ALL") or os.environ.get("LANG") or ""),
    }
```

Rules of thumb:

- **Never block on a terminal query response.** Writing `CSI ?2026$p` and reading the reply
  hangs forever on terminals that do not answer, and corrupts input if you get the parsing
  wrong. Libraries like `textual-image` do this carefully with timeouts and raw-mode
  capture; do not roll your own in the UI thread.
- Under `tmux`, image protocols and OSC 52 need passthrough configuration. Degrade to
  half-cell/unicode images rather than printing garbage.
- In CI, run headless (`App.run_test()`); do not try to detect a terminal.

### 3.5 Windows specifics

- Windows Terminal, and Windows 10 1809+ consoles, support VT sequences; `conhost` on older
  builds does not. Textual's `windows_driver` handles enabling virtual-terminal processing.
- Set the console to UTF-8 so box-drawing and icons work:

```python
import sys
if sys.platform == "win32":
    # Python 3.7+: make stdio UTF-8 regardless of the active code page.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

Better: ship with `PYTHONUTF8=1` in your launcher, or build with PyInstaller (which pins
UTF-8 mode in modern versions).

- A TUI is a **console** application. In PyInstaller terms that means **do not** pass
  `--windowed`/`--noconsole`; see §23.
- `ConPTY` adds latency versus Unix PTYs. Budget for it: aim for <8 ms frame work so the
  pipe, not your code, is the bottleneck.

---

## 4. Project architecture

### 4.1 Layout that scales

```
nocturne/
├── pyproject.toml
├── assets/                      # shipped, read-only: .tcss, .ico, .png, seed data
│   ├── app.tcss
│   ├── logo.ico
│   └── logo.png
├── src/nocturne/
│   ├── __init__.py
│   ├── __main__.py              # python -m nocturne
│   ├── cli.py                   # argument parsing; may not import the TUI at module level
│   ├── app.py                   # the App subclass and nothing else
│   ├── paths.py                 # resource_path / app-data resolution (§22, §23)
│   ├── settings.py              # typed config, migration
│   ├── logging_setup.py
│   ├── concurrency.py           # pools, debounce, pipelines (§21)
│   ├── domain/                  # pure logic: no textual imports, 100% unit-testable
│   │   ├── models.py
│   │   └── services.py
│   ├── widgets/                 # custom widgets, one per file
│   │   ├── __init__.py
│   │   ├── meter.py
│   │   └── status_bar.py
│   ├── screens/
│   │   ├── main.py
│   │   ├── settings.py
│   │   └── confirm.py
│   └── styles/                  # TCSS split by concern, imported by the App
│       ├── base.tcss
│       ├── layout.tcss
│       └── widgets.tcss
└── tests/
    ├── test_domain.py
    ├── test_app.py              # Pilot-driven
    └── __snapshots__/           # SVG snapshots
```

**The one rule that matters:** `domain/` must not import `textual`. Everything interesting
— parsing, diffing, scoring, network, database — lives there and is tested without an event
loop. The `screens/` and `widgets/` layers translate domain objects into widgets and
messages. This is what keeps a TUI maintainable past ~5k lines.

### 4.2 `pyproject.toml`

```toml
[project]
name = "nocturne"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
  "textual>=8.2,<9",
  "textual[syntax]>=8.2,<9",   # only if you use TextArea highlighting
  "platformdirs>=4,<5",
  "rich>=14.2",
]

[project.optional-dependencies]
dev = [
  "textual-dev>=1.8",
  "pytest>=8",
  "pytest-asyncio>=0.24",
  "pytest-textual-snapshot",
  "ruff",
  "mypy",
]

[project.scripts]
nocturne = "nocturne.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/nocturne"]
artifacts = ["assets/**"]       # ship the TCSS/icons inside the wheel
```

**Pin the Textual major version.** Textual follows semver and 8.0.0 did rename
`Select.BLANK` → `Select.NULL`; 7.x→8.x also changed screen-dismissal semantics. An
unpinned `textual` in a shipped app is a future support ticket.

**The nastiest version trap, concretely.** 7.1.0 added `Widget.BLANK`; 8.0.0 therefore
renamed `Select.BLANK` (the "nothing selected" sentinel) to `Select.NULL`. `Select.BLANK`
still *resolves* — but it now inherits `Widget.BLANK`, whose value is `False`. Verified on
8.2.8: `Select.BLANK is Select.NULL` is `False` and `Select.BLANK` is `False`. Pre-8.0 code
comparing `value is Select.BLANK` therefore fails silently rather than raising. Grep for
`Select.BLANK` when you upgrade.

### 4.3 Fast CLI, lazy TUI

A TUI binary that takes 800 ms to print `--version` feels broken. Keep the import of
`textual` out of the CLI's hot path:

```python
# src/nocturne/cli.py
from __future__ import annotations
import argparse, sys

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nocturne")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--theme", default=None)
    parser.add_argument("path", nargs="?")
    args = parser.parse_args(argv)

    if args.version:
        from nocturne import __version__          # cheap
        print(__version__)
        return 0

    from nocturne.app import Nocturne             # imports textual: ~250 ms
    return Nocturne(path=args.path, theme=args.theme).run() or 0

if __name__ == "__main__":
    sys.exit(main())
```

### 4.4 Entry points and `__main__.py`

```python
# src/nocturne/__main__.py
from nocturne.cli import main
import sys
sys.exit(main())
```

That makes `python -m nocturne`, `nocturne` (console script), and the frozen binary all
route through one function — which is exactly what you want when debugging "it works from
source but not when packaged".

---
## 5. Textual's core model

Five concepts carry the whole framework. Learn these and the rest is lookup.

### 5.1 The DOM

An `App` owns a stack of `Screen`s; a screen owns a tree of `Widget`s. Every node has an
optional `id`, a set of `classes`, and a type name — exactly like HTML. You build the tree
declaratively in `compose()`:

```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, Input, Label

class Demo(App[None]):
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            with VerticalScroll(id="sidebar", classes="panel"):
                yield Label("Filters")
                yield Input(placeholder="search…", id="q")
            yield VerticalScroll(id="content")
        yield Footer()
```

`compose()` is a generator. `with Container(...)` pushes a parent; anything yielded inside
becomes its child. `App[None]` is the return type of `run()` — type it so
`app.exit(value)` is checked.

**Querying** the DOM uses CSS selectors:

```python
self.query_one("#q", Input)              # exactly one, typed, raises NoMatches otherwise
self.query_one(Input)                    # by type
self.query_one_optional("#maybe", Input) # 7.3.0+: returns None instead of raising
self.query(".panel")                     # DOMQuery — iterable, and supports bulk ops
self.query(".row").add_class("-dim")     # bulk mutate
self.query("Button").last(Button).focus()
```

Mutating the tree at runtime:

```python
await self.mount(Label("new"), after="#sidebar")   # or before=/after= index|selector|widget
self.query("#old").remove()                        # awaitable
widget.refresh(recompose=True)                     # re-run compose() and diff
```

### 5.2 Reactivity

A `reactive` attribute is a descriptor that schedules work when it changes.

```python
from textual.reactive import reactive, var

class Counter(Widget):
    count: reactive[int] = reactive(0)                      # repaint on change
    rows: reactive[list[str]] = reactive(list, layout=True)  # relayout too
    query: reactive[str] = reactive("", init=False)           # don't fire on mount
    mode: reactive[str] = reactive("list", recompose=True)    # rebuild children
    tall: reactive[bool] = reactive(False, toggle_class="-tall")
    silent: var[int] = var(0)                                 # no refresh at all

    def validate_count(self, value: int) -> int:   # coerce / clamp
        return max(0, value)

    def watch_count(self, old: int, new: int) -> None:  # react
        self.app.notify(f"{old} → {new}")

    def compute_label(self) -> str:                  # derived reactive
        return f"{self.count} items"
```

`reactive()` parameters, verified against 8.2.8:
`default, *, layout=False, repaint=True, init=True, always_update=False, recompose=False,
bindings=False, toggle_class=None`.

- `validate_x` runs first and may rewrite the value.
- `watch_x` can take `(new)`, `(old, new)`, or nothing; it may be `async`.
- `compute_x` creates a read-only derived attribute recomputed when dependencies change.
- `always_update=True` fires watchers even when the value compares equal (needed for
  mutable values you mutate in place — though *preferring immutable replacement* is better:
  `self.rows = [*self.rows, item]`).
- `bindings=True` refreshes the footer when the value changes (use with `check_action`).
- **To set a reactive without triggering watchers** (e.g. loading persisted state):
  `self.set_reactive(MyWidget.count, 10)`.

`var()` is `reactive(..., init=False, layout=False, repaint=False)` — a plain observable
with watchers but no rendering side effects.

### 5.3 Messages and events

Widgets communicate by posting messages up the DOM. Events (keyboard, mouse, lifecycle)
are messages the framework posts to you.

```python
from textual import on
from textual.message import Message
from textual.widgets import Button, Input

class Row(Widget):
    class Picked(Message):                 # custom message
        def __init__(self, row_id: str) -> None:
            self.row_id = row_id
            super().__init__()

    def on_click(self) -> None:
        self.post_message(self.Picked(self.id or ""))

class Screenish(Screen):
    @on(Row.Picked)                               # decorator: any Row
    def _picked(self, event: Row.Picked) -> None: ...

    @on(Button.Pressed, "#save")                  # decorator + CSS selector filter
    def _save(self) -> None: ...

    @on(Input.Changed, "#q, #filter")             # multiple selectors
    def _filter(self, event: Input.Changed) -> None: ...

    def on_input_submitted(self, event: Input.Submitted) -> None:
        ...                                       # naming convention still works
```

Two dispatch styles exist: the naming convention (`on_<widget>_<message>`, snake-cased) and
`@on(MessageType, "selector")`. **Prefer `@on`** — it supports selector filtering, allows
several handlers per message, and reads better.

Message control:

- `event.stop()` — stop bubbling. `event.prevent_default()` — suppress built-in behaviour.
- `with self.prevent(Input.Changed): self.query_one(Input).value = "x"` — set a value
  without triggering your own handler (the classic infinite-loop fix).
- Messages are delivered in order, per-widget, on the event loop. A slow handler blocks the
  UI; see §21.

The 43 built-in event classes are listed in [Appendix D](#appendix-d-events).

### 5.4 Bindings and actions

```python
from textual.binding import Binding

class Demo(App[None]):
    BINDINGS = [
        Binding("ctrl+s", "save", "Save", tooltip="Write changes to disk"),
        Binding("ctrl+shift+s", "save_as", "Save as…", show=False),
        Binding("q", "quit", "Quit", priority=True),       # beats widget bindings
        Binding("j,down", "move(1)", "Down", show=False),  # several keys, parameterised
        Binding("k,up", "move(-1)", "Up", show=False),
        Binding("f1", "show_help_panel", "Help", group="Help"),  # grouped in the footer
    ]

    def action_save(self) -> None: ...
    def action_move(self, delta: int) -> None: ...

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """True = enabled, False = hidden, None = shown but disabled (greyed)."""
        if action == "save":
            return self.dirty or None
        return True
```

`Binding` fields (8.2.8): `key, action, description, show, key_display, priority, tooltip,
id, system, group`.

- Bindings resolve from the focused widget upward; `priority=True` inverts that for app-level
  keys you must never lose.
- After changing state that affects `check_action`, call `self.refresh_bindings()` — or
  declare the reactive with `bindings=True`.
- Actions are also reachable from markup links and the command palette:
  `Label("[@click=app.save]Save[/]")`.
- `Binding(..., id="save")` lets users remap keys via `App.KEYMAP`-style overrides, which is
  the hook you expose in a settings screen.

### 5.5 Lifecycle

| Hook | When | Use it for |
|---|---|---|
| `__init__` | construction | store plain args; **no DOM access** |
| `on_load` (App) | before the driver starts | reading config, deciding the first screen |
| `compose` | mount time | declare children |
| `on_mount` | after the node joins the DOM | query children, set intervals, start workers |
| `on_ready` (App) | first paint done | anything that should not delay first paint |
| `on_show` / `on_hide` | visibility change | pause/resume animations |
| `on_resize` | size change | recompute derived layout values |
| `on_unmount` | removal | cancel timers, close files |
| `on_screen_suspend` / `on_screen_resume` | screen stack changes | pause polling on hidden screens |

```python
def on_mount(self) -> None:
    self.timer = self.set_interval(1 / 30, self.tick, pause=True)
    self.load_data()                 # a @work method — returns immediately

def on_show(self) -> None:
    self.timer.resume()

def on_hide(self) -> None:
    self.timer.pause()
```

`set_interval(interval, callback, *, name=None, repeat=0, pause=False) -> Timer` and
`set_timer(delay, callback, …)` both return a `Timer` with `.pause()`, `.resume()`,
`.reset()`, `.stop()`. Always stop timers you own in `on_unmount` — or use the widget's own
`set_interval`, which is cleaned up automatically when the widget is removed.

---

## 6. Layout

### 6.1 Units

| Unit | Meaning |
|---|---|
| `10` | 10 cells |
| `50%` | 50% of the parent's content box |
| `1fr`, `2fr` | fraction of the *remaining* space (flex-grow) |
| `auto` | size to content |
| `10w`, `10h` | 10% of the **window** width/height (viewport units) |
| `5vw`, `5vh` | aliases of the above |

```css
#sidebar { width: 28; }                  /* fixed */
#content { width: 1fr; }                 /* takes the rest */
#a { width: 2fr; } #b { width: 1fr; }    /* 2:1 split */
#modal { width: 60%; max-width: 80; min-width: 40; height: auto; }
```

`1fr` is the single most useful value in Textual CSS. `auto` height on a container inside a
scrollable parent is how you get natural document flow.

### 6.2 The four layouts

`layout: vertical | horizontal | grid | stream` (verified list).

```css
#toolbar  { layout: horizontal; height: 3; }
#stack    { layout: vertical; }
#dashboard{ layout: grid; grid-size: 3 2; grid-gutter: 1 2;
            grid-columns: 1fr 2fr 1fr; grid-rows: auto 1fr; }
#doc      { layout: stream; }   /* optimised for long append-only content */
```

Grid children can span:

```css
.hero { column-span: 2; row-span: 1; }
```

`stream` layout (newer) is for very long vertical content where you want cheap append — log
views, chat transcripts, rendered markdown.

### 6.3 Containers

Verified container classes in `textual.containers`:

| Container | Behaviour |
|---|---|
| `Container` | generic, vertical, no scroll |
| `Vertical` / `Horizontal` | lay out children on that axis (expand to fill) |
| `VerticalGroup` / `HorizontalGroup` | same but `height: auto` — for rows of controls |
| `VerticalScroll` / `HorizontalScroll` | scrollable, focusable scroll container |
| `ScrollableContainer` | base scrollable (both axes) |
| `Center` / `Middle` / `Right` | align children on one axis |
| `CenterMiddle` | centre both axes — the modal idiom |
| `Grid` | grid layout container |
| `ItemGrid` | **responsive** grid: `min_column_width` decides the column count |

`ItemGrid` is the card-dashboard primitive. It reflows the number of columns as the terminal
resizes with zero code:

```python
from textual.containers import ItemGrid
from textual.widgets import Static

def compose(self):
    with ItemGrid(min_column_width=28, id="cards"):
        for metric in self.metrics:
            yield Static(render_card(metric), classes="card")
```

```css
#cards { grid-gutter: 1 2; keyline: thin $primary; height: auto; }
.card  { height: 6; padding: 1; background: $panel; border: round $primary; }
```

### 6.4 Docking

```css
#header  { dock: top;    height: 1; }
#footer  { dock: bottom; height: 1; }
#nav     { dock: left;   width: 24; }
#inspect { dock: right;  width: 40; }
```

Docked widgets are removed from the normal flow and pinned to an edge of their parent; the
remaining children share what is left. `dock` beats everything else for persistent chrome.

### 6.5 Layers and overlays

```css
Screen { layers: base dialogs toasts; }
#editor  { layer: base; }
#palette { layer: dialogs; }
#toast   { layer: toasts; }
```

Later names in `layers` render on top. For popups anchored to a widget (dropdowns), use:

```css
#dropdown { overlay: screen; constrain: none inflect; }
```

`overlay: screen` takes the widget out of flow and sizes it against the screen;
`constrain-x/-y` accept `none | inside | inflect` and keep a dropdown on-screen by sliding
(`inside`) or flipping (`inflect`) it — this is how `Select` keeps its menu visible near the
bottom edge.

### 6.6 Responsive design: breakpoints

Verified: `App.HORIZONTAL_BREAKPOINTS` / `App.VERTICAL_BREAKPOINTS` (also settable per
`Screen`) are lists of `(min_size, class_name)`. Textual sets the class on the screen when
the size crosses the threshold, so you style with plain CSS:

```python
class Demo(App[None]):
    HORIZONTAL_BREAKPOINTS = [(0, "-narrow"), (80, "-normal"), (120, "-wide")]
    VERTICAL_BREAKPOINTS = [(0, "-short"), (30, "-tall")]
```

```css
Screen.-narrow #sidebar { display: none; }
Screen.-narrow #content { width: 1fr; }
Screen.-wide   #inspector { display: block; width: 44; }
Screen.-short  Header { height: 1; }
```

This replaces the `on_resize` + manual class juggling that older Textual apps use. For
anything finer-grained, `on_resize(self, event: events.Resize)` gives you
`event.size` and `event.virtual_size`.

### 6.7 Scrolling

```python
container.scroll_to(y=0, animate=True, duration=0.2, easing="out_cubic")
widget.scroll_visible(animate=True, top=True)
container.scroll_end(animate=False, immediate=True)
log_view.anchor()        # stick to the bottom until the user scrolls away
```

CSS controls:

```css
#list {
  overflow-y: auto;            /* auto | scroll | hidden */
  overflow-x: hidden;
  scrollbar-size-vertical: 1;
  scrollbar-gutter: stable;    /* reserve space so content doesn't jump */
  scrollbar-color: $primary;
  scrollbar-background: $surface-darken-1;
  scrollbar-color-hover: $primary-lighten-1;
  scrollbar-color-active: $accent;
}
```

`scrollbar-gutter: stable` is the fix for "my content shifts one cell when the scrollbar
appears". `TEXTUAL_SMOOTH_SCROLL=0` disables sub-cell smooth scrolling if a user's terminal
struggles.

### 6.8 Splitters

```css
#sidebar { split: left; width: 30; }    /* draggable divider, resizable by the user */
```

`split: left|right|top|bottom` docks the widget *and* gives it a drag handle. This is the
one-line version of a resizable pane.

### 6.9 Maximise / minimise

Screens support `maximize(widget)` / `minimize()`, and a widget can opt in with
`ALLOW_MAXIMIZE = True`. `Screen.ALLOW_IN_MAXIMIZED_VIEW = "Footer"` (the default) keeps the
footer visible when something is maximised. Bind it:

```python
BINDINGS = [Binding("f", "screen.maximize", "Focus pane")]
```

---

## 7. Styling, theming and design tokens

Textual CSS ("TCSS") is a real cascade with specificity, variables, nesting and
transitions. `App.CSS` (inline string), `App.CSS_PATH` (file or list of files), and
`Widget.DEFAULT_CSS` (scoped to the widget by default) all feed it.

### 7.1 Where CSS lives

```python
class Nocturne(App[None]):
    CSS_PATH = ["styles/base.tcss", "styles/layout.tcss", "styles/widgets.tcss"]
```

```python
class Card(Widget):
    DEFAULT_CSS = """
    Card {
        height: auto;
        border: round $primary;
        padding: 1 2;
        &:hover { border: round $accent; }
        & > .card--title { text-style: bold; color: $text-primary; }
    }
    """
    SCOPED_CSS = True     # default: these rules only match inside Card
```

`DEFAULT_CSS` has the lowest priority, so app CSS always wins — that is exactly what you
want for a reusable widget. Set `SCOPED_CSS = False` only if the widget deliberately styles
things outside itself.

With `textual run --dev`, edits to `CSS_PATH` files are **hot-reloaded live**. Keep your CSS
in files during development for this reason alone.

### 7.2 Nesting and the `&` operator

```css
DataTable {
    height: 1fr;
    &:focus { border: tall $accent; }
    & > .datatable--header { text-style: bold; }
    &.-compact { padding: 0; }
    .datatable--cursor { background: $primary 40%; }
}
```

### 7.3 Pseudo-classes (verified complete list)

`:ansi`, `:blur`, `:can-focus`, `:dark`, `:disabled`, `:empty`, `:enabled`, `:even`,
`:first-child`, `:first-of-type`, `:focus`, `:focus-within`, `:hover`, `:inline`,
`:last-child`, `:last-of-type`, `:light`, `:nocolor`, `:odd`

```css
.row:odd  { background: $boost; }
.row:even { background: transparent; }
Button:disabled { text-style: dim; }
Input:focus-within { border: tall $accent; }
Screen:light .card { background: white; }
Screen:nocolor .badge { text-style: reverse; }   /* NO_COLOR users still see state */
Screen:inline Footer { display: none; }          /* running inline under the shell */
```

`:nocolor` and `:ansi` are the accessibility escape hatches: you can express every state
with text styles instead of colour.

### 7.4 Design tokens

A `Theme` defines 12 base colours and arbitrary variables; Textual *generates* 168 CSS
variables from it (verified count on the default theme). You never hard-code a hex value in
app CSS.

The generated families:

| Family | Tokens | Purpose |
|---|---|---|
| Core | `$primary`, `$secondary`, `$accent`, `$warning`, `$error`, `$success` | semantic colour |
| Neutral | `$background`, `$surface`, `$panel`, `$boost`, `$foreground` | elevation |
| Shades | `$X-lighten-1..3`, `$X-darken-1..3`, `$X-muted` on every core/neutral colour | hover/active/subtle states |
| Text | `$text`, `$text-muted`, `$text-disabled`, `$text-primary`, `$text-secondary`, `$text-success`, `$text-warning`, `$text-error`, `$text-accent` | auto-contrast text |
| Borders | `$border`, `$border-blurred` | focus-aware borders |
| Component | `$block-cursor-*`, `$block-hover-background`, `$input-cursor-*`, `$input-selection-*`, `$button-*`, `$footer-*`, `$scrollbar*`, `$link-*`, `$markdown-h1..h6-*`, `$screen-selection-*` | widget internals |

`$text` and friends are special: they are `auto 87%`-style values, meaning "pick black or
white against the current background, at 87% opacity". Using `color: $text` rather than
`color: white` is what makes a widget work in both light and dark themes with no extra
rules. Full token list in [Appendix B](#appendix-b-design-tokens).

### 7.5 Custom variables

```css
$radius-card: round;
$gutter: 1 2;
$brand: #7C4DFF;

.card { border: $radius-card $brand; padding: $gutter; }
```

Or per-theme, which is better because it survives theme switching:

```python
from textual.theme import Theme

ARCTIC = Theme(
    name="arctic",
    primary="#88C0D0",
    secondary="#81A1C1",
    accent="#B48EAD",
    foreground="#D8DEE9",
    background="#2E3440",
    surface="#3B4252",
    panel="#434C5E",
    success="#A3BE8C",
    warning="#EBCB8B",
    error="#BF616A",
    dark=True,
    luminosity_spread=0.15,       # how far -lighten/-darken shades spread
    text_alpha=0.95,              # alpha applied to $text
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#88C0D0",
        "input-selection-background": "#81a1c1 35%",
        "brand": "#B48EAD",       # becomes $brand
    },
)
```

Register and use it:

```python
def on_mount(self) -> None:
    self.register_theme(ARCTIC)
    self.theme = "arctic"
```

`Theme` fields verified in 8.2.8: `name, primary, secondary, warning, error, success,
accent, foreground, background, surface, panel, boost, dark, luminosity_spread, text_alpha,
variables, ansi`.

### 7.6 Built-in themes (21, verified)

`textual-dark`, `textual-light`, `nord`, `gruvbox`, `catppuccin-mocha`,
`catppuccin-latte`, `catppuccin-frappe`, `catppuccin-macchiato`, `dracula`, `tokyo-night`,
`monokai`, `flexoki`, `solarized-light`, `solarized-dark`, `rose-pine`, `rose-pine-moon`,
`rose-pine-dawn`, `atom-one-dark`, `atom-one-light`, `ansi-dark`, `ansi-light`.

```python
# cycle themes; also exposed automatically in the command palette
def action_cycle_theme(self) -> None:
    names = list(self.available_themes)
    self.theme = names[(names.index(self.theme) + 1) % len(names)]

# react to theme changes (e.g. to recolour a chart you render yourself)
def on_mount(self) -> None:
    self.theme_changed_signal.subscribe(self, self._retheme)

def _retheme(self, theme) -> None:
    self.query_one(PlotextPlot).refresh()
```

`TEXTUAL_THEME=nord` sets the default theme without code — a nice user-facing knob.

### 7.7 Borders, outlines, keylines, hatch

Verified border styles: `ascii, blank, block, dashed, double, heavy, hidden, hkey, inner,
none, outer, panel, round, solid, tab, tall, thick, vkey, wide`.

```css
.panel   { border: round $primary; }
.focused { border: tall $accent; }          /* 'tall' = thick top/bottom look */
.sep     { border-left: vkey $primary; }    /* vertical key line only */
.tabbar  { border-bottom: tab $primary; }
.outlined{ outline: double $warning; }      /* drawn *over* content, no layout shift */
#grid    { keyline: thin $primary-muted; }  /* grid cell separators: none|thin|heavy|double */
.texture { hatch: right $primary 20%; }     /* cross|horizontal|left|right|vertical */
```

**`border` vs `outline`:** `border` consumes layout space; `outline` overlays the widget's
own content. Use `outline` for transient validation states so nothing reflows.

Border titles are a signature Textual look:

```python
panel.border_title = "Requests"
panel.border_subtitle = "12 pending"
```

```css
.panel {
  border: round $primary;
  border-title-align: left;
  border-title-color: $text-primary;
  border-title-style: bold;
  border-subtitle-align: right;
  border-subtitle-color: $text-muted;
}
```

Run `textual borders` to see every style rendered live.

### 7.8 Text styling

```css
.title   { text-style: bold; }
.subtle  { text-style: dim italic; }
.error   { text-style: bold underline; color: $text-error; }
.code    { text-style: not bold; }
.wrapped { text-wrap: wrap; text-overflow: ellipsis; text-align: justify; }
.nowrap  { text-wrap: nowrap; text-overflow: clip; }
.fade    { text-opacity: 60%; }
```

Verified flags: `b, blink, bold, dim, i, italic, none, not, o, overline, reverse, strike,
u, underline, uu` (`uu` = double underline). `text-align`: `left, center, right, justify,
start, end`. `text-overflow`: `clip, ellipsis, fold`.

Note (8.2.7): in ANSI themes, `text-opacity` below 50% is rendered as the terminal's `dim`
attribute, because there is no alpha to blend against. Do not rely on fine-grained opacity
for ANSI mode.

### 7.9 Content markup

Textual has its own markup, distinct from Rich markup, in `Static`/`Label`/`Content`:

```python
Label("[b]Bold[/b] [i on $panel]inverse[/] [$text-error]error[/]")
Label("[@click=app.open('x')]a clickable action link[/]")
```

```python
from textual.content import Content
Content.from_markup("Hello [b]$name[/b]", name="world")   # safe variable interpolation
Content.assemble("plain ", ("styled", "bold red"), " more")
```

**Always use `Content.from_markup(template, **vars)` or `markup=False` for user data.**
A filename containing `[` will otherwise be parsed as markup — the TUI equivalent of an
injection bug.

### 7.10 The complete CSS property list

All 104 style properties exposed in 8.2.8 — see [Appendix A](#appendix-a-css-properties)
for the full table with value grammars. The high-value ones you will use constantly:

`width height min-/max-width min-/max-height`, `padding margin`, `border outline`,
`background color`, `text-style text-align text-wrap text-overflow`, `display visibility
opacity`, `layout dock layer layers`, `align content-align`, `grid-size grid-columns
grid-rows grid-gutter`, `overflow-x overflow-y`, `scrollbar-*`, `offset position`,
`transition`, `keyline hatch tint background-tint`, `box-sizing`, `pointer`, `expand`,
`split`, `constrain-x constrain-y`, `overlay`, `line-pad`.

Two newer ones worth knowing:

- `pointer` (7.4.0+) sets the **mouse cursor shape** — 30 values including `pointer`,
  `text`, `grab`, `grabbing`, `not-allowed`, `col-resize` family, `wait`, `zoom-in`. This is
  the detail that makes a TUI feel native in Kitty/Ghostty/WezTerm.
- `background-tint` blends a colour over the resolved background *after* theming — ideal for
  "selected row" states that must work on any theme.

```css
Button           { pointer: pointer; }
Button:disabled  { pointer: not-allowed; }
Input            { pointer: text; }
#divider         { pointer: ew-resize; }
.row.-selected   { background-tint: $primary 25%; }
```

---
## 8. Colour

### 8.1 The `Color` API

```python
from textual.color import Color, Gradient

c = Color.parse("#88C0D0")          # hex, hex8, rgb(), hsl(), named, "ansi_red", "auto"
c.lighten(0.2); c.darken(0.2)
c.with_alpha(0.4)                   # alpha is composited by Textual, not the terminal
c.blend(Color.parse("red"), 0.5)
c.get_contrast_text(alpha=0.87)     # black or white, whichever reads
c.hsl, c.hsv, c.rgb, c.hex, c.hex6, c.brightness, c.inverse, c.monochrome
c.tint(Color.parse("#ff0000").with_alpha(0.1))
```

Alpha works because Textual composites against the known background colour before emitting
a solid cell colour. That is why `background: $primary 20%` works in a terminal that has no
concept of transparency — and also why `background: red 20%` over an *image* widget will not
blend with the image.

### 8.2 Gradients

```python
gradient = Gradient.from_colors("#881177", "#aa3355", "#cc6666", "#ee9944")
gradient = Gradient((0.0, "#1e1e2e"), (0.5, "#89b4fa"), (1.0, "#f5e0dc"), quality=80)
colour_at = gradient.get_color(0.33)
```

Used directly by `ProgressBar(gradient=…)`, `LoadingIndicator`, and any custom widget:

```python
def render_line(self, y: int) -> Strip:
    colour = self._gradient.get_color(y / max(1, self.size.height - 1))
    return Strip([Segment("█" * self.size.width, RichStyle(color=colour.rich_color))])
```

### 8.3 Choosing a palette that survives every theme

1. **Never hard-code hex in app CSS.** Use tokens; a user switching to `solarized-light`
   should not find unreadable text.
2. For data colours (chart series, syntax, status), define them *in the theme's
   `variables`* so each theme can override them:

```python
variables={"chart-1": "#89b4fa", "chart-2": "#a6e3a1", "chart-3": "#f9e2af"}
```

```css
.series-1 { color: $chart-1; }
```

3. **Contrast:** aim for a luminance ratio ≥ 4.5:1 for body text. `Color.get_contrast_text()`
   does the choice for you; `$text` tokens already use it.
4. **Never encode meaning in colour alone.** Pair with a glyph or text style — see §25.

```python
def contrast_ratio(a: Color, b: Color) -> float:
    def lum(c: Color) -> float:
        def ch(v: float) -> float:
            v /= 255
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        r, g, bl = (ch(x) for x in (c.r, c.g, c.b))
        return 0.2126 * r + 0.7152 * g + 0.0722 * bl
    l1, l2 = sorted((lum(a), lum(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)
```

Run `textual colors` to browse the live design system for the active theme.

---

## 9. Typography, glyphs and icons

You have no fonts to choose. You have Unicode, the user's terminal font, and one layout
constraint: **cell width**.

### 9.1 The safe glyph tiers

| Tier | Examples | Safe? |
|---|---|---|
| 1. ASCII | `-`, `|`, `+`, `>`, `*`, `[x]` | Always |
| 2. Box drawing (U+2500–257F) | `─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ ━ ┃ ╭ ╮ ╰ ╯ ╔ ╗` | Virtually always |
| 3. Block elements (U+2580–259F) | `█ ▉ ▊ ▋ ▌ ▍ ▎ ▏ ▀ ▄ ░ ▒ ▓` | Virtually always |
| 4. Geometric/arrows (U+2190–21FF, U+25A0–25FF) | `← → ↑ ↓ ▶ ◀ ▲ ▼ ● ○ ◆ ◇` | Nearly always |
| 5. Braille (U+2800–28FF) | `⠁⠂⠄⡀⢀⣿` | Widely; the basis of 2×4 sub-cell plotting |
| 6. Misc symbols | `✓ ✗ ⚠ ⏻ ⏱ ⌘ ⏎ ⇧` | Usually; width occasionally wrong |
| 7. Emoji | `🔥 ✅ ⚠️ 📁` | **Width 2 and inconsistent**; avoid in aligned columns |
| 8. Nerd Font / Private Use Area | ``, ``, `` | Only if the user has a patched font |

### 9.2 Icons without betting on Nerd Fonts

The right pattern is a **tiered icon set chosen at startup**, not a hard-coded glyph:

```python
from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class IconSet:
    ok: str; warn: str; err: str; info: str
    folder: str; file: str; expand: str; collapse: str
    spinner: tuple[str, ...]
    branch: str; modified: str; added: str; removed: str

ASCII_ICONS = IconSet(
    ok="[ok]", warn="[!]", err="[x]", info="[i]",
    folder="+", file="-", expand=">", collapse="v",
    spinner=("|", "/", "-", "\\"),
    branch="(b)", modified="M", added="A", removed="D",
)
UNICODE_ICONS = IconSet(
    ok="✓", warn="⚠", err="✗", info="ℹ",
    folder="▸", file="·", expand="▶", collapse="▼",
    spinner=("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"),
    branch="⎇", modified="●", added="+", removed="−",
)
NERD_ICONS = IconSet(
    ok="", warn="", err="", info="",
    folder="", file="", expand="", collapse="",
    spinner=UNICODE_ICONS.spinner,
    branch="", modified="", added="", removed="",
)

def pick_icons(preference: str = "auto") -> IconSet:
    """preference: auto | ascii | unicode | nerd  (expose this in settings)"""
    if preference == "ascii":
        return ASCII_ICONS
    if preference == "nerd":
        return NERD_ICONS
    if preference == "unicode":
        return UNICODE_ICONS
    encoding = (os.environ.get("LC_ALL") or os.environ.get("LC_CTYPE")
                or os.environ.get("LANG") or "")
    if "UTF-8" not in encoding.upper() and os.name != "nt":
        return ASCII_ICONS
    if os.environ.get("NERD_FONT") == "1":
        return NERD_ICONS
    return UNICODE_ICONS
```

Store the user's choice in settings (§22) and expose it in a settings screen. This single
abstraction eliminates the most common "the app looks broken on my machine" report.

Nerd Fonts (current series v3.5.x) packs its glyphs into the Private Use Area; the practical
ranges are Seti-UI `E5FA–E6BB`, Devicons `E700–E8EF`, Font Awesome `F000–F2E0`, Powerline
`E0A0–E0A2` / `E0B0–E0B3`, VS Code codicons `EA60–EC84`, Material Design `F0001–F1AF0`.
Because they are PUA, a terminal without the patched font renders tofu (`􏿽`) — hence the
tiering above. Never make a Nerd Font the default.

### 9.3 Sub-cell precision with Braille and blocks

- **Braille** gives you a 2×4 dot matrix per cell: 2× horizontal, 4× vertical resolution.
  This is how `plotext`, `textual-plot` and sparkline libraries draw smooth curves.
- **Block eighths** (`▁▂▃▄▅▆▇█` vertically, `▏▎▍▌▋▊▉█` horizontally) give 8 sub-steps on one
  axis — ideal for bars and meters.
- **Quadrants** (`▘▝▖▗▚▞▀▄█`) give a 2×2 matrix with solid fills, which looks better than
  braille for images.

```python
BLOCKS = " ▏▎▍▌▋▊▉█"

def smooth_bar(fraction: float, width: int) -> str:
    """A horizontal bar with 1/8-cell precision."""
    fraction = max(0.0, min(1.0, fraction))
    total_eighths = round(fraction * width * 8)
    full, remainder = divmod(total_eighths, 8)
    return ("█" * full + (BLOCKS[remainder] if remainder else "")).ljust(width)
```

### 9.4 Measuring text correctly

```python
from rich.cells import cell_len, set_cell_size
cell_len("日本語")      # 6, not 3
set_cell_size("日本語abc", 7)   # truncates respecting double-width cells
```

Use these (or let Textual's `Content`/`Strip` do it) for anything you pad or truncate
yourself. `str.ljust` on CJK or emoji text is a guaranteed misalignment bug.

### 9.5 The app's own logo

Three different artefacts, often confused:

1. **In-terminal logo** — ASCII/ANSI art or a figlet banner shown on a splash/about screen.
2. **Window/taskbar icon** — the `.ico` (Windows), `.icns` (macOS), `.png` (Linux `.desktop`)
   embedded by the packager. See §23.5.
3. **Header glyph** — `Header(icon="❄")`, one cell, shown top-left.

```python
# Figlet banner, optional dependency, graceful fallback
def banner(text: str) -> str:
    try:
        from pyfiglet import Figlet
        return Figlet(font="slant").renderText(text)
    except Exception:
        return text.upper()
```

For a real raster logo in-terminal, see §16.4 (`textual-image` / `rich-pixels`).

---

## 10. The complete built-in widget catalogue

All 42 widgets exported by `textual.widgets` in 8.2.8, with the signature detail you
actually need. Messages are nested classes — handle with `@on(Widget.Message)`.

### 10.1 Input and control

| Widget | Key constructor args | Messages |
|---|---|---|
| `Button` | `label, variant='default'\|'primary'\|'success'\|'warning'\|'error', compact=False, flat=False, action=None, tooltip=None` | `Pressed` |
| `Checkbox` | `label, value=False, button_first=True, compact=False` | `Changed` |
| `RadioButton` | `label, value=False, button_first=True, compact=False` | `Changed` |
| `RadioSet` | `*buttons, compact=False` | `Changed` (gives `.pressed`; index via `event.radio_set.pressed_index`) |
| `Switch` | `value=False, animate=True` | `Changed` |
| `Input` | `value, placeholder, password=False, type='text'\|'integer'\|'number', restrict=<regex>, max_length, suggester, validators, validate_on, valid_empty, select_on_focus=True, compact=False` | `Changed`, `Submitted`, `Blurred` |
| `MaskedInput` | `template, value, placeholder, validators, …` | `Changed`, `Submitted`, `Blurred` |
| `TextArea` | `text, language, theme='css', soft_wrap=True, tab_behavior='focus'\|'indent', read_only=False, show_line_numbers=False, line_number_start=1, max_checkpoints=50, highlight_cursor_line=True, placeholder, compact=False` | `Changed`, `SelectionChanged` |
| `Select` | `options, prompt='Select', allow_blank=True, value=Select.NULL, type_to_search=True, compact=False` | `Changed` |
| `SelectionList` | `*selections, compact=False` | `SelectionHighlighted`, `SelectionToggled`, `SelectedChanged` |
| `OptionList` | `*content, markup=True, compact=False` | `OptionHighlighted`, `OptionSelected` |
| `ListView` | `*items, initial_index=0` | `Highlighted`, `Selected` |
| `Link` | `text, url, tooltip` | — (opens via `action_open_link`) |

Note the `compact=False` parameter that now appears across the input widgets: it removes
padding/borders for dense forms and toolbars. `flat=True` on `Button` removes the 3-D look.

### 10.2 Data display

| Widget | Purpose | Key API |
|---|---|---|
| `DataTable` | virtualised table/grid | `add_column(s)`, `add_row(s)`, `update_cell(_at)`, `sort`, `move_cursor`, `get_row(_at)`, `remove_row`, `cursor_type='cell'\|'row'\|'column'\|'none'` |
| `Tree` | generic tree | `root.add()`, `add_leaf()`, `add_json()`, `move_cursor`, `select_node` |
| `DirectoryTree` | filesystem tree | `path`, `reload`, `reload_node`, `filter_paths` |
| `Markdown` / `MarkdownViewer` | rendered markdown (+ TOC, history) | `update`, `append`, `load`, `goto_anchor`, `back`, `forward`, `go` |
| `Log` | fast plain-text log | `write`, `write_line`, `write_lines`, `max_lines`, `auto_scroll` |
| `RichLog` | log accepting Rich renderables | `write(renderable)`, `markup`, `highlight`, `wrap` |
| `Pretty` | pretty-printed Python object | `update(obj)` |
| `Sparkline` | inline mini-chart | `data`, `summary_function`, `min_color`, `max_color` |
| `Digits` | 7-segment style big numbers | `update("12:34")` |
| `ProgressBar` | determinate/indeterminate progress | `total`, `progress`, `advance`, `update`, `gradient`, `show_eta` |
| `LoadingIndicator` | animated spinner | — |
| `Static` / `Label` | any renderable / one line | `update`, `content`; `Label(variant=…)` |
| `Placeholder` | layout scaffolding | `variant='default'\|'size'\|'text'`, `cycle_variant()` |
| `Rule` | horizontal/vertical divider | `orientation`, `line_style` |
| `Tooltip` | hover tooltip (set via `widget.tooltip = "..."`) | — |

### 10.3 Layout and navigation widgets

| Widget | Purpose |
|---|---|
| `Header` | title bar; `show_clock=True`, `icon`, `time_format`, click to expand |
| `Footer` | live keybinding bar; `show_command_palette=True`, `compact=False` |
| `TabbedContent` + `TabPane` | tabbed panes with content management |
| `Tabs` + `Tab` | just the tab strip (bind content yourself) |
| `ContentSwitcher` | show exactly one child by `current` id |
| `Collapsible` | expand/collapse section; `title`, `collapsed`, custom symbols |
| `HelpPanel` | auto-generated keybinding help (`action_show_help_panel`) |
| `KeyPanel` | live key display panel |
| `Welcome` | stock welcome screen |

### 10.4 Twenty recipes, one per widget family

```python
# Button variants + action links + compact toolbars
yield Button("Save", variant="success", id="save", tooltip="⌘S")
yield Button("Danger", variant="error", flat=True, compact=True)
yield Button("Docs", action="app.open_docs")        # no handler needed

# Switch / Checkbox / RadioSet
yield Switch(value=settings.dark, id="dark")
yield Checkbox("Follow tail", value=True, id="tail")
with RadioSet(id="mode"):
    yield RadioButton("List", value=True)
    yield RadioButton("Grid")

@on(RadioSet.Changed, "#mode")
def _mode(self, event: RadioSet.Changed) -> None:
    # Changed carries .radio_set and .pressed; the index lives on the set.
    self.view_mode = ("list", "grid")[event.radio_set.pressed_index]

# Digits as a live clock
self.set_interval(1, lambda: self.query_one(Digits).update(time.strftime("%H:%M:%S")))

# ProgressBar with gradient + ETA
bar = ProgressBar(total=len(items), show_eta=True,
                  gradient=Gradient.from_colors("#881177", "#cc6666", "#ee9944"))
bar.advance(1)                      # or bar.update(progress=n, total=m)
bar.update(total=None)              # switch to indeterminate

# Sparkline driven by a rolling window
spark = self.query_one(Sparkline)
spark.data = self.history[-60:] or [0]
spark.summary_function = max

# Collapsible sections (a great alternative to tabs for forms)
with Collapsible(title="Advanced", collapsed=True):
    yield Checkbox("Verify TLS", value=True)
    yield Input(placeholder="proxy url")

# ContentSwitcher: the cleanest master/detail
with ContentSwitcher(initial="empty", id="detail"):
    yield Static("Nothing selected", id="empty")
    yield RequestView(id="request")
    yield ResponseView(id="response")
self.query_one("#detail", ContentSwitcher).current = "request"

# Log vs RichLog
self.query_one(Log).write_line("plain, fastest, 100k lines fine")
self.query_one(RichLog).write(Panel(syntax, title="response"))   # renderables

# Loading state for any widget — no custom spinner needed
table.loading = True
try:
    rows = await fetch()
finally:
    table.loading = False

# Tooltips and help
widget.tooltip = "Shown after App.TOOLTIP_DELAY (0.5s)"
class MyScreen(Screen):
    HELP = "Use j/k to move, / to search, enter to open."   # shown by HelpPanel
```

### 10.5 Notifications (toasts)

```python
self.notify("Saved 42 records", title="Done", severity="information", timeout=4)
self.notify("Disk almost full", severity="warning")
self.notify("Upload failed: 503", severity="error", timeout=10)
self.notify("[b]Markup[/] is allowed", markup=True)
```

`App.NOTIFICATION_TIMEOUT = 5` sets the default. Toasts are real widgets
(`Toast`/`ToastRack`) so they are themeable:

```css
Toast { width: 48; }
Toast.-error { border-left: wide $error; }
ToastRack { align-horizontal: right; }
```

### 10.6 Delivering files to the user

For apps that also run in the browser via `textual serve`, Textual abstracts "save a file":

```python
self.deliver_text(path_or_file, save_filename="report.csv", mime_type="text/csv")
self.deliver_binary(buffer, save_filename="export.zip")
# then handle events.DeliveryComplete / events.DeliveryFailed
```

In a terminal it writes to disk; in the browser it triggers a download. Use it instead of
`open(...).write(...)` if web deployment is on your roadmap.

---
## 11. Tables and data grids

`DataTable` is the most important widget in a serious TUI, and the one most often misused.

### 11.1 Constructor, verified

```python
DataTable(
    *, show_header=True, show_row_labels=True, fixed_rows=0, fixed_columns=0,
    zebra_stripes=False, header_height=1, show_cursor=True,
    cursor_foreground_priority="css",          # "css" | "renderable"
    cursor_background_priority="renderable",
    cursor_type="cell",                        # "cell" | "row" | "column" | "none"
    cell_padding=1, name=None, id=None, classes=None, disabled=False,
)
```

### 11.2 Building a table properly

```python
from rich.text import Text
from textual.widgets import DataTable

class Orders(DataTable):
    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.fixed_columns = 1              # freeze the id column while scrolling right
        self.add_column("ID", key="id", width=8)
        self.add_column("Customer", key="customer")
        self.add_column(Text("Total", justify="right"), key="total", width=12)
        self.add_column("Status", key="status", width=10)

    def load(self, orders: list[Order]) -> None:
        self.clear()                        # clear(columns=True) also drops columns
        for order in orders:
            self.add_row(
                order.id,
                order.customer,
                Text(f"{order.total:,.2f}", justify="right", style="bold"),
                status_cell(order.status),
                key=order.id,               # stable key — never rely on row index
                height=1,                   # explicit height keeps scrolling O(1)
            )

def status_cell(status: str) -> Text:
    palette = {"paid": "green", "pending": "yellow", "failed": "red bold"}
    glyph = {"paid": "✓", "pending": "…", "failed": "✗"}[status]
    return Text(f"{glyph} {status}", style=palette[status])
```

**Keys, not indices.** `add_row(..., key=...)` returns a `RowKey`; `RowSelected` gives you
`event.row_key`. Index-based code breaks the moment you sort or filter.

### 11.3 Sorting

```python
table.sort("total", reverse=True)                        # by column key
table.sort("status", "customer")                         # multi-column
table.sort("total", key=lambda value: float(str(value).replace(",", "")))

@on(DataTable.HeaderSelected)
def _sort(self, event: DataTable.HeaderSelected) -> None:
    key = event.column_key
    self._reverse = not self._reverse if key == self._sort_key else False
    self._sort_key = key
    event.data_table.sort(key, reverse=self._reverse)
    self._paint_sort_indicator(event.column_index)
```

Add a sort indicator by relabelling the header:

```python
def _paint_sort_indicator(self, active: int) -> None:
    table = self.query_one(DataTable)
    for index, column in enumerate(table.columns.values()):
        base = str(column.label).rstrip(" ▲▼")
        arrow = (" ▼" if self._reverse else " ▲") if index == active else ""
        column.label = Text(base + arrow)
    table.refresh()
```

### 11.4 In-place editing

`DataTable` is not an editable grid out of the box. The idiomatic pattern is
**cell → modal → update**:

```python
@on(DataTable.CellSelected)
@work
async def _edit(self, event: DataTable.CellSelected) -> None:
    new_value = await self.app.push_screen_wait(
        EditCellScreen(str(event.value), title=str(event.cell_key.column_key.value))
    )
    if new_value is None:
        return
    event.data_table.update_cell_at(event.coordinate, new_value, update_width=True)
    await self.persist(event.cell_key, new_value)
```

For a true inline editor, overlay an `Input` positioned at the cursor region:

```python
def _inline_edit(self, table: DataTable) -> None:
    region = table._get_cell_region(table.cursor_coordinate)   # internal but stable-ish
    editor = Input(value=str(table.get_cell_at(table.cursor_coordinate)), compact=True)
    editor.styles.position = "absolute"
    editor.styles.offset = (region.x, region.y)
    editor.styles.width = region.width
    editor.styles.layer = "overlay"
    self.mount(editor)
    editor.focus()
```

Prefer the modal; the inline version touches private geometry APIs and needs re-testing on
each Textual minor release.

### 11.5 Scaling to very large datasets

`DataTable` virtualises rendering (only visible strips are built) but **keeps every row in
memory** and does per-row width measurement. Measured guidance:

| Rows | Approach |
|---|---|
| ≤ 10,000 | `add_rows()` in one call; fine |
| 10k–100k | add in chunks from a worker, with `batch_update()`; set explicit `width=` on every column to skip auto-measurement |
| > 100k | **do not load it all.** Window the data: keep a page of ~2× the viewport in the table and swap on scroll, or build a custom `ScrollView` widget (§18.4) that renders directly from your data source |

```python
@work(exclusive=True, thread=True)
def load_big(self, rows: Iterable[tuple]) -> None:
    table = self.query_one(DataTable)
    buffer: list[tuple] = []
    worker = get_current_worker()
    for row in rows:
        if worker.is_cancelled:
            return
        buffer.append(row)
        if len(buffer) >= 1000:
            self.call_from_thread(self._flush, table, buffer.copy())
            buffer.clear()
    if buffer:
        self.call_from_thread(self._flush, table, buffer)

def _flush(self, table: DataTable, rows: list[tuple]) -> None:
    with self.app.batch_update():          # one repaint for the whole chunk
        table.add_rows(rows)
```

`App.batch_update()` is the single biggest win for bulk mutation: it suppresses refreshes
until the block exits.

Other levers:

- Explicit `width=` on columns avoids measuring every cell.
- Fixed `height=1` rows avoid per-row height computation.
- `cursor_type="row"` is cheaper than `"cell"` (fewer component-style lookups).
- Do your filtering and sorting in the domain layer (or SQL), not by rebuilding the table.

### 11.6 Component classes for styling

```css
DataTable {
  & > .datatable--header        { background: $primary-muted; text-style: bold; }
  & > .datatable--header-hover  { background: $primary; }
  & > .datatable--cursor        { background: $primary 40%; text-style: bold; }
  & > .datatable--hover         { background: $boost; }
  & > .datatable--odd-row       { background: $surface; }
  & > .datatable--even-row      { background: $surface-lighten-1; }
  & > .datatable--fixed         { background: $panel; }
  & > .datatable--fixed-cursor  { background: $accent 30%; }
}
```

All nine verified component classes are listed in [Appendix C](#appendix-c-component-classes).

### 11.7 Rich tables, when you are *not* in a TUI

For CLI output (reports, `--list`), a Rich `Table` is the right tool:

```python
from rich.console import Console
from rich import box
from rich.table import Table

table = Table(title="Orders", box=box.ROUNDED, header_style="bold cyan",
              row_styles=["", "on grey11"], show_lines=False, expand=True)
table.add_column("ID", style="dim", no_wrap=True)
table.add_column("Customer", overflow="ellipsis", max_width=30)
table.add_column("Total", justify="right")
table.add_row("1001", "Acme Corporation Limited", "1,204.55")
Console().print(table)
```

23 box styles are available (`ASCII`, `ASCII2`, `ROUNDED`, `HEAVY`, `HEAVY_HEAD`, `DOUBLE`,
`DOUBLE_EDGE`, `MINIMAL`, `MINIMAL_HEAVY_HEAD`, `SIMPLE`, `SIMPLE_HEAD`, `SIMPLE_HEAVY`,
`SQUARE`, `SQUARE_DOUBLE_HEAD`, `HORIZONTALS`, `MARKDOWN`, …). You can also drop a Rich
`Table` straight into a `Static` or `RichLog` inside Textual — handy for a one-off summary
panel where `DataTable`'s interactivity is unwanted.

---

## 12. Selectors: single, multiple, searchable

### 12.1 Decision table

| Need | Widget |
|---|---|
| One value from a short list, collapsed | `Select` |
| One value from a long list, always visible | `OptionList` |
| One value, rich multi-widget rows | `ListView` + `ListItem` |
| One value, mutually exclusive, all visible | `RadioSet` |
| Many values with checkboxes | `SelectionList` |
| Many values, free-form tags | `Input` + chips (custom) or `textual-tags` |
| Any action in the app | command palette (§20) |
| A value typed with completion | `Input` + `textual-autocomplete` |

### 12.2 `Select` — single choice, collapsed

```python
from textual.widgets import Select

REGIONS = [("US East (N. Virginia)", "us-east-1"),
           ("EU (Frankfurt)", "eu-central-1"),
           ("AP (Singapore)", "ap-southeast-1")]

yield Select(REGIONS, prompt="Choose a region", allow_blank=True,
             value="eu-central-1", type_to_search=True, id="region", compact=True)

# Also: Select.from_values(["a", "b"]) when label == value
@on(Select.Changed, "#region")
def _region(self, event: Select.Changed) -> None:
    if event.value is Select.NULL:       # NOT Select.BLANK on 8.x — see §4.2
        return
    self.region = str(event.value)

# repopulating
self.query_one("#region", Select).set_options(new_options)
self.query_one("#region", Select).clear()
```

`type_to_search=True` (default) lets the user jump by typing while the overlay is open.
Style the overlay:

```css
Select { width: 40; }
Select > SelectOverlay { max-height: 12; border: round $primary; }
Select:focus > SelectCurrent { border: tall $accent; }
```

### 12.3 `SelectionList` — multiple choice

```python
from textual.widgets import SelectionList
from textual.widgets.selection_list import Selection

yield SelectionList[str](
    Selection("Unit tests", "unit", True),          # (label, value, initial_state)
    Selection("Integration tests", "integration"),
    Selection("End-to-end tests", "e2e", False, id="e2e"),
    id="suites",
)
```

Verified API: `select`, `deselect`, `toggle`, `select_all`, `deselect_all`, `toggle_all`,
`add_option(s)`, `remove_option`, `clear_options`, `get_option(_at_index)`, plus the
`selected` property.

```python
@on(SelectionList.SelectedChanged, "#suites")
def _suites(self, event: SelectionList.SelectedChanged) -> None:
    self.chosen = set(event.selection_list.selected)
    self.query_one("#run", Button).disabled = not self.chosen
```

`SelectionList` subclasses `OptionList`, so it inherits keyboard navigation; `space` toggles,
`enter` highlights. Add select-all/invert bindings yourself:

```python
class Suites(SelectionList[str]):
    BINDINGS = [
        Binding("ctrl+a", "select_all_items", "All"),
        Binding("ctrl+d", "deselect_all_items", "None"),
        Binding("ctrl+i", "invert", "Invert"),
    ]
    def action_select_all_items(self) -> None: self.select_all()
    def action_deselect_all_items(self) -> None: self.deselect_all()
    def action_invert(self) -> None: self.toggle_all()
```

Component classes for the checkbox glyphs:

```css
SelectionList {
  & > .selection-list--button                     { color: $panel; background: $surface; }
  & > .selection-list--button-selected            { color: $success; }
  & > .selection-list--button-highlighted         { background: $boost; }
  & > .selection-list--button-selected-highlighted{ color: $success; background: $boost; }
}
```

### 12.4 `OptionList` — the flexible list primitive

```python
from textual.widgets import OptionList
from textual.widgets.option_list import Option

yield OptionList(
    Option("Open…",        id="open"),
    Option("Open recent",  id="recent"),
    None,                                  # ← a separator (8.x: plain None)
    Option("Quit",         id="quit"),
    markup=True, compact=True, id="menu",
)
```

**Breaking change worth flagging:** in Textual 8.x `textual.widgets.option_list` exports
only `DuplicateID, Option, OptionDoesNotExist`. The old `Separator()` class is gone —
pass `None` in the content stream instead. (Verified: importing `Separator` raises
`ImportError` on 8.2.8.)

```python
@on(OptionList.OptionSelected, "#menu")
def _menu(self, event: OptionList.OptionSelected) -> None:
    match event.option.id:
        case "open":   self.action_open()
        case "quit":   self.exit()
```

Options can be any renderable (a `Table`, a `Group`, a `Content`), which is how you build
rich rows — e.g. a two-line result with a title and a dim path.

### 12.5 `ListView` — multi-widget rows

```python
from textual.widgets import ListItem, ListView, Label

class Result(ListItem):
    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__()
        self.title, self.subtitle = title, subtitle
    def compose(self) -> ComposeResult:
        yield Label(self.title, classes="result--title")
        yield Label(self.subtitle, classes="result--sub")

yield ListView(*(Result(t, s) for t, s in results), id="results")
```

```css
Result { height: 2; padding: 0 1; }
Result.--highlight { background: $primary 30%; }
.result--title { text-style: bold; }
.result--sub   { color: $text-muted; }
```

Mutation API: `append`, `extend`, `insert`, `pop`, `remove_items`, `clear`.

### 12.6 A searchable, filterable multi-select (composite pattern)

This is the control real apps need and no framework ships. Verified working on 8.2.8.

```python
from __future__ import annotations
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.fuzzy import Matcher
from textual.widgets import Input, Label, SelectionList
from textual.widgets.selection_list import Selection


class FilterableMultiSelect(Vertical):
    """Search box + checkbox list + live count, with fuzzy filtering."""

    DEFAULT_CSS = """
    FilterableMultiSelect {
        height: auto; border: round $primary; padding: 0 1;
        & > Input { border: none; padding: 0; height: 1; }
        & > SelectionList { height: auto; max-height: 12; }
        & > #fms-count { color: $text-muted; height: 1; }
        &:focus-within { border: round $accent; }
    }
    """
    BINDINGS = [
        Binding("ctrl+a", "select_all", "All", show=False),
        Binding("ctrl+d", "clear_all", "None", show=False),
    ]

    def __init__(self, items: dict[str, str], *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._items = items                      # value -> label
        self._selected: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Input(placeholder="type to filter…", id="fms-search")
        yield SelectionList[str](id="fms-list")
        yield Label("0 selected", id="fms-count")

    def on_mount(self) -> None:
        self._repopulate("")

    @property
    def selected(self) -> set[str]:
        return set(self._selected)

    def _repopulate(self, query: str) -> None:
        listing = self.query_one("#fms-list", SelectionList)
        matcher = Matcher(query) if query else None
        rows: list[tuple[float, Selection[str]]] = []
        for value, label in self._items.items():
            if matcher is None:
                rows.append((0.0, Selection(label, value, value in self._selected)))
                continue
            score = matcher.match(label)
            if score > 0:
                rows.append((score, Selection(matcher.highlight(label), value,
                                              value in self._selected)))
        rows.sort(key=lambda pair: -pair[0])
        listing.clear_options()
        if rows:
            listing.add_options([selection for _score, selection in rows])
        self._refresh_count()

    def _refresh_count(self) -> None:
        total = len(self._items)
        self.query_one("#fms-count", Label).update(
            f"{len(self._selected)} of {total} selected"
        )

    @on(Input.Changed, "#fms-search")
    def _filter(self, event: Input.Changed) -> None:
        event.stop()
        self._repopulate(event.value)

    @on(SelectionList.SelectedChanged, "#fms-list")
    def _sync(self, event: SelectionList.SelectedChanged) -> None:
        event.stop()
        visible = {
            option.value
            for option in (event.selection_list.get_option_at_index(index)
                           for index in range(event.selection_list.option_count))
        }
        chosen = set(event.selection_list.selected)
        self._selected -= (visible - chosen)      # unticked while visible
        self._selected |= chosen                  # ticked while visible
        self._refresh_count()

    def action_select_all(self) -> None:
        self._selected |= set(self._items)
        self._repopulate(self.query_one("#fms-search", Input).value)

    def action_clear_all(self) -> None:
        self._selected.clear()
        self._repopulate(self.query_one("#fms-search", Input).value)
```

The important subtlety: **selection state lives in the component, not the widget**, because
filtering destroys and rebuilds the options. Every filterable multi-select has this bug if
it does not separate the two.

`textual.fuzzy.Matcher` is the same fuzzy matcher the command palette uses — `match()`
returns a score and `highlight()` returns the string with matched characters styled. Reuse
it rather than writing your own scorer.

### 12.7 Autocomplete input

```python
from textual_autocomplete import AutoComplete, DropdownItem, PathAutoComplete

yield Input(placeholder="language", id="lang")
yield AutoComplete("#lang", candidates=[
    DropdownItem("Python", prefix="🐍 "),
    DropdownItem("Rust",   prefix="🦀 "),
    DropdownItem("Go",     prefix="🐹 "),
])

# Dynamic candidates (called on each keystroke with the current TargetState)
yield AutoComplete("#q", candidates=lambda state: [
    DropdownItem(name) for name in self.index.prefix(state.text)
])

# Path completion with one line
yield Input(placeholder="file", id="pth")
yield PathAutoComplete(target="#pth", path=Path.cwd())
```

Verified against `textual-autocomplete` 4.0.6: `AutoComplete(target, candidates=None, *,
prevent_default_enter=True, prevent_default_tab=True, …)` where `target` is an `Input` or a
selector string, and candidates may be a sequence or a callable. Exports: `AutoComplete`,
`AutoCompleteList`, `DropdownItem`, `DropdownItemHit`, `PathAutoComplete`, `TargetState`.

---

## 13. Trees, file pickers and filesystem UX

### 13.1 `Tree`

```python
from textual.widgets import Tree

tree: Tree[dict] = Tree("Project", id="tree")
tree.show_root = False
tree.guide_depth = 3
tree.auto_expand = True
src = tree.root.add("src", data={"kind": "dir"}, expand=True)
src.add_leaf("app.py", data={"kind": "file", "size": 2048})
tree.root.add_json({"config": {"debug": True, "levels": [1, 2, 3]}})  # JSON → tree
```

```css
Tree {
  & > .tree--guides          { color: $surface-lighten-2; }
  & > .tree--guides-hover    { color: $primary; }
  & > .tree--guides-selected { color: $accent; }
  & > .tree--cursor          { background: $primary 35%; text-style: bold; }
  & > .tree--highlight       { text-style: underline; }
  & > .tree--label           { color: $foreground; }
}
```

Messages: `NodeExpanded`, `NodeCollapsed`, `NodeHighlighted`, `NodeSelected`.

**Lazy loading** is the key tree pattern — never walk a big hierarchy eagerly:

```python
@on(Tree.NodeExpanded)
@work(thread=True, group="tree")
def _expand(self, event: Tree.NodeExpanded) -> None:
    node = event.node
    if node.data and node.data.get("loaded"):
        return
    children = scan(node.data["path"])          # blocking I/O, on a thread
    self.app.call_from_thread(self._fill, node, children)

def _fill(self, node, children) -> None:
    node.remove_children()
    for child in children:
        if child.is_dir():
            node.add(child.name, data={"path": child, "loaded": False})
        else:
            node.add_leaf(child.name, data={"path": child})
    node.data["loaded"] = True
```

### 13.2 `DirectoryTree`

```python
from textual.widgets import DirectoryTree

class SourceTree(DirectoryTree):
    IGNORE = {".git", "__pycache__", ".venv", "node_modules", ".mypy_cache"}

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return sorted(
            (p for p in paths if p.name not in self.IGNORE and not p.name.startswith(".")),
            key=lambda p: (not p.is_dir(), p.name.lower()),
        )
```

```css
DirectoryTree {
  & > .directory-tree--folder    { text-style: bold; color: $text-primary; }
  & > .directory-tree--file      { color: $foreground; }
  & > .directory-tree--extension { text-style: italic; color: $text-muted; }
  & > .directory-tree--hidden    { color: $foreground-disabled; }
}
```

Messages: `FileSelected(node, path)`, `DirectorySelected(node, path)`. Call `reload()` or
`reload_node(node)` after you know the filesystem changed.

Textual 8.0.1 moved `DirectoryTree`'s directory scanning onto a thread specifically to stop
micro-freezes on slow/networked filesystems — so on 8.x you get non-blocking expansion for
free. On a network mount, still add your own timeout guard before pointing a tree at it.

### 13.3 Modal file pickers with `textual-fspicker`

Verified signatures (`textual-fspicker` 1.0.1):

```python
from textual_fspicker import FileOpen, FileSave, SelectDirectory, Filters

FileOpen(location=".", title="Open", *, open_button="", cancel_button="",
         filters=None, must_exist=True, default_file=None,
         double_click_directories=True, suggest_completions=True)

FileSave(location=".", title="Save as", *, save_button="", cancel_button="",
         filters=None, can_overwrite=True, default_file=None, suggest_completions=True)

SelectDirectory(location=".", title="Select directory", *, select_button="",
                cancel_button="", double_click_directories=True)
```

```python
from pathlib import Path
from textual import work
from textual_fspicker import FileOpen, FileSave, Filters, SelectDirectory

class Editor(App[None]):
    @work
    async def action_open(self) -> None:
        path: Path | None = await self.push_screen_wait(
            FileOpen(
                Path.cwd(),
                title="Open a document",
                filters=Filters(
                    ("Markdown", lambda p: p.suffix.lower() in {".md", ".markdown"}),
                    ("Text", lambda p: p.suffix.lower() == ".txt"),
                    ("Any", lambda _: True),
                ),
            )
        )
        if path is not None:
            await self.load_document(path)

    @work
    async def action_save_as(self) -> None:
        path = await self.push_screen_wait(
            FileSave(default_file="untitled.md", can_overwrite=True)
        )
        if path is not None:
            await self.write_document(path)

    @work
    async def action_choose_workspace(self) -> None:
        folder = await self.push_screen_wait(SelectDirectory(Path.home()))
        if folder is not None:
            self.workspace = folder
```

All three dismiss with `None` on cancel — always check. `@work` + `push_screen_wait` is the
pattern: `push_screen_wait` must be awaited inside a worker, never in a message handler
directly (it would deadlock the message pump).

### 13.4 Rolling your own picker

When you need custom behaviour (remote filesystems, previews, multi-select), compose it:

```python
class PickFiles(ModalScreen[list[Path]]):
    """Directory tree + multi-select + preview, returning several paths."""

    CSS = """
    PickFiles { align: center middle; }
    #frame { width: 90%; height: 80%; border: round $primary; background: $surface; }
    #cols { height: 1fr; }
    #tree { width: 34; border-right: vkey $primary-muted; }
    #chosen { width: 30; border-left: vkey $primary-muted; }
    #actions { height: 3; align-horizontal: right; padding: 0 1; }
    """

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        self.chosen: list[Path] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="frame"):
            with Horizontal(id="cols"):
                yield DirectoryTree(self.root, id="tree")
                yield Static(id="preview")
                yield ListView(id="chosen")
            with HorizontalGroup(id="actions"):
                yield Button("Cancel", id="cancel", compact=True)
                yield Button("Add", id="add", variant="primary", compact=True)
                yield Button("Done", id="done", variant="success", compact=True)

    @on(DirectoryTree.FileSelected)
    @work(exclusive=True, thread=True)
    def _preview(self, event: DirectoryTree.FileSelected) -> None:
        try:
            head = event.path.read_text("utf-8", errors="replace")[:4096]
        except OSError as error:
            head = f"[{error.strerror}]"
        self.app.call_from_thread(self.query_one("#preview", Static).update, head)

    @on(Button.Pressed, "#add")
    def _add(self) -> None:
        tree = self.query_one("#tree", DirectoryTree)
        node = tree.cursor_node
        if node is not None and node.data is not None and not node.data.path.is_dir():
            self.chosen.append(node.data.path)
            self.query_one("#chosen", ListView).append(ListItem(Label(node.data.path.name)))

    @on(Button.Pressed, "#done")
    def _done(self) -> None: self.dismiss(self.chosen)

    @on(Button.Pressed, "#cancel")
    def _cancel(self) -> None: self.dismiss([])
```

### 13.5 Drag and drop

`textual-filedrop` provides a `FileDrop` widget that handles the bracketed-paste-style file
drops most terminals emit when you drag a file in. It is terminal-dependent; always keep a
keyboard path to the same action.

### 13.6 Recent files, done right

```python
def push_recent(settings: Settings, path: Path, limit: int = 10) -> None:
    resolved = str(path.resolve())
    recent = [r for r in settings.recent if r != resolved]
    recent.insert(0, resolved)
    settings.recent = recent[:limit]
```

Filter out paths that no longer exist *when displaying*, not when storing — a file on an
unmounted drive should come back when the drive returns.

---

## 14. Forms, inputs and validation

### 14.1 `Input` in full

```python
from textual.validation import Function, Integer, Length, Number, Regex, URL
from textual.suggester import SuggestFromList
from textual.widgets import Input

yield Input(
    placeholder="https://api.example.com",
    id="endpoint",
    type="text",                       # "text" | "integer" | "number"
    restrict=r"[^\s]*",                # regex the *whole value* must match to be accepted
    max_length=200,
    suggester=SuggestFromList(["https://api.example.com", "http://localhost:8000"],
                              case_sensitive=False),
    validators=[URL(), Length(minimum=8, failure_description="too short")],
    validate_on=["changed", "submitted", "blur"],
    valid_empty=True,                  # empty is valid (optional fields)
    select_on_focus=True,
    compact=True,
    tooltip="Base URL of the service",
)
```

Built-in validators (verified): `Number(minimum, maximum, failure_description)`,
`Integer(...)`, `Length(minimum, maximum, ...)`, `Regex(regex, flags, ...)`,
`Function(callable, failure_description)`, `URL(...)`, plus `Validator` to subclass and
`ValidationResult` / `Failure`.

```python
from textual.validation import ValidationResult, Validator

class Port(Validator):
    def validate(self, value: str) -> ValidationResult:
        if not value:
            return self.success()
        if not value.isdigit():
            return self.failure("ports are numeric")
        if not 1 <= int(value) <= 65535:
            return self.failure("out of range 1–65535")
        return self.success()
```

`restrict` vs validators: `restrict` **prevents** keystrokes that would make the value not
match; validators **report** on the value. Use `restrict` for structure (digits only) and
validators for meaning (in range, resolvable host).

### 14.2 Showing validation state

```python
@on(Input.Changed)
def _validate(self, event: Input.Changed) -> None:
    result = event.validation_result
    error_label = self.query_one(f"#{event.input.id}-error", Label)
    if result is None or result.is_valid:
        event.input.remove_class("-invalid")
        error_label.update("")
        error_label.display = False
    else:
        event.input.add_class("-invalid")
        error_label.update(" · ".join(result.failure_descriptions))
        error_label.display = True
    self.query_one("#submit", Button).disabled = not self._form_valid()
```

```css
Input.-invalid { outline: tall $error; }       /* outline, not border: no reflow */
Input.-invalid:focus { outline: tall $error-lighten-1; }
.field-error { color: $text-error; height: auto; display: none; }
```

Verified: `Input.Changed`, `Input.Submitted` and `Input.Blurred` all carry
`validation_result: ValidationResult | None`.

### 14.3 `MaskedInput`

```python
from textual.widgets import MaskedInput

yield MaskedInput("9999-99-99", placeholder="YYYY-MM-DD", id="dob")
yield MaskedInput(">AAA-999;_", id="plate")        # > = upcase the rest
yield MaskedInput("9999 9999 9999 9999", id="card")
```

Template characters: `A` required alpha, `a` optional alpha, `N` required alphanumeric,
`n` optional, `X` required any, `x` optional, `9` required digit, `0` optional digit,
`D`/`d` non-zero digit, `#` digit or sign, `H`/`h` hex, `B`/`b` binary; `>` upper-cases
and `<` lower-cases subsequent input, `!` disables case conversion; everything after `;` is
the placeholder fill character.

### 14.4 A reusable form pattern

```python
from __future__ import annotations
from dataclasses import dataclass, fields
from typing import Any
from textual.containers import HorizontalGroup, VerticalScroll
from textual.widgets import Button, Input, Label, Select, Switch


@dataclass
class ConnectionForm:
    host: str = "localhost"
    port: str = "5432"
    database: str = ""
    tls: bool = True
    mode: str = "prefer"


class FormScreen(ModalScreen[ConnectionForm | None]):
    CSS = """
    FormScreen { align: center middle; }
    #form { width: 64; height: auto; border: round $primary; background: $surface; padding: 1 2; }
    .row { height: auto; }
    .row > Label { width: 14; content-align-vertical: middle; }
    .row > Input, .row > Select { width: 1fr; }
    .field-error { color: $text-error; height: auto; padding-left: 14; }
    #buttons { align-horizontal: right; height: auto; padding-top: 1; }
    """

    def __init__(self, initial: ConnectionForm) -> None:
        super().__init__()
        self.initial = initial

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="form"):
            yield from self._field("host", "Host", Input(self.initial.host, id="host"))
            yield from self._field("port", "Port",
                                   Input(self.initial.port, id="port", type="integer",
                                         validators=[Integer(1, 65535)],
                                         validate_on=["changed"]))
            yield from self._field("database", "Database",
                                   Input(self.initial.database, id="database",
                                         validators=[Length(minimum=1)],
                                         validate_on=["changed"]))
            with HorizontalGroup(classes="row"):
                yield Label("TLS")
                yield Switch(self.initial.tls, id="tls")
            with HorizontalGroup(classes="row"):
                yield Label("Mode")
                yield Select([(m, m) for m in ("disable", "prefer", "require")],
                             value=self.initial.mode, allow_blank=False, id="mode")
            with HorizontalGroup(id="buttons"):
                yield Button("Cancel", id="cancel", compact=True)
                yield Button("Connect", id="ok", variant="primary", compact=True)

    def _field(self, name: str, label: str, control):
        with HorizontalGroup(classes="row"):
            yield Label(label)
            yield control
        yield Label("", id=f"{name}-error", classes="field-error")

    def _collect(self) -> ConnectionForm:
        return ConnectionForm(
            host=self.query_one("#host", Input).value,
            port=self.query_one("#port", Input).value,
            database=self.query_one("#database", Input).value,
            tls=self.query_one("#tls", Switch).value,
            mode=str(self.query_one("#mode", Select).value),
        )

    def _all_valid(self) -> bool:
        return all(
            (widget.validate(widget.value) or ValidationResult.success()).is_valid
            for widget in self.query(Input)
        )

    @on(Input.Changed)
    def _revalidate(self, event: Input.Changed) -> None:
        name = event.input.id or ""
        label = self.query_one(f"#{name}-error", Label)
        bad = event.validation_result is not None and not event.validation_result.is_valid
        event.input.set_class(bad, "-invalid")
        label.update("" if not bad else ", ".join(event.validation_result.failure_descriptions))
        self.query_one("#ok", Button).disabled = not self._all_valid()

    @on(Input.Submitted)
    def _next_field(self) -> None:
        self.focus_next()

    @on(Button.Pressed, "#ok")
    def _ok(self) -> None:
        if self._all_valid():
            self.dismiss(self._collect())

    @on(Button.Pressed, "#cancel")
    def _cancel(self) -> None:
        self.dismiss(None)
```

Form UX rules that separate good TUIs from bad ones:

1. `enter` moves to the next field; `ctrl+enter` or the explicit button submits.
2. The submit button is **disabled** until valid, and says *why* next to the offending field.
3. `escape` cancels, with a confirm step only if the form is dirty.
4. `tab`/`shift+tab` always work (Textual's `focus_next`/`focus_previous` do this for free).
5. Field labels are a fixed width so controls align — a `Label` at `width: 14` beats padding
   hacks.
6. `AUTO_FOCUS = "#host"` on the screen puts the cursor in the first field.

### 14.5 Command-prompt input (`:` style)

```python
class CommandLine(Input):
    """A vim-style command line that appears on ':'."""
    BINDINGS = [Binding("escape", "dismiss_line", "Cancel", show=False)]

    def action_dismiss_line(self) -> None:
        self.value = ""
        self.display = False
        self.screen.focus_next()
```

Pair with `history` (persist to app-data, §22) and a `SuggestFromList` of past commands —
`Input` shows the suggestion inline as dim text with `right`/`end` to accept.

---
## 15. Text editing and syntax highlighting

`TextArea` is a full editor: multi-line, soft wrap, undo/redo (50 checkpoints by default),
bracket matching, line numbers, tree-sitter syntax highlighting, and selection.

### 15.1 Setup

```bash
pip install "textual[syntax]"
```

That extra pulls `tree-sitter` plus 15 grammar packages (verified from the metadata):
`bash, css, go, html, java, javascript, json, markdown, python, regex, rust, sql, toml,
xml, yaml`. **Without the extra, `TextArea(language="python")` raises
`LanguageDoesNotExist`** — it is not a silent downgrade.

```python
from textual.widgets import TextArea

yield TextArea.code_editor(
    source, language="python", theme="vscode_dark",
    show_line_numbers=True, tab_behavior="indent", soft_wrap=False, id="editor",
)
# or the plain constructor
yield TextArea("notes…", soft_wrap=True, tab_behavior="focus", placeholder="Notes")
```

`TextArea.code_editor()` is the convenience constructor that enables line numbers,
`tab_behavior="indent"`, disables soft wrap and defaults `theme="monokai"` — editor
defaults rather than text-field defaults.

Built-in `TextArea` themes (verified, 5): `css` (the default for the plain constructor —
it follows your app theme), `monokai`, `dracula`, `vscode_dark`, `github_light`.
Inspect at runtime with `area.available_themes` and `area.available_languages`.

### 15.2 Working with the document

```python
area = self.query_one("#editor", TextArea)
area.load_text(source)                       # replace, resetting undo history
area.text                                    # whole document
area.selected_text
area.selection                               # Selection(start=(row, col), end=(row, col))
area.cursor_location                         # (row, column)
area.get_text_range((0, 0), (5, 0))
area.insert("hello", location=(2, 4))
area.replace("x", start=(1, 0), end=(1, 5))
area.delete((3, 0), (4, 0))
area.move_cursor((10, 0), select=False, center=True)
area.select_line(4); area.select_all()
area.undo(); area.redo()
area.read_only = True
area.document.line_count
```

Messages: `TextArea.Changed`, `TextArea.SelectionChanged`. For an editor, debounce
persistence off `Changed` (§21.6) — it fires per keystroke.

### 15.3 Custom languages and themes

```python
from textual.widgets.text_area import TextAreaTheme
from rich.style import Style
import tree_sitter_toml

area.register_language("toml", tree_sitter_toml.language(), highlight_query)
area.register_theme(TextAreaTheme(
    name="nocturne",
    base_style=Style(color="#D8DEE9", bgcolor="#2E3440"),
    gutter_style=Style(color="#4C566A"),
    cursor_style=Style(color="#2E3440", bgcolor="#88C0D0"),
    cursor_line_style=Style(bgcolor="#3B4252"),
    selection_style=Style(bgcolor="#434C5E"),
    bracket_matching_style=Style(bgcolor="#4C566A", bold=True),
    syntax_styles={
        "string": Style(color="#A3BE8C"),
        "comment": Style(color="#616E88", italic=True),
        "keyword": Style(color="#81A1C1", bold=True),
        "function": Style(color="#88C0D0"),
        "number": Style(color="#B48EAD"),
    },
))
area.theme = "nocturne"
```

Textual ships the tree-sitter highlight queries as `.scm` **package data** inside the
`textual/tree-sitter/highlights/` directory (verified: 16 `.scm` files). That matters
enormously for packaging — see §23.3.

### 15.4 Component classes

```css
TextArea {
  & > .text-area--gutter           { color: $foreground-disabled; }
  & > .text-area--cursor-gutter    { color: $text-primary; background: $surface-lighten-1; }
  & > .text-area--cursor-line      { background: $boost; }
  & > .text-area--cursor           { background: $primary; color: $background; }
  & > .text-area--selection        { background: $primary 35%; }
  & > .text-area--matching-bracket { background: $accent 30%; text-style: bold; }
  & > .text-area--placeholder      { color: $foreground-disabled; text-style: italic; }
  & > .text-area--suggestion       { color: $foreground-disabled; }
}
```

### 15.5 Key handling inside an editor

An editor eats most keys. To keep app-level shortcuts, declare them `priority=True` on the
App, and be aware of `check_consume_key` — `Input` and `TextArea` implement it so Textual
knows which printable keys they will consume, which is how app bindings on plain letters
still work elsewhere.

```python
class Editor(App[None]):
    BINDINGS = [
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("ctrl+p", "command_palette", "Commands", priority=True),
    ]
```

---

## 16. Charts, graphics and images

### 16.1 Sparklines — the cheapest signal

```python
from textual.widgets import Sparkline

yield Sparkline(self.latency_history, summary_function=max, id="latency")
```

```css
Sparkline {
  width: 1fr; height: 3;
  & > .sparkline--max-color { color: $error; }
  & > .sparkline--min-color { color: $success; }
}
```

Set `data` to a new list to update. Textual 7.3.0 made `Sparkline` height-flexible, so a
3-row sparkline now actually uses the vertical space.

### 16.2 `textual-plotext` — real charts

```python
from textual_plotext import PlotextPlot

class Latency(PlotextPlot):
    def on_mount(self) -> None:
        self.plt.title("Latency (ms)")
        self.plt.xlabel("sample")
        self.replot([])

    def replot(self, series: list[float]) -> None:
        self.plt.clear_data()
        self.plt.plot(series, marker="braille", color="cyan")
        self.plt.hline(sum(series) / len(series) if series else 0, color="red")
        self.refresh()
```

`PlotextPlot` exposes `.plt`, a per-widget Plotext façade that is already wired to the
widget's size and the active theme (it does *not* share Plotext's global state, so several
plots coexist). Supported plot types include `plot`, `scatter`, `bar`, `hist`, `candlestick`,
`heatmap`-ish matrix plots, `hline`/`vline`, and date-axis plots.

Call `self.refresh()` after mutating `self.plt`, and re-plot on `theme_changed_signal` so
colours follow the theme.

### 16.3 Other plotting options

| Library | Strength |
|---|---|
| `textual-plot` | native Textual widget with mouse zoom/pan |
| `textual-canvas` | character canvas: draw your own primitives |
| `textual-hires-canvas` | braille/quadrant canvas for 2×/4× resolution |
| `plotext` (direct) | printing charts from a CLI, not in a widget |
| `asciichartpy` | tiny line charts in one call |

### 16.4 Raster images in the terminal

```python
from textual_image.widget import Image, AutoImage, HalfcellImage, SixelImage, TGPImage, UnicodeImage

yield AutoImage("assets/logo.png", id="logo")   # picks the best protocol available
```

The render ladder, best to worst:

1. **`TGPImage`** — Kitty Terminal Graphics Protocol. True pixels, fast. Kitty, Ghostty,
   WezTerm, Konsole.
2. **`SixelImage`** — Sixel. True pixels. WezTerm, foot, xterm, Windows Terminal 1.22+,
   Contour, mlterm.
3. **`HalfcellImage`** — two colours per cell using `▀`: resolution = (width, height×2).
   Works **everywhere** with truecolor.
4. **`UnicodeImage`** — block/quadrant characters; works in 256-colour terminals.

`AutoImage` (and `AutoRenderable`) probe the terminal and pick. For a logo that must always
render, pin `HalfcellImage` — it has no capability requirements beyond colour.

```python
# Rich renderable (usable in Static, RichLog, Panel, or a plain Console)
from rich_pixels import Pixels
pixels = Pixels.from_image_path("assets/logo.png", resize=(40, 20))
yield Static(pixels)
```

Caveats, from experience:

- Image protocols and `tmux` need `allow-passthrough` and still often fail. Detect `TMUX`
  and fall back to half-cell.
- Kitty/Sixel images are drawn *by the terminal*, not composited by Textual. They will
  overlay your widgets if the terminal does not clip them — keep images inside a container
  whose region does not move during animation.
- Resize events must re-emit the image. `textual-image`'s widgets handle this; a raw
  escape-sequence approach will not.
- Pillow is a heavyweight dependency (≈40 MB unpacked with its bundled libraries). If your
  app only needs a small logo, pre-render it to a text/ANSI file at build time and ship that
  instead — see §23.4 for the measured size impact.

### 16.5 ASCII art and banners

```python
# textual-pyfiglet integrates figlet fonts as a widget with colour + animation
from textual_pyfiglet import FigletWidget
yield FigletWidget("NOCTURNE", font="slant", colors=["#88C0D0", "#B48EAD"], animate=True)
```

For a splash screen, a static pre-rendered ANSI banner stored in `assets/` is the fastest
and most reliable option:

```python
banner = (resource_path("assets/banner.ansi")).read_text("utf-8")
yield Static(Text.from_ansi(banner))
```

### 16.6 QR codes, canvases, miscellanea

- `textual-qrcode` renders a QR code widget (useful for device-pairing flows).
- `textual-canvas` / `textual-hires-canvas` for bespoke drawing (graphs, maps, game boards).
- `textual-coloromatic` for animated gradient/tiled backgrounds.
- `textual-terminal` embeds a real terminal emulator widget inside your app.
- `textual-window` adds floating, draggable windows with a window bar.
- `textual-slidecontainer` gives sliding drawer menus.

The full ecosystem inventory is in [Appendix E](#appendix-e-ecosystem-libraries), with a
compatibility warning you should read before adding any of them.

---

## 17. Animation and motion design

Terminal animation is cheap if you respect the frame budget and expensive if you do not. The
default cap is 60 fps (`TEXTUAL_FPS`); anything that cannot finish its work in ~16 ms will
drop frames.

### 17.1 The animator

Verified signature:

```python
widget.animate(
    attribute,            # a float/Animatable attribute name
    value,
    *, final_value=...,   # value to set when the animation completes
    duration=None,        # seconds — pass duration OR speed
    speed=None,           # units per second
    delay=0.0,
    easing="in_out_cubic",
    on_complete=None,
    level="full",         # "full" | "basic" | "none" — honours the user's animation level
)
```

```python
# Animate a reactive
meter.animate("value", 1.0, duration=0.4, easing="out_elastic")

# Animate a style
panel.styles.animate("opacity", 0.0, duration=0.2,
                     on_complete=lambda: panel.remove())
panel.styles.animate("offset", (0, 0), duration=0.25, easing="out_cubic")

# Chain
def slide_in(widget) -> None:
    widget.styles.offset = (-40, 0)
    widget.styles.animate("offset", (0, 0), duration=0.2, easing="out_cubic",
                          on_complete=lambda: widget.styles.animate("opacity", 1.0,
                                                                     duration=0.12))
```

Note (8.1.0): `on_complete` is now also invoked when an in-flight animation of the same
attribute is restarted. If your callback mounts/removes widgets, make it idempotent.

### 17.2 Easing — all 33, verified

`none`, `round`, `linear`,
`in_sine`, `in_out_sine`, `out_sine`,
`in_quad`, `in_out_quad`, `out_quad`,
`in_cubic`, `in_out_cubic`, `out_cubic`,
`in_quart`, `in_out_quart`, `out_quart`,
`in_quint`, `in_out_quint`, `out_quint`,
`in_expo`, `in_out_expo`, `out_expo`,
`in_circ`, `in_out_circ`, `out_circ`,
`in_back`, `in_out_back`, `out_back`,
`in_elastic`, `in_out_elastic`, `out_elastic`,
`in_bounce`, `in_out_bounce`, `out_bounce`

Guidance:

| Intent | Easing | Duration |
|---|---|---|
| Something appears | `out_cubic` | 150–200 ms |
| Something leaves | `in_cubic` | 100–150 ms |
| Panel slides | `out_quint` | 200–250 ms |
| A value counts up | `out_expo` | 300–500 ms |
| Playful confirm | `out_back` / `out_elastic` | 300–450 ms |
| Scroll-to | `out_cubic` | 150–250 ms |
| Never | `in_out_elastic`, `*_bounce` on anything frequent | — |

`round` snaps to integers — use it for cell-grid motion that must not show sub-cell
positions. Explore them interactively with `textual easing`.

### 17.3 CSS transitions

Declarative and usually better, because the animation follows the *state*, not the code
path:

```css
#drawer {
  offset-x: -100%;
  transition: offset 220ms out_cubic, opacity 160ms linear;
}
#drawer.-open { offset-x: 0; }

.card { transition: background 120ms linear, border 120ms linear; }
.card:hover { background: $boost; border: round $accent; }

Button { transition: background 80ms linear, tint 80ms linear; }
Button:hover { tint: $foreground 8%; }
```

Then animation is just `self.query_one("#drawer").toggle_class("-open")`. Not every property
is animatable — colours, scalars (width/height/offset/padding/margin), opacity, tint and
border colours are; enums like `display`/`layout` are not. Combine with
`DOMNode.update_classes({"-open": True, "-wide": False}, animate=True)` (added 8.2.4) to
flip several classes in one animated pass.

### 17.4 Loading and progress states

```python
widget.loading = True       # overlays a LoadingIndicator; blocks interaction
widget.loading = False
```

```python
class Loadable(Widget):
    def get_loading_widget(self) -> Widget:
        return Static("fetching…", classes="custom-loading")
```

For determinate work, drive a `ProgressBar` from the worker:

```python
@work(thread=True, exclusive=True)
def download(self, url: str) -> None:
    worker = get_current_worker()
    bar = self.query_one(ProgressBar)
    self.app.call_from_thread(bar.update, total=total_bytes, progress=0)
    for chunk in stream(url):
        if worker.is_cancelled:
            return
        written += len(chunk)
        # Do NOT call_from_thread per chunk; throttle to ~20 Hz
        if time.monotonic() - last > 0.05:
            self.app.call_from_thread(bar.update, progress=written)
            last = time.monotonic()
```

**The throttle is not optional.** A 1 MB/s download with 8 KB chunks posts 128 messages per
second; at 60 fps you only get 60 frames, so 68 of them are pure overhead that also starves
input handling.

Workers themselves carry progress state (`worker.update(total_steps=…)`,
`worker.advance(1)`, `worker.progress`), which a status bar can read without the worker
knowing about the UI.

### 17.5 Hand-rolled frame animation

```python
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

class Spinner(Static):
    frame: reactive[int] = reactive(0)

    def on_mount(self) -> None:
        self._timer = self.set_interval(1 / 12, self._tick)   # 12 fps is plenty

    def _tick(self) -> None:
        self.frame = (self.frame + 1) % len(SPINNER)

    def render(self) -> str:
        return SPINNER[self.frame]
```

Rich ships 73 named spinners (`rich.spinner.SPINNERS`) you can borrow frame sets from:
`dots`, `dots2`–`dots12`, `line`, `arc`, `circle`, `bouncingBar`, `bouncingBall`, `moon`,
`earth`, `clock`, `pong`, `hamburger`, `grenade`, `weather`, `aesthetic`, `betaWave`, and
more (full list in [Appendix F](#appendix-f-rich-spinners)).

**Frame-rate guidance:** 10–12 fps for spinners, 30 fps for progress/meters, 60 fps only for
direct user-driven motion (scrolling, dragging). Every animated widget costs a repaint of
its region on every frame.

### 17.6 Respecting the user

```python
# Users set this; honour it.
#   TEXTUAL_ANIMATIONS=none   -> no animation at all
#   TEXTUAL_ANIMATIONS=basic  -> only essential animation
#   TEXTUAL_ANIMATIONS=full   -> everything (default)
from textual.constants import TEXTUAL_ANIMATIONS

widget.animate("value", 1.0, duration=0.4, level="full")   # skipped at 'basic'/'none'
widget.animate("value", 1.0, duration=0.1, level="basic")  # kept at 'basic'
```

Pass `level=` on everything decorative. Over SSH on a high-latency link, or for users with
vestibular sensitivity, this is the difference between usable and unusable. Expose it in
your settings screen as well as via the environment variable.

### 17.7 Testing animation

```python
async with app.run_test() as pilot:
    await pilot.press("a")
    await pilot.wait_for_animation()             # in-flight animations
    await pilot.wait_for_scheduled_animations()  # including delayed ones
    assert app.query_one(Meter).value == 1.0
```

Verified working: this is how the animation examples in this guide were checked.

---

## 18. Building custom widgets

Three levels, in increasing power and cost.

### 18.1 Level 1: compose existing widgets

Most "custom widgets" should be this. No rendering code, full styling, free accessibility.

```python
class StatCard(VerticalGroup):
    DEFAULT_CSS = """
    StatCard {
        width: 1fr; height: auto; padding: 1 2;
        border: round $primary; background: $panel;
        & > .stat--label { color: $text-muted; }
        & > .stat--value { text-style: bold; }
        &.-up    > .stat--delta { color: $text-success; }
        &.-down  > .stat--delta { color: $text-error; }
    }
    """
    value: reactive[float] = reactive(0.0)
    delta: reactive[float] = reactive(0.0)

    def __init__(self, label: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._label = label

    def compose(self) -> ComposeResult:
        yield Label(self._label, classes="stat--label")
        yield Label(classes="stat--value")
        yield Label(classes="stat--delta")

    def watch_value(self, value: float) -> None:
        self.query_one(".stat--value", Label).update(f"{value:,.2f}")

    def watch_delta(self, delta: float) -> None:
        self.query_one(".stat--delta", Label).update(f"{delta:+.1%}")
        self.set_class(delta > 0, "-up")
        self.set_class(delta < 0, "-down")
```

### 18.2 Level 2: `render()` a renderable

```python
class Badge(Static):
    def render(self) -> RenderableType:
        return Text.assemble(("● ", self._colour), (self._label, "bold"))
```

`render()` returns anything Rich or Textual can render (`str`, `Text`, `Panel`, `Table`,
`Content`). Cheap, but the whole widget re-renders on any change — fine for small widgets.

### 18.3 Level 3: the line API (`render_line`)

For anything large or scrollable, implement `render_line(y)`. Textual calls it only for
visible lines, which is how a million-row widget stays fast.

```python
from rich.segment import Segment
from rich.style import Style as RichStyle
from textual.geometry import Size
from textual.strip import Strip
from textual.widget import Widget


class WaveMeter(Widget, can_focus=True):
    """A two-row meter: a 1/8-cell bar plus an animated wave."""

    DEFAULT_CSS = """
    WaveMeter {
        height: 2; width: 1fr;
        background: $surface; color: $primary;
        &:focus { background: $surface-lighten-1; }
    }
    """
    COMPONENT_CLASSES = {"wavemeter--bar", "wavemeter--wave"}

    value: reactive[float] = reactive(0.0)
    phase: reactive[float] = reactive(0.0)

    def watch_value(self) -> None:
        self.refresh()

    def watch_phase(self) -> None:
        self.refresh()

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return 2

    def get_content_width(self, container: Size, viewport: Size) -> int:
        return container.width

    def render_line(self, y: int) -> Strip:
        width = self.content_size.width
        if width <= 0:
            return Strip.blank(0)
        if y == 0:
            style = self.get_component_rich_style("wavemeter--bar")
            return Strip([Segment(smooth_bar(self.value, width), style)], width)
        style = self.get_component_rich_style("wavemeter--wave")
        return Strip([Segment(wave(width, self.phase), style)], width)
```

Rules for `render_line`:

- Return a `Strip` whose cell width matches `self.content_size.width`, or you get visual
  corruption. `Strip.blank(width)`, `strip.adjust_cell_length(width)` and
  `strip.crop(start, end)` help.
- Use `self.get_component_rich_style("name")` so your widget is themeable — never hard-code
  a `rich.style.Style`. (7.3.0 added a `default=` parameter for when the class is absent.)
- Cache expensive work keyed on `(width, state)`; `render_line` is called for every visible
  row on every repaint.
- `Widget.BLANK` (7.1.0+) can be returned from a render path to say "nothing here",
  which lets Textual skip work for huge scrollables.

### 18.4 Scrollable custom widgets

```python
from textual.scroll_view import ScrollView

class HexView(ScrollView):
    def __init__(self, data: bytes) -> None:
        super().__init__()
        self._data = data
        self.virtual_size = Size(78, (len(data) + 15) // 16)

    def render_line(self, y: int) -> Strip:
        scroll_x, scroll_y = self.scroll_offset
        row = y + scroll_y
        if row * 16 >= len(self._data):
            return Strip.blank(self.size.width)
        chunk = self._data[row * 16:(row + 1) * 16]
        text = (f"{row * 16:08x}  "
                + " ".join(f"{b:02x}" for b in chunk).ljust(47)
                + "  "
                + "".join(chr(b) if 32 <= b < 127 else "." for b in chunk))
        strip = Strip([Segment(text, self.rich_style)])
        return strip.crop(scroll_x, scroll_x + self.size.width)
```

Set `virtual_size` to the full logical content size; Textual gives you scrollbars, mouse
wheel, keyboard scrolling and the `scroll_offset` for free. `crop()` handles horizontal
scrolling. This pattern renders arbitrarily large content in O(viewport).

### 18.5 Focus, mouse and keyboard

```python
class Clickable(Widget, can_focus=True, can_focus_children=False):
    ALLOW_SELECT = False          # opt out of text selection
    FOCUS_ON_CLICK = True

    BINDINGS = [Binding("space,enter", "activate", "Activate")]

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self.capture_mouse()                 # receive moves outside our region
        self._drag_from = event.offset

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self._drag_from is not None:
            self.offset = self.offset + (event.offset - self._drag_from)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        self.release_mouse()
        self._drag_from = None

    def on_enter(self, event: events.Enter) -> None: self.add_class("-hover")
    def on_leave(self, event: events.Leave) -> None: self.remove_class("-hover")

    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+x":
            event.stop()
            self.cut()
```

`capture_mouse()`/`release_mouse()` is the drag idiom — without capture you lose events the
moment the pointer leaves the widget. Set `pointer:` in CSS so the cursor shape matches.

### 18.6 Packaging a widget library

- Put styles in `DEFAULT_CSS` with `SCOPED_CSS = True` (the default) so you never leak rules.
- Declare `COMPONENT_CLASSES` for every styleable sub-part and document them.
- Emit messages (`class Changed(Message)`) rather than taking callbacks: it composes.
- Expose a `compact` flag if the widget has chrome.
- Type the widget generically when it carries user data (`SelectionList[str]`, `Tree[MyNode]`).
- Ship `py.typed`.
- **Pin the Textual major version in your dependency spec** — and see the warning in
  Appendix E about third-party widgets with narrow pins.

---
## 19. Screens, modals, modes and navigation

### 19.1 The screen stack

```python
self.push_screen(SettingsScreen())
self.push_screen(SettingsScreen(), callback=self._settings_closed)
self.pop_screen()
self.switch_screen(OtherScreen())          # replace the top
self.install_screen(HeavyScreen(), name="heavy")   # keep it alive, reuse
self.push_screen("heavy")
```

Screens declared on the App can be referenced by name:

```python
class Nocturne(App[None]):
    SCREENS = {"settings": SettingsScreen, "about": AboutScreen}
    BINDINGS = [("comma", "push_screen('settings')", "Settings")]
```

8.0.0 added a `mode` argument to `push_screen`/`push_screen_wait`, so you can push onto a
*specific* mode's stack rather than the active one.

### 19.2 Modal screens that return a value

```python
from textual.screen import ModalScreen

class Confirm(ModalScreen[bool]):
    CSS = """
    Confirm { align: center middle; background: $background 60%; }
    #box { width: 48; height: auto; padding: 1 2;
           border: round $primary; background: $surface; }
    #row { height: auto; align-horizontal: right; }
    """
    BINDINGS = [("escape", "dismiss(False)", "Cancel"),
                ("enter", "dismiss(True)", "OK")]

    def __init__(self, question: str, *, danger: bool = False) -> None:
        super().__init__()
        self.question, self.danger = question, danger

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label(self.question)
            with HorizontalGroup(id="row"):
                yield Button("Cancel", id="no", compact=True)
                yield Button("Delete" if self.danger else "OK", id="yes",
                             variant="error" if self.danger else "primary", compact=True)

    @on(Button.Pressed, "#yes")
    def _yes(self) -> None: self.dismiss(True)

    @on(Button.Pressed, "#no")
    def _no(self) -> None: self.dismiss(False)
```

Consume it in two equivalent ways:

```python
# (a) callback style — works anywhere
self.push_screen(Confirm("Delete 3 files?", danger=True), self._after_confirm)

def _after_confirm(self, confirmed: bool | None) -> None:
    if confirmed:
        self.delete_selected()

# (b) await style — MUST be inside a worker
@work
async def action_delete(self) -> None:
    if await self.push_screen_wait(Confirm("Delete 3 files?", danger=True)):
        self.delete_selected()
```

**Why `@work` is required:** `push_screen_wait` suspends until the screen dismisses. A
message handler runs *on* the message pump; awaiting there would block the pump that must
deliver the dismiss. Workers run as separate tasks, so they can wait. Verified by running
both forms.

`ModalScreen` differs from `Screen` by setting `is_modal`, which stops bindings and focus
from reaching the screens beneath. The `background: $background 60%` trick is what produces
the dimmed-backdrop look.

### 19.3 Modes

Modes are independent screen stacks — the right model for an app with top-level sections
(think a mail client's Mail / Calendar / Contacts).

```python
class Nocturne(App[None]):
    MODES = {
        "browse":   BrowseScreen,
        "editor":   EditorScreen,
        "settings": SettingsScreen,
    }
    DEFAULT_MODE = "browse"           # ← required; the default is "_default"
    BINDINGS = [
        Binding("f2", "switch_mode('browse')", "Browse"),
        Binding("f3", "switch_mode('editor')", "Editor"),
        Binding("f4", "switch_mode('settings')", "Settings"),
    ]
```

Each mode keeps its own stack, scroll positions and focus. Switching is instant because
nothing is rebuilt.

**Gotcha found while verifying:** calling `self.switch_mode("main")` in `on_mount` does
*not* make the mode's widgets queryable in that same tick (the switch is awaitable). Set
`DEFAULT_MODE` instead, or `await self.switch_mode(...)`.

8.0.0 added `App.mode_change_signal` and `App.screen_change_signal` so a status bar can
react to navigation without every screen having to tell it.

### 19.4 Screen lifecycle for expensive screens

```python
class HeavyScreen(Screen[None]):
    def on_screen_resume(self) -> None:
        self._poll = self.set_interval(2.0, self.refresh_data)

    def on_screen_suspend(self) -> None:
        self._poll.stop()
```

Any screen that polls, animates or holds a subscription must pause on suspend. This is the
single most common cause of "the app gets slower the longer I use it".

Also useful: `Screen.AUTO_FOCUS = "#search"` (a selector focused on entry), and
`Screen.ESCAPE_TO_MINIMIZE`.

### 19.5 Lazy mounting for fast first paint

```python
from textual import lazy

def compose(self) -> ComposeResult:
    yield Header()
    with TabbedContent("Overview", "Logs", "Metrics"):
        yield Overview()                 # mounted now
        yield lazy.Lazy(LogsPane())      # mounted after first paint
        yield lazy.Lazy(MetricsPane())
    yield Footer()
```

`lazy.Lazy` defers mounting a widget until after the screen has painted;
`lazy.Reveal` mounts a sequence of children progressively, one per frame, so a dense screen
appears instantly and fills in. On a 30-widget dashboard this is the difference between a
250 ms and a 40 ms first paint.

---

## 20. Command palette, keymaps and discoverability

### 20.1 The built-in palette

`ctrl+p` (configurable via `App.COMMAND_PALETTE_BINDING`) opens a fuzzy-search palette. It
ships with system commands: change theme, toggle dark mode, save a screenshot, show the
keys panel, quit. `App.ENABLE_COMMAND_PALETTE = False` disables it.

### 20.2 Your own command providers

```python
from functools import partial
from textual.command import DiscoveryHit, Hit, Hits, Provider


class FileCommands(Provider):
    async def startup(self) -> None:
        """Called once when the palette opens — do the expensive indexing here."""
        self._paths = [p for p in self.app.workspace.rglob("*") if p.is_file()]

    async def discover(self) -> Hits:
        """Shown with an empty query — your 'recommended' commands."""
        for path in self._paths[:10]:
            yield DiscoveryHit(
                f"Open {path.name}",
                partial(self.app.open_file, path),
                text=str(path),
                help=str(path.parent),
            )

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for path in self._paths:
            label = str(path)
            score = matcher.match(label)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(label),       # Content with matches styled
                    partial(self.app.open_file, path),
                    help="Open this file",
                )


class Nocturne(App[None]):
    COMMANDS = App.COMMANDS | {FileCommands}
```

Verified: `Hit(score, match_display, command, text=None, help=None)`,
`DiscoveryHit(display, command, text=None, help=None)`, and `Provider` exposes
`app`, `screen`, `focused`, `matcher()`, `match_style`, `startup()`, `search()`,
`discover()`, `shutdown()`.

Important details:

- `search()` is an **async generator** and is cancelled when the query changes. Yield
  incrementally — do not build a full list first — so a 100k-item index stays responsive.
- `self.matcher(query)` returns the same `textual.fuzzy.Matcher` used everywhere else.
- Put per-session work in `startup()`, not in `search()`.
- Screens can have their own `COMMANDS` so context-specific commands only appear where they
  apply.

### 20.3 A one-off palette

```python
self.search_commands(
    [
        ("Reload config", self.reload_config, "Re-read settings.json"),
        ("Clear cache", self.clear_cache),
    ],
    placeholder="Run a maintenance task…",
)
```

Verified: `App.search_commands(commands, placeholder="Search for commands…")`. This is the
right tool for a contextual "pick one of these N actions" prompt — far less code than a
modal list.

### 20.4 Footer, help panel and keys panel

```python
yield Footer(show_command_palette=True, compact=False)
```

The footer renders the **live** binding set for the focused widget chain, with grouping
(`Binding(..., group="Navigation")`, `BINDING_GROUP_TITLE` on the widget) and tooltips.
`Footer.combine_groups` and `compact` control density.

```python
BINDINGS = [Binding("question_mark", "show_help_panel", "Help")]

class MainScreen(Screen):
    HELP = """
    ## Browsing
    - `j` / `k` — move
    - `/` — search
    - `enter` — open
    """
```

`action_show_help_panel()` mounts a `HelpPanel` showing bindings plus the nearest `HELP`
attribute — since 7.2.0 it searches **ancestor** widgets for `HELP`, so a screen-level help
string covers its children; `action_hide_help_panel()` closes it. (The action is
`show_help_panel`, not `help_panel` — verified against `dir(App)` on 8.2.8.) The separate
`KeyPanel` widget gives a live key display, which is excellent for screencasts and bug
reports.

Textual's own default `App.BINDINGS` is deliberately tiny — just `ctrl+q` → `quit` and
`ctrl+c` → `help_quit` (both `show=False`). Everything a user sees in the footer is yours
to declare.

### 20.5 User-remappable keys

```python
class Nocturne(App[None]):
    BINDINGS = [
        Binding("ctrl+s", "save", "Save", id="app.save"),
        Binding("ctrl+f", "find", "Find", id="app.find"),
    ]

    def on_load(self) -> None:
        # from settings.json: {"keymap": {"app.save": "ctrl+w"}}
        self.set_keymap(self.settings.keymap)
```

Give every user-facing binding an `id` and ship a keymap section in your settings file. This
costs nothing up-front and is impossible to retrofit cleanly once users have muscle memory.

### 20.6 Discoverability checklist

- [ ] A `Footer` is visible on every screen.
- [ ] Every action reachable by mouse is also reachable by key, and appears in the palette.
- [ ] `?` or `F1` opens help.
- [ ] Destructive actions confirm, and the confirm button is not the default focus.
- [ ] Every binding has a `description`; non-obvious ones have a `tooltip`.
- [ ] Bindings follow platform convention where one exists (`ctrl+c` copy in the *editor*,
      `ctrl+q` quit the app) — and note that Textual 8.2.7 maps `cmd+c/x/v/z/y` on
      terminals that report super.

---

## 21. Threading, concurrency and scaling

This is where most TUIs fail. The rules are simple and absolute.

### 21.1 The single-threaded truth

Textual runs one asyncio event loop. **Every** widget method, message handler, reactive
watcher and render call happens on it. Therefore:

> Any blocking call in a handler freezes the entire UI — input, animation, rendering, all of
> it — for exactly as long as it blocks.

A 200 ms DNS lookup in `on_button_pressed` is 12 dropped frames and an app that feels
broken. There is no "it's only sometimes slow" exemption: write it as if it will always be
slow.

### 21.2 The decision table

| Work | Mechanism | Why |
|---|---|---|
| Async I/O (httpx, asyncpg, aiofiles) | `@work` (async) | cooperative, cancellable, cheap |
| Blocking I/O (requests, psycopg2, `os.walk`, `open`) | `@work(thread=True)` | releases the GIL during I/O |
| CPU-bound Python (parsing, hashing, compression, image work) | `ProcessPoolExecutor` via `run_in_executor` | threads cannot beat the GIL |
| CPU-bound in C (numpy, orjson, zlib, cryptography) | thread is fine | these release the GIL |
| Subprocess | `asyncio.create_subprocess_exec` | stream output without blocking |
| Many small awaits | `asyncio.gather` + `Semaphore` | bounded fan-out |
| Periodic | `set_interval` | integrated with the frame clock |

### 21.3 Workers

```python
from textual import work
from textual.worker import Worker, WorkerState, get_current_worker
```

Verified decorator signature:

```python
@work(name="", group="default", exit_on_error=True,
      exclusive=False, description=None, thread=False)
```

```python
class Browser(App[None]):

    # Async worker — the common case
    @work(exclusive=True, group="fetch")
    async def fetch_page(self, url: str) -> None:
        self.query_one(DataTable).loading = True
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
            self.render_rows(response.json())
        except httpx.HTTPError as error:
            self.notify(f"Request failed: {error}", severity="error")
        finally:
            self.query_one(DataTable).loading = False

    # Thread worker — for blocking libraries
    @work(thread=True, group="scan", exclusive=True)
    def scan_tree(self, root: Path) -> int:
        worker = get_current_worker()
        count = 0
        for batch in chunked_scan(root):
            if worker.is_cancelled:            # cooperative cancellation
                return count
            count += len(batch)
            self.call_from_thread(self.add_paths, batch)   # ← the only safe bridge
        return count

    # Reacting to worker lifecycle (progress bars, error toasts)
    @on(Worker.StateChanged)
    def _worker_state(self, event: Worker.StateChanged) -> None:
        if event.state is WorkerState.ERROR:
            self.notify(f"{event.worker.name} failed", severity="error")
        elif event.state is WorkerState.SUCCESS and event.worker.group == "scan":
            self.notify(f"Indexed {event.worker.result} files")
```

Key semantics:

- `exclusive=True` **cancels any running worker in the same `group`** before starting. This
  single flag solves the classic search-as-you-type race: each keystroke cancels the
  previous query.
- `WorkerState` is `PENDING, RUNNING, CANCELLED, ERROR, SUCCESS` (verified).
- `exit_on_error=True` (the default) will **exit your app** on an unhandled worker
  exception. For user-triggered work that can legitimately fail (a bad URL), set
  `exit_on_error=False` and handle it, or catch inside the worker.
- `self.workers.cancel_group(self, "fetch")`, `self.workers.cancel_all()`, and
  `await worker.wait()` give you manual control.
- A thread worker **cannot** be forcibly killed. `worker.cancel()` only sets a flag — you
  must poll `worker.is_cancelled`. Structure long loops in chunks.

### 21.4 Crossing the thread boundary

Only two things are legal from a non-event-loop thread:

```python
self.app.call_from_thread(widget.update, value)   # run a callable on the loop, wait for it
widget.post_message(MyMessage(payload))            # thread-safe, fire-and-forget
```

Everything else — setting a reactive, mutating a widget, `query_one`, `mount` — is a race
that will manifest as corrupted rendering or a hard crash hours later.

```python
# WRONG: mutating a widget from a thread
@work(thread=True)
def bad(self) -> None:
    rows = fetch()
    self.query_one(DataTable).add_rows(rows)      # ← race

# RIGHT
@work(thread=True)
def good(self) -> None:
    rows = fetch()
    self.app.call_from_thread(self._apply, rows)

def _apply(self, rows) -> None:
    with self.app.batch_update():
        self.query_one(DataTable).add_rows(rows)
```

`call_from_thread` is **synchronous** — it blocks the worker thread until the callback has
run on the loop. That is usually what you want (natural backpressure), but it means a slow
callback slows your worker. For fire-and-forget telemetry, `post_message` is better.

### 21.5 CPU-bound work: processes, not threads

Verified, measured module (4 parallel `fib(25)` calls completed in 0.03 s on a 4-core box
versus ~0.1 s serially):

```python
from __future__ import annotations
import asyncio, os
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, TypeVar

R = TypeVar("R")
CPU_WORKERS = max(1, (os.cpu_count() or 2) - 1)   # leave a core for the UI

_pool: ProcessPoolExecutor | None = None

def process_pool() -> ProcessPoolExecutor:
    global _pool
    if _pool is None:
        _pool = ProcessPoolExecutor(max_workers=CPU_WORKERS)
    return _pool

def shutdown_process_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.shutdown(cancel_futures=True)
        _pool = None

async def run_cpu(fn: Callable[..., R], *args: object) -> R:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(process_pool(), fn, *args)
```

```python
@work(group="cpu")
async def reindex(self) -> None:
    sizes = await asyncio.gather(*(run_cpu(hash_file, p) for p in self.paths))
    self.apply(sizes)

def on_unmount(self) -> None:
    shutdown_process_pool()
```

Rules that will bite you otherwise:

- **The function and its arguments must be picklable.** Module-level functions only — no
  lambdas, no closures, no bound methods of widgets.
- **Never pass a widget, an `App`, or anything holding a socket into a subprocess.**
- **Create the pool lazily and shut it down explicitly.** An abandoned pool leaves orphan
  processes, which under PyInstaller `--onefile` means orphan copies of your whole app.
- **Under PyInstaller you must call `multiprocessing.freeze_support()`** as the very first
  thing in your entry point, or every subprocess re-runs your app. See §23.6.
- `CPU_WORKERS = cpu_count() - 1`: saturating all cores starves the render loop and the app
  stutters even though "the work is in another process".

### 21.6 Debounce, throttle and coalesce

Three distinct tools; people confuse them.

| Pattern | Behaviour | Use for |
|---|---|---|
| Debounce | run once, `delay` after the last call | search-as-you-type, autosave |
| Throttle | run at most once per interval | progress updates, scroll handlers |
| Coalesce | collect calls, run once with the batch | log lines, incoming events |

```python
class Debouncer:
    """Collapse rapid calls into one, after `delay` seconds of quiet."""

    def __init__(self, delay: float) -> None:
        self.delay = delay
        self._handle: asyncio.TimerHandle | None = None

    def __call__(self, fn: Callable[[], None]) -> None:
        if self._handle is not None:
            self._handle.cancel()
        self._handle = asyncio.get_running_loop().call_later(self.delay, fn)

    def cancel(self) -> None:
        if self._handle is not None:
            self._handle.cancel()
            self._handle = None
```

```python
class Search(Widget):
    def on_mount(self) -> None:
        self._debounce = Debouncer(0.2)

    @on(Input.Changed, "#q")
    def _typed(self, event: Input.Changed) -> None:
        self._debounce(lambda: self.run_query(event.value))

    @work(exclusive=True, group="query")      # belt and braces: cancels in-flight queries
    async def run_query(self, text: str) -> None:
        results = await self.index.search(text)
        self.show(results)

    def on_unmount(self) -> None:
        self._debounce.cancel()
```

Verified behaviour: 10 calls 5 ms apart through a 50 ms debouncer produce exactly **one**
invocation.

Textual also gives you `widget.call_after_refresh(fn)` (run after the next repaint) and
`widget.set_timer(...)`, which cover simpler cases without a helper class.

Throttling the other way round — for a producer you do not control:

```python
class Throttle:
    def __init__(self, interval: float) -> None:
        self.interval, self._last = interval, 0.0

    def ready(self) -> bool:
        now = time.monotonic()
        if now - self._last >= self.interval:
            self._last = now
            return True
        return False
```

### 21.7 Bounded fan-out

Never `asyncio.gather` an unbounded list of network calls: you will open 5,000 sockets and
get rate-limited or OOM.

```python
async def gather_bounded(tasks: Sequence[Callable[[], Awaitable[R]]],
                         limit: int = 8) -> list[R | BaseException]:
    sem = asyncio.Semaphore(limit)
    async def run(factory):
        async with sem:
            return await factory()
    return await asyncio.gather(*(run(t) for t in tasks), return_exceptions=True)
```

Verified: with `limit=4` over 20 jobs, measured peak concurrency was exactly 4, and
`return_exceptions=True` means one failure does not cancel the other 19.

To show results as they land instead of waiting for all:

```python
async def as_completed_stream(coros: Iterable[Awaitable[R]]) -> AsyncIterator[R | BaseException]:
    pending = {asyncio.ensure_future(c) for c in coros}
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            try:
                yield task.result()
            except BaseException as error:
                yield error
```

```python
@work(group="fan")
async def check_all(self) -> None:
    table = self.query_one(DataTable)
    async for result in as_completed_stream([probe(h) for h in self.hosts]):
        if isinstance(result, BaseException):
            continue
        table.add_row(*result)        # rows appear progressively — feels 10× faster
```

### 21.8 Backpressured pipelines

For a producer that can outrun the UI (a log tail, a websocket, a subprocess):

```python
async def pipeline(produce, consume, *, maxsize: int = 64, workers: int = 4) -> None:
    queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)

    async def worker() -> None:
        while True:
            item = await queue.get()
            try:
                if item is None:
                    return
                await consume(item)
            finally:
                queue.task_done()

    consumers = [asyncio.create_task(worker()) for _ in range(workers)]
    try:
        await produce(queue)
        for _ in consumers:
            await queue.put(None)
        await asyncio.gather(*consumers)
    finally:
        for task in consumers:
            task.cancel()
```

The bounded `maxsize` is the whole point: `await queue.put(item)` blocks the producer when
the UI falls behind, instead of growing a list until memory runs out. Verified with 100
items, 5 consumers, `maxsize=8`.

For a log tail specifically, coalesce instead of consuming one-by-one:

```python
@work(group="tail")
async def tail(self, path: Path) -> None:
    log = self.query_one(Log)
    buffer: list[str] = []
    async for line in follow(path):
        buffer.append(line)
        if len(buffer) >= 200 or self._flush_due():
            log.write_lines(buffer)       # one widget call per frame, not per line
            buffer.clear()
```

### 21.9 Subprocesses

```python
@work(group="proc", exclusive=True)
async def run_build(self) -> None:
    log = self.query_one(RichLog)
    process = await asyncio.create_subprocess_exec(
        "make", "-j4",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=self.workspace,
    )
    self._process = process
    assert process.stdout is not None
    async for raw in process.stdout:
        log.write(raw.decode("utf-8", "replace").rstrip())
    code = await process.wait()
    self.notify("Build OK" if code == 0 else f"Build failed ({code})",
                severity="information" if code == 0 else "error")

def action_stop_build(self) -> None:
    if self._process is not None and self._process.returncode is None:
        self._process.terminate()
```

Notes: use `create_subprocess_exec` (not `shell`) to avoid quoting bugs; always decode with
`errors="replace"` because build tools emit broken UTF-8; and `terminate()` then
`kill()` after a grace period, since not every process honours SIGTERM.

### 21.10 Timers vs intervals vs the frame clock

```python
self.set_interval(1 / 30, self.tick)                  # repeating
self.set_interval(5.0, self.poll, name="poll")
self.set_timer(0.3, self.show_tooltip)                # one-shot
timer = self.set_interval(1.0, self.tick, pause=True) # start paused
timer.resume(); timer.pause(); timer.reset(); timer.stop()
self.call_later(self.after_everything)                # next loop iteration
self.call_after_refresh(self.measure)                 # after the next repaint
self.call_next(self.handle)                           # next message, before others
```

An interval callback that takes longer than its interval does **not** queue up — Textual
skips, so you degrade to a lower frame rate rather than falling permanently behind. Still,
keep interval callbacks under 2 ms.

**Own the timer where the widget lives.** An App-level `set_interval` whose callback does
`self.query_one("#meter")` will eventually fire after that widget has been removed and raise
`NoMatches` — this happened while writing the reference app in `examples/nocturne`, during
test teardown. Put the timer on the widget itself, in its `on_mount`, and it is cancelled
automatically when the widget is removed:

```python
class WaveMeter(Widget):
    def on_mount(self) -> None:
        self.set_interval(1 / 20, self._advance)   # dies with the widget

    def _advance(self) -> None:
        self.phase += 0.25
```

**And do not name private attributes after Textual internals.** `App.__init__` and
`Widget.__init__` both assign `self._animate = <BoundAnimator>`. A method named `_animate`
on your `App` subclass is silently shadowed by that instance attribute, and
`self.set_interval(1/20, self._animate)` then calls the animator with no arguments:
`TypeError: BoundAnimator.__call__() missing 2 required positional arguments`. Verified on
8.2.8. Prefix your own private members distinctly (`_advance_meter`, `_my_timer`).

### 21.11 Scaling checklist

- [ ] No `time.sleep`, `requests.get`, `subprocess.run`, or file read in any handler.
- [ ] Every search-as-you-type path is `@work(exclusive=True, group=...)` plus a debounce.
- [ ] Every thread worker polls `worker.is_cancelled` in its loop.
- [ ] Every thread→UI call is `call_from_thread` or `post_message`.
- [ ] High-frequency UI updates are throttled to ≤ 30 Hz and wrapped in `batch_update()`.
- [ ] Fan-out is bounded by a `Semaphore`.
- [ ] Producer/consumer queues have a `maxsize`.
- [ ] CPU work is in a process pool sized `cpu_count() - 1`, with `freeze_support()` called.
- [ ] Pools, timers, subprocesses and subscriptions are shut down in `on_unmount`.
- [ ] Hidden screens pause their polling (`on_screen_suspend`).
- [ ] `TEXTUAL_SLOW_THRESHOLD` (default 500 ms) warnings are checked in the dev console.

---
## 22. Application data, config and storage

### 22.1 Never guess paths

`~/.myapp` is wrong on every platform. Use `platformdirs` (which Textual already depends
on, so it costs you nothing).

```python
from platformdirs import PlatformDirs

DIRS = PlatformDirs(appname="Nocturne", appauthor="Acme", roaming=True, ensure_exists=True)
```

Constructor, verified (4.12.3): `PlatformDirs(appname=None, appauthor=None, version=None,
roaming=False, multipath=False, opinion=True, ensure_exists=False, use_site_for_root=False)`.

Resolved paths for `appname="Nocturne"`, `appauthor="Acme"`:

| Property | Windows | macOS | Linux (XDG) |
|---|---|---|---|
| `user_data_dir` | `%APPDATA%\Acme\Nocturne` (roaming) or `%LOCALAPPDATA%\…` | `~/Library/Application Support/Nocturne` | `~/.local/share/Nocturne` |
| `user_config_dir` | `%APPDATA%\Acme\Nocturne` | `~/Library/Application Support/Nocturne` | `~/.config/Nocturne` |
| `user_cache_dir` | `%LOCALAPPDATA%\Acme\Nocturne\Cache` | `~/Library/Caches/Nocturne` | `~/.cache/Nocturne` |
| `user_state_dir` | `%LOCALAPPDATA%\Acme\Nocturne` | `~/Library/Application Support/Nocturne` | `~/.local/state/Nocturne` |
| `user_log_dir` | `%LOCALAPPDATA%\Acme\Nocturne\Logs` | `~/Library/Logs/Nocturne` | `~/.local/state/Nocturne/log` |
| `user_runtime_dir` | `%LOCALAPPDATA%\Temp\Acme\Nocturne` | `~/Library/Caches/TemporaryItems/Nocturne` | `$XDG_RUNTIME_DIR/Nocturne` |
| `user_documents_dir` | `%USERPROFILE%\Documents` | `~/Documents` | `~/Documents` |
| `user_downloads_dir` | `%USERPROFILE%\Downloads` | `~/Downloads` | `~/Downloads` |
| `site_config_dir` | `%PROGRAMDATA%\Acme\Nocturne` | `/Library/Application Support/Nocturne` | `/etc/xdg/Nocturne` |
| `site_data_dir` | `%PROGRAMDATA%\Acme\Nocturne` | `/Library/Application Support/Nocturne` | `/usr/local/share/Nocturne` |

(Linux values verified by running it; every `*_dir` also has a `*_path` variant returning a
`pathlib.Path`.) Note `user_runtime_dir` warns and falls back to `/tmp/runtime-<uid>` when
`XDG_RUNTIME_DIR` is unset — expected in containers and over bare SSH.

**What goes where:**

| Directory | Contents | Safe to delete? |
|---|---|---|
| config | `settings.json`, keymaps, profiles — things the user edits | No (user loses preferences) |
| data | databases, saved documents, plugins, indices | No (user loses work) |
| state | window/layout state, last-opened, session restore | Yes (cosmetic loss) |
| cache | HTTP caches, thumbnails, derived artefacts | **Yes, always** |
| logs | rotating log files | Yes |
| runtime | sockets, pid/lock files | Yes (on reboot) |

The practical test: if deleting a directory loses user data, it is not a cache.

### 22.2 A complete `paths.py` (verified)

```python
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from platformdirs import PlatformDirs

APP_NAME = "Nocturne"
APP_AUTHOR = "Acme"
DIRS = PlatformDirs(appname=APP_NAME, appauthor=APP_AUTHOR, roaming=True)


def is_frozen() -> bool:
    """True when running from a PyInstaller/Nuitka bundle."""
    return bool(getattr(sys, "frozen", False))


def resource_path(relative: str | os.PathLike[str]) -> Path:
    """Path to a *read-only shipped asset*, frozen or not."""
    base = getattr(sys, "_MEIPASS", None)          # set by the PyInstaller bootloader
    if base is None:
        base = Path(__file__).resolve().parent     # the package directory in dev
    return Path(base) / relative


def portable_root() -> Path | None:
    """Portable mode: a 'portable.txt' next to the executable moves data beside it."""
    if not is_frozen():
        return None
    exe_dir = Path(sys.executable).resolve().parent
    return exe_dir if (exe_dir / "portable.txt").exists() else None


@dataclass(frozen=True)
class Paths:
    config: Path
    data: Path
    cache: Path
    state: Path
    logs: Path

    @classmethod
    def resolve(cls) -> "Paths":
        # 1. portable install wins
        root = portable_root()
        if root is not None:
            base = root / "userdata"
            return cls(base / "config", base / "data", base / "cache",
                       base / "state", base / "logs")
        # 2. explicit override (tests, CI, power users)
        override = os.environ.get(f"{APP_NAME.upper()}_HOME")
        if override:
            base = Path(override).expanduser()
            return cls(base / "config", base / "data", base / "cache",
                       base / "state", base / "logs")
        # 3. OS conventions
        return cls(
            Path(DIRS.user_config_dir), Path(DIRS.user_data_dir),
            Path(DIRS.user_cache_dir), Path(DIRS.user_state_dir),
            Path(DIRS.user_log_dir),
        )

    def ensure(self) -> "Paths":
        for path in (self.config, self.data, self.cache, self.state, self.logs):
            path.mkdir(parents=True, exist_ok=True)
        return self
```

The three-tier resolution (portable → env override → OS) is what makes an app work on a USB
stick, in a test harness, and as a normal install, with no branching anywhere else.

`resource_path` vs app-data: **`resource_path` is read-only.** Under `--onefile` it points
into a temporary extraction directory that is deleted on exit, and under `--onedir` it is
inside the installation (often not writable). Writing there is the single most common
packaging bug.

### 22.3 Atomic writes

A config file half-written because the user closed the laptop lid is a support ticket you
can prevent in ten lines.

```python
import os, tempfile
from pathlib import Path

def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())        # data hits the disk
        os.replace(tmp, path)                # atomic on POSIX and Windows
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)                 # the rename hits the disk too
        finally:
            os.close(dir_fd)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
```

Details that matter: the temp file must be **in the same directory** (`os.replace` across
filesystems is not atomic); `newline="\n"` stops Windows from writing CRLF into your JSON;
and the directory `fsync` is what makes the rename itself durable. On Windows,
`os.fsync` on a directory handle raises — guard it with `if os.name != "nt"` if you support
very old Windows, though it works on modern builds.

### 22.4 Typed settings with migration

```python
import json
from dataclasses import asdict, dataclass, field, fields
from typing import Any

@dataclass
class Settings:
    schema_version: int = 2
    theme: str = "textual-dark"
    page_size: int = 50
    animations: str = "full"          # full | basic | none
    icons: str = "auto"               # auto | ascii | unicode | nerd
    recent: list[str] = field(default_factory=list)
    keymap: dict[str, str] = field(default_factory=dict)
    flags: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Settings":
        try:
            raw = json.loads(path.read_text("utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return cls()                      # never crash on a bad config
        if not isinstance(raw, dict):
            return cls()
        raw = migrate(raw)
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known})

    def save(self, path: Path) -> None:
        atomic_write_text(path, json.dumps(asdict(self), indent=2, sort_keys=True) + "\n")


def migrate(raw: dict[str, Any]) -> dict[str, Any]:
    version = int(raw.get("schema_version", 1))
    if version < 2:
        raw["animations"] = "full" if raw.pop("fancy", True) else "none"
        raw["schema_version"] = 2
    # if version < 3: ...
    return raw
```

Verified behaviour: a v1 file `{"schema_version": 1, "fancy": false, "theme": "nord",
"junk": 1}` loads as `Settings(schema_version=2, theme="nord", animations="none")` with
`junk` dropped; a corrupt file loads as defaults.

Four non-negotiable properties:

1. **A broken or missing config never crashes the app.** Fall back to defaults and
   `notify()` the user.
2. **Unknown keys are dropped on read, not on write** — so a newer version's config
   survives a downgrade round-trip reasonably.
3. **`schema_version` is written from day one.** Adding it later means guessing.
4. **Saves are atomic and debounced** — do not write on every keystroke:

```python
def on_mount(self) -> None:
    self._save_settings = Debouncer(1.0)

def _settings_changed(self) -> None:
    self._save_settings(lambda: self.settings.save(self.paths.config / "settings.json"))
```

For richer config, TOML is friendlier to hand-edit (`tomllib` reads it in the stdlib since
3.11; writing needs `tomli-w`). Use JSON for machine state, TOML for user-facing config.

### 22.5 SQLite for real data

```python
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS item (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS item_name ON item(name);
"""

@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5.0, isolation_level=None,
                           check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
    finally:
        conn.close()
```

Verified: `PRAGMA journal_mode` reads back `wal` after this setup.

Why each setting:

- **`journal_mode=WAL`** — readers do not block the writer. Essential when a worker thread
  writes while the UI reads.
- **`synchronous=NORMAL`** — with WAL this is durable against app crashes (not against power
  loss), and far faster than `FULL`.
- **`isolation_level=None`** — turns off Python's implicit transaction magic so `BEGIN`/
  `COMMIT` are yours to control explicitly.
- **`check_same_thread=False`** — required to hand the connection to a worker thread. You
  must then serialise access yourself (one connection per thread is simpler and safer).
- **`timeout=5.0`** — wait for a lock instead of raising `database is locked` instantly.
- **`row_factory = sqlite3.Row`** — name-based access; your query code stops caring about
  column order.

Keep all database calls inside `@work(thread=True)` workers. SQLite is fast but it is
blocking, and a `VACUUM` on a 2 GB file will freeze a UI that calls it on the loop.

### 22.6 Caches with budgets

```python
import hashlib, shutil, time

class DiskCache:
    def __init__(self, root: Path, *, max_bytes: int = 256 * 1024 * 1024) -> None:
        self.root, self.max_bytes = root, max_bytes
        root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.blake2b(key.encode(), digest_size=16).hexdigest()
        return self.root / digest[:2] / digest          # shard: avoid 100k files in one dir

    def get(self, key: str, max_age: float | None = None) -> bytes | None:
        path = self._path(key)
        try:
            if max_age is not None and time.time() - path.stat().st_mtime > max_age:
                return None
            return path.read_bytes()
        except OSError:
            return None

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)

    def evict(self) -> int:
        """LRU-ish eviction by mtime. Call on startup from a worker."""
        files = sorted((p for p in self.root.rglob("*") if p.is_file()),
                       key=lambda p: p.stat().st_mtime)
        total = sum(p.stat().st_size for p in files)
        freed = 0
        for path in files:
            if total - freed <= self.max_bytes:
                break
            size = path.stat().st_size
            path.unlink(missing_ok=True)
            freed += size
        return freed

    def clear(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
        self.root.mkdir(parents=True, exist_ok=True)
```

Always expose a "Clear cache" command. An app whose cache grows forever will eventually be
the reason someone uninstalls it.

### 22.7 Secrets

Do not put tokens in `settings.json`.

```python
def store_token(service: str, account: str, token: str) -> bool:
    try:
        import keyring                     # macOS Keychain / Windows Credential Manager /
        keyring.set_password(service, account, token)   # Secret Service on Linux
        return True
    except Exception:
        return False

def load_token(service: str, account: str) -> str | None:
    # 1. environment wins (CI, containers, power users)
    env = os.environ.get(f"{service.upper()}_TOKEN")
    if env:
        return env
    # 2. OS keychain
    try:
        import keyring
        value = keyring.get_password(service, account)
        if value:
            return value
    except Exception:
        pass
    # 3. a 0600 file as a last resort, clearly documented
    path = Paths.resolve().config / "credentials"
    try:
        if path.stat().st_mode & 0o077:
            return None                    # refuse to read world-readable secrets
        return path.read_text("utf-8").strip() or None
    except OSError:
        return None
```

Never log a token, never put one in a crash report, and never echo one back in the UI
(`Input(password=True)`). On headless Linux, `keyring` often has no backend — the env-var
path is not a fallback, it is the primary mechanism there.

### 22.8 Logging

```python
import logging, logging.handlers

def setup_logging(log_dir: Path, *, level: int = logging.INFO, debug: bool = False) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        log_dir / "nocturne.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s %(message)s"
    ))
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else level)
    root.addHandler(handler)
    logging.getLogger("httpx").setLevel(logging.WARNING)   # quiet chatty deps
```

**Never add a `StreamHandler` in a TUI.** Anything written to stdout/stderr lands in the
middle of your rendered screen. Textual provides its own channel:

```python
from textual import log

log("plain message")
log(locals())                     # pretty-printed
log.debug("fine detail")
log.warning("careful")
log(renderable=some_rich_table)
self.log.event(event)             # widget-scoped logger
```

These go to the dev console (`textual console`) and to `TEXTUAL_LOG=app.log` — never to the
screen. Use the `logging` module for things the *user* may need to send you, and
`textual.log` for things *you* need while developing.

To capture third-party `print()` calls instead of letting them corrupt the display:

```python
def on_mount(self) -> None:
    self.begin_capture_print(self)      # routes print() to events.Print

def on_print(self, event: events.Print) -> None:
    self.query_one(RichLog).write(event.text)
```

### 22.9 Single instance

```python
class SingleInstance:
    def __init__(self, lock_path: Path) -> None:
        self.lock_path, self._handle = lock_path, None

    def __enter__(self) -> "SingleInstance":
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = open(self.lock_path, "a+b")
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self._handle.close()
            self._handle = None
            raise RuntimeError("another instance is already running") from error
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._handle is not None:
            self._handle.close()        # releases the lock on both platforms
            self._handle = None
```

Verified: the second `SingleInstance` on the same path raises `RuntimeError`, and the lock
is reacquirable after the first exits. Put the lock file in `user_runtime_dir` (cleared on
reboot), not in config. Use it whenever two instances would corrupt shared state — a
SQLite file in a non-WAL mode, an index, a daemon socket.

---

## 23. Packaging: `resource_path`, PyInstaller, icons

Everything in this section was executed: builds run, binaries launched, sizes and startup
times measured on Linux/x86-64 with PyInstaller 6.22.3 and Textual 8.2.8.

### 23.1 `resource_path`, correctly

```python
import os, sys
from pathlib import Path

def resource_path(relative: str | os.PathLike[str]) -> Path:
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = Path(__file__).resolve().parent
    return Path(base) / relative
```

- `sys._MEIPASS` is set **only** by the PyInstaller bootloader. In `--onefile` it is a
  temporary extraction directory (`/tmp/_MEIxxxxxx`, `%TEMP%\_MEIxxxxxx`) deleted on exit;
  in `--onedir` it is the `_internal/` folder next to the executable (verified — the naive
  build looked for `dist/demo/_internal/assets/app.tcss`).
- `sys.frozen` is the flag to test "am I bundled?"; `sys._MEIPASS` is "where are my assets?".
- The fallback must be `Path(__file__).parent`, **not** `os.getcwd()`. A user running
  `nocturne` from `~/Documents` has a cwd that has nothing to do with your package. Many
  tutorials get this wrong.
- Put `resource_path` in a module inside your package (it resolves relative to that file),
  and never in the `.spec`.

Using it for `CSS_PATH`:

```python
class Nocturne(App[None]):
    CSS_PATH = [resource_path("styles/base.tcss"),
                resource_path("styles/widgets.tcss")]
```

### 23.2 The naive build fails — concretely

A build with no data flags:

```
$ pyinstaller --onedir --name demo main.py
$ ./dist/demo/demo
StylesheetError: unable to read CSS file '…/dist/demo/_internal/assets/app.tcss'
```

Add the data but not the package data:

```
$ pyinstaller --onedir --add-data "assets:assets" --name demo main.py
$ ./dist/demo/demo
textual.widgets._text_area.LanguageDoesNotExist: tree-sitter is available, but no
built-in or user-registered language called 'python'.
```

Both reproduced on 8.2.8 / PyInstaller 6.22.3. Two separate problems:

1. **Your own assets** are not collected automatically. `--add-data` them.
2. **Textual's own package data** (the `tree-sitter/highlights/*.scm` queries) is not
   collected, and the grammar packages (`tree_sitter_python`, …) are imported *dynamically
   by language name*, so static analysis never sees them.

### 23.3 The build that works

```bash
pyinstaller --noconfirm --onedir --name nocturne \
  --add-data "assets:assets" \
  --collect-data textual \
  --hidden-import tree_sitter \
  --hidden-import tree_sitter_python \
  --hidden-import tree_sitter_markdown \
  --icon assets/logo.ico \
  src/nocturne/__main__.py
```

(Windows uses `;` instead of `:` in `--add-data`.) Verified result: the app starts, the
stylesheet loads, `TextArea(language="python")` highlights, and
`dist/nocturne/_internal/textual/tree-sitter/highlights/` contains the `.scm` files.

Good news verified by inspecting the build's cross-reference: **you do not need hidden
imports for the built-in widgets.** Although `textual/widgets/__init__.py` loads submodules
lazily through `__getattr__`, it also lists them in a `TYPE_CHECKING` import block, and
PyInstaller's bytecode analysis picks those up — all 41 widget modules
(`textual.widgets._button` … `textual.widgets._welcome`) were collected. Add hidden imports
only for:

- `tree_sitter_*` grammar packages you want available in `TextArea`
- any plugin modules *you* import by string name
- third-party widget libraries that load drivers dynamically (`textual-image`'s protocol
  backends, database drivers)

### 23.4 A spec file (recommended for anything real)

```python
# nocturne.spec  — build with:  pyinstaller --noconfirm nocturne.spec
# ruff: noqa
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project = Path(SPECPATH)

datas = [
    (str(project / "assets"), "assets"),
    (str(project / "src/nocturne/styles"), "styles"),
]
datas += collect_data_files("textual")                 # the .scm highlight queries

hiddenimports = [
    "tree_sitter",
    "tree_sitter_python",
    "tree_sitter_json",
    "tree_sitter_markdown",
]
# hiddenimports += collect_submodules("nocturne.plugins")   # if you load plugins by name

excludes = [
    "tkinter", "turtle", "idlelib", "lib2to3", "pydoc_data",
    "test", "unittest", "doctest",
    "PIL", "numpy", "pandas", "matplotlib",      # drop whatever you truly do not use
    "setuptools", "pip", "wheel",
    "IPython", "jedi", "sqlalchemy",
]

a = Analysis(
    ["src/nocturne/__main__.py"],
    pathex=["src"],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    hookspath=[],
    runtime_hooks=[],
    noarchive=False,
    optimize=2,                       # strip docstrings + asserts
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="nocturne",
    console=True,                     # ← a TUI is a console app. Never False.
    debug=False,
    strip=False,
    upx=False,                        # UPX breaks code signing and triggers AV heuristics
    icon="assets/logo.ico",
    version="version_info.txt",       # Windows file metadata (see 23.5)
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False, name="nocturne",
)

# macOS only: wrap it in an .app bundle if you want Finder integration.
# app = BUNDLE(coll, name="Nocturne.app", icon="assets/logo.icns",
#              bundle_identifier="com.acme.nocturne",
#              info_plist={"LSBackgroundOnly": False, "NSHighResolutionCapable": True})
```

`console=True` is the one line people get wrong. `--windowed`/`console=False` detaches the
process from a console; your TUI then has no terminal to draw on and either exits
immediately or hangs invisibly.

### 23.5 Icons: `.ico`, `.icns`, `.png`

A terminal app still needs an icon: taskbar, Alt-Tab, Finder, `.desktop` entries, installer
artwork, and the `.exe` file icon.

| Platform | Format | Sizes needed |
|---|---|---|
| Windows | `.ico` (multi-image) | 16, 24, 32, 48, 64, 128, 256 — 256 must be PNG-compressed |
| macOS | `.icns` | 16, 32, 128, 256, 512 at 1× and 2× |
| Linux | `.png` | 16, 22, 24, 32, 48, 64, 128, 256, 512 + optional SVG |

Generate everything from one 1024×1024 master with Pillow — verified script that produced a
7-image, 17,437-byte `.ico`:

```python
# tools/make_icons.py
from pathlib import Path
from PIL import Image

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
PNG_SIZES = [16, 22, 24, 32, 48, 64, 128, 256, 512]

def build(master_path: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    master = Image.open(master_path).convert("RGBA")
    if master.size != (1024, 1024):
        master = master.resize((1024, 1024), Image.LANCZOS)

    # Windows: one .ico holding every size
    master.save(out / "logo.ico", format="ICO", sizes=[(s, s) for s in ICO_SIZES])

    # Linux / generic
    for size in PNG_SIZES:
        master.resize((size, size), Image.LANCZOS).save(out / f"logo-{size}.png")
    master.save(out / "logo.png")

    # macOS: build an .iconset, then `iconutil -c icns` on a Mac
    iconset = out / "logo.iconset"
    iconset.mkdir(exist_ok=True)
    for size in (16, 32, 128, 256, 512):
        master.resize((size, size), Image.LANCZOS).save(iconset / f"icon_{size}x{size}.png")
        master.resize((size * 2, size * 2), Image.LANCZOS).save(
            iconset / f"icon_{size}x{size}@2x.png")

if __name__ == "__main__":
    build(Path("assets/logo-master.png"), Path("assets/icons"))
```

```bash
# macOS, on a Mac (iconutil ships with Xcode command line tools)
iconutil -c icns assets/icons/logo.iconset -o assets/logo.icns
```

Design notes for a 16×16 target: one bold shape, no gradients, no text beyond a single
letter, high contrast, and test it against both a light and a dark taskbar.

**`--icon` is platform-specific.** On Windows it embeds the `.ico` in the PE resources; on
macOS it sets the bundle icon; **on Linux it does nothing** — you ship a `.desktop` file:

```ini
# packaging/nocturne.desktop  →  /usr/share/applications/
[Desktop Entry]
Type=Application
Name=Nocturne
Comment=Terminal log explorer
Exec=nocturne %F
Icon=nocturne
Terminal=true
Categories=Development;Utility;ConsoleOnly;
MimeType=text/plain;application/json;
```

`Terminal=true` is mandatory for a TUI launched from a desktop environment — without it the
app starts with no terminal attached. Install the PNGs into
`/usr/share/icons/hicolor/<size>x<size>/apps/nocturne.png`.

Windows file metadata (shown in Properties → Details, and required by some installers):

```
# version_info.txt — referenced by EXE(version=...)
VSVersionInfo(
  ffi=FixedFileInfo(filevers=(1,0,0,0), prodvers=(1,0,0,0), mask=0x3f, flags=0x0,
                    OS=0x4, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable("040904B0", [
        StringStruct("CompanyName", "Acme"),
        StringStruct("FileDescription", "Nocturne — terminal log explorer"),
        StringStruct("FileVersion", "1.0.0.0"),
        StringStruct("InternalName", "nocturne"),
        StringStruct("LegalCopyright", "© 2026 Acme"),
        StringStruct("OriginalFilename", "nocturne.exe"),
        StringStruct("ProductName", "Nocturne"),
        StringStruct("ProductVersion", "1.0.0.0"),
    ])]),
    VarFileInfo([VarStruct("Translation", [1033, 1200])]),
  ],
)
```

### 23.6 `multiprocessing` under a frozen app

If you use a `ProcessPoolExecutor` (§21.5) this is mandatory:

```python
# src/nocturne/__main__.py
import multiprocessing, sys

if __name__ == "__main__":
    multiprocessing.freeze_support()     # MUST be first — before any other import work
    from nocturne.cli import main
    sys.exit(main())
```

Without it, on Windows (and with the `spawn` start method anywhere) every worker process
re-executes your entry point and you get an exponentially multiplying army of TUIs. Also
consider `multiprocessing.set_start_method("spawn")` explicitly so dev and frozen behave
the same.

### 23.7 Onefile vs onedir — measured

Measured on this machine (Linux x86-64, Python 3.11, Textual 8.2.8, a trivial Textual app
with `DataTable` + `TextArea`):

| Build | Size | Startup (min of 3) |
|---|---|---|
| `python main.py` (source, in the venv) | — | 0.346 s |
| `--onedir`, **no** excludes (vacuumed up PIL, aiohttp, numpy) | **102 MB** | 0.406 s |
| `--onedir` via the spec file below (excludes applied) | **28 MB** | ~0.41 s |
| `--onefile` + the same excludes | **14 MB** | 0.512 s |

Three lessons:

1. **Excludes dominate size.** The 102 MB build was large because unrelated packages were
   installed in the venv and got vacuumed up transitively. Build in a **clean virtualenv
   with only runtime dependencies** and audit with `--log-level=DEBUG` or the generated
   `build/<name>/xref-<name>.html`.
2. **`--onefile` costs ~100 ms of startup** because the bootloader extracts the archive to a
   temp directory on every launch. It grows with bundle size.
3. Prefer `--onedir` (shipped inside an installer/`.dmg`/`.tar.gz`) for anything the user
   installs, and `--onefile` for a single-file download or a CI artefact.

Further size reduction, in order of effectiveness:

- Audit and `--exclude-module` aggressively (`tkinter`, `test`, `unittest`, `pydoc_data`,
  `setuptools`, `pip`, `IPython`, `lib2to3` are almost always safe).
- Make heavy features optional: import `PIL` lazily inside the image widget so a user
  without image support never pays for it, and drop it from the bundle entirely.
- `optimize=2` in the spec strips docstrings and asserts.
- Trim the tree-sitter grammars to the languages you actually offer (each is ~1–3 MB).
- `strip=True` on Linux/macOS binaries (test it; it occasionally breaks a wheel's .so).
- **Do not use UPX.** It breaks macOS code signing, trips antivirus heuristics, and adds
  decompression time on every start.

### 23.8 Platform packaging notes

**Windows**

- Sign the executable: `signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /f cert.pfx nocturne.exe`.
  Unsigned binaries get SmartScreen warnings and are often quarantined.
- Build the installer with Inno Setup or WiX; add to `PATH` optionally, install the `.desktop`
  equivalent (Start Menu shortcut) with `Terminal` semantics handled by `cmd /k` or
  Windows Terminal profile.
- Ship a Windows Terminal fragment (`%LOCALAPPDATA%\Microsoft\Windows Terminal\Fragments\`)
  if you want a branded profile — this is how you get a proper icon and UTF-8 by default.
- Test on `conhost` as well as Windows Terminal.

**macOS**

- Universal2 binaries need a universal Python; otherwise ship separate arm64 and x86_64
  builds.
- Code sign **and notarise**, or Gatekeeper blocks it:
  ```bash
  codesign --deep --force --options runtime --timestamp \
           --sign "Developer ID Application: Acme (TEAMID)" dist/Nocturne.app
  ditto -c -k --keepParent dist/Nocturne.app Nocturne.zip
  xcrun notarytool submit Nocturne.zip --apple-id … --team-id … --password … --wait
  xcrun stapler staple dist/Nocturne.app
  ```
- For a CLI/TUI, a plain binary in a `.tar.gz` plus a Homebrew formula is usually a better
  experience than a `.app`.

**Linux**

- Prefer **not** to ship a PyInstaller bundle: `pipx install nocturne` or
  `uv tool install nocturne` is simpler, smaller and updates cleanly.
- If you must ship a binary, use the oldest glibc you support (build in a
  `manylinux` container) or build with musl.
- AppImage works well for TUIs; Flatpak/Snap sandboxing interferes with terminal and
  filesystem access and is rarely worth it.
- Install the `.desktop` file and icons as in §23.5.

### 23.9 Alternatives to PyInstaller

| Tool | Trade-off |
|---|---|
| **`uv tool install` / `pipx`** | Best option when the user has Python. No bundling, instant updates, tiny |
| **Nuitka** | Compiles to C; smaller and faster-starting binaries, longer builds, occasional compatibility work |
| **PyApp** | Rust launcher that bootstraps your app from PyPI on first run; a ~3 MB binary that self-installs |
| **PyOxidizer** | Embeds the interpreter and modules in the binary; powerful, steeper learning curve |
| **Briefcase** | Full BeeWare packaging to platform installers; aimed at GUI but works |
| **`python -m zipapp`** | A `.pyz` requiring a system Python; trivially small, good for internal tools |
| **Docker** | For server-side TUIs run over SSH/`docker exec` |

For a TUI specifically, my ranked recommendation: `uv tool`/`pipx` for developers;
PyInstaller `--onedir` inside a platform installer for everyone else; Nuitka if startup time
is a selling point.

### 23.10 A build script and CI matrix

```bash
#!/usr/bin/env bash
# tools/build.sh
set -euo pipefail

VERSION=$(python -c "import tomllib,pathlib;print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])")
rm -rf build dist

python -m venv .build-venv                       # clean venv => small bundle
.build-venv/bin/pip install --quiet --upgrade pip
.build-venv/bin/pip install --quiet ".[syntax]" pyinstaller
.build-venv/bin/python tools/make_icons.py
.build-venv/bin/pyinstaller --noconfirm nocturne.spec

case "$(uname -s)" in
  Linux)  tar -czf "dist/nocturne-${VERSION}-linux-$(uname -m).tar.gz" -C dist nocturne ;;
  Darwin) ditto -c -k --keepParent dist/nocturne "dist/nocturne-${VERSION}-macos.zip" ;;
esac

# Smoke test: the bundle must actually start.
SMOKE=1 ./dist/nocturne/nocturne
```

```yaml
# .github/workflows/release.yml
name: release
on:
  push:
    tags: ["v*"]
jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        include:
          - { os: ubuntu-22.04,  name: linux-x86_64 }   # old glibc on purpose
          - { os: macos-14,      name: macos-arm64 }
          - { os: macos-13,      name: macos-x86_64 }
          - { os: windows-2022,  name: windows-x86_64 }
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install ".[syntax]" pyinstaller
      - run: python tools/make_icons.py
      - run: pyinstaller --noconfirm nocturne.spec
      - name: Smoke test the bundle
        shell: bash
        env: { SMOKE: "1" }
        run: ./dist/nocturne/nocturne* || ./dist/nocturne/nocturne.exe
      - uses: actions/upload-artifact@v4
        with:
          name: nocturne-${{ matrix.name }}
          path: dist/
```

The **smoke test step is the point of the whole matrix.** Add a `SMOKE` environment flag to
your entry point that runs the app headlessly through `run_test()` and exits non-zero on
failure:

```python
if os.environ.get("SMOKE"):
    import asyncio
    async def smoke() -> None:
        app = Nocturne()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            assert app.query_one(DataTable) is not None
    asyncio.run(smoke())
    sys.exit(0)
```

This is exactly how the `LanguageDoesNotExist` and `StylesheetError` failures in §23.2 were
caught — a build that compiles is not a build that runs.

### 23.11 Packaging checklist

- [ ] `resource_path()` used for every shipped asset; nothing read from `os.getcwd()`.
- [ ] Nothing **written** under `sys._MEIPASS`; all writes go to app-data (§22).
- [ ] `--add-data` for your assets, `--collect-data textual` for the highlight queries.
- [ ] `--hidden-import` for every tree-sitter grammar and dynamically imported module.
- [ ] `console=True` / no `--windowed`.
- [ ] `multiprocessing.freeze_support()` first in `__main__`.
- [ ] Built in a clean venv; `--exclude-module` audited; no UPX.
- [ ] Multi-size `.ico`, `.icns` and PNGs generated from one master.
- [ ] `.desktop` file with `Terminal=true` for Linux.
- [ ] Windows signed; macOS signed **and** notarised and stapled.
- [ ] CI smoke test launches the bundle on every platform.
- [ ] `--version` works and is fast.

---
## 24. Testing, debugging and observability

### 24.1 Three layers of tests

1. **Domain tests** — plain pytest over `domain/`. No event loop, no widgets. This should be
   the bulk of your suite.
2. **Behavioural tests** — drive the real app with `Pilot`.
3. **Snapshot tests** — assert the rendered SVG has not changed.

### 24.2 `Pilot`

```python
import pytest
from nocturne.app import Nocturne
from textual.widgets import DataTable, Input

@pytest.mark.asyncio
async def test_search_filters_rows():
    app = Nocturne()
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()                      # let on_mount/workers settle
        await pilot.click("#search")
        await pilot.press(*"error")
        await pilot.pause(0.3)                   # past the debounce
        table = app.screen.query_one(DataTable)
        assert table.row_count == 4
```

Verified `Pilot` API (8.2.8):

```python
await pilot.press("ctrl+s", "tab", "a")     # keys, in order
await pilot.click("#save")                   # or click(Button), click(offset=(x, y))
await pilot.click("#cell", offset=(2, 0), shift=True, control=True, times=2, button=1)
await pilot.double_click("#row"); await pilot.triple_click("#row")
await pilot.hover("#card")
await pilot.mouse_down("#divider"); await pilot.mouse_up("#divider")
await pilot.resize_terminal(60, 20)          # exercise your breakpoints
await pilot.pause()                          # one loop turn
await pilot.pause(0.25)                      # or wait a bit
await pilot.wait_for_animation()
await pilot.wait_for_scheduled_animations()
pilot.exit(result)
pilot.app
```

`App.run_test(*, headless=True, size=(80, 24), tooltips=False, notifications=False,
message_hook=None)`.

**Two gotchas found while verifying this guide:**

1. `app.query_one(...)` is rooted at the app's **default screen**. With a modal pushed, use
   `app.screen.query_one(...)` — otherwise you get `NoMatches` on widgets that are plainly
   on screen.
2. Anything using `push_screen_wait` must be kicked off as a worker
   (`app.open_form()` where `open_form` is `@work`), then `await pilot.pause(...)` to let
   the screen mount before you interact with it.

`message_hook` is the tool for asserting on messages:

```python
seen: list[Message] = []
async with app.run_test(message_hook=seen.append) as pilot:
    await pilot.press("enter")
    assert any(isinstance(m, Button.Pressed) for m in seen)
```

### 24.3 Snapshot testing

```bash
pip install pytest-textual-snapshot
```

```python
def test_initial_render(snap_compare):
    assert snap_compare("src/nocturne/app.py", terminal_size=(100, 30))

def test_after_navigation(snap_compare):
    assert snap_compare("src/nocturne/app.py", press=["j", "j", "enter"],
                        terminal_size=(100, 30))

def test_with_setup(snap_compare):
    async def before(pilot):
        pilot.app.load_fixture(FIXTURE)
        await pilot.pause()
    assert snap_compare("src/nocturne/app.py", run_before=before)
```

Workflow, verified end to end:

```bash
pytest --snapshot-update      # record/refresh:  "2 snapshots generated."
pytest                        # assert:          "2 snapshots passed."
```

Snapshots land in `tests/__snapshots__/<test_module>/<test_name>.svg`. On failure the plugin
writes an HTML report with a side-by-side diff — open it, and if the change is intended,
re-run with `--snapshot-update` and commit the new SVG.

**A snapshot must be deterministic**, and whole applications usually are not. `Header(
show_clock=True)` renders the current time; a running animation renders a different phase
every run; `random` data differs per process. All three produce a snapshot that passes once
and then fails forever. Verified while writing the reference app: snapshotting the full
`Nocturne` app passed in isolation and failed when the suite ran, because the animated meter
and the header clock had both moved on.

Two fixes, both used in `examples/nocturne/tests`:

1. **Snapshot small harness apps**, one per component, with fixed data and no clock —
   `tests/snapshot_apps/multiselect_app.py`, `tests/snapshot_apps/settings_app.py`.
2. **Freeze the moving parts** in `run_before` (stop timers, set a fixed phase, seed the
   RNG) before the frame is captured.

Also note that `snap_compare` resolves its path **relative to the test file**, not the
working directory — build it from `__file__`, or you get
`AppFail: [Errno 2] No such file or directory: '…/tests/src/nocturne/app.py'`.

Snapshot tests are superb at catching accidental layout and style regressions and terrible
at asserting behaviour. Keep them few, cover the key screens, and review the SVG diffs in
code review like any other artefact.

### 24.4 The dev console

```bash
# terminal 1
textual console                       # or: textual console -x SYSTEM -x EVENT   (filter)
# terminal 2
textual run --dev src/nocturne/app.py
textual run --dev "nocturne.app:Nocturne"      # import path form
```

What `--dev` gives you:

- `textual.log(...)` output, `print()` output, tracebacks and warnings routed to the console
  instead of corrupting the screen.
- **Live CSS reloading** — save a `.tcss` file and the running app restyles instantly.
- Slow-callback warnings when a handler exceeds `TEXTUAL_SLOW_THRESHOLD` (default 500 ms).

Other `textual-dev` commands (verified):

| Command | Purpose |
|---|---|
| `textual run [--dev] TARGET` | run an app, optionally with devtools |
| `textual console` | the devtools log console |
| `textual borders` | browse every border style |
| `textual colors` | browse the live design system/theme tokens |
| `textual easing` | preview all 33 easing functions |
| `textual keys` | show key events as the terminal reports them — invaluable for bug reports |
| `textual diagnose` | dump versions, OS and terminal info as Markdown for issues |
| `textual serve` | serve the app over HTTP |

### 24.5 Environment variables (verified list)

| Variable | Effect |
|---|---|
| `TEXTUAL_DEBUG` | enable debug behaviour |
| `TEXTUAL_LOG` | write the devtools log to this file |
| `TEXTUAL_DEVTOOLS_HOST` / `_PORT` | console location (default `127.0.0.1:8081`) |
| `TEXTUAL_FPS` | frame-rate cap (default 60) |
| `TEXTUAL_ANIMATIONS` | `full` \| `basic` \| `none` |
| `TEXTUAL_THEME` | default theme name |
| `TEXTUAL_COLOR_SYSTEM` | `auto` \| `standard` \| `256` \| `truecolor` |
| `TEXTUAL_SLOW_THRESHOLD` | ms before a slow-callback warning (default 500) |
| `TEXTUAL_SMOOTH_SCROLL` | `0` disables sub-cell smooth scrolling |
| `TEXTUAL_DISABLE_KITTY_KEY` | disable the Kitty keyboard protocol (debugging keys) |
| `TEXTUAL_DRIVER` | override the driver |
| `TEXTUAL_FILTERS` | render filters (e.g. `dim` simulation) |
| `TEXTUAL_SCREENSHOT` | take a screenshot after N seconds and exit |
| `TEXTUAL_SCREENSHOT_LOCATION` / `_FILENAME` | where to put it |
| `TEXTUAL_PRESS` | comma-separated keys to auto-press at startup |
| `TEXTUAL_SHOW_RETURN` | print the app's return value on exit |
| `ESCDELAY` | escape-key disambiguation delay in ms (default 100) |

`TEXTUAL_SCREENSHOT` + `TEXTUAL_PRESS` together let you generate documentation screenshots
in CI with no code:

```bash
TEXTUAL_PRESS="tab,down,down,enter" \
TEXTUAL_SCREENSHOT=2 \
TEXTUAL_SCREENSHOT_FILENAME=docs/screens/detail.svg \
  python -m nocturne
```

### 24.6 Programmatic screenshots

```python
app.save_screenshot("docs/main.svg")          # writes an SVG
svg = app.export_screenshot()                 # returns the SVG string
```

Verified: `export_screenshot()` returns an SVG document. These are real vector screenshots
with selectable text — ideal for READMEs and far better than a PNG of a terminal.

### 24.7 Crash handling

Textual installs its own exception handling that restores the terminal and prints a Rich
traceback. Add your own reporting on top:

```python
import platform, sys, traceback
from datetime import datetime, timezone

class Nocturne(App[None]):
    def _handle_exception(self, error: Exception) -> None:
        try:
            self._write_crash_report(error)
        finally:
            super()._handle_exception(error)

    def _write_crash_report(self, error: Exception) -> None:
        report = self.paths.logs / f"crash-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.log"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            "\n".join([
                f"version: {__version__}",
                f"python: {sys.version}",
                f"platform: {platform.platform()}",
                f"frozen: {getattr(sys, 'frozen', False)}",
                f"terminal: {os.environ.get('TERM_PROGRAM', '?')} TERM={os.environ.get('TERM')}",
                f"size: {self.size}",
                f"theme: {self.theme}",
                "",
                "".join(traceback.format_exception(error)),
            ]),
            encoding="utf-8",
        )
```

Redact aggressively: no tokens, no file contents, no environment dump. Tell the user where
the report is (`self.notify(...)` will not survive a crash, so print the path on exit) and
make it trivially attachable to an issue. Pair it with `textual diagnose` output.

### 24.8 Profiling

```bash
# Where is the time going at import?
python -X importtime -m nocturne 2>&1 | sort -k2 -n -r | head -25

# Where is the time going at runtime? (run, interact, quit)
python -m cProfile -o profile.out -m nocturne
python -c "import pstats; pstats.Stats('profile.out').sort_stats('cumulative').print_stats(30)"

# Sampling profiler — best for a live TUI, no instrumentation overhead
pip install py-spy
py-spy top --pid $(pgrep -f nocturne)
py-spy record -o flame.svg --pid $(pgrep -f nocturne)
```

In a Textual app the usual culprits, in order: a blocking call in a handler; `render_line`
doing work that should be cached; too-frequent `refresh()`; an un-throttled
`call_from_thread`; a `set_interval` that is too fast; and auto-width measurement on a large
`DataTable`.

### 24.9 CI configuration

```yaml
# .github/workflows/test.yml
name: test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --all-extras
      - run: uv run ruff check .
      - run: uv run mypy src
      - run: uv run pytest -q
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: snapshot-report-${{ matrix.python }}
          path: snapshot_report.html
```

Textual apps test cleanly headless, so no `xvfb` or terminal emulation is needed. Uploading
the snapshot report on failure is what makes snapshot tests tolerable in CI.

---

## 25. Accessibility, i18n and UX polish

### 25.1 Accessibility

Terminal apps are used with screen readers (NVDA/JAWS reading Windows Terminal, VoiceOver
reading Terminal.app, Orca on Linux), on 16-colour terminals, at 200% font size (= a 40×12
grid), and by people who cannot distinguish red from green.

- **Never rely on colour alone.** Every colour-coded state gets a glyph or text style too.
  Test by exporting with `NO_COLOR=1` and by styling `Screen:nocolor`.
- **Keyboard-complete.** Every mouse action has a key path. Check with
  `screen.focus_chain` that every interactive widget is reachable by `tab`.
- **Visible focus.** `:focus` must change something structural (border style), not only hue.
- **Respect `TEXTUAL_ANIMATIONS`** and `NO_COLOR`.
- **Survive small terminals.** Design for 80×24; use breakpoints to drop panels below that.
  Test `await pilot.resize_terminal(40, 12)` in CI.
- **Avoid blink** (`text-style: blink`): it is a seizure risk and most terminals ignore it.
- **Screen-reader mode:** a settings flag that disables animation, disables the mouse, puts
  one widget per line and announces state changes via plain text in a status region. This is
  cheap to build if your `domain/` layer is clean, and it is the difference between usable
  and unusable for some users.
- **High-contrast theme:** register one with `luminosity_spread` near 0 and maximum contrast
  text, and surface it in the theme list.

```python
HIGH_CONTRAST = Theme(
    name="high-contrast", dark=True,
    primary="#FFFFFF", secondary="#FFFF00", accent="#00FFFF",
    foreground="#FFFFFF", background="#000000", surface="#000000", panel="#1A1A1A",
    success="#00FF00", warning="#FFFF00", error="#FF4444",
    luminosity_spread=0.05, text_alpha=1.0,
)
```

### 25.2 Internationalisation

```python
import gettext
from pathlib import Path

def install_translations(locale_dir: Path, language: str | None = None) -> None:
    translation = gettext.translation(
        "nocturne", localedir=locale_dir,
        languages=[language] if language else None, fallback=True,
    )
    translation.install()          # provides the global _()
```

TUI-specific i18n constraints:

1. **Translated strings change width.** German is routinely 30% longer than English, and
   CJK is double-width. Never size a widget to fit an English string — use `auto`, `1fr`,
   `min-width`, and `text-overflow: ellipsis`.
2. **Keyboard mnemonics do not translate.** Bind to keys, not to letters-in-words.
3. **Dates, numbers and sorting** go through `locale`/`babel`, not f-strings.
4. **RTL is effectively unsupported** in terminals. If you must support Arabic or Hebrew,
   expect to render right-aligned LTR and accept the compromise.
5. Mark up everything, including validator failure descriptions and notification text.

### 25.3 UX polish that users notice

- **Instant first paint.** `lazy.Lazy`/`Reveal`, and never block `on_mount`.
- **Optimistic UI.** Apply the change immediately, revert with a toast if the write fails.
- **Undo.** A small command stack costs little and transforms trust in a destructive tool.
- **Empty states.** Never show a blank panel: say what it will hold and how to fill it.
- **Error messages with a next step.** "Connection refused — is the service running on
  :5432? Press `e` to edit the connection."
- **Persist what the user arranged**: panel widths, sort order, last-opened, theme, scroll
  position. Put it in `user_state_dir`.
- **Clipboard support** for anything the user may want elsewhere
  (`self.copy_to_clipboard(text)` uses OSC 52, so it works over SSH).
- **Text selection** works by default in Textual 8.x (`ALLOW_SELECT`, `TextSelected`); do
  not disable it unless the widget is a canvas.
- **A status line** showing what the app is doing right now (worker counts, connection
  state). Users forgive slowness they can see.
- **Resize gracefully.** Test at 40×12 and 300×100.
- **Honour `ctrl+c`.** Textual binds it to `help_quit`, which tells the user the real quit
  key rather than exiting mid-write — good default, but make sure your own `quit` action
  flushes pending saves.

---

## 26. Performance playbook

### 26.1 The budget

At 60 fps you have **16.6 ms** per frame for everything: event handling, layout, rendering
and the write to the terminal. Practical targets:

| Operation | Target |
|---|---|
| Keystroke → visible response | < 50 ms |
| `render_line` for one line | < 0.1 ms |
| A message handler | < 2 ms |
| `set_interval` callback | < 2 ms |
| First paint | < 100 ms |
| Process start → first paint (frozen) | < 600 ms |

### 26.2 Diagnosing

1. Run with `--dev` and watch for slow-callback warnings
   (`TEXTUAL_SLOW_THRESHOLD=100` to tighten).
2. `py-spy top` on the live process: if `select`/`epoll` dominates, you are idle-healthy; if
   your own functions dominate, you have a hot path.
3. `python -X importtime` for startup.
4. Count messages with `message_hook` in a test — unexpected message storms are a common
   cause of jank.

### 26.3 The fixes, ranked by impact

1. **Move blocking work off the loop** (§21). Nothing else matters until this is true.
2. **Throttle updates to ≤ 30 Hz** and wrap bulk changes in `App.batch_update()`.
3. **Use `reactive(..., repaint=True)` rather than `layout=True`** unless geometry really
   changed. A relayout is an order of magnitude more expensive than a repaint.
4. **Virtualise.** `render_line` + `virtual_size` instead of thousands of child widgets.
   A `ScrollView` over 6,400 logical rows renders in viewport time — verified.
5. **Cache in `render_line`,** keyed on `(width, state)`.
6. **Prefer `Static`/`Label` over custom `render()`** for text that rarely changes.
7. **Set explicit widths/heights** where you can; `auto` forces measurement.
8. **Avoid deep DOMs.** 2,000 widgets costs real time in style resolution; prefer one
   line-API widget over 500 small ones.
9. **`lazy.Lazy`** for off-screen tab content.
10. **Pause hidden work** (`on_screen_suspend`, `on_hide`).
11. **Narrow your CSS selectors.** `#id .class` beats `* > *`.
12. **Lower the frame cap** for a remote/SSH session: `TEXTUAL_FPS=30` halves the bytes on
    the wire and is usually imperceptible.

### 26.4 Textual's own recent performance work (8.x)

Worth knowing because it changes what you need to do yourself:

- 7.0.3 / 7.1.0 — large scrollable container rendering improved; `Widget.BLANK` added to
  skip work for empty regions.
- 8.0.1 — `DirectoryTree` scanning moved to a thread (no more micro-freezes on slow mounts).
- 8.1.0 — circular DOM references replaced with weak references, improving GC behaviour;
  experimental `App.PAUSE_GC_ON_SCROLL`.
- 8.2.2 / 8.2.3 — resize made far cheaper (fewer style updates, timer-driven rather than
  idle-driven).

If you are on Textual 6.x or earlier and fighting scroll performance, upgrading is likely
cheaper than optimising.

### 26.5 Memory

- A `DataTable` row costs roughly a few hundred bytes plus the rendered cell cache. 100k
  rows is hundreds of MB — window the data instead.
- `Log`/`RichLog` **must** have `max_lines` set, or tailing a busy file grows without bound.
- Cap your own caches (§22.6) and clear them on `on_unmount`.
- Watch out for closures that capture a widget: a `set_interval(…, lambda: widget.update())`
  on a removed widget keeps it alive. Use bound methods on the widget itself so removal
  cleans up the timer.

---

## 27. Beyond the terminal: web, SSH, inline and embedded

### 27.1 Serving over HTTP

```bash
pip install textual-serve
textual serve "python -m nocturne"
textual serve --host 0.0.0.0 --port 8080 "nocturne"
```

```python
from textual_serve.server import Server
Server("python -m nocturne", host="0.0.0.0", port=8080, title="Nocturne").serve()
```

The same app, in a browser, with working mouse, clipboard and file delivery (this is why
`deliver_text`/`deliver_binary` exist). Caveats: put it behind authentication — each
connection spawns a process; images and Kitty-protocol features do not translate; and
`App.suspend()` is meaningless there.

### 27.2 Inline mode

```python
Nocturne().run(inline=True)                 # renders under the shell prompt, no alt-screen
Nocturne().run(inline=True, inline_no_clear=True)   # leave the output in the scrollback
```

Inline mode is excellent for short interactions in a CLI — a picker, a progress dashboard, a
confirm — because the user keeps their scrollback. Style for it with the `:inline`
pseudo-class (hide the footer, shrink the header) and set `App.INLINE_PADDING`.

### 27.3 Over SSH

A Textual app works over SSH with no changes, but:

- Set `TEXTUAL_FPS=30` (or lower) and `TEXTUAL_ANIMATIONS=basic` server-side for high-latency
  links; every frame is bytes on the wire.
- Clipboard works via OSC 52 (`copy_to_clipboard`) where the client allows it.
- Image protocols generally do not survive SSH + tmux. Degrade to half-cell.
- For a multi-user service, `asyncssh` + a per-connection `App` is a known pattern, but you
  must set the terminal size from the SSH PTY request and handle window-change messages.

### 27.4 Embedding a TUI in a CLI

The best CLIs are both: scriptable by default, interactive on request.

```python
def main(argv=None) -> int:
    args = parse(argv)
    if args.json or not sys.stdout.isatty():
        print(json.dumps(run_query(args)))      # pipeline-friendly
        return 0
    from nocturne.app import Nocturne
    return Nocturne(query=args.query).run() or 0
```

`trogon` inverts this: it turns an existing Click CLI into a Textual form-filling UI
automatically, which is a remarkably cheap way to add discoverability to a large CLI.

---
## 28. Appendices

### Appendix A: CSS properties

All 104 style properties exposed by `textual.css.styles.StylesBase` on 8.2.8, grouped.
Scalars accept cells, `%`, `fr`, `auto`, `w`/`h`/`vw`/`vh`. Colours accept hex, `rgb()`,
`hsl()`, names, `$tokens`, `ansi_*`, `auto`, and an optional trailing percentage for alpha.

**Box model**

| Property | Values |
|---|---|
| `width`, `height` | scalar |
| `min-width`, `min-height`, `max-width`, `max-height` | scalar |
| `padding` (`-top/-right/-bottom/-left`) | 1, 2 or 4 integers |
| `margin` (`-top/-right/-bottom/-left`) | 1, 2 or 4 integers |
| `box-sizing` | `border-box` \| `content-box` |
| `offset` (`-x`, `-y`) | two scalars |
| `position` | `relative` \| `absolute` |

**Layout**

| Property | Values |
|---|---|
| `layout` | `vertical` \| `horizontal` \| `grid` \| `stream` |
| `dock` | `top` \| `right` \| `bottom` \| `left` \| `none` |
| `split` | `top` \| `right` \| `bottom` \| `left` (adds a drag handle) |
| `layer` | a layer name |
| `layers` | space-separated layer names (back to front) |
| `align` (`-horizontal`, `-vertical`) | `left\|center\|right`, `top\|middle\|bottom` |
| `content-align` (`-horizontal`, `-vertical`) | same |
| `grid-size` (`-columns`, `-rows`) | integers |
| `grid-columns`, `grid-rows` | scalar list |
| `grid-gutter` (`-horizontal`, `-vertical`) | integers |
| `column-span`, `row-span` | integers |
| `keyline` | `none\|thin\|heavy\|double` + colour |
| `overlay` | `none` \| `screen` |
| `constrain-x`, `constrain-y` | `none` \| `inside` \| `inflect` |
| `expand` | `greedy` \| `optimal` |
| `display` | `block` \| `none` |
| `visibility` | `visible` \| `hidden` |

**Colour and surface**

| Property | Values |
|---|---|
| `color`, `auto-color` | colour / bool |
| `background` | colour (+ alpha) |
| `background-tint` | colour blended over the resolved background |
| `tint` | colour blended over the whole widget |
| `opacity` | fraction / percentage |
| `text-opacity` | fraction / percentage |
| `hatch` | `cross\|horizontal\|left\|right\|vertical` + colour (+ alpha) |

**Borders and outlines**

| Property | Values |
|---|---|
| `border` (`-top/-right/-bottom/-left`) | style + colour |
| `outline` (`-top/-right/-bottom/-left`) | style + colour |
| `border-title-align`, `border-subtitle-align` | `left\|center\|right` |
| `border-title-color`, `border-subtitle-color` | colour |
| `border-title-background`, `border-subtitle-background` | colour |
| `border-title-style`, `border-subtitle-style` | style flags |
| `auto-border-title-color`, `auto-border-subtitle-color` | bool |

Border styles: `ascii, blank, block, dashed, double, heavy, hidden, hkey, inner, none,
outer, panel, round, solid, tab, tall, thick, vkey, wide`.

**Text**

| Property | Values |
|---|---|
| `text-style` | `b, bold, i, italic, u, underline, uu, o, overline, strike, reverse, dim, blink, none, not <flag>` |
| `text-align` | `left, center, right, justify, start, end` |
| `text-wrap` | `wrap` \| `nowrap` |
| `text-overflow` | `clip` \| `ellipsis` \| `fold` |
| `line-pad` | integer (extra cells each side of a line) |

**Scrolling**

| Property | Values |
|---|---|
| `overflow-x`, `overflow-y` | `auto` \| `hidden` \| `scroll` |
| `scrollbar-size-horizontal`, `scrollbar-size-vertical` | integers |
| `scrollbar-gutter` | `auto` \| `stable` |
| `scrollbar-visibility` | `visible` \| `hidden` |
| `scrollbar-color`, `-hover`, `-active` | colour |
| `scrollbar-background`, `-hover`, `-active` | colour |
| `scrollbar-corner-color` | colour |

**Links (inside text content)**

`link-color`, `link-background`, `link-style`, `link-color-hover`,
`link-background-hover`, `link-style-hover`, `auto-link-color`, `auto-link-color-hover`.

**Interaction and motion**

| Property | Values |
|---|---|
| `transition` | `<property> <duration> <easing> [<delay>]`, comma-separated |
| `pointer` | `alias, cell, copy, crosshair, default, e-resize, ew-resize, grab, grabbing, help, move, n-resize, ne-resize, nesw-resize, no-drop, not-allowed, ns-resize, nw-resize, nwse-resize, pointer, progress, s-resize, se-resize, sw-resize, text, vertical-text, w-resize, wait, zoom-in, zoom-out` |

Pseudo-classes: `:ansi, :blur, :can-focus, :dark, :disabled, :empty, :enabled, :even,
:first-child, :first-of-type, :focus, :focus-within, :hover, :inline, :last-child,
:last-of-type, :light, :nocolor, :odd`.

### Appendix B: design tokens

The default theme generates 168 variables. The families (every core and neutral colour also
gets `-lighten-1/2/3`, `-darken-1/2/3` and `-muted`):

**Semantic colours** `$primary $secondary $accent $success $warning $error`
**Neutrals** `$background $surface $surface-active $panel $boost $foreground`
**Contrast text** `$text $text-muted $text-disabled $text-primary $text-secondary
$text-success $text-warning $text-error $text-accent`
**Foreground variants** `$foreground-muted $foreground-disabled`
**Borders** `$border $border-blurred`
**Block cursor** `$block-cursor-foreground $block-cursor-background
$block-cursor-text-style $block-cursor-blurred-foreground
$block-cursor-blurred-background $block-cursor-blurred-text-style
$block-hover-background`
**Inputs** `$input-cursor-foreground $input-cursor-background $input-cursor-text-style
$input-selection-foreground $input-selection-background`
**Buttons** `$button-foreground $button-color-foreground $button-focus-text-style`
**Footer** `$footer-foreground $footer-background $footer-key-foreground
$footer-key-background $footer-item-background $footer-description-foreground
$footer-description-background`
**Scrollbars** `$scrollbar $scrollbar-hover $scrollbar-active $scrollbar-background
$scrollbar-background-hover $scrollbar-background-active $scrollbar-corner-color`
**Links** `$link-color $link-background $link-style $link-color-hover
$link-background-hover $link-style-hover`
**Markdown headings** `$markdown-h1-color/-background/-text-style` … `h6`
**Selection** `$screen-selection-foreground $screen-selection-background`
**ANSI mode** `$ansi-foreground $ansi-background`

Print them at runtime for the active theme:

```python
for name, value in sorted(app.get_css_variables().items()):
    print(f"${name} = {value}")
```

### Appendix C: component classes

| Widget | Component classes |
|---|---|
| `Checkbox`, `RadioButton` | `toggle--button`, `toggle--label` |
| `DataTable` | `datatable--cursor`, `datatable--even-row`, `datatable--fixed`, `datatable--fixed-cursor`, `datatable--header`, `datatable--header-cursor`, `datatable--header-hover`, `datatable--hover`, `datatable--odd-row` |
| `DirectoryTree` | `directory-tree--extension`, `directory-tree--file`, `directory-tree--folder`, `directory-tree--hidden` |
| `Input`, `MaskedInput` | `input--cursor`, `input--placeholder`, `input--selection`, `input--suggestion` |
| `OptionList` | `option-list--option`, `option-list--option-disabled`, `option-list--option-highlighted`, `option-list--option-hover`, `option-list--separator` |
| `SelectionList` | `selection-list--button`, `selection-list--button-highlighted`, `selection-list--button-selected`, `selection-list--button-selected-highlighted` |
| `Sparkline` | `sparkline--max-color`, `sparkline--min-color` |
| `Switch` | `switch--slider` |
| `TextArea` | `text-area--cursor`, `text-area--cursor-gutter`, `text-area--cursor-line`, `text-area--gutter`, `text-area--matching-bracket`, `text-area--placeholder`, `text-area--selection`, `text-area--suggestion` |
| `Tree` | `tree--cursor`, `tree--guides`, `tree--guides-hover`, `tree--guides-selected`, `tree--highlight`, `tree--highlight-line`, `tree--label` |

### Appendix D: events

All 43 classes in `textual.events` on 8.2.8:

**Lifecycle** `Load`, `Compose`, `Mount`, `Unmount`, `Ready`, `Show`, `Hide`, `Resize`,
`ScreenSuspend`, `ScreenResume`, `AppBlur`, `AppFocus`

**Focus** `Focus`, `Blur`, `DescendantFocus`, `DescendantBlur`

**Keyboard** `Key`, `InputEvent`, `Paste`, `CursorPosition`

**Mouse** `MouseEvent`, `MouseDown`, `MouseUp`, `MouseMove`, `Click`, `Enter`, `Leave`,
`MouseCapture`, `MouseRelease`, `MouseScrollUp`, `MouseScrollDown`, `MouseScrollLeft`,
`MouseScrollRight`

**Selection** `TextSelected`

**System** `Idle`, `Timer`, `Callback`, `Action`, `Print`, `Event`, `Message`

**File delivery** `DeliveryComplete`, `DeliveryFailed`

### Appendix E: ecosystem libraries

**Read this first.** Third-party Textual widgets frequently pin a narrow Textual range.
Verified example: installing `textual-pandas` 0.2.3 (which requires `textual<4.0,>=1.0`)
into an environment with Textual 8.2.8 **silently downgraded Textual to 3.7.1**, breaking
everything built against 8.x. Always:

```bash
pip install textual-widget-x --dry-run        # inspect the resolution first
pip check                                     # after install, look for conflicts
```

and prefer `uv`/Poetry with an explicit `textual = "^8.2"` constraint so the resolver fails
loudly instead of downgrading.

**Compatibility verified against Textual 8.2.8 while writing this guide** (installed, imported
and exercised in a running app): `textual-fspicker` 1.0.1, `textual-autocomplete` 4.0.6,
`textual-plotext` 1.0.1, `textual-image` 0.12.0, `textual-slider` 0.2.0, `rich-pixels` 3.0.1.
**Not compatible with 8.x at time of writing:** `textual-pandas` 0.2.3 (`textual<4.0`).

**Official (Textualize)**

| Package | Purpose |
|---|---|
| `textual-dev` | devtools: console, `run --dev`, `borders`, `colors`, `easing`, `keys`, `diagnose`, `serve` |
| `pytest-textual-snapshot` | SVG snapshot testing |
| `textual-serve` | serve an app over HTTP |
| `textual-plotext` | Plotext charts as a widget |

**Widgets and components**

| Package | Purpose |
|---|---|
| `textual-fspicker` | modal file-open / file-save / select-directory dialogs |
| `textual-autocomplete` | dropdown autocomplete + `PathAutoComplete` |
| `textual-image` | images via Kitty graphics protocol, Sixel, half-cell, unicode |
| `rich-pixels` | images as a Rich renderable |
| `textual-imageview` | image viewer widget and app |
| `textual-pdf` | PDF preview (on `textual-image`) |
| `textual-slider` | slider / range input |
| `textual-spinbox` | numeric spinbox |
| `textual-datepicker`, `textual-timepiece` | date, time, timeline widgets |
| `textual-colorpicker`, `RichColorPicker` | colour pickers |
| `textual-canvas`, `textual-hires-canvas` | character / braille drawing canvases |
| `textual-plot` | native plotting with zoom and pan |
| `textual-window` | floating draggable windows + window bar |
| `textual-slidecontainer` | sliding drawer containers |
| `textual-tags` | tag chips |
| `textual-filedrop` | drag-and-drop file target |
| `textual-terminal` | an embedded terminal emulator widget |
| `textual-universal-directorytree` | `DirectoryTree` over remote filesystems (S3, SSH, …) |
| `textual-pyfiglet` | figlet banners with colour and animation |
| `textual-coloromatic` | animated gradient / tiled backgrounds |
| `textual-effects` | transition effects (blinds, curtains, fire, Matrix) |
| `textual-qrcode` | QR code widget |
| `textual-astview` | Python AST explorer widget |
| `textual-pandas` | DataFrame display (pins `textual<4`) |
| `tuilwindcss` | Tailwind-inspired utility classes for TCSS |

**Adjacent**

| Package | Purpose |
|---|---|
| `trogon` | turn a Click CLI into a Textual UI automatically |
| `rich` | renderables, tables, progress, syntax, tracebacks |
| `prompt_toolkit` | line editing, REPLs, completers |
| `questionary` | quick prompt flows |
| `plotext` | terminal plotting (non-widget) |
| `pyfiglet`, `art` | ASCII banners |
| `platformdirs` | app-data paths |
| `keyring` | OS credential stores |
| `typer`, `click`, `cyclopts` | CLI front ends |

**Apps worth reading the source of**

`Harlequin` (SQL IDE), `Posting` (API client), `toolong` (log viewer), `Dolphie`
(MySQL monitor), `Memray`/`Flameshow` (profiler viewers), `Frogmouth` (Markdown browser),
`Elia` (LLM chat), `kaskade` (Kafka), `browsr` / `kupo` / `rovr` (file explorers),
`hexabyte` (hex editor), `Dooit` (todo), `tiptop` (system monitor), `Spiel` (presentations),
`textual-paint` (MS Paint clone — an education in custom rendering).

### Appendix F: Rich spinners

All 73 names in `rich.spinner.SPINNERS` — useful as ready-made frame sets even outside Rich:

`aesthetic, arc, arrow, arrow2, arrow3, balloon, balloon2, betaWave, bounce, bouncingBall,
bouncingBar, boxBounce, boxBounce2, christmas, circle, circleHalves, circleQuarters, clock,
dots, dots2, dots3, dots4, dots5, dots6, dots7, dots8, dots8Bit, dots9, dots10, dots11,
dots12, dqpb, earth, flip, grenade, growHorizontal, growVertical, hamburger, hearts, layer,
line, line2, material, monkey, moon, noise, pipe, point, pong, runner, shark, simpleDots,
simpleDotsScrolling, smiley, squareCorners, squish, star, star2, toggle, toggle2, toggle3,
toggle4, toggle5, toggle6, toggle7, toggle8, toggle9, toggle10, toggle11, toggle12,
toggle13, triangle, weather`

```python
from rich.spinner import SPINNERS
frames = SPINNERS["dots12"]["frames"]
interval_ms = SPINNERS["dots12"]["interval"]
```

### Appendix G: key names

Textual normalises keys to 152 names. Printable characters arrive as themselves (`a`, `A`,
`1`, `!`), with these special names available in `BINDINGS`:

**Navigation** `up, down, left, right, home, end, pageup, pagedown, insert, delete,
backspace, tab, shift+tab, enter, return, escape, space`

**Function** `f1`–`f24` (plus `ctrl+f1`–`ctrl+f24`)

**Modified** `ctrl+a`–`ctrl+z`, `ctrl+0`–`ctrl+9`, `ctrl+shift+0`–`ctrl+shift+9`,
`ctrl+left/right/up/down`, `ctrl+home/end/insert/delete`, `ctrl+pageup/pagedown`,
`shift+left/right/up/down`, `shift+home/end/insert/delete`, `shift+pageup/pagedown`,
`shift+escape`, `ctrl+shift+left/right/up/down`, `ctrl+shift+home/end`,
`ctrl+shift+pageup/pagedown`, `ctrl+shift+insert/delete`

**Punctuation control codes** `ctrl+@`, `ctrl+backslash`, `ctrl+right_square_bracket`,
`ctrl+circumflex_accent`, `ctrl+underscore`

Notes:

- `ctrl+m` **is** `enter` and `ctrl+i` **is** `tab` on terminals without the Kitty keyboard
  protocol — the control codes are identical. Do not bind both.
- `ctrl+c` is bound by Textual to `help_quit`; `ctrl+q` quits.
- Run `textual keys` to see exactly what your terminal sends.
- `super+…` (cmd on macOS) is reported only by terminals that support it; Textual 8.2.7 maps
  `super+c/x/v/z/y` for clipboard and undo where available. Never make it the only binding.
- `ESCDELAY` (default 100 ms) is how long Textual waits to decide whether an `escape` is a
  lone key or the start of a sequence.

### Appendix H: widget message reference

| Widget | Messages |
|---|---|
| `Button` | `Pressed` |
| `Checkbox`, `RadioButton` | `Changed` |
| `RadioSet` | `Changed` |
| `Switch` | `Changed` |
| `Input`, `MaskedInput` | `Changed`, `Submitted`, `Blurred` |
| `TextArea` | `Changed`, `SelectionChanged` |
| `Select` | `Changed` |
| `OptionList` | `OptionMessage`, `OptionHighlighted`, `OptionSelected` |
| `SelectionList` | `SelectionMessage`, `SelectionHighlighted`, `SelectionToggled`, `SelectedChanged` |
| `ListView` | `Highlighted`, `Selected` |
| `DataTable` | `CellHighlighted`, `CellSelected`, `RowHighlighted`, `RowSelected`, `ColumnHighlighted`, `ColumnSelected`, `HeaderSelected`, `RowLabelSelected` |
| `Tree` | `NodeExpanded`, `NodeCollapsed`, `NodeHighlighted`, `NodeSelected` |
| `DirectoryTree` | `FileSelected`, `DirectorySelected` (+ all `Tree` messages) |
| `Collapsible` | `Toggled`, `Expanded`, `Collapsed` |
| `Tabs` | `TabActivated`, `TabDisabled`, `TabEnabled`, `TabHidden`, `TabShown`, `Cleared` |
| `TabbedContent` | `TabActivated`, `Cleared` |
| `TabPane` | `Disabled`, `Enabled`, `Focused` |
| `Tab` | `Clicked`, `Disabled`, `Enabled`, `Relabelled` |
| `Markdown` | `TableOfContentsUpdated`, `TableOfContentsSelected`, `LinkClicked` |
| `MarkdownViewer` | `NavigatorUpdated` |
| `Worker` (not a widget) | `StateChanged` |

Every one of these is a nested class: handle with `@on(DataTable.RowSelected)` and access
the originating widget through the message's `.control` property (or the specifically named
attribute, e.g. `event.data_table`, `event.input`, `event.selection_list`).

### Appendix I: quick-start skeleton

A minimal but correctly structured app with everything wired: resource paths, app-data,
settings, logging, workers, theme, command palette, footer and a smoke-test hook.

```python
# src/nocturne/app.py
from __future__ import annotations

import asyncio
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Input, Static

from nocturne.paths import Paths, resource_path
from nocturne.settings import Settings
from nocturne.themes import ARCTIC
from nocturne.commands import FileCommands
from nocturne.concurrency import Debouncer, shutdown_process_pool


class Nocturne(App[int]):
    TITLE = "Nocturne"
    CSS_PATH = [resource_path("styles/base.tcss")]
    COMMANDS = App.COMMANDS | {FileCommands}
    HORIZONTAL_BREAKPOINTS = [(0, "-narrow"), (100, "-normal"), (140, "-wide")]
    BINDINGS = [
        Binding("ctrl+r", "reload", "Reload", id="app.reload", priority=True),
        Binding("slash", "focus('#search')", "Search", id="app.search"),
        Binding("f1", "show_help_panel", "Help", id="app.help"),
    ]

    status: reactive[str] = reactive("ready")

    def __init__(self, path: Path | None = None) -> None:
        super().__init__()
        self.paths = Paths.resolve().ensure()
        self.settings = Settings.load(self.paths.config / "settings.json")
        self.target = path or Path.cwd()
        self._search_debounce: Debouncer | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, icon="❄")
        with Horizontal():
            with VerticalScroll(id="sidebar"):
                yield Input(placeholder="search…", id="search")
                yield Static(id="facets")
            yield DataTable(id="rows", cursor_type="row", zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(ARCTIC)
        self.theme = self.settings.theme
        self.set_keymap(self.settings.keymap)
        self._search_debounce = Debouncer(0.2)
        self.query_one("#rows", DataTable).add_columns("when", "level", "message")
        self.load()

    def watch_status(self, status: str) -> None:
        self.sub_title = status

    @work(exclusive=True, group="io", thread=True)
    def load(self) -> None:
        rows = list(read_rows(self.target))                 # blocking, on a thread
        self.call_from_thread(self._apply, rows)

    def _apply(self, rows: list[tuple[str, str, str]]) -> None:
        table = self.query_one("#rows", DataTable)
        with self.batch_update():
            table.clear()
            table.add_rows(rows)
        self.status = f"{len(rows)} rows"

    @on(Input.Changed, "#search")
    def _typed(self, event: Input.Changed) -> None:
        self._debounce_search(event.value)

    def _debounce_search(self, text: str) -> None:
        assert self._search_debounce is not None
        self._search_debounce(lambda: self.filter_rows(text))

    @work(exclusive=True, group="query")
    async def filter_rows(self, text: str) -> None:
        await asyncio.sleep(0)                              # yield to the UI
        ...

    def action_reload(self) -> None:
        self.load()

    def on_unmount(self) -> None:
        self.settings.theme = self.theme
        self.settings.save(self.paths.config / "settings.json")
        shutdown_process_pool()
```

```python
# src/nocturne/__main__.py
import multiprocessing, sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from nocturne.cli import main
    sys.exit(main())
```

### Appendix J: the master checklist

**Architecture**
- [ ] `domain/` has no `textual` imports and is unit-tested
- [ ] `textual` pinned to a major version
- [ ] CLI does not import the TUI unless it needs to
- [ ] One `resource_path()` and one `Paths` resolver, used everywhere

**UI**
- [ ] No hard-coded colours; everything is a `$token`
- [ ] `Footer` on every screen; every action in the command palette
- [ ] Focus visible via structure, not just hue
- [ ] Works at 80×24 and at 40×12 (breakpoints tested)
- [ ] Works with `NO_COLOR=1` and with the `ansi-dark` theme
- [ ] Icons degrade: nerd → unicode → ASCII
- [ ] All animation passes `level=` and respects `TEXTUAL_ANIMATIONS`
- [ ] Empty states and error states are designed, not blank

**Concurrency**
- [ ] No blocking call in any handler
- [ ] Search-as-you-type: debounce + `@work(exclusive=True)`
- [ ] Thread workers poll `is_cancelled`; UI touched only via `call_from_thread`/`post_message`
- [ ] UI updates throttled ≤ 30 Hz, bulk changes in `batch_update()`
- [ ] Fan-out bounded; queues bounded
- [ ] CPU work in a process pool of `cpu_count() - 1`
- [ ] Everything shut down in `on_unmount`; hidden screens paused

**Data**
- [ ] `platformdirs` for every path; nothing in `~/.myapp`
- [ ] Atomic writes with `fsync` + `os.replace`
- [ ] `schema_version` and a `migrate()` from day one
- [ ] Corrupt config falls back to defaults without crashing
- [ ] SQLite in WAL mode, accessed from workers only
- [ ] Caches have a byte budget and a "Clear cache" command
- [ ] Secrets in the OS keychain or an env var, never in config
- [ ] Rotating file logs; no `StreamHandler`

**Packaging**
- [ ] `--add-data` for assets; `--collect-data textual`; tree-sitter grammars hidden-imported
- [ ] `console=True`; `freeze_support()` first
- [ ] Clean build venv; excludes audited; no UPX
- [ ] Multi-size `.ico`/`.icns`/PNGs from one master; `.desktop` with `Terminal=true`
- [ ] Signed (and notarised on macOS)
- [ ] CI launches the built bundle on every platform

**Quality**
- [ ] Pilot tests for the critical flows
- [ ] Snapshot tests for the key screens
- [ ] `textual diagnose` output requested in the issue template
- [ ] Crash reports written to the log directory, redacted
- [ ] Startup profiled with `-X importtime`; runtime with `py-spy`

---

## Sources

Primary verification was done against the installed packages themselves (introspection of
`textual` 8.2.8, `rich` 15.0.0, `platformdirs` 4.12.3, `prompt_toolkit` 3.0.53,
`questionary` 2.1.1, `pyinstaller` 6.22.3 and the widget libraries listed in Appendix E),
plus executed code: Textual `run_test`/`Pilot` runs, `pytest-textual-snapshot` runs, and
four PyInstaller builds that were launched and smoke-tested.

Documentary sources consulted:

- [Textual CHANGELOG](https://raw.githubusercontent.com/Textualize/textual/main/CHANGELOG.md) — release history and breaking changes for 6.11 → 8.2.8
- [Textual documentation](https://textual.textualize.io/) — framework guide and widget gallery
- [Textual on GitHub](https://github.com/Textualize/textual)
- [transcendent-textual](https://github.com/stuidev/transcendent-textual) — the community inventory of Textual libraries and applications
- [Rich documentation](https://rich.readthedocs.io/)
- [PyInstaller run-time information](https://pyinstaller.org/en/stable/runtime-information.html) — `sys.frozen`, `sys._MEIPASS`
- [PyInstaller spec files](https://pyinstaller.org/en/stable/spec-files.html)
- [platformdirs](https://github.com/tox-dev/platformdirs)
- [prompt_toolkit documentation](https://python-prompt-toolkit.readthedocs.io/)
- [Nerd Fonts glyph sets and code points](https://github.com/ryanoasis/nerd-fonts/wiki/Glyph-Sets-and-Code-Points)
- [Kitty graphics protocol](https://sw.kovidgoyal.net/kitty/graphics-protocol/)
- [Kitty keyboard protocol](https://sw.kovidgoyal.net/kitty/keyboard-protocol/)
- [Terminal compatibility matrix](https://tmuxai.dev/terminal-compatibility/) — image/graphics protocol support by terminal
- [Terminal emulator comparison 2026](https://terminaltrove.com/compare/terminals/)
- [Python terminal UI libraries compared (2026)](https://www.pistack.xyz/posts/2026-07-01-python-terminal-ui-libraries-textual-rich-prompt-toolkit-urwid/)
- [awesometui.com — TUI frameworks and libraries](https://awesometui.com/frameworks-libraries)
- [no-color.org](https://no-color.org/) — the `NO_COLOR` convention
