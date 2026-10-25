"""Integration-style tests for the async play path in the app."""

from __future__ import annotations

import asyncio
import time

from textual.widgets import Static

import playyt.app as app_module
from playyt.models.video import Video
from playyt.services.playback import playback
from playyt.ui.screens.now_playing import NowPlayingScreen


class _SlowYTDLP:
    def resolve_url(self, video_id: str) -> dict[str, str]:
        time.sleep(0.2)
        return {
            "url": f"https://media/{video_id}",
            "title": "New Track",
            "channel": "New Artist",
        }


class _FailingYTDLP:
    def resolve_url(self, video_id: str) -> dict[str, str]:
        raise RuntimeError("network down")


def _fake_load(url: str, title: str = "", channel: str = "", source: str = "YouTube") -> None:
    playback.state.video_id = url
    playback.state.title = title
    playback.state.channel = channel
    playback.state.source = source
    playback.state.duration = 210
    playback.state.position = 2.0
    playback.state.playing = True
    playback.state.idle = False
    playback.state.pending = False


def _reset_to_previous_track() -> None:
    playback.state.video_id = "old-url"
    playback.state.title = "Old Track"
    playback.state.channel = "Old Artist"
    playback.state.duration = 999
    playback.state.position = 500.0
    playback.state.playing = True
    playback.state.idle = False
    playback.state.pending = False


def _text(screen: NowPlayingScreen, selector: str) -> str:
    return screen.query_one(selector, Static).render().plain


def test_play_video_shows_new_track_while_loading(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "YTDLP", _SlowYTDLP)
    monkeypatch.setattr(playback, "load", _fake_load)
    monkeypatch.setattr(app_module.HistoryRepository, "add", lambda *args, **kwargs: None)

    async def scenario() -> None:
        app = app_module.PlayYTApp()
        _reset_to_previous_track()
        async with app.run_test(size=(90, 32)) as pilot:
            await pilot.pause(0.2)
            app.play_video(Video("new-id", "New Track", "New Artist", 180))
            await pilot.pause(0.05)

            screen = app.screen
            assert isinstance(screen, NowPlayingScreen)
            assert "LOADING" in _text(screen, "#np-state")
            assert "New Track" in _text(screen, "#np-track-title")
            assert "3:00" in _text(screen, "#np-progress")

            for _ in range(30):
                await pilot.pause(0.1)
                if "PLAYING" in _text(screen, "#np-state"):
                    break
            assert "PLAYING" in _text(screen, "#np-state")
            assert "3:30" in _text(screen, "#np-progress")
            assert playback.state.pending is False

    asyncio.run(scenario())


def test_play_video_failure_returns_to_previous_screen(monkeypatch) -> None:
    monkeypatch.setattr(app_module, "YTDLP", _FailingYTDLP)
    monkeypatch.setattr(playback, "load", _fake_load)

    async def scenario() -> None:
        app = app_module.PlayYTApp()
        _reset_to_previous_track()
        async with app.run_test(size=(90, 32)) as pilot:
            await pilot.pause(0.2)
            app.play_video(Video("bad-id", "Bad Track", "Artist", 100))
            for _ in range(30):
                await pilot.pause(0.1)
                if not isinstance(app.screen, NowPlayingScreen):
                    break
            assert not isinstance(app.screen, NowPlayingScreen)
            assert playback.state.pending is False

    asyncio.run(scenario())
