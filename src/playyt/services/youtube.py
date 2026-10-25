"""YouTube Data API service for PlayYT."""

from __future__ import annotations

from typing import Any

import requests

from ..services.authentication import auth
from ..utils.errors import YouTubeAPIError
from ..utils.logging import get_logger

logger = get_logger("youtube")

API_BASE = "https://www.googleapis.com/youtube/v3"

HTTP_OK = 200
HTTP_UNAUTHORIZED = 401


class YouTubeService:
    """Client for the YouTube Data API v3."""

    def __init__(self) -> None:
        self.session = requests.Session()

    def _headers(self) -> dict[str, str]:
        token = auth.access_token()
        if not token:
            raise YouTubeAPIError("Not authenticated. Please log in first.")
        return {"Authorization": f"Bearer {token}"}

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = self.session.get(
                f"{API_BASE}/{path}",
                headers=self._headers(),
                params=params,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise YouTubeAPIError(f"YouTube API request failed: {exc}") from exc
        if resp.status_code == HTTP_UNAUTHORIZED:
            raise YouTubeAPIError("Authentication expired. Please log in again.")
        if resp.status_code != HTTP_OK:
            raise YouTubeAPIError(f"YouTube API error ({resp.status_code}): {resp.text[:200]}")
        return resp.json()  # type: ignore[no-any-return]

    def search(
        self,
        query: str,
        limit: int = 10,
        type_: str = "video",
    ) -> list[dict[str, Any]]:
        """Search YouTube via the official API."""
        params = {
            "part": "snippet",
            "q": query,
            "type": type_,
            "maxResults": limit,
        }
        data = self._get("search", params)
        results: list[dict[str, Any]] = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            results.append(
                {
                    "id": item.get("id", {}).get("videoId")
                    or item.get("id", {}).get("playlistId")
                    or item.get("id", {}).get("channelId"),
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "type": item["id"].get("kind", "").split("#")[-1],
                }
            )
        return results

    def channels_list(self, part: str = "snippet,statistics", **kwargs) -> dict:
        params = {"part": part, **kwargs}
        return self._get("channels", params)

    def playlists_list(self, part: str = "snippet,contentDetails", **kwargs) -> dict:
        params = {"part": part, **kwargs}
        return self._get("playlists", params)

    def playlist_items_list(
        self,
        playlist_id: str,
        part: str = "snippet,contentDetails",
        max_results: int = 50,
        page_token: str | None = None,
    ) -> dict:
        params = {
            "part": part,
            "playlistId": playlist_id,
            "maxResults": max_results,
        }
        if page_token:
            params["pageToken"] = page_token
        return self._get("playlistItems", params)

    def subscriptions_list(
        self,
        part: str = "snippet",
        max_results: int = 50,
    ) -> dict:
        params = {"part": part, "maxResults": max_results, "mine": "true"}
        return self._get("subscriptions", params)

    def videos_list(self, video_id: str, part: str = "snippet,contentDetails") -> dict:
        params = {"part": part, "id": video_id}
        return self._get("videos", params)


youtube = YouTubeService()
