"""Queue model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QueueItem:
    """An item in the playback queue."""

    video_id: str
    title: str
    channel: str | None = None
    duration: int | None = None


@dataclass
class Queue:
    """The playback queue."""

    items: list[QueueItem] = field(default_factory=list)
    current_index: int = -1

    @property
    def current(self) -> QueueItem | None:
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index]
        return None

    def add(self, item: QueueItem) -> None:
        self.items.append(item)

    def remove(self, index: int) -> QueueItem | None:
        if 0 <= index < len(self.items):
            return self.items.pop(index)
        return None

    def clear(self) -> None:
        self.items.clear()
        self.current_index = -1

    def move(self, from_index: int, to_index: int) -> None:
        if not (0 <= from_index < len(self.items)) or not (0 <= to_index < len(self.items)):
            return
        item = self.items.pop(from_index)
        self.items.insert(to_index, item)
        if self.current_index == from_index:
            self.current_index = to_index
        elif from_index < self.current_index:
            self.current_index -= 1
        elif to_index < self.current_index:
            self.current_index += 1

    def next(self) -> QueueItem | None:
        if self.current_index + 1 < len(self.items):
            self.current_index += 1
            return self.current
        return None

    def previous(self) -> QueueItem | None:
        if self.current_index - 1 >= 0:
            self.current_index -= 1
            return self.current
        return None
