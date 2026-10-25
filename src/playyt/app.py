"""Main PlayYT Textual application."""

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, ListView, Static

from .integrations.ytdlp import YTDLP
from .services.playback import playback
from .ui.bindings import NAVIGATION_BINDINGS
from .ui.screens.account import AccountScreen
from .ui.screens.help import HelpScreen
from .ui.screens.home import HomeScreen
from .ui.screens.now_playing import NowPlayingScreen
from .ui.screens.queue import QueueScreen
from .ui.screens.search import SearchScreen
from .ui.styles.theme import PLAYYT_THEME
from .ui.widgets.mini_player import MiniPlayer
from .ui.widgets.sidebar import Sidebar
from .utils.logging import setup_logging


class PlayYTApp(App[None]):
    """PlayYT terminal music player."""

    TITLE = "PlayYT"
    SUB_TITLE = "YouTube music for the terminal"

    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
    }

    #sidebar {
        width: 26;
        background: $panel;
        border-right: solid $border;
        padding: 1;
    }

    #content {
        height: 1fr;
        padding: 1 2;
    }

    #mini-player {
        height: 3;
        background: $panel;
        border-top: solid $border;
        padding: 0 1;
    }

    #status {
        height: 1;
        background: $panel;
        border-top: solid $border;
        color: $text-secondary;
        padding: 0 1;
    }

    .title {
        text-style: bold;
        color: $primary;
    }

    .section {
        text-style: bold;
        color: $text-secondary;
    }
    """

    BINDINGS: ClassVar[list] = [
        (b.key, b.action, b.description) for b in NAVIGATION_BINDINGS if b.show
    ]

    def __init__(self, debug: bool = False) -> None:
        super().__init__()
        setup_logging(debug=debug)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Sidebar(id="sidebar")
            yield Vertical(Static(id="content-home", classes="title"), id="content")
        yield MiniPlayer(id="mini-player")
        yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(PLAYYT_THEME)
        self.theme = PLAYYT_THEME.name
        self.push_screen(HomeScreen())
        self.set_interval(1.0, self.refresh_status)

    def refresh_status(self) -> None:
        state = playback.get_state()
        if state.video_id is None:
            self.notify_status("No track playing   |   ? for help")
            return
        title = state.title or "Unknown"
        channel = state.channel or ""
        marker = ">" if state.playing else "||"
        self.notify_status(f"{title}  ·  {channel}   {marker}   {state.volume}%   |   ? for help")

    # ------------------------------------------------------------------ #
    # Navigation actions
    # ------------------------------------------------------------------ #
    def action_quit(self) -> None:  # type: ignore[override]
        self.exit()

    def action_back(self) -> None:  # type: ignore[override]
        self.pop_screen()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_home(self) -> None:
        self.push_screen(HomeScreen())

    def action_search(self) -> None:
        self.push_screen(SearchScreen())

    def action_queue(self) -> None:
        self.push_screen(QueueScreen())

    def action_playlists(self) -> None:
        self.notify("Playlists: browse your YouTube playlists (requires login).")

    def action_liked(self) -> None:
        self.notify("Liked: browse your liked videos (requires login).")

    def action_history(self) -> None:
        self.notify("History: local play history.")

    def action_subscriptions(self) -> None:
        self.notify("Subscriptions: your subscribed channels (requires login).")

    def action_library(self) -> None:
        self.notify("Library: your saved content.")

    def action_account(self) -> None:
        self.push_screen(AccountScreen())

    def action_settings(self) -> None:
        self.notify("Settings: configure playback and appearance.")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "nav-list":
            return
        item_id = event.item.id
        if item_id is None:
            return
        screen_map = {
            "home": lambda: self.push_screen(HomeScreen()),
            "search": lambda: self.push_screen(SearchScreen()),
            "queue": lambda: self.push_screen(QueueScreen()),
            "account": lambda: self.push_screen(AccountScreen()),
        }
        action = screen_map.get(item_id)
        if action:
            action()

    def notify_status(self, message: str) -> None:
        status = self.query_one("#status", Static)
        status.update(message)

    # ------------------------------------------------------------------ #
    # Playback actions
    # ------------------------------------------------------------------ #
    def action_toggle_playback(self) -> None:
        playback.play_pause()

    def action_next_track(self) -> None:
        playback.next_track()

    def action_previous_track(self) -> None:
        playback.previous_track()

    def action_volume_up(self) -> None:
        playback.volume_up()

    def action_volume_down(self) -> None:
        playback.volume_down()

    def action_toggle_shuffle(self) -> None:
        playback.toggle_shuffle()

    def action_toggle_repeat(self) -> None:
        playback.toggle_repeat()

    def action_seek_backward(self) -> None:
        playback.seek(-10)

    def action_seek_forward(self) -> None:
        playback.seek(10)

    # ------------------------------------------------------------------ #
    # Video playback
    # ------------------------------------------------------------------ #
    def play_video(self, video) -> None:
        """Resolve a video via yt-dlp and start playback, showing Now Playing."""
        ytdlp = YTDLP()
        try:
            resolved = ytdlp.resolve_url(video.video_id)
        except Exception as exc:
            self.notify(f"Failed to resolve media: {exc}")
            return
        playback.load(
            resolved["url"],
            title=resolved.get("title") or video.title,
            channel=resolved.get("channel") or video.channel,
        )
        self.push_screen(NowPlayingScreen(video=video))
