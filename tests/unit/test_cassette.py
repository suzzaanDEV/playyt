"""Tests for the cassette reel renderer and animation lifecycle."""

from __future__ import annotations

import asyncio

from rich.text import Text
from textual.app import App, ComposeResult
from textual.content import Content

from playyt.ui.widgets.cassette import CassetteReels, render_cassette


def _plain_width(line: str) -> int:
    return Text.from_markup(line).cell_len


def test_frames_rotate_but_wrap_around() -> None:
    first = render_cassette(80, frame=0)
    second = render_cassette(80, frame=1)
    wrapped = render_cassette(80, frame=8)
    assert first != second
    assert first == wrapped


def test_left_and_right_reels_counter_rotate() -> None:
    view = render_cassette(80, frame=3)
    assert "bright_cyan" in view
    assert "bright_magenta" in view


def test_ascii_fallback_uses_star_marker() -> None:
    unicode_view = render_cassette(80, frame=0, unicode_ok=True)
    ascii_view = render_cassette(80, frame=0, unicode_ok=False)
    assert "●" in unicode_view
    assert "●" not in ascii_view
    assert "*" in ascii_view


def test_markup_is_valid_at_every_size_and_frame() -> None:
    for width in (10, 18, 22, 30, 44, 80):
        for frame in range(8):
            for unicode_ok in (True, False):
                markup = render_cassette(width, frame, unicode_ok)
                Text.from_markup(markup)
                Content.from_markup(markup)


def test_rendering_fits_available_width() -> None:
    for width in (80, 60, 40, 30, 22, 18, 12):
        lines = render_cassette(width, frame=2).splitlines()
        assert lines
        assert max(_plain_width(line) for line in lines) <= width


def test_width_adapts_layout_size() -> None:
    wide = render_cassette(80, frame=0).splitlines()
    narrow = render_cassette(20, frame=0).splitlines()
    assert len(wide) > len(narrow)


class _CassetteHost(App[None]):
    def compose(self) -> ComposeResult:
        yield CassetteReels()


def test_animation_lifecycle() -> None:
    async def scenario() -> None:
        app = _CassetteHost()
        async with app.run_test(size=(80, 24)) as pilot:
            reels = app.query_one(CassetteReels)

            reels.set_playback(playing=True)
            assert reels.is_animating
            timer = reels._timer
            assert timer is not None

            # Repeated playing updates must not spawn a second timer.
            reels.set_playback(playing=True)
            assert reels._timer is timer

            reels.set_playback(playing=False)
            assert not reels.is_animating

            reels.set_playback(playing=True, buffering=True)
            assert not reels.is_animating

            reels.set_playback(playing=True, buffering=False)
            assert reels.is_animating
            assert reels._timer is timer

            reels.remove()
            await pilot.pause()
            assert reels._timer is None
            assert not reels.is_animating

    asyncio.run(scenario())


def test_widget_re_renders_on_terminal_resize() -> None:
    async def scenario() -> None:
        app = _CassetteHost()
        async with app.run_test(size=(30, 20)) as pilot:
            reels = app.query_one(CassetteReels)
            narrow = reels.render().plain
            await pilot.resize_terminal(80, 24)
            await pilot.pause()
            wide = reels.render().plain
            assert narrow != wide
            assert wide.count("\n") > narrow.count("\n")

    asyncio.run(scenario())
