"""Configuration paths for PlayYT."""

from __future__ import annotations

import os
from pathlib import Path


def config_dir() -> Path:
    """Return the XDG configuration directory for PlayYT."""
    env = os.environ.get("XDG_CONFIG_HOME")
    base = Path(env) if env else Path.home() / ".config"
    return base / "playyt"


def data_dir() -> Path:
    """Return the XDG data directory for PlayYT."""
    env = os.environ.get("XDG_DATA_HOME")
    base = Path(env) if env else Path.home() / ".local" / "share"
    return base / "playyt"


def cache_dir() -> Path:
    """Return the XDG cache directory for PlayYT."""
    env = os.environ.get("XDG_CACHE_HOME")
    base = Path(env) if env else Path.home() / ".cache"
    return base / "playyt"


def log_dir() -> Path:
    """Return the logs directory for PlayYT."""
    return config_dir() / "logs"


def credentials_dir() -> Path:
    """Return the directory for OAuth credentials."""
    return config_dir() / "credentials"


def database_path() -> Path:
    """Return the path to the SQLite database."""
    return data_dir() / "database.sqlite"


def config_path() -> Path:
    """Return the path to config.toml."""
    return config_dir() / "config.toml"
