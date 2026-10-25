"""Video model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Video:
    """A YouTube video / track."""

    video_id: str
    title: str
    channel: Optional[str] = None
    duration: Optional[int] = None  # seconds
    thumbnail: Optional[str] = None
    source_playlist: Optional[str] = None
