"""Application themes. Every colour the app uses comes from a token here."""

from __future__ import annotations

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
    luminosity_spread=0.15,
    text_alpha=0.95,
    variables={
        "block-cursor-text-style": "none",
        "footer-key-foreground": "#88C0D0",
        "input-selection-background": "#81a1c1 35%",
        "chart-1": "#88C0D0",
        "chart-2": "#A3BE8C",
        "chart-3": "#EBCB8B",
    },
)

HIGH_CONTRAST = Theme(
    name="high-contrast",
    primary="#FFFFFF",
    secondary="#FFFF00",
    accent="#00FFFF",
    foreground="#FFFFFF",
    background="#000000",
    surface="#000000",
    panel="#1A1A1A",
    success="#00FF00",
    warning="#FFFF00",
    error="#FF4444",
    dark=True,
    luminosity_spread=0.05,
    text_alpha=1.0,
    variables={"chart-1": "#FFFFFF", "chart-2": "#00FF00", "chart-3": "#FFFF00"},
)

ALL_THEMES = (ARCTIC, HIGH_CONTRAST)
