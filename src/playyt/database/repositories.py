"""Database repositories."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List

from .db import Database, db


class HistoryRepository:
    """Repository for local play history."""

    def __init__(self, database: Database | None = None) -> None:
        self._db = database or db

    def add(
        self,
        video_id: str,
        title: str,
        channel: str | None = None,
        duration: int | None = None,
        source_playlist: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            """
            INSERT INTO history
            (video_id, title, channel, played_at, duration, source_playlist)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (video_id, title, channel, now, duration, source_playlist),
        )
        self._db.commit()

    def recent(self, limit: int = 20) -> List[dict[str, Any]]:
        rows = self._db.fetchall(
            """
            SELECT video_id, title, channel, played_at, duration,
                   completion_percentage, source_playlist
            FROM history
            ORDER BY played_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(r) for r in rows]


class QueueRepository:
    """Repository for the playback queue."""

    def __init__(self, database: Database | None = None) -> None:
        self._db = database or db

    def list(self) -> List[dict[str, Any]]:
        rows = self._db.fetchall(
            """
            SELECT id, video_id, title, channel, duration, position, added_at
            FROM queue
            ORDER BY position
            """
        )
        return [dict(r) for r in rows]

    def add(
        self,
        video_id: str,
        title: str,
        channel: str | None = None,
        duration: int | None = None,
        position: int | None = None,
    ) -> None:
        if position is None:
            row = self._db.fetchone("SELECT COALESCE(MAX(position), 0) + 1 FROM queue")
            position = row[0] if row else 1
        self._db.execute(
            """
            INSERT INTO queue (video_id, title, channel, duration, position, added_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                video_id,
                title,
                channel,
                duration,
                position,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._db.commit()

    def remove(self, queue_id: int) -> None:
        self._db.execute("DELETE FROM queue WHERE id = ?", (queue_id,))
        self._db.commit()
        self._reindex()

    def clear(self) -> None:
        self._db.execute("DELETE FROM queue")
        self._db.commit()

    def _reindex(self) -> None:
        rows = self._db.fetchall("SELECT id FROM queue ORDER BY position")
        for index, row in enumerate(rows, start=1):
            self._db.execute(
                "UPDATE queue SET position = ? WHERE id = ?",
                (index, row["id"]),
            )
        self._db.commit()

    def move(self, queue_id: int, new_position: int) -> None:
        items = self.list()
        target = next(i for i in items if i["id"] == queue_id)
        items = [i for i in items if i["id"] != queue_id]
        items.insert(new_position - 1, target)
        self.clear()
        for item in items:
            self.add(
                item["video_id"],
                item["title"],
                item.get("channel"),
                item.get("duration"),
                position=items.index(item) + 1,
            )


class SearchHistoryRepository:
    """Repository for local search history."""

    def __init__(self, database: Database | None = None) -> None:
        self._db = database or db

    def add(self, query: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            "INSERT INTO search_history (query, searched_at) VALUES (?, ?)",
            (query, now),
        )
        self._db.commit()

    def recent(self, limit: int = 10) -> list[str]:
        rows = self._db.fetchall(
            "SELECT query FROM search_history ORDER BY searched_at DESC LIMIT ?",
            (limit,),
        )
        return [r["query"] for r in rows]


class PlaylistRepository:
    """Repository for cached playlists."""

    def __init__(self, database: Database | None = None) -> None:
        self._db = database or db

    def upsert(
        self,
        playlist_id: str,
        title: str,
        channel: str | None = None,
        video_count: int = 0,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._db.execute(
            """
            INSERT INTO playlists (id, title, channel, video_count, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                channel=excluded.channel,
                video_count=excluded.video_count,
                fetched_at=excluded.fetched_at
            """,
            (playlist_id, title, channel, video_count, now),
        )
        self._db.commit()

    def list(self) -> List[dict[str, Any]]:
        rows = self._db.fetchall(
            "SELECT id, title, channel, video_count, fetched_at FROM playlists ORDER BY title"
        )
        return [dict(r) for r in rows]

    def get(self, playlist_id: str) -> dict[str, Any] | None:
        row = self._db.fetchone(
            "SELECT id, title, channel, video_count, fetched_at FROM playlists WHERE id = ?",
            (playlist_id,),
        )
        return dict(row) if row else None

    def add_item(
        self,
        playlist_id: str,
        video_id: str,
        title: str,
        channel: str | None = None,
        position: int | None = None,
    ) -> None:
        if position is None:
            row = self._db.fetchone(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM playlist_items WHERE playlist_id = ?",
                (playlist_id,),
            )
            position = row[0] if row else 1
        self._db.execute(
            """
            INSERT INTO playlist_items (playlist_id, video_id, title, channel, position)
            VALUES (?, ?, ?, ?, ?)
            """,
            (playlist_id, video_id, title, channel, position),
        )
        self._db.commit()

    def items(self, playlist_id: str) -> List[dict[str, Any]]:
        rows = self._db.fetchall(
            """
            SELECT video_id, title, channel, position
            FROM playlist_items
            WHERE playlist_id = ?
            ORDER BY position
            """,
            (playlist_id,),
        )
        return [dict(r) for r in rows]
