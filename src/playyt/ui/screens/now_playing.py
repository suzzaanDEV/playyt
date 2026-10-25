"""Now Playing screen with a live cassette-reel visualization."""

from __future__ import annotations

from typing import ClassVar

from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static

from ...models.video import Video
from ...services.playback import playback
from ..widgets.cassette import CassetteReels, detect_unicode_support

_CYAN = "bright_cyan"
_GREEN = "bright_green"
_YELLOW = "bright_yellow"
_MUTED = "grey50"
_DIM = "grey35"
_TEXT = "bright_white"


def playback_status(playing: bool, buffering: bool, has_track: bool) -> str:
    """Return the textual playback status shown in the header."""
    if not has_track:
        return "STOPPED"
    if buffering:
        return "BUFFERING"
    if playing:
        return "PLAYING"
    return "PAUSED"


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


def format_progress(
    position: float | None,
    duration: float | None,
    width: int = 80,
    unicode_ok: bool = True,
) -> str:
    """Build a colored progress line; omit the total when it is unknown."""
    pos = format_time(position)
    sep = "·" if unicode_ok else "|"
    if not duration or duration <= 0:
        return f"[{_MUTED}]{pos}[/]  {sep}  duration unknown"

    total = format_time(duration)
    remaining = format_time(max(0.0, duration - (position or 0.0)))
    if width < 36:
        return f"[{_MUTED}]{pos}[/] / [{_TEXT}]{total}[/]  {sep}  -{remaining}"

    bar_width = max(10, min(36, width - 28))
    ratio = min(max((position or 0.0) / duration, 0.0), 1.0)
    played = int(ratio * bar_width)
    fill = "━" if unicode_ok else "="
    empty = "━" if unicode_ok else "-"
    bar = f"[{_CYAN}]{fill * played}[/][{_DIM}]{empty * (bar_width - played)}[/]"
    return f"[{_MUTED}]{pos}[/]  {bar}  [{_TEXT}]{total}[/]  {sep}  -{remaining}"


def format_speed(speed: float) -> str:
    """Format a speed multiplier without trailing noise (1.0x, 1.25x)."""
    if abs(speed - round(speed)) < 0.001:
        return f"{speed:.1f}x"
    return f"{speed:g}x"


def truncate_text(text: str, width: int, unicode_ok: bool = True) -> str:
    """Shorten text to fit, appending an ellipsis that suits the terminal."""
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    ellipsis = "…" if unicode_ok else "..."
    if width <= len(ellipsis):
        return text[:width]
    return text[: width - len(ellipsis)] + ellipsis


