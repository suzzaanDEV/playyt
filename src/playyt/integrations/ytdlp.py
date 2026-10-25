"""yt-dlp integration for resolving playable media URLs."""

from __future__ import annotations

import subprocess
from typing import Any

from ..utils.errors import YTDLPError
from ..utils.logging import get_logger

logger = get_logger("ytdlp")

MIN_RESOLVE_LINES = 6
MIN_SEARCH_LINES = 5


class YTDLP:
    """Wrapper around yt-dlp for resolving YouTube media."""

    def __init__(self, yt_dlp_path: str = "yt-dlp") -> None:
        self.yt_dlp_path = yt_dlp_path

    def _run(self, args: list[str]) -> str:
        cmd = [self.yt_dlp_path, "--quiet", "--no-warnings", *args]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                check=False,
                text=True,
                timeout=60,
            )
        except FileNotFoundError as exc:
            raise YTDLPError("yt-dlp is not installed. Install it to play YouTube media.") from exc
        except subprocess.TimeoutExpired as exc:
            raise YTDLPError("yt-dlp timed out while resolving media.") from exc
        if result.returncode != 0:
            err = result.stderr.strip() or "yt-dlp failed"
            raise YTDLPError(f"yt-dlp error: {err}")
        return result.stdout.strip()

    def resolve_url(self, url: str) -> dict[str, Any]:
        """Resolve a YouTube URL to a playable media URL and metadata.

        Returns a dict with keys: url, title, channel, duration, thumbnail, video_id.
        """
        args = [
            "--print",
            "%(url)s",
            "--print",
            "%(title)s",
            "--print",
            "%(uploader)s",
            "--print",
            "%(duration)s",
            "--print",
            "%(thumbnail)s",
            "--print",
            "%(id)s",
            "--format",
            "bestaudio/best",
            url,
        ]
        output = self._run(args)
        lines = output.split("\n")
        if len(lines) < MIN_RESOLVE_LINES:
            raise YTDLPError("yt-dlp returned incomplete metadata.")
        return {
            "url": lines[0],
            "title": lines[1],
            "channel": lines[2] or None,
            "duration": int(lines[3]) if lines[3].isdigit() else None,
            "thumbnail": lines[4] or None,
            "video_id": lines[5],
        }

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search YouTube and return a list of video results."""
        args = [
            "--default-search",
            "ytsearch%d" % limit,
            "--print",
            "%(title)s",
            "--print",
            "%(uploader)s",
            "--print",
            "%(duration)s",
            "--print",
            "%(id)s",
            "--print",
            "%(webpage_url)s",
            "--print",
            "---SEPARATOR---",
            "ytsearch%d:%s" % (limit, query),
        ]
        output = self._run(args)
        results: list[dict[str, Any]] = []
        blocks = output.split("---SEPARATOR---")
        for block in blocks:
            stripped = block.strip()
            if not stripped:
                continue
            lines = stripped.split("\n")
            if len(lines) < MIN_SEARCH_LINES:
                continue
            results.append(
                {
                    "title": lines[0],
                    "channel": lines[1] or None,
                    "duration": int(lines[2]) if lines[2].isdigit() else None,
                    "video_id": lines[3],
                    "url": lines[4],
                }
            )
        return results

    def is_available(self) -> bool:
        """Return True if yt-dlp is installed and runnable."""
        try:
            subprocess.run(
                [self.yt_dlp_path, "--version"],
                capture_output=True,
                check=False,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
        else:
            return True
