"""Tiered state glyphs (handbook section 9.2): nerd -> unicode -> ascii."""

from __future__ import annotations

import os

_UNICODE = {"open": "●", "closed": "·", "filtered": "▲", "error": "✗"}
_ASCII = {"open": "[+]", "closed": "[-]", "filtered": "[?]", "error": "[x]"}


def glyphs(preference: str = "auto") -> dict[str, str]:
    if preference == "ascii":
        return dict(_ASCII)
    if preference in ("unicode", "nerd"):
        return dict(_UNICODE)
    encoding = (os.environ.get("LC_ALL") or os.environ.get("LANG") or "")
    if "UTF-8" not in encoding.upper() and os.name != "nt":
        return dict(_ASCII)
    return dict(_UNICODE)
