"""Help / keyboard shortcuts screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from ...ui.bindings import NAVIGATION_BINDINGS


class HelpScreen(Screen):
    """Keyboard shortcuts reference."""

    def compose(self) -> ComposeResult:
        yield Static("Keyboard Shortcuts", id="help-title")
        yield Static("")
        yield Static("Navigation", classes="section")
        for binding in NAVIGATION_BINDINGS:
            yield Static(f"  {binding.key:<12} {binding.description}")
        yield Static("")
        yield Static("Playback", classes="section")
        yield Static("  Space        Play / pause")
        yield Static("  n / p        Next / previous track")
        yield Static("  Left / Right Seek backward / forward (10s)")
        yield Static("  + / -        Volume up / down")
        yield Static("  s            Shuffle")
        yield Static("  r            Repeat")
        yield Static("  a            Add to queue")
        yield Static("  d            Remove item")
        yield Static("")
        yield Static("App", classes="section")
        yield Static("  /            Search")
        yield Static("  Esc          Back")
        yield Static("  q            Quit")
        yield Static("  ?            Help")
        yield Static("")
        yield Static("Press Esc to return.", id="help-hint")
