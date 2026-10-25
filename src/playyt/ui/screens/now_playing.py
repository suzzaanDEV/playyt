"""Now Playing screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from ...models.video import Video
from ...services.playback import playback


class NowPlayingScreen(Screen):
    """Full screen now playing view with live playback state."""

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
            yield Static(id="np-title-track")
            yield Static(id="np-artist")
            yield Static("")
            yield Static(id="np-progress")
            yield Static("")
            yield Static(id="np-controls")
            yield Static("")
            yield Static(id="np-modes")
            yield Static("")
            yield Static(id="np-volume-speed")
            yield Static("")
            yield Static("Press Esc to return to browsing.", id="np-hint")

    def on_mount(self) -> None:
        self.refresh_display()
        self.set_interval(1.0, self.refresh_display)

    def refresh_display(self) -> None:
        state = playback.get_state()
        video = self.video or Video(
            video_id=state.video_id or "",
            title=state.title or "Unknown",
            channel=state.channel or "",
            duration=state.duration,
        )

        self.query_one("#np-title-track", Static).update(video.title or "Unknown")
        self.query_one("#np-artist", Static).update(video.channel or "")

        pos = self._fmt(state.position)
        dur = self._fmt(state.duration) if state.duration else "?:??"
        bar = self._progress_bar(state.position, state.duration)
        self.query_one("#np-progress", Static).update(f"{pos}  {bar}  {dur}")

        marker = "||" if state.playing else ">"
        self.query_one("#np-controls", Static).update(f"  <<   {marker}   >>")

        shuffle = "ON" if state.shuffle else "off"
        repeat = state.repeat.upper() if state.repeat != "off" else "off"
        self.query_one("#np-modes", Static).update(f"  Shuffle: {shuffle}    Repeat: {repeat}")

        self.query_one("#np-volume-speed", Static).update(
            f"  Volume: {state.volume}%    Speed: {state.speed}x"
        )

    @staticmethod
    def _fmt(seconds) -> str:
        if seconds is None:
            return "0:00"
        total = int(seconds)
        minutes, secs = divmod(total, 60)
        return f"{minutes}:{secs:02d}"

    @staticmethod
    def _progress_bar(position, duration, width: int = 20) -> str:
        if not duration or duration <= 0:
            return "-" * width
        played = int((position or 0) / duration * width)
        played = max(0, min(played, width))
        return "=" * played + "-" * (width - played)
