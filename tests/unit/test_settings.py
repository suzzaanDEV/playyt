"""Unit tests for PlayYT configuration and settings."""

from __future__ import annotations

from playyt.config.defaults import DEFAULTS
from playyt.config.settings import Settings


def test_defaults_contain_expected_keys() -> None:
    assert "volume" in DEFAULTS
    assert "playback_speed" in DEFAULTS
    assert "repeat_mode" in DEFAULTS
    assert "shuffle" in DEFAULTS


def test_settings_get_default() -> None:
    settings = Settings()
    assert settings.get("volume") == DEFAULTS["volume"]
    assert settings.get("playback_speed") == DEFAULTS["playback_speed"]


def test_settings_set_and_get() -> None:
    settings = Settings()
    settings.set("volume", 42)
    assert settings.get("volume") == 42


def test_settings_unknown_key_returns_default() -> None:
    settings = Settings()
    assert settings.get("nonexistent", "fallback") == "fallback"


def test_settings_as_dict() -> None:
    settings = Settings()
    data = settings.as_dict()
    assert isinstance(data, dict)
    assert "volume" in data
