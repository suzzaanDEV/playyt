"""Playback controller service for PlayYT."""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Optional

from ..config.settings import settings
from ..integrations.mpv import MPVIPC, find_existing_socket
from ..models.playback import PlaybackState
from ..utils.errors import PlaybackError
from ..utils.logging import get_logger

logger = get_logger("playback")


class PlaybackService:
    """Controls mpv playback and exposes a synchronous API."""

    def __init__(self) -> None:
        self.ipc: Optional[MPVIPC] = None
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.RLock()
        self.state = PlaybackState()
        self._volume = int(settings.get("volume", 80))
        self._speed = float(settings.get("playback_speed", 1.0))

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start_player(self, force_new: bool = False) -> None:
        """Start mpv with IPC, or attach to an existing instance."""
        with self._lock:
            if self.ipc is not None and self.ipc._connected:
                logger.debug("Already connected to mpv")
                return

            socket_path = None
            if not force_new:
                existing = find_existing_socket()
                if existing:
                    socket_path = existing

            self.ipc = MPVIPC(socket_path=socket_path)
            try:
                self.ipc.connect()
            except Exception:
                # No existing player; start a new mpv instance.
                if socket_path is not None:
                    socket_path = None
                    self.ipc = MPVIPC(socket_path=None)
                    self.ipc.connect()
                else:
                    raise

            if self._process is None:
                self._spawn_mpv(socket_path)

            self._apply_settings()
            logger.info("Playback service ready")

    def _spawn_mpv(self, socket_path: Optional[str]) -> None:
        sock = socket_path or str(Path("/tmp") / "mpvplayyt.sock")
        cmd = [
            settings.get("mpv_path", "mpv"),
            "--idle",
            "--force-window=immediate",
            "--input-ipc-server=" + sock,
            "--quiet",
            "--really-quiet",
            "--term-playing-msg=",
        ]
        # Detach mpv from the controlling terminal so it survives SSH drops.
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        logger.debug("Spawned mpv (pid=%s) with IPC socket %s", self._process.pid, sock)

    def _apply_settings(self) -> None:
        if self.ipc is None:
            return
        try:
            self.ipc.set_property("volume", self._volume)
            self.ipc.set_property("speed", self._speed)
        except Exception as exc:
            logger.warning("Failed to apply playback settings: %s", exc)

    def is_running(self) -> bool:
        return self.ipc is not None and self.ipc._connected

    def stop(self) -> None:
        """Stop playback and quit mpv."""
        with self._lock:
            if self.ipc is not None:
                try:
                    self.ipc.command("quit")
                except Exception:
                    pass
                self.ipc.close()
                self.ipc = None
            self.state = PlaybackState()
            logger.info("Playback stopped")

    def detach(self) -> None:
        """Detach from mpv without stopping it."""
        with self._lock:
            if self.ipc is not None:
                self.ipc.close()
                self.ipc = None
            logger.info("Detached from mpv (playback continues)")

    # ------------------------------------------------------------------ #
    # Playback control
    # ------------------------------------------------------------------ #
    def load(self, url: str, title: str = "", channel: str = "") -> None:
        """Load and play a media URL."""
        if self.ipc is None:
            self.start_player()
        assert self.ipc is not None
        try:
            self.ipc.command("loadfile", url, "replace")
            self.state.playing = True
            self.state.video_id = url
            self.state.title = title or url
            self.state.channel = channel or ""
            self.state.position = 0.0
            self._refresh_state()
        except Exception as exc:
            raise PlaybackError(f"Failed to load media: {exc}") from exc

    def load_next(self, url: str, title: str = "", channel: str = "") -> None:
        """Append a URL to be played after the current one."""
        if self.ipc is None:
            self.start_player()
        assert self.ipc is not None
        try:
            self.ipc.command("loadfile", url, "append")
        except Exception as exc:
            raise PlaybackError(f"Failed to queue media: {exc}") from exc

    def play_pause(self) -> None:
        self._require_ipc()
        assert self.ipc is not None
        self.ipc.command("cycle", "pause")
        self.state.playing = not self.state.playing

    def play(self) -> None:
        self._require_ipc()
        assert self.ipc is not None
        self.ipc.set_property("pause", False)
        self.state.playing = True

    def pause(self) -> None:
        self._require_ipc()
        assert self.ipc is not None
        self.ipc.set_property("pause", True)
        self.state.playing = False

    def stop_playback(self) -> None:
        self._require_ipc()
        assert self.ipc is not None
        self.ipc.command("stop")
        self.state.playing = False

    def next_track(self) -> None:
        self._require_ipc()
        assert self.ipc is not None
        self.ipc.command("playlist-next")

    def previous_track(self) -> None:
        self._require_ipc()
        assert self.ipc is not None
        self.ipc.command("playlist-prev")

    def seek(self, seconds: float) -> None:
        self._require_ipc()
        assert self.ipc is not None
        self.ipc.command("seek", seconds)

    def volume_up(self) -> None:
        self._adjust_volume(5)

    def volume_down(self) -> None:
        self._adjust_volume(-5)

    def _adjust_volume(self, delta: int) -> None:
        self._require_ipc()
        assert self.ipc is not None
        current = int(self.ipc.get_property("volume") or self._volume)
        new = max(0, min(100, current + delta))
        self.ipc.set_property("volume", new)
        self._volume = new
        settings.set("volume", new)

    def set_volume(self, value: int) -> None:
        self._require_ipc()
        assert self.ipc is not None
        self.ipc.set_property("volume", value)
        self._volume = value
        settings.set("volume", value)

    def set_speed(self, speed: float) -> None:
        self._require_ipc()
        assert self.ipc is not None
        self.ipc.set_property("speed", speed)
        self._speed = speed
        settings.set("playback_speed", speed)

    def cycle_speed(self) -> None:
        speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
        current = self._speed
        idx = speeds.index(current) if current in speeds else 2
        next_speed = speeds[(idx + 1) % len(speeds)]
        self.set_speed(next_speed)

    def toggle_shuffle(self) -> None:
        self._require_ipc()
        assert self.ipc is not None
        self.ipc.command("cycle", "shuffle")
        self.state.shuffle = not self.state.shuffle

    def toggle_repeat(self) -> None:
        self._require_ipc()
        assert self.ipc is not None
        self.ipc.command("cycle", "loop")
        # mpv loop: no -> inf -> one -> no
        order = ["off", "all", "one"]
        current = self.state.repeat
        next_idx = (order.index(current) + 1) % len(order) if current in order else 0
        self.state.repeat = order[next_idx]

    # ------------------------------------------------------------------ #
    # State
    # ------------------------------------------------------------------ #
    def _refresh_state(self) -> None:
        if self.ipc is None:
            return
        try:
            self.state.position = float(self.ipc.get_property("time-pos") or 0.0)
            self.state.duration = self.ipc.get_property("duration")
            self.state.playing = not bool(self.ipc.get_property("pause"))
            self.state.volume = int(self.ipc.get_property("volume") or self._volume)
            self.state.speed = float(self.ipc.get_property("speed") or self._speed)
        except Exception as exc:
            logger.debug("State refresh failed: %s", exc)

    def get_state(self) -> PlaybackState:
        self._refresh_state()
        return self.state

    def _require_ipc(self) -> None:
        if self.ipc is None or not self.ipc._connected:
            raise PlaybackError("mpv is not running")


playback = PlaybackService()
