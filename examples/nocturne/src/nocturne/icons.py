"""Tiered icon sets, so the app looks right without betting on Nerd Fonts."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class IconSet:
    ok: str
    warn: str
    err: str
    info: str
    folder: str
    file: str
    expand: str
    collapse: str
    spinner: tuple[str, ...]


ASCII_ICONS = IconSet(
    ok="[ok]", warn="[!]", err="[x]", info="[i]",
    folder="+", file="-", expand=">", collapse="v",
    spinner=("|", "/", "-", "\\"),
)
UNICODE_ICONS = IconSet(
    ok="✓", warn="⚠", err="✗", info="ℹ",
    folder="▸", file="·", expand="▶", collapse="▼",
    spinner=tuple("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"),
)
NERD_ICONS = IconSet(
    ok="", warn="", err="", info="",
    folder="", file="", expand="", collapse="",
    spinner=UNICODE_ICONS.spinner,
)


def pick_icons(preference: str = "auto") -> IconSet:
    """preference: auto | ascii | unicode | nerd"""
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
