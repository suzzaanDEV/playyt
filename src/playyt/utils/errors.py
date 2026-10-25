"""Application exceptions."""

from __future__ import annotations


class PlayYTError(Exception):
    """Base exception for PlayYT."""


class ConfigurationError(PlayYTError):
    """Configuration related errors."""


class DatabaseError(PlayYTError):
    """Database related errors."""


class NetworkError(PlayYTError):
    """Network related errors."""


class YouTubeAPIError(PlayYTError):
    """YouTube Data API errors."""


class AuthenticationError(PlayYTError):
    """Authentication errors."""


class PlaybackError(PlayYTError):
    """Playback / mpv errors."""


class YTDLPError(PlayYTError):
    """yt-dlp media resolution errors."""


class MPVError(PlayYTError):
    """mpv IPC errors."""


class CacheError(PlayYTError):
    """Cache related errors."""