class NowPlayingScreen(Screen):
    """Full screen now playing view with live playback state."""

    BINDINGS: ClassVar[list] = [("escape", "close", "Back")]

    CSS = """
    NowPlayingScreen {
        background: #1e1e2e;
        color: #cdd6f4;
    }

    #np-container {
        width: 100%;
        height: 100%;
        padding: 1 2;
        scrollbar-size: 1 1;
    }

    #np-header {
        width: 100%;
        height: 1;
    }

    #np-heading {
        width: 1fr;
        color: #89dceb;
        text-style: bold;
    }

    #np-state {
        width: auto;
        text-align: right;
    }

    #np-track-title {
        width: 100%;
        text-align: center;
        color: #f8f8f2;
        text-style: bold;
    }

    #np-artist,
    #np-source {
        width: 100%;
        text-align: center;
    }

    #np-artist {
        color: #89dceb;
    }

    #np-source {
        color: #cba6f7;
    }

    #np-progress {
        width: 100%;
        text-align: center;
        margin-top: 1;
    }

    #np-controls {
        width: 100%;
        text-align: center;
        margin-top: 1;
    }

    #np-audio {
        width: 100%;
        text-align: center;
        margin-top: 1;
    }

    #np-footer {
        width: 100%;
        text-align: center;
        color: #6c7086;
        margin-top: 1;
    }
    """

    def __init__(self, video: Video | None = None) -> None:
        super().__init__()
        self.video = video
        self._unicode = detect_unicode_support()

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="np-container"):
            with Horizontal(id="np-header"):
                yield Static("NOW PLAYING", id="np-heading")
                yield Static(id="np-state")
            yield CassetteReels(id="np-cassette")
            yield Static(id="np-track-title")
            yield Static(id="np-artist")
            yield Static(id="np-source")
            yield Static(id="np-progress")
            yield Static(id="np-controls")
            yield Static(id="np-audio")
            yield Static(id="np-footer")

    def on_mount(self) -> None:
        self.refresh_display()
        self.set_interval(0.5, self.refresh_display)

    def action_close(self) -> None:
        self.app.pop_screen()

    def on_resize(self, event: events.Resize) -> None:
        self.refresh_display()

    def refresh_display(self) -> None:
        state = playback.get_state()
        width = max(18, self.size.width or 80)

        duration = state.duration
        if duration is None and self.video is not None:
            duration = self.video.duration

        has_track = bool(state.video_id or self.video)
        title = state.title or (self.video.title if self.video else "") or "Nothing playing"
        artist = state.channel or (self.video.channel if self.video else "") or ""
        source = state.source or ("YouTube" if has_track else "")

        status = playback_status(state.playing, state.buffering, has_track)
        self.query_one("#np-state", Static).update(self._status_markup(status))
        self.query_one("#np-cassette", CassetteReels).set_playback(
            playing=state.playing,
            buffering=state.buffering,
        )

        text_width = max(8, width - 6)
        self.query_one("#np-track-title", Static).update(
            self._escape(truncate_text(title, text_width, self._unicode))
        )
        self.query_one("#np-artist", Static).update(
            self._escape(truncate_text(artist, text_width, self._unicode))
        )
        self.query_one("#np-source", Static).update(
            self._escape(truncate_text(source, text_width, self._unicode))
        )

        self.query_one("#np-progress", Static).update(
            format_progress(state.position, duration, width, self._unicode)
        )
        self.query_one("#np-controls", Static).update(
            self._controls_markup(state.playing, state.shuffle, state.repeat, has_track)
        )
        self.query_one("#np-audio", Static).update(
            f"[bold {_CYAN}]- / +[/] volume [{_TEXT}]{state.volume}%[/]     "
            f"[bold {_CYAN}], / .[/] speed [{_TEXT}]{format_speed(state.speed)}[/]"
        )
        self.query_one("#np-footer", Static).update(self._footer_markup())

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("[", "\\[")

    @staticmethod
    def _status_markup(status: str) -> str:
        color = {
            "PLAYING": _GREEN,
            "PAUSED": _YELLOW,
            "BUFFERING": _CYAN,
            "STOPPED": _MUTED,
        }.get(status, _MUTED)
        return f"[bold {color}]{status}[/]"

    @staticmethod
    def _controls_markup(playing: bool, shuffle: bool, repeat: str, has_track: bool) -> str:
        play = "PAUSE" if playing else "PLAY"
        shuffle_label = "ON" if shuffle else "off"
        repeat_label = repeat.upper() if repeat != "off" else "off"
        if not has_track:
            play = "PLAY"
        return (
            f"[bold {_CYAN}]p[/] prev     "
            f"[bold {_CYAN}]space[/] {play}     "
            f"[bold {_CYAN}]n[/] next     "
            f"[bold {_CYAN}]s[/] shuffle {shuffle_label}     "
            f"[bold {_CYAN}]r[/] repeat {repeat_label}"
        )

    def _footer_markup(self) -> str:
        joiner = "  ·  " if self._unicode else "  |  "
        parts = [
            "Esc back",
            "Space play/pause",
            "n / p skip",
            "Left / Right seek",
            "+ / - volume",
            ", / . speed",
            "s / r modes",
            "? help",
        ]
        return joiner.join(parts)
