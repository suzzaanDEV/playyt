"""Playlist model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .video import Video


@dataclass
class Playlist:
    """A YouTube playlist."""

    playlist_id: str
    title: str
    channel: Optional[str] = None
    video_count: int = 0
    items: list[Video] = field(default_factory=list)


@dataclass
class PlaylistItem:
    """An item within a playlist."""

    video_id: str
    title: str
    channel: Optional[str] = None
    position: Optional[int] = None
    duration: Optional[int] = None
