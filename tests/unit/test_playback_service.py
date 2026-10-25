"""Tests for playback state refresh and start behavior."""

from __future__ import annotations

from typing import Any

from playyt.services.playback import PlaybackService


class _FakeIPC:
    _connected = True

    def __init__(self, **properties: Any) -> None:
        self.properties: dict[str, Any] = {
            "time-pos": 12.0,
            "duration": 200,
            "pause": False,
            "volume": 70,
            "speed": 1.0,
            "paused-for-cache": False,
            "idle-active": False,
        }
        self.properties.update(properties)
        self.commands: list[tuple[Any, ...]] = []
        self.set_calls: list[tuple[str, Any]] = []

    def command(self, name: str, *args: Any) -> dict[str, str]:
        self.commands.append((name, *args))
        return {"error": "success"}

    def set_property(self, name: str, value: Any) -> dict[str, str]:
        self.set_calls.append((name, value))
        self.properties[name] = value
        return {"error": "success"}

    def get_property(self, name: str) -> Any:
        return self.properties.get(name)


def _service_with(ipc: _FakeIPC) -> PlaybackService:
    service = PlaybackService()
    service.ipc = ipc  # type: ignore[assignment]
    return service


def test_load_starts_unpaused_and_resets_state() -> None:
    ipc = _FakeIPC(pause=True)
    service = _service_with(ipc)

    service.load("https://media", title="Song", channel="Artist")

    assert ("loadfile", "https://media", "replace") in ipc.commands
    assert ("pause", False) in ipc.set_calls
    assert service.state.playing is True
    assert service.state.video_id == "https://media"
    assert service.state.title == "Song"
    assert service.state.channel == "Artist"
    assert service.state.source == "YouTube"
    assert service.state.idle is False
    assert service.state.buffering is False
    assert service.state.pending is False


def test_begin_pending_and_load_clears_it() -> None:
    ipc = _FakeIPC()
    service = _service_with(ipc)
    service.begin_pending()
    assert service.state.pending is True
    service.load("https://media", title="Song")
    assert service.state.pending is False


def test_refresh_state_reports_buffering_and_idle() -> None:
    ipc = _FakeIPC(pause=False, **{"paused-for-cache": True, "idle-active": False})
    service = _service_with(ipc)
    service._refresh_state()
    assert service.state.playing is True
    assert service.state.buffering is True
    assert service.state.idle is False

    ipc.properties.update({"paused-for-cache": False, "idle-active": True})
    service._refresh_state()
    assert service.state.playing is False
    assert service.state.buffering is False
    assert service.state.idle is True


def test_refresh_state_without_mpv_clears_buffering() -> None:
    service = PlaybackService()
    service.state.buffering = True
    service._refresh_state()
    assert service.state.buffering is False
