# PyInstaller spec.  Build with:  pyinstaller --noconfirm nocturne.spec
# ruff: noqa
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

project = Path(SPECPATH)

datas = [
    (str(project / "src/nocturne/styles"), "styles"),
    (str(project / "assets"), "assets"),
]
# Textual ships its tree-sitter highlight queries (.scm) as package data and they
# are NOT collected automatically.
datas += collect_data_files("textual")

# Tree-sitter grammars are imported dynamically by language name, so static
# analysis never sees them. List only the languages you actually offer.
hiddenimports = [
    "tree_sitter",
    "tree_sitter_python",
    "tree_sitter_json",
    "tree_sitter_markdown",
]

excludes = [
    "tkinter", "turtle", "idlelib", "lib2to3", "pydoc_data",
    "test", "unittest", "doctest",
    "PIL", "numpy", "pandas", "matplotlib",
    "setuptools", "pip", "wheel",
    "IPython", "jedi", "sqlalchemy", "aiohttp",
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
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="nocturne",
    console=True,          # a TUI is a console application. Never False.
    debug=False,
    strip=False,
    upx=False,             # UPX breaks code signing and trips AV heuristics
    icon=str(project / "assets/logo.ico") if (project / "assets/logo.ico").exists() else None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="nocturne")
