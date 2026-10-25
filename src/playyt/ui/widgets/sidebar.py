"""Sidebar navigation widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView, Static

NAV_ITEMS = [
    ("home", "Home"),
    ("search", "Search"),
    ("queue", "Queue"),
    ("playlists", "Playlists"),
    ("liked", "Liked"),
    ("history", "History"),
    ("subscriptions", "Subscriptions"),
    ("library", "Library"),
    ("account", "Account"),
    ("settings", "Settings"),
]


class Sidebar(Widget):
    """Left-hand navigation sidebar."""

    def compose(self) -> ComposeResult:
        yield Static("PLAYYT", classes="title")
        yield Static("")
        yield VerticalScroll(
            ListView(
                *[ListItem(Label(label), id=key) for key, label in NAV_ITEMS],
                id="nav-list",
            )
        )
