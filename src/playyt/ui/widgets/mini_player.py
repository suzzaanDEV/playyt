"""Mini player widget shown at the bottom."""

from __future__ import annotations

from textual.widget import Widget
from textual.widgets import Static

from ...services.playback import playback


class MiniPlayer(Widget):
    """Compact bottom playback bar reflecting live playback state."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.title_static = Static("No track playing", id="mini-title")
        self.status_static = Static("", id="mini-status")

    def compose(self):
        yield self.title_static
        yield self.status_static

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_display)

    def refresh_display(self) -> None:
        state = playback.get_state()
        if state.video_id is None:
            self.title_static.update("No track playing")
            self.status_static.update("")
            return
        title = state.title or "Unknown"
        channel = state.channel or ""
        pos = self._fmt(state.position)
        dur = self._fmt(state.duration) if state.duration else "?:??"
        vol = state.volume
        marker = ">" if state.playing else "||"
        self.title_static.update(f"{title}  ·  {channel}")
        self.status_static.update(f"{pos} / {dur}   {marker}   {vol}%")

    @staticmethod
    def _fmt(seconds) -> str:
        if seconds is None:
            return "0:00"
        total = int(seconds)
        minutes, secs = divmod(total, 60)
        return f"{minutes}:{secs:02d}"
