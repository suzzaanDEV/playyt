"""SQLite database layer for PlayYT."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from ..config.paths import database_path
from ..utils.errors import DatabaseError
from ..utils.logging import get_logger

logger = get_logger("database")

MIGRATIONS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT NOT NULL,
        title TEXT NOT NULL,
        channel TEXT,
        played_at TEXT NOT NULL,
        duration INTEGER,
        completion_percentage REAL DEFAULT 0,
        source_playlist TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_history_played_at ON history(played_at);
    CREATE INDEX IF NOT EXISTS idx_history_video_id ON history(video_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT NOT NULL,
        title TEXT NOT NULL,
        channel TEXT,
        duration INTEGER,
        position INTEGER NOT NULL,
        added_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_queue_position ON queue(position);
    """,
    """
    CREATE TABLE IF NOT EXISTS search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        searched_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_search_history_searched_at ON search_history(searched_at);
    """,
    """
    CREATE TABLE IF NOT EXISTS playlists (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        channel TEXT,
        video_count INTEGER DEFAULT 0,
        fetched_at TEXT NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS playlist_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id TEXT NOT NULL,
        video_id TEXT NOT NULL,
        title TEXT NOT NULL,
        channel TEXT,
        position INTEGER,
        FOREIGN KEY (playlist_id) REFERENCES playlists(id)
    );
    CREATE INDEX IF NOT EXISTS idx_playlist_items_playlist ON playlist_items(playlist_id);
    """,
]

SCHEMA_VERSION = len(MIGRATIONS)


class Database:
    """Thread-safe SQLite wrapper with migrations."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @property
    def conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._connect()
            self._local.conn = conn
        return conn

    def _initialize(self) -> None:
        with self._lock:
            conn = self.conn
            try:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"
                )
                row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
                current = row["version"] if row else 0
                if current < SCHEMA_VERSION:
                    for idx in range(current, SCHEMA_VERSION):
                        conn.executescript(MIGRATIONS[idx])
                    conn.execute(
                        "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                        (SCHEMA_VERSION,),
                    )
                conn.commit()
            except sqlite3.Error as exc:
                conn.rollback()
                raise DatabaseError(f"Database initialization failed: {exc}") from exc

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass
            self._local.conn = None

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        try:
            return self.conn.execute(sql, params)
        except sqlite3.Error as exc:
            raise DatabaseError(f"Query failed: {exc}") from exc

    def executemany(self, sql: str, params: list[tuple]) -> sqlite3.Cursor:
        try:
            return self.conn.executemany(sql, params)
        except sqlite3.Error as exc:
            raise DatabaseError(f"Query failed: {exc}") from exc

    def commit(self) -> None:
        self.conn.commit()

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self.execute(sql, params).fetchone()  # type: ignore[no-any-return]

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self.execute(sql, params).fetchall()  # type: ignore[no-any-return]


db = Database()
