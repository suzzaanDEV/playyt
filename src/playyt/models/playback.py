"""Playback model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlaybackState:
    """Current playback state."""

    playing: bool = False
    video_id: str | None = None
    title: str | None = None
    channel: str | None = None
    duration: int | None = None
    position: float = 0.0
    volume: int = 80
    speed: float = 1.0
    shuffle: bool = False
    repeat: str = "off"
    source: str | None = None
    buffering: bool = False
    idle: bool = False
    pending: bool = False
