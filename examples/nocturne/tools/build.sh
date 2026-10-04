#!/usr/bin/env bash
# Build a distributable bundle in a clean virtualenv, then prove it runs.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf build dist .build-venv
python -m venv .build-venv
.build-venv/bin/pip install --quiet --upgrade pip
.build-venv/bin/pip install --quiet ".[syntax]" pyinstaller pillow
.build-venv/bin/python tools/make_icons.py
.build-venv/bin/pyinstaller --noconfirm nocturne.spec

echo "--- bundle size"
du -sh dist/nocturne

echo "--- smoke test"
NOCTURNE_SMOKE=1 NOCTURNE_HOME="$(mktemp -d)" ./dist/nocturne/nocturne
