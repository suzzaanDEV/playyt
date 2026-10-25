"""Unit tests for PlayYT playback state model."""

from __future__ import annotations

from playyt.models.playback import PlaybackState


def test_playback_state_defaults() -> None:
    state = PlaybackState()
    assert state.playing is False
    assert state.video_id is None
    assert state.title is None
    assert state.volume == 80
    assert state.speed == 1.0
    assert state.shuffle is False
    assert state.repeat == "off"


def test_playback_state_custom() -> None:
    state = PlaybackState(
        playing=True,
        video_id="v1",
        title="Song",
        channel="Artist",
        duration=200,
        position=30.5,
        volume=60,
        speed=1.5,
        shuffle=True,
        repeat="all",
    )
    assert state.playing is True
    assert state.video_id == "v1"
    assert state.title == "Song"
    assert state.channel == "Artist"
    assert state.duration == 200
    assert state.position == 30.5
    assert state.volume == 60
    assert state.speed == 1.5
    assert state.shuffle is True
    assert state.repeat == "all"
