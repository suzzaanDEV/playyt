"""Custom theme for PlayYT (warm, analog-inspired palette)."""

from __future__ import annotations

from textual.theme import Theme

PLAYYT_THEME = Theme(
    name="playyt-dark",
    primary="#d8a25e",  # Warm amber
    secondary="#cf9aa4",  # Dusty rose
    warning="#e6c384",  # Soft gold
    error="#e07a6f",  # Terracotta
    success="#9fb98f",  # Sage
    foreground="#e9dfd1",  # Warm cream
    background="#171310",  # Espresso
    surface="#221c17",  # Warm charcoal
    panel="#2a221c",
    dark=True,
)
