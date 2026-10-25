"""Custom theme for PlayYT (colorful Dracula-inspired palette)."""

from __future__ import annotations

from textual.theme import Theme

PLAYYT_THEME = Theme(
    name="playyt-dark",
    primary="#bd93f9",  # Hex - purple
    secondary="#ff79c6",  # Veil - magenta
    warning="#f1fa8c",  # Fang - yellow
    error="#ff5555",  # Blood - red
    success="#50fa7b",  # Wolfsbane - green
    foreground="#f8f8f2",  # Parchment - near white
    background="#282a36",  # Crypt - dark
    surface="#44475a",  # Dracula selection gray
    panel="#44475a",
    dark=True,
)
