"""Now Playing screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from ...models.video import Video


class NowPlayingScreen(Screen):
    """Full screen now playing view."""

    def __init__(self, video: Video | None = None) -> None:
        super().__init__()
        self.video = video

    def compose(self) -> ComposeResult:
        with Vertical(id="np-container"):
            yield Static("NOW PLAYING", id="np-title")
            yield Static("")
            yield Static("+----------------------+", id="np-artwork-top")
            yield Static("|      ARTWORK         |", id="np-artwork")
            yield Static("+----------------------+", id="np-artwork-bottom")
            yield Static("")
            yield Static(
                self.video.title if self.video else "No track",
                id="np-title-track",
            )
            yield Static(
                (self.video.channel if self.video else "") or "",
                id="np-artist",
            )
            yield Static("")
            yield Static("0:00  --------------------  0:00", id="np-progress")
            yield Static("")
            yield Static("<<   > / ||   >>", id="np-controls")
            yield Static("")
            yield Static("Shuffle   Repeat", id="np-modes")
            yield Static("")
            yield Static("Volume 80%   Speed 1.0x", id="np-volume-speed")
