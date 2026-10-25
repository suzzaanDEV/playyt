"""Cassette reel visualization for the Now Playing screen.

The renderer is deliberately dependency-free and returns a Rich markup string
so it can be unit tested without a terminal. All drawing uses plain ASCII
characters plus a single Unicode marker, with an ASCII fallback, which keeps it
readable on limited terminals and over SSH.
"""

from __future__ import annotations

import os
import sys
from typing import Final

from textual import events
from textual.timer import Timer
from textual.widgets import Static

FRAME_INTERVAL: Final = 0.18
FRAME_COUNT: Final = 8

# 7 rows x 13 cols. Spokes and hub are drawn once; a bright marker travels
# around the eight ring positions to create the rotation illusion.
_LARGE_REEL: Final = (
    "    .---.    ",
    "   /  |  \\   ",
    "  |   |   |  ",
    "  |---o---|  ",
    "  |   |   |  ",
    "   \\  |  /   ",
    "    '---'    ",
)
_LARGE_MARKERS: Final = (
    (3, 9),
    (4, 9),
    (5, 6),
    (4, 3),
    (3, 3),
    (2, 3),
    (1, 6),
    (2, 9),
)

# 5 rows x 9 cols.
_SMALL_REEL: Final = (
    "  .-.-.  ",
    " /  |  \\ ",
    "|   o   |",
    " \\  |  / ",
    "  '-.-'  ",
)
_SMALL_MARKERS: Final = (
    (2, 7),
    (3, 6),
    (4, 4),
    (3, 3),
    (2, 1),
    (1, 2),
    (1, 4),
    (1, 6),
)

# 3 rows x 7 cols.
_TINY_REEL: Final = (
    " .---. ",
    "(  o  )",
    " '---' ",
)
_TINY_MARKERS: Final = (
    (0, 3),
    (0, 5),
    (1, 6),
    (2, 5),
    (2, 3),
    (2, 1),
    (1, 0),
    (0, 1),
)

_WHEEL_COLOR: Final = "grey50"
_FRAME_COLOR: Final = "grey35"
_HUB_COLOR: Final = "bright_white"
_LEFT_COLOR: Final = "bright_cyan"
_RIGHT_COLOR: Final = "bright_magenta"


def detect_unicode_support() -> bool:
    """Return True when the terminal can render a Unicode marker."""
    override = os.environ.get("PLAYYT_ASCII", "").strip().lower()
    if override in {"1", "true", "yes", "on"}:
        return False
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower()
    if "utf" in encoding:
        return True
    for name in ("LC_ALL", "LC_CTYPE", "LANG"):
        value = os.environ.get(name)
        if value:
            return "utf" in value.lower()
    return True


def _decorate_line(
    line: str,
    row: int,
    marker_pos: tuple[int, int],
    marker: str,
    marker_color: str,
) -> str:
    marker_row, marker_col = marker_pos
    pieces: list[str] = []
    for col, char in enumerate(line):
        if row == marker_row and col == marker_col:
            pieces.append(f"[bold {marker_color}]{marker}[/]")
        elif char == "o":
            pieces.append(f"[{_HUB_COLOR}]{char}[/]")
        else:
            pieces.append(char)
    return f"[{_WHEEL_COLOR}]{''.join(pieces)}[/]"


def _reel(
    template: tuple[str, ...],
    markers: tuple[tuple[int, int], ...],
    frame: int,
    marker: str,
    color: str,
) -> list[str]:
    position = markers[frame % FRAME_COUNT]
    return [_decorate_line(line, row, position, marker, color) for row, line in enumerate(template)]


def _frame_lines(rows: list[str], inner_width: int, unicode_ok: bool) -> list[str]:
    if unicode_ok:
        horizontal, vertical = "─", "│"
        top_left, top_right, bottom_left, bottom_right = "╭", "╮", "╰", "╯"
    else:
        horizontal, vertical = "-", "|"
        top_left = top_right = bottom_left = bottom_right = "+"
    rule = horizontal * (inner_width + 2)
    top = f"[{_FRAME_COLOR}]{top_left}{rule}{top_right}[/]"
    bottom = f"[{_FRAME_COLOR}]{bottom_left}{rule}{bottom_right}[/]"
    sides = [f"[{_FRAME_COLOR}]{vertical}[/] {row} [{_FRAME_COLOR}]{vertical}[/]" for row in rows]
    return [top, *sides, bottom]


def render_cassette(width: int, frame: int = 0, unicode_ok: bool = True) -> str:
    """Render two cassette reels, adapting to the available terminal width."""
    marker = "●" if unicode_ok else "*"

    template: tuple[str, ...]
    markers: tuple[tuple[int, int], ...]
    gap: str
    framed: bool

    if width >= 44:
        template, markers, gap, framed = _LARGE_REEL, _LARGE_MARKERS, "      ", True
    elif width >= 30:
        template, markers, gap, framed = _SMALL_REEL, _SMALL_MARKERS, "    ", True
    elif width >= 18:
        template, markers, gap, framed = _TINY_REEL, _TINY_MARKERS, "  ", False
    else:
        return (
            f"[{_WHEEL_COLOR}]([/][bold {_LEFT_COLOR}]{marker}[/][{_WHEEL_COLOR}])[/]"
            f"   "
            f"[{_WHEEL_COLOR}]([/][bold {_RIGHT_COLOR}]{marker}[/][{_WHEEL_COLOR}])[/]"
        )

    left = _reel(template, markers, frame, marker, _LEFT_COLOR)
    # Start the right reel opposite the left one and rotate counter-clockwise.
    right = _reel(template, markers, FRAME_COUNT // 2 - frame, marker, _RIGHT_COLOR)
    rows = [f"{left_row}{gap}{right_row}" for left_row, right_row in zip(left, right, strict=True)]

    if framed:
        inner_width = len(template[0]) * 2 + len(gap)
        rows = _frame_lines(rows, inner_width, unicode_ok)
    return "\n".join(rows)


class CassetteReels(Static):
    """Animated cassette reels driven by real playback state."""

    DEFAULT_CSS = """
    CassetteReels {
        width: 100%;
        height: auto;
        text-align: center;
        padding: 1 0;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._frame = 0
        self._timer: Timer | None = None
        self._animating = False
        self._playing = False
        self._buffering = False
        self._unicode = detect_unicode_support()

    @property
    def is_animating(self) -> bool:
        """Whether the reel animation is currently running."""
        return self._animating

    def on_mount(self) -> None:
        self._refresh_view()

    def set_playback(self, playing: bool, buffering: bool = False) -> None:
        """Sync the reels with playback state, stopping when paused or buffering."""
        should_animate = playing and not buffering
        changed = (playing, buffering) != (self._playing, self._buffering)
        self._playing = playing
        self._buffering = buffering

        if should_animate:
            if self._timer is None:
                self._timer = self.set_interval(FRAME_INTERVAL, self._tick)
            self._timer.resume()
        elif self._timer is not None:
            self._timer.pause()

        self._animating = should_animate
        if changed or not should_animate:
            self._refresh_view()

    def _tick(self) -> None:
        if not self._animating:
            return
        self._frame = (self._frame + 1) % FRAME_COUNT
        self._refresh_view()

    def _refresh_view(self) -> None:
        width = self.size.width
        if not width:
            try:
                width = self.app.size.width
            except Exception:
                width = 80
        self.update(render_cassette(width, self._frame, self._unicode))

    def on_resize(self, event: events.Resize) -> None:
        self._refresh_view()

    def on_unmount(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self._animating = False
