"""Account model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Account:
    """YouTube account state."""

    authenticated: bool = False
    channel_id: str | None = None
    channel_title: str | None = None
    email: str | None = None
