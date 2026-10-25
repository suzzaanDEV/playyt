"""Playback controller service for PlayYT."""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import BinaryIO, Optional

from ..config.paths import log_dir
from ..config.settings import settings
from ..integrations.mpv import MPVIPC, default_socket_path, find_existing_socket
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
        self._mpv_log: Optional[BinaryIO] = None
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
        sock = default_socket_path()
        self._remove_stale_socket(sock)
        cmd = self._build_mpv_command(mpv_bin, sock)
        self._open_mpv_log()
        logger.debug("Spawning mpv: %s", " ".join(cmd))
        self._launch_process(cmd, mpv_bin)
        self._wait_for_socket(sock, mpv_bin)
        self._connect_new_socket(sock)
        self._apply_settings()
        pid = self._process.pid if self._process is not None else "?"
        logger.info("Playback service ready with mpv (pid=%s)", pid)

    def _remove_stale_socket(self, sock: str) -> None:
        try:
            Path(sock).unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.debug("Could not remove stale socket %s: %s", sock, exc)

    def _build_mpv_command(self, mpv_bin: str, sock: str) -> list[str]:
        # Headless-friendly: this is an audio player, so never open a video
        # window (that fails over SSH / on servers without a display).
        cmd = [
            mpv_bin,
            "--idle=yes",
            "--no-video",
            "--vo=null",
            "--no-terminal",
            "--audio-display=no",
            "--input-ipc-server=" + sock,
            "--msg-level=all=warn",
        ]
        audio_output = settings.get("audio_output", "auto")
        if audio_output != "auto":
            cmd.append("--ao=" + str(audio_output))
        return cmd

    def _open_mpv_log(self) -> None:
        log_path = log_dir() / "mpv.log"
        log_dir().mkdir(parents=True, exist_ok=True)
        try:
            self._mpv_log = log_path.open("ab")
        except OSError:
            self._mpv_log = None

    def _launch_process(self, cmd: list[str], mpv_bin: str) -> None:
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=self._mpv_log or subprocess.DEVNULL,
                stderr=self._mpv_log or subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        except FileNotFoundError as exc:
            self._last_error = (
                f"mpv binary not found at '{mpv_bin}'. Install it with: sudo apt install mpv"
            )
            logger.error(self._last_error)
            self._close_mpv_log()
            self.ipc = None
            raise PlaybackError(self._last_error) from exc
        except Exception as exc:
            self._last_error = f"Failed to start mpv: {exc}"
            logger.exception(self._last_error)
            self._close_mpv_log()
            self.ipc = None
            raise PlaybackError(self._last_error) from exc

    def _wait_for_socket(self, sock: str, mpv_bin: str) -> None:
        for _ in range(50):  # up to 5 seconds
            if self._process is not None and self._process.poll() is not None:
                break
            if Path(sock).exists():
                return
            time.sleep(0.1)
        self._last_error = self._mpv_failure_message(mpv_bin, sock)
        logger.error(self._last_error)
        self._terminate_process()
        self._close_mpv_log()
        self.ipc = None
        raise PlaybackError(self._last_error)

    def _connect_new_socket(self, sock: str) -> None:
        self.ipc = MPVIPC(socket_path=sock)
        try:
            self.ipc.connect()
        except Exception as exc:
            self._last_error = f"Cannot connect to mpv IPC at {sock}: {exc}. {self._mpv_log_tail()}"
            logger.exception(self._last_error)
            self._terminate_process()
            self._close_mpv_log()
            self.ipc = None
            raise PlaybackError(self._last_error) from exc

    def _mpv_failure_message(self, mpv_bin: str, sock: str) -> str:
        tail = self._mpv_log_tail()
        parts = [f"mpv failed to start from '{mpv_bin}' (socket: {sock})."]
        if tail:
            parts.append(tail)
        parts.append("Try running 'mpv --no-video --vo=null --idle=yes' manually to see the error.")
        return " ".join(parts)

    def _mpv_log_tail(self, lines: int = 8) -> str:
        log_path = log_dir() / "mpv.log"
        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        tail = [line for line in content.splitlines() if line.strip()][-lines:]
        if not tail:
            return ""
        return "mpv stderr: " + " | ".join(tail)

    def _terminate_process(self) -> None:
        if self._process is None:
            return
        try:
            self._process.terminate()
            self._process.wait(timeout=2)
        except Exception:
            try:
                self._process.kill()
            except Exception:
                pass
        self._process = None

    def _close_mpv_log(self) -> None:
        log = self._mpv_log
        if log is None:
            return
        try:
            log.close()
        except Exception:
            pass
        self._mpv_log = None

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
            self._terminate_process()
            self._close_mpv_log()
            self.state = PlaybackState()
            logger.info("Playback stopped")

    def detach(self) -> None:
        """Detach from mpv without stopping it."""
        with self._lock:
            if self.ipc is not None:
                self.ipc.close()
                self.ipc = None
            self._close_mpv_log()
            logger.info("Detached from mpv (playback continues)")

    def get_last_error(self) -> Optional[str]:
        """Return the last playback error, if any."""
        return self._last_error

    # ------------------------------------------------------------------ #
    # Playback control
    # ------------------------------------------------------------------ #
    def begin_pending(self) -> None:
        """Mark a requested track as resolving before mpv gets the URL."""
        self.state.pending = True

    def load(
        self,
        url: str,
        title: str = "",
        channel: str = "",
        source: str = "YouTube",
    ) -> None:
        """Load and play a media URL."""
        if not self.is_running():
            if self._process is not None:
                self.stop()
            self.start_player()
        assert self.ipc is not None
        try:
            self.ipc.command("loadfile", url, "replace")
            # A previous pause must not carry over to the next track.
            self.ipc.set_property("pause", False)
            self.state.playing = True
            self.state.video_id = url
            self.state.title = title or url
            self.state.channel = channel or ""
            self.state.source = source or "YouTube"
            self.state.position = 0.0
            self.state.buffering = False
            self.state.idle = False
            self.state.pending = False
            self._refresh_state()
        except Exception as exc:
            self.state.pending = False
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

    def speed_up(self) -> None:
        """Increase playback speed by 0.25x, capped at 2.0x."""
        self.set_speed(min(2.0, round(self._speed + 0.25, 2)))

    def speed_down(self) -> None:
        """Decrease playback speed by 0.25x, floored at 0.25x."""
        self.set_speed(max(0.25, round(self._speed - 0.25, 2)))

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
            self.state.buffering = False
            return
        try:
            self.state.position = float(self.ipc.get_property("time-pos") or 0.0)
            self.state.duration = self.ipc.get_property("duration")
            self.state.playing = not bool(self.ipc.get_property("pause"))
            self.state.volume = int(self.ipc.get_property("volume") or self._volume)
            self.state.speed = float(self.ipc.get_property("speed") or self._speed)
            # mpv reports this while it is waiting for more data.
            self.state.buffering = bool(self.ipc.get_property("paused-for-cache"))
            self.state.idle = bool(self.ipc.get_property("idle-active"))
            if self.state.idle:
                self.state.playing = False
                self.state.buffering = False
        except Exception as exc:
            logger.debug("State refresh failed: %s", exc)

    def get_state(self) -> PlaybackState:
        self._refresh_state()
        return self.state

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #
    def diagnose(self) -> list[str]:
        """Run environment checks for playback and return human-readable lines."""
        lines: list[str] = []

        mpv_bin = find_mpv()
        mpv_resolved = shutil.which(mpv_bin)
        lines.append(f"mpv binary      : {mpv_resolved or 'NOT FOUND (' + mpv_bin + ')'}")
        if mpv_resolved:
            try:
                result = subprocess.run(
                    [mpv_resolved, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                version = (result.stdout.splitlines() or ["unknown"])[0]
                lines.append(f"mpv version     : {version}")
            except Exception as exc:
                lines.append(f"mpv version     : FAILED ({exc})")

        ytdlp_bin = str(settings.get("yt_dlp_path", "yt-dlp"))
        ytdlp_resolved = shutil.which(ytdlp_bin)
        lines.append(f"yt-dlp binary   : {ytdlp_resolved or 'NOT FOUND (' + ytdlp_bin + ')'}")

        lines.append(f"IPC socket      : {default_socket_path()}")
        lines.append(f"audio_output    : {settings.get('audio_output', 'auto')}")
        lines.append(f"mpv log         : {log_dir() / 'mpv.log'}")

        self.stop()
        try:
            self.start_player(force_new=True)
            pid = self._process.pid if self._process is not None else "?"
            lines.append(f"mpv launch      : OK (pid {pid})")
            self.stop()
            lines.append("playback        : OK")
        except PlaybackError as exc:
            lines.append("mpv launch      : FAILED")
            lines.append(f"  {exc}")
        return lines


playback = PlaybackService()
