"""Tests for the yt-dlp command construction and result parsing."""

from __future__ import annotations

from playyt.integrations.ytdlp import YTDLP


def test_search_uses_flat_playlist_for_speed(monkeypatch) -> None:
    ytdlp = YTDLP()
    captured: dict[str, list[str]] = {}

    def fake_run(args: list[str]) -> str:
        captured["args"] = args
        return (
            "Song [Live]\n"
            "Artist Name\n"
            "185\n"
            "abc123\n"
            "https://www.youtube.com/watch?v=abc123\n"
            "---SEPARATOR---"
        )

    monkeypatch.setattr(ytdlp, "_run", fake_run)
    results = ytdlp.search("lofi hip hop", limit=5)

    assert "--flat-playlist" in captured["args"]
    assert "--default-search" not in captured["args"]
    assert "ytsearch5:lofi hip hop" in captured["args"]
    assert results == [
        {
            "title": "Song [Live]",
            "channel": "Artist Name",
            "duration": 185,
            "video_id": "abc123",
            "url": "https://www.youtube.com/watch?v=abc123",
        }
    ]


def test_search_skips_incomplete_blocks(monkeypatch) -> None:
    ytdlp = YTDLP()

    def fake_run(args: list[str]) -> str:
        return "Only A Title\n\n---SEPARATOR---\nGood\nChannel\n90\nvid\nurl\n---SEPARATOR---"

    monkeypatch.setattr(ytdlp, "_run", fake_run)
    results = ytdlp.search("query", limit=2)

    assert len(results) == 1
    assert results[0]["video_id"] == "vid"
