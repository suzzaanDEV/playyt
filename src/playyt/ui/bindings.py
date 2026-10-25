"""Keyboard bindings for PlayYT."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Binding:
    key: str
    action: str
    description: str
    show: bool = True


NAVIGATION_BINDINGS: list[Binding] = [
    Binding("up", "cursor_up", "Navigate up"),
    Binding("down", "cursor_down", "Navigate down"),
    Binding("enter", "select", "Select / play"),
    Binding("space", "toggle_playback", "Play / pause"),
    Binding("n", "next_track", "Next track"),
    Binding("p", "previous_track", "Previous track"),
    Binding("a", "add_to_queue", "Add to queue"),
    Binding("d", "remove_item", "Remove"),
    Binding("s", "toggle_shuffle", "Shuffle"),
    Binding("r", "toggle_repeat", "Repeat"),
    Binding("plus", "volume_up", "Volume up"),
    Binding("minus", "volume_down", "Volume down"),
    Binding("left", "seek_backward", "Seek backward"),
    Binding("right", "seek_forward", "Seek forward"),
    Binding("/", "search", "Search"),
    Binding("escape", "back", "Back"),
    Binding("q", "quit", "Quit"),
    Binding("?", "show_help", "Help"),
]
