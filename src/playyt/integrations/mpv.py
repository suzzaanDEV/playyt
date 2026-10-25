"""mpv IPC integration for PlayYT playback."""

from __future__ import annotations

import json
import os
import socket
import threading
from pathlib import Path
from typing import Any

from ..utils.errors import MPVError
from ..utils.logging import get_logger

logger = get_logger("mpv")


class MPVIPC:
    """Client for mpv's JSON IPC interface."""

    def __init__(self, socket_path: str | None = None, timeout: float = 5.0) -> None:
        self.socket_path = socket_path or self._default_socket_path()
        self.timeout = timeout
        self._sock: socket.socket | None = None
        self._lock = threading.RLock()
        self._connected = False

    @staticmethod
    def _default_socket_path() -> str:
        runtime = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
        return str(Path(runtime) / "mpvplayyt.sock")

    def connect(self) -> None:
        with self._lock:
            if self._connected:
                return
            try:
                self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self._sock.settimeout(self.timeout)
                self._sock.connect(self.socket_path)
                self._sock.settimeout(None)
                self._connected = True
                logger.debug("Connected to mpv IPC at %s", self.socket_path)
            except (FileNotFoundError, ConnectionRefusedError, OSError) as exc:
                self._sock = None
                self._connected = False
                raise MPVError(f"Cannot connect to mpv IPC socket: {self.socket_path}") from exc

    def close(self) -> None:
        with self._lock:
            if self._sock is not None:
                try:
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None
            self._connected = False

    def _send(self, command: dict[str, Any]) -> dict[str, Any]:
        if not self._connected:
            self.connect()
        assert self._sock is not None
        payload = (json.dumps(command) + "\n").encode("utf-8")
        with self._lock:
            try:
                self._sock.sendall(payload)
            except OSError as exc:
                self._connected = False
                raise MPVError(f"Failed to send command to mpv: {exc}") from exc
            return self._read_response()

    def _read_response(self) -> dict[str, Any]:
        assert self._sock is not None
        buffer = b""
        while True:
            try:
                chunk = self._sock.recv(4096)
            except OSError as exc:
                self._connected = False
                raise MPVError(f"Failed to read from mpv: {exc}") from exc
            if not chunk:
                self._connected = False
                raise MPVError("mpv closed the IPC connection")
            buffer += chunk
            if b"\n" in buffer:
                line, _ = buffer.split(b"\n", 1)
                try:
                    return json.loads(line.decode("utf-8"))  # type: ignore[no-any-return]
                except json.JSONDecodeError as exc:
                    raise MPVError(f"Invalid JSON from mpv: {line!r}") from exc

    def command(self, name: str, *args: Any) -> dict[str, Any]:
        return self._send({"command": [name, *args]})

    def get_property(self, name: str) -> Any:
        resp = self._send({"get_property": name})
        if resp.get("error") != "success":
            raise MPVError(f"Failed to get property {name}: {resp.get('error')}")
        return resp.get("data")

    def set_property(self, name: str, value: Any) -> dict[str, Any]:
        return self._send({"set_property": name, "value": value})


def find_existing_socket() -> str | None:
    """Look for an existing PlayYT mpv IPC socket."""
    candidates = [
        os.environ.get("XDG_RUNTIME_DIR", "/tmp") + "/mpvplayyt.sock",
        "/tmp/mpvplayyt.sock",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    return None
