"""Home screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class HomeScreen(Screen):
    """Home screen with recently played and playlists."""

    def compose(self) -> ComposeResult:
        yield Static("Home", id="home-title")
        yield Static("")
        yield Static("Recently Played", classes="section")
        yield Static("(empty)")
        yield Static("")
        yield Static("Your Playlists", classes="section")
        yield Static("(none)")
