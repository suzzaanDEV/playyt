"""Custom theme for PlayYT."""

from __future__ import annotations

from textual.theme import Theme

PLAYYT_THEME = Theme(
    name="playyt-dark",
    primary="#00d4ff",
    secondary="#b066ff",
    warning="#fbbf24",
    error="#ff4d4d",
    success="#4ade80",
    foreground="#ffffff",
    background="#0f172a",
    surface="#1e293b",
    panel="#1e293b",
    dark=True,
)
