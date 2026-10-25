"""Tests for the Now Playing screen and its formatting helpers."""

from __future__ import annotations

import asyncio

from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Static

from playyt.models.playback import PlaybackState
from playyt.services.playback import playback
from playyt.ui.screens.now_playing import (
    NowPlayingScreen,
    format_progress,
    format_speed,
    format_time,
    playback_status,
    truncate_text,
)
from playyt.ui.widgets.cassette import CassetteReels


def _plain(widget: Static) -> str:
    return widget.render().plain


def test_playback_status_labels() -> None:
    assert playback_status(playing=False, buffering=False, has_track=False) == "STOPPED"
    assert playback_status(playing=True, buffering=False, has_track=True) == "PLAYING"
    assert playback_status(playing=False, buffering=False, has_track=True) == "PAUSED"
    assert playback_status(playing=True, buffering=True, has_track=True) == "BUFFERING"


def test_format_time() -> None:
    assert format_time(None) == "0:00"
    assert format_time(0) == "0:00"
    assert format_time(42.9) == "0:42"
    assert format_time(201) == "3:21"
    assert format_time(3725) == "1:02:05"


def test_format_progress_known_duration() -> None:
    line = format_progress(42, 201, width=80, unicode_ok=True)
    plain = Text.from_markup(line).plain
    assert "0:42" in plain
    assert "3:21" in plain
    assert "-2:39" in plain
    assert "bright_cyan" in line


def test_format_progress_unknown_duration_invents_no_total() -> None:
    line = format_progress(42, None, width=80)
    plain = Text.from_markup(line).plain
    assert "0:42" in plain
    assert "duration unknown" in plain
    assert "3:21" not in plain


def test_format_progress_narrow_uses_compact_form() -> None:
    line = Text.from_markup(format_progress(10, 100, width=24)).plain
    assert "0:10" in line
    assert "1:40" in line
    assert "━" not in line


def test_truncate_text() -> None:
    assert truncate_text("short", 10) == "short"
    assert truncate_text("a very long title", 10, unicode_ok=True) == "a very lo…"
    assert truncate_text("a very long title", 10, unicode_ok=False) == "a very ..."
    assert truncate_text("abc", 0) == ""


def test_format_speed() -> None:
    assert format_speed(1.0) == "1.0x"
    assert format_speed(1.25) == "1.25x"
    assert format_speed(0.75) == "0.75x"


class _ScreenHost(App[None]):
    def compose(self) -> ComposeResult:
        yield Static("host")

    def on_mount(self) -> None:
        self.push_screen(NowPlayingScreen())


def _run_screen(monkeypatch, state: PlaybackState):
    monkeypatch.setattr(playback, "get_state", lambda: state)

    async def scenario() -> None:
        app = _ScreenHost()
        async with app.run_test(size=(80, 30)) as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, NowPlayingScreen)

            state_text = _plain(screen.query_one("#np-state", Static))
            assert "PLAYING" in state_text
            assert "Song Title" in _plain(screen.query_one("#np-track-title", Static))
            assert "Artist" in _plain(screen.query_one("#np-artist", Static))
            assert "YouTube" in _plain(screen.query_one("#np-source", Static))
            assert "1.25x" in _plain(screen.query_one("#np-audio", Static))
            reels = screen.query_one(CassetteReels)
            assert reels.is_animating

            state.playing = False
            screen.refresh_display()
            assert "PAUSED" in _plain(screen.query_one("#np-state", Static))
            assert not reels.is_animating

            state.playing = True
            state.buffering = True
            screen.refresh_display()
            assert "BUFFERING" in _plain(screen.query_one("#np-state", Static))
            assert not reels.is_animating

            state.buffering = False
            screen.refresh_display()
            assert "PLAYING" in _plain(screen.query_one("#np-state", Static))
            assert reels.is_animating

            state.duration = None
            screen.refresh_display()
            progress = screen.query_one("#np-progress", Static).render().plain
            assert "duration unknown" in progress

            state.duration = 200
            state.title = "[LIVE] Song"
            screen.refresh_display()
            title = screen.query_one("#np-track-title", Static).render().plain
            assert "[LIVE] Song" in title

            await pilot.resize_terminal(40, 20)
            await pilot.pause()
            assert "[LIVE] Song" in _plain(screen.query_one("#np-track-title", Static))

            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, NowPlayingScreen)

    asyncio.run(scenario())


def test_now_playing_tracks_playback_state(monkeypatch) -> None:
    state = PlaybackState(
        playing=True,
        video_id="v1",
        title="Song Title",
        channel="Artist",
        duration=200,
        position=25.0,
        volume=55,
        speed=1.25,
        shuffle=False,
        repeat="off",
        source="YouTube",
    )
    _run_screen(monkeypatch, state)
