"""Search service backed by yt-dlp."""

from __future__ import annotations

from ..integrations.ytdlp import YTDLP
from ..models.video import Video
from ..utils.errors import YouTubeAPIError
from ..utils.logging import get_logger

logger = get_logger("search")


class SearchService:
    """Searches YouTube using yt-dlp (no API key required)."""

    def __init__(self, ytdlp: YTDLP | None = None) -> None:
        self.ytdlp = ytdlp or YTDLP()

    def search(self, query: str, limit: int = 10) -> list[Video]:
        if not query.strip():
            return []
        try:
            raw = self.ytdlp.search(query, limit=limit)
        except Exception as exc:
            logger.warning("Search failed: %s", exc)
            raise YouTubeAPIError(f"Search failed: {exc}") from exc
        return [
            Video(
                video_id=r["video_id"],
                title=r["title"],
                channel=r.get("channel"),
                duration=r.get("duration"),
            )
            for r in raw
        ]
