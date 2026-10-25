"""Default configuration values for PlayYT."""

from __future__ import annotations

DEFAULTS: dict[str, object] = {
    "volume": 80,
    "playback_speed": 1.0,
    "repeat_mode": "off",  # off, one, all
    "shuffle": False,
    "theme": "dark",
    "audio_output": "auto",
    "search_limit": 20,
    "cache_size": 200,
    "mpv_path": "mpv",
    "yt_dlp_path": "yt-dlp",
    "youtube_api_key": "",
}
