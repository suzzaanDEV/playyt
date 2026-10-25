"""Settings management for PlayYT."""

from __future__ import annotations

import threading
from typing import Any

import toml  # type: ignore[import-untyped]

from .defaults import DEFAULTS
from .paths import config_path


class Settings:
    """Thread-safe settings store backed by a TOML config file."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        path = config_path()
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as fh:
                    loaded = toml.load(fh)
                for key, value in loaded.items():
                    if key in DEFAULTS:
                        self._data[key] = value
            except Exception:
                # Keep defaults on config read failure.
                pass

    def save(self) -> None:
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            toml.dump(self._data, fh)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def as_dict(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)


settings = Settings()
