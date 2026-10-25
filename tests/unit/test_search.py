"""Unit tests for PlayYT search service."""

from __future__ import annotations

import pytest

from playyt.models.video import Video
from playyt.services.search import SearchService
from playyt.utils.errors import YouTubeAPIError


class FakeYTDLP:
    def search(self, query: str, limit: int = 10):
        return [
            {
                "title": "Fake Song",
                "channel": "Fake Artist",
                "duration": 200,
                "video_id": "fakeid",
                "url": "https://youtube.com/watch?v=fakeid",
            }
        ]


def test_search_returns_videos() -> None:
    service = SearchService(ytdlp=FakeYTDLP())
    results = service.search("query")
    assert len(results) == 1
    assert isinstance(results[0], Video)
    assert results[0].video_id == "fakeid"
    assert results[0].title == "Fake Song"
    assert results[0].channel == "Fake Artist"
    assert results[0].duration == 200


def test_search_empty_query() -> None:
    service = SearchService(ytdlp=FakeYTDLP())
    assert service.search("") == []
    assert service.search("   ") == []


def test_search_failure_raises() -> None:
    class BrokenYTDLP:
        def search(self, query: str, limit: int = 10):
            raise RuntimeError("network down")

    service = SearchService(ytdlp=BrokenYTDLP())
    with pytest.raises(YouTubeAPIError):
        service.search("query")
