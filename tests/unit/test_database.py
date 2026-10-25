"""Unit tests for PlayYT database and repositories."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from playyt.database import Database, HistoryRepository, QueueRepository


@pytest.fixture
def temp_db() -> Database:
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "test.sqlite")
        yield db
        db.close()


def test_history_add_and_recent(temp_db: Database) -> None:
    repo = HistoryRepository(temp_db)
    repo.add("v1", "Song One", "Artist A", 180)
    repo.add("v2", "Song Two", "Artist B", 200)
    recent = repo.recent(5)
    assert len(recent) == 2
    assert recent[0]["video_id"] == "v2"
    assert recent[1]["video_id"] == "v1"


def test_queue_persist(temp_db: Database) -> None:
    repo = QueueRepository(temp_db)
    repo.add("v1", "Song One", "Artist A", 180)
    repo.add("v2", "Song Two", "Artist B", 200)
    items = repo.list()
    assert len(items) == 2
    assert items[0]["title"] == "Song One"
    repo.clear()
    assert repo.list() == []


def test_queue_remove_reindexes(temp_db: Database) -> None:
    repo = QueueRepository(temp_db)
    repo.add("v1", "Song One", None, 180)
    repo.add("v2", "Song Two", None, 200)
    repo.add("v3", "Song Three", None, 220)
    items = repo.list()
    repo.remove(items[0]["id"])
    remaining = repo.list()
    assert len(remaining) == 2
    assert remaining[0]["position"] == 1
    assert remaining[1]["position"] == 2
