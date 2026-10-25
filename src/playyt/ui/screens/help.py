"""Help / keyboard shortcuts screen."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static

from ...ui.bindings import NAVIGATION_BINDINGS

_KEY_LABELS = {
    "up": "Up",
    "down": "Down",
    "enter": "Enter",
    "space": "Space",
    "left": "Left",
    "right": "Right",
    "plus": "+",
    "minus": "-",
    "comma": ",",
    "full_stop": ".",
    "escape": "Esc",
    "ctrl+z": "Ctrl+Z",
}


def _key_label(key: str) -> str:
    return _KEY_LABELS.get(key, key)


class HelpScreen(Screen):
    """Keyboard shortcuts reference."""

    BINDINGS: ClassVar[list] = [Binding("escape", "close", "Back")]

    def action_close(self) -> None:
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        yield Static("Keyboard Shortcuts", id="help-title")
        yield Static("")
        yield Static("Navigation", classes="section")
        for binding in NAVIGATION_BINDINGS:
            yield Static(f"  {_key_label(binding.key):<12} {binding.description}")
        yield Static("")
        yield Static("Playback", classes="section")
        yield Static("  Space        Play / pause")
        yield Static("  n / p        Next / previous track")
        yield Static("  Left / Right Seek backward / forward (10s)")
        yield Static("  + / -        Volume up / down")
        yield Static("  , / .        Slower / faster")
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
