"""Queue screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class QueueScreen(Screen):
    """Playback queue screen."""

    def compose(self) -> ComposeResult:
        yield Static("QUEUE", id="queue-title")
        yield Static("")
        yield Static("(empty)")
