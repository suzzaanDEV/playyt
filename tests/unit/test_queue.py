"""Unit tests for PlayYT queue model."""

from __future__ import annotations

import pytest

from playyt.models.queue import Queue, QueueItem


@pytest.fixture
def empty_queue() -> Queue:
    return Queue()


@pytest.fixture
def sample_queue() -> Queue:
    q = Queue()
    q.add(QueueItem("v1", "Song One", "Artist A", 180))
    q.add(QueueItem("v2", "Song Two", "Artist B", 200))
    q.add(QueueItem("v3", "Song Three", "Artist C", 220))
    return q


def test_queue_current_empty(empty_queue: Queue) -> None:
    assert empty_queue.current is None


def test_queue_add_and_current(sample_queue: Queue) -> None:
    assert sample_queue.current is None
    item = sample_queue.next()
    assert item is not None
    assert item.video_id == "v1"
    assert sample_queue.current == item


def test_queue_next_and_previous(sample_queue: Queue) -> None:
    sample_queue.next()
    assert sample_queue.current.video_id == "v1"
    sample_queue.next()
    assert sample_queue.current.video_id == "v2"
    sample_queue.previous()
    assert sample_queue.current.video_id == "v1"


def test_queue_next_wraps_none(sample_queue: Queue) -> None:
    sample_queue.current_index = len(sample_queue.items) - 1
    assert sample_queue.next() is None


def test_queue_remove(sample_queue: Queue) -> None:
    removed = sample_queue.remove(0)
    assert removed is not None
    assert removed.video_id == "v1"
    assert len(sample_queue.items) == 2


def test_queue_clear(sample_queue: Queue) -> None:
    sample_queue.clear()
    assert len(sample_queue.items) == 0
    assert sample_queue.current_index == -1


def test_queue_move(sample_queue: Queue) -> None:
    sample_queue.move(2, 0)
    assert sample_queue.items[0].video_id == "v3"
    assert sample_queue.items[1].video_id == "v1"
    assert sample_queue.items[2].video_id == "v2"
