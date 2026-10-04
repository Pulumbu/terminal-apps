"""PortoScan themes. All UI colour comes from tokens defined here."""

from __future__ import annotations

from textual.theme import Theme

MIDNIGHT = Theme(
    name="midnight",
    primary="#56B6C2",
    secondary="#61AFEF",
    accent="#C678DD",
    foreground="#D7DAE0",
    background="#14161F",
    surface="#1C1F2B",
    panel="#242838",
    success="#98C379",
    warning="#E5C07B",
    error="#E06C75",
    dark=True,
    luminosity_spread=0.15,
    text_alpha=0.95,
    variables={
        "footer-key-foreground": "#56B6C2",
        "block-cursor-text-style": "none",
        "state-open": "#98C379",
        "state-closed": "#6B7089",
        "state-filtered": "#E5C07B",
        "state-error": "#E06C75",
    },
)

AMBER_CRT = Theme(
    name="amber-crt",
    primary="#FFB000",
    secondary="#FF8C00",
    accent="#FFD700",
    foreground="#FFCC66",
    background="#0A0600",
    surface="#140D00",
    panel="#1F1600",
    success="#B5E853",
    warning="#FFD700",
    error="#FF5F56",
    dark=True,
    luminosity_spread=0.2,
    text_alpha=1.0,
    variables={
        "footer-key-foreground": "#FFB000",
        "state-open": "#B5E853",
        "state-closed": "#8A6D00",
        "state-filtered": "#FFD700",
        "state-error": "#FF5F56",
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
    panel="#141414",
    success="#00FF00",
    warning="#FFFF00",
    error="#FF4444",
    dark=True,
    luminosity_spread=0.05,
    text_alpha=1.0,
    variables={
        "state-open": "#00FF00",
        "state-closed": "#AAAAAA",
        "state-filtered": "#FFFF00",
        "state-error": "#FF4444",
    },
)

ALL_THEMES = (MIDNIGHT, AMBER_CRT, HIGH_CONTRAST)
