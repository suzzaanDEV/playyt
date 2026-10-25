"""Logging configuration for PlayYT."""

from __future__ import annotations

import logging
import logging.handlers
import sys

from ..config.paths import log_dir

logger = logging.getLogger("playyt")


def setup_logging(debug: bool = False) -> None:
    """Configure application logging."""
    log_dir().mkdir(parents=True, exist_ok=True)
    log_file = log_dir() / "playyt.log"

    level = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    root = logging.getLogger("playyt")
    root.setLevel(level)

    # File handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # Stderr handler for errors only
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)
    root.addHandler(stderr_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"playyt.{name}")
