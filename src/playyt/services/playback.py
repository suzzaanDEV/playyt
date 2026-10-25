"""Playback controller service for PlayYT."""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

from ..config.settings import settings
from ..integrations.mpv import MPVIPC, find_existing_socket
from ..models.playback import PlaybackState
from ..utils.errors import PlaybackError
from ..utils.logging import get_logger

logger = get_logger("playback")


def find_mpv() -> str:
    """Find the mpv binary path, checking common locations."""
    mpv_path = settings.get("mpv_path", "mpv")
    found: Optional[str] = shutil.which(mpv_path)
    if found:
        return found
    # Check common installation paths
    for candidate in ["/usr/bin/mpv", "/usr/local/bin/mpv", "/opt/homebrew/bin/mpv"]:
        if Path(candidate).exists():
            return candidate
    return "mpv"


class PlaybackService:
    """Controls mpv playback and exposes a synchronous API."""

    def __init__(self) -> None:
        self.ipc: Optional[MPVIPC] = None
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.RLock()
        self.state = PlaybackState()
        self._volume = int(settings.get("volume", 80))
        self._speed = float(settings.get("playback_speed", 1.0))
        self._last_error: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    def start_player(self, force_new: bool = False) -> None:
        """Start mpv with IPC, or attach to an existing instance.

        Raises PlaybackError with a clear message if mpv cannot start.
        """
        with self._lock:
            self._start_or_attach(force_new)

    def _start_or_attach(self, force_new: bool) -> None:
        if self.ipc is not None and self.ipc._connected:
            logger.debug("Already connected to mpv")
            return

        socket_path = self._find_existing_socket_path(force_new)

        self.ipc = MPVIPC(socket_path=socket_path)
        try:
            self.ipc.connect()
            logger.debug("Connected to existing mpv IPC at %s", socket_path)
            return
        except Exception as exc:
            logger.debug("No existing mpv IPC: %s", exc)

        self._spawn_new_mpv(socket_path)

    def _find_existing_socket_path(self, force_new: bool) -> Optional[str]:
        if not force_new:
            existing = find_existing_socket()
            if existing:
                return existing
        return None

    def _spawn_new_mpv(self, socket_path: Optional[str]) -> None:
        # No existing player; start a new mpv instance.
        mpv_bin = find_mpv()
        sock = str(Path("/tmp") / "mpvplayyt.sock")

        # Build mpv command with headless-friendly audio options
        audio_output = settings.get("audio_output", "auto")
        cmd = [
            mpv_bin,
            "--idle",
            "--force-window=immediate",
            "--input-ipc-server=" + sock,
            "--quiet",
            "--really-quiet",
            "--term-playing-msg=",
            "--audio-display=no",
        ]
        if audio_output != "auto":
            cmd.extend(["--audio-output=" + audio_output])

        logger.debug("Spawning mpv: %s", " ".join(cmd))

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        except FileNotFoundError as exc:
            self._last_error = (
                f"mpv binary not found at '{mpv_bin}'. Install it: sudo apt install mpv"
            )
            logger.exception(self._last_error)
            self.ipc = None
            raise PlaybackError(self._last_error) from exc
        except Exception as exc:
            self._last_error = f"Failed to start mpv: {exc}"
            logger.exception(self._last_error)
            self.ipc = None
            raise PlaybackError(self._last_error) from exc

        # Wait briefly for the IPC socket to appear
        socket_ready = False
        for _ in range(50):  # up to 5 seconds
            time.sleep(0.1)
            if Path(sock).exists():
                socket_ready = True
                break

        if not socket_ready:
            # mpv failed to start; capture stderr for diagnostics
            stderr_output = ""
            try:
                _, stderr = self._process.communicate(timeout=2)
                stderr_output = stderr.decode("utf-8", errors="replace")[:500]
            except Exception:
                pass

            self._process = None
            self.ipc = None
            self._last_error = (
                "mpv failed to start. "
                f"Stderr: {stderr_output if stderr_output else 'no output'}. "
                "Install mpv: sudo apt install mpv yt-dlp"
            )
            logger.exception(self._last_error)
            raise PlaybackError(self._last_error)

        # Connect to the new IPC socket
        self.ipc = MPVIPC(socket_path=sock)
        try:
            self.ipc.connect()
        except Exception as exc:
            self.ipc = None
            self._last_error = f"Cannot connect to mpv IPC: {exc}"
            logger.exception(self._last_error)
            raise PlaybackError(self._last_error) from exc

        self._apply_settings()
        logger.info("Playback service ready with mpv (pid=%s)", self._process.pid)

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
            if self._process is not None:
                try:
                    self._process.wait(timeout=5)
                except Exception:
                    self._process.kill()
                self._process = None
            self.state = PlaybackState()
            logger.info("Playback stopped")

    def detach(self) -> None:
        """Detach from mpv without stopping it."""
        with self._lock:
            if self.ipc is not None:
                self.ipc.close()
                self.ipc = None
            logger.info("Detached from mpv (playback continues)")

    def get_last_error(self) -> Optional[str]:
        """Return the last playback error, if any."""
        return self._last_error

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
            self._last_error = f"Failed to load media: {exc}"
            logger.error(self._last_error)
            raise PlaybackError(self._last_error) from exc

    def load_next(self, url: str, title: str = "", channel: str = "") -> None:
        """Append a URL to be played after the current one."""
        if self.ipc is None:
            self.start_player()
        assert self.ipc is not None
        try:
            self.ipc.command("loadfile", url, "append")
        except Exception as exc:
            self._last_error = f"Failed to queue media: {exc}"
            logger.error(self._last_error)
            raise PlaybackError(self._last_error) from exc

    def play_pause(self) -> None:
        """Toggle play/pause. Starts mpv if not running."""
        if self.ipc is None:
            self._last_error = (
                "mpv is not running. Search for a track and press Enter to play it first."
            )
            logger.warning(self._last_error)
            raise PlaybackError(self._last_error)
        try:
            self.ipc.command("cycle", "pause")
            self.state.playing = not self.state.playing
        except Exception as exc:
            self._last_error = f"Playback control failed: {exc}"
            logger.error(self._last_error)
            raise PlaybackError(self._last_error) from exc

    def play(self) -> None:
        if self.ipc is None:
            self._last_error = "mpv is not running. Play a track first."
            raise PlaybackError(self._last_error)
        try:
            self.ipc.set_property("pause", False)
            self.state.playing = True
        except Exception as exc:
            self._last_error = f"Playback control failed: {exc}"
            raise PlaybackError(self._last_error) from exc

    def pause(self) -> None:
        if self.ipc is None:
            self._last_error = "mpv is not running. Play a track first."
            raise PlaybackError(self._last_error)
        try:
            self.ipc.set_property("pause", True)
            self.state.playing = False
        except Exception as exc:
            self._last_error = f"Playback control failed: {exc}"
            raise PlaybackError(self._last_error) from exc

    def stop_playback(self) -> None:
        if self.ipc is None:
            return
        try:
            self.ipc.command("stop")
            self.state.playing = False
        except Exception as exc:
            self._last_error = f"Stop failed: {exc}"
            raise PlaybackError(self._last_error) from exc

    def next_track(self) -> None:
        if self.ipc is None:
            self._last_error = "mpv is not running. Play a track first."
            raise PlaybackError(self._last_error)
        try:
            self.ipc.command("playlist-next")
        except Exception as exc:
            self._last_error = f"Next track failed: {exc}"
            raise PlaybackError(self._last_error) from exc

    def previous_track(self) -> None:
        if self.ipc is None:
            self._last_error = "mpv is not running. Play a track first."
            raise PlaybackError(self._last_error)
        try:
            self.ipc.command("playlist-prev")
        except Exception as exc:
            self._last_error = f"Previous track failed: {exc}"
            raise PlaybackError(self._last_error) from exc

    def seek(self, seconds: float) -> None:
        if self.ipc is None:
            self._last_error = "mpv is not running. Play a track first."
            raise PlaybackError(self._last_error)
        try:
            self.ipc.command("seek", seconds)
        except Exception as exc:
            self._last_error = f"Seek failed: {exc}"
            raise PlaybackError(self._last_error) from exc

    def volume_up(self) -> None:
        self._adjust_volume(5)

    def volume_down(self) -> None:
        self._adjust_volume(-5)

    def _adjust_volume(self, delta: int) -> None:
        if self.ipc is None:
            self._last_error = "mpv is not running. Play a track first."
            raise PlaybackError(self._last_error)
        assert self.ipc is not None
        try:
            current = int(self.ipc.get_property("volume") or self._volume)
        except Exception:
            current = self._volume
        new = max(0, min(100, current + delta))
        try:
            self.ipc.set_property("volume", new)
        except Exception as exc:
            self._last_error = f"Volume control failed: {exc}"
            raise PlaybackError(self._last_error) from exc
        self._volume = new
        settings.set("volume", new)

    def set_volume(self, value: int) -> None:
        if self.ipc is None:
            self._last_error = "mpv is not running. Play a track first."
            raise PlaybackError(self._last_error)
        assert self.ipc is not None
        try:
            self.ipc.set_property("volume", value)
        except Exception as exc:
            self._last_error = f"Volume control failed: {exc}"
            raise PlaybackError(self._last_error) from exc
        self._volume = value
        settings.set("volume", value)

    def set_speed(self, speed: float) -> None:
        if self.ipc is None:
            self._last_error = "mpv is not running. Play a track first."
            raise PlaybackError(self._last_error)
        assert self.ipc is not None
        try:
            self.ipc.set_property("speed", speed)
        except Exception as exc:
            self._last_error = f"Speed control failed: {exc}"
            raise PlaybackError(self._last_error) from exc
        self._speed = speed
        settings.set("playback_speed", speed)

    def cycle_speed(self) -> None:
        speeds = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
        current = self._speed
        idx = speeds.index(current) if current in speeds else 2
        next_speed = speeds[(idx + 1) % len(speeds)]
        self.set_speed(next_speed)

    def toggle_shuffle(self) -> None:
        if self.ipc is None:
            self._last_error = "mpv is not running. Play a track first."
            raise PlaybackError(self._last_error)
        try:
            self.ipc.command("cycle", "shuffle")
            self.state.shuffle = not self.state.shuffle
        except Exception as exc:
            self._last_error = f"Shuffle control failed: {exc}"
            raise PlaybackError(self._last_error) from exc

    def toggle_repeat(self) -> None:
        if self.ipc is None:
            self._last_error = "mpv is not running. Play a track first."
            raise PlaybackError(self._last_error)
        try:
            self.ipc.command("cycle", "loop")
            order = ["off", "all", "one"]
            current = self.state.repeat
            next_idx = (order.index(current) + 1) % len(order) if current in order else 0
            self.state.repeat = order[next_idx]
        except Exception as exc:
            self._last_error = f"Repeat control failed: {exc}"
            raise PlaybackError(self._last_error) from exc

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


playback = PlaybackService()
