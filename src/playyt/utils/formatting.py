"""Small formatting helpers shared by the UI."""

from __future__ import annotations


def format_time(seconds: float | None) -> str:
    """Format seconds as m:ss, or h:mm:ss for long tracks."""
    if seconds is None:
        return "0:00"
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
