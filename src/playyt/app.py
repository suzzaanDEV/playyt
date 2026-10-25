"""Main PlayYT Textual application."""

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, ListView, Static

from .database import HistoryRepository
from .integrations.ytdlp import YTDLP
from .services.authentication import auth
from .services.playback import playback
from .ui.bindings import NAVIGATION_BINDINGS
from .ui.content import (
    AccountPanel,
    ContentPanel,
    HistoryPanel,
    HomePanel,
    LibraryPanel,
    LikedPanel,
    PlaylistsPanel,
    QueuePanel,
    SearchPanel,
    SettingsPanel,
    SubscriptionsPanel,
)
from .ui.screens.help import HelpScreen
from .ui.screens.now_playing import NowPlayingScreen
from .ui.styles.theme import PLAYYT_THEME
from .ui.widgets.mini_player import MiniPlayer
from .ui.widgets.sidebar import Sidebar
from .utils.errors import PlaybackError
from .utils.logging import setup_logging

PANEL_CLASSES: dict[str, type[ContentPanel]] = {
    "home": HomePanel,
    "search": SearchPanel,
    "queue": QueuePanel,
    "playlists": PlaylistsPanel,
    "liked": LikedPanel,
    "history": HistoryPanel,
    "subscriptions": SubscriptionsPanel,
    "library": LibraryPanel,
    "account": AccountPanel,
    "settings": SettingsPanel,
}


class PlayYTApp(App[None]):
    """PlayYT terminal music player."""

    TITLE = "PlayYT"
    SUB_TITLE = "YouTube music for the terminal"

    CSS = """
    Screen {
        layout: vertical;
        background: #1e1e2e;
    }

    Header {
        background: #181825;
        border-bottom: solid #cba6f7;
        color: #cdd6f4;
        height: 3;
    }

    #sidebar {
        width: 26;
        background: #313244;
        border-right: solid #45475a;
        padding: 1;
    }

    #content {
        height: 1fr;
        padding: 0;
    }

    #mini-player {
        height: 3;
        background: #313244;
        border-top: solid #fab387;
        color: #cdd6f4;
        padding: 0 1;
    }

    #status {
        height: 1;
        background: #181825;
        border-top: solid #a6e3a1;
        color: #cdd6f4;
        padding: 0 1;
    }

    .title {
        text-style: bold;
        color: #89b4fa;
    }

    .section {
        text-style: bold;
        color: #fab387;
    }

    .panel-header {
        text-style: bold;
        color: #cdd6f4;
    }

    ListView {
        background: #1e1e2e;
        border: solid #45475a;
    }

    ListView:focus {
        border: solid #cba6f7;
    }

    ListItem {
        padding: 0 1;
        color: #cdd6f4;
    }

    ListItem.-highlight {
        background: #45475a;
        color: #f5e0dc;
    }

    ListItem.armed {
        background: #585b70;
        color: #f9e2af;
        text-style: bold;
    }

    #search-results-list ListItem {
        border-bottom: solid #313244;
    }

    #home-scroll,
    #search-scroll,
    #queue-scroll,
    #playlists-scroll,
    #liked-scroll,
    #history-scroll,
    #subscriptions-scroll,
    #library-scroll,
    #account-scroll,
    #settings-scroll {
        background: #1e1e2e;
        padding: 1;
    }

    #search-input {
        margin: 1 0;
        background: #313244;
        border: tall #45475a;
    }

    #search-input:focus {
        border: tall #cba6f7;
    }

    .search-result {
        color: #cdd6f4;
    }

    .separator {
        color: #45475a;
    }

    .panel {
        border: solid #45475a;
        padding: 1;
        margin: 0 1;
        height: 1fr;
    }

    .panel-purple {
        border: solid #cba6f7;
    }

    .panel-orange {
        border: solid #fab387;
    }

    .panel-green {
        border: solid #a6e3a1;
    }

    .panel-magenta {
        border: solid #cba6f7;
    }

    .panel-header {
        text-style: bold;
        color: #cdd6f4;
        margin-bottom: 1;
    }
    """

    BINDINGS: ClassVar[list] = [
        (b.key, b.action, b.description) for b in NAVIGATION_BINDINGS if b.show
    ]

    def __init__(self, debug: bool = False) -> None:
        super().__init__()
        setup_logging(debug=debug)
        self.current_panel: ContentPanel | None = None
        self.auth = auth

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Sidebar(id="sidebar")
            yield Vertical(id="content")
        yield MiniPlayer(id="mini-player")
        yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.register_theme(PLAYYT_THEME)
        self.theme = PLAYYT_THEME.name
        self.switch_panel("home")
        self.set_interval(1.0, self.refresh_status)
        # Focus the sidebar list so arrow keys work immediately
        self.query_one("#nav-list").focus()

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
    # Panel switching
    # ------------------------------------------------------------------ #
    def switch_panel(self, key: str) -> None:
        """Swap the content area to the given panel key."""
        content = self.query_one("#content", Vertical)
        content.remove_children()
        panel_cls = PANEL_CLASSES.get(key, HomePanel)
        panel = panel_cls(app_ref=self)
        content.mount(panel)
        self.current_panel = panel

    def notify_status(self, message: str) -> None:
        status = self.query_one("#status", Static)
        status.update(message)

    # ------------------------------------------------------------------ #
    # Navigation actions (bound to keys)
    # ------------------------------------------------------------------ #
    def action_quit(self) -> None:  # type: ignore[override]
        self.exit()

    def action_back(self) -> None:  # type: ignore[override]
        self.switch_panel("home")

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_home(self) -> None:
        self.switch_panel("home")

    def action_search(self) -> None:
        self.switch_panel("search")

    def action_queue(self) -> None:
        self.switch_panel("queue")

    def action_playlists(self) -> None:
        self.switch_panel("playlists")

    def action_liked(self) -> None:
        self.switch_panel("liked")

    def action_history(self) -> None:
        self.switch_panel("history")

    def action_subscriptions(self) -> None:
        self.switch_panel("subscriptions")

    def action_library(self) -> None:
        self.switch_panel("library")

    def action_account(self) -> None:
        self.switch_panel("account")

    def action_settings(self) -> None:
        self.switch_panel("settings")

    def on_list_view_selected(self, event) -> None:
        """Handle list item selection (sidebar navigation and search results)."""
        if event.list_view.id == "search-results-list":
            panel = self.current_panel
            if isinstance(panel, SearchPanel):
                panel.arm_selected()
            return
        if event.list_view.id != "nav-list":
            return
        item_id = event.item.id
        if item_id is None:
            return
        self.switch_panel(item_id)

    # ------------------------------------------------------------------ #
    # Search actions
    # ------------------------------------------------------------------ #
    def action_search_input(self) -> None:
        """Placeholder for search input handling from panels."""
        pass

    def play_video(self, video) -> None:
        """Resolve a video via yt-dlp and start playback, showing Now Playing."""
        ytdlp = YTDLP()
        try:
            resolved = ytdlp.resolve_url(video.video_id)
        except Exception as exc:
            self.notify(f"Failed to resolve media: {exc}")
            return
        try:
            playback.load(
                resolved["url"],
                title=resolved.get("title") or video.title,
                channel=resolved.get("channel") or video.channel,
            )
        except PlaybackError as exc:
            self.notify(f"  {exc}  |  Install mpv to play audio: sudo apt install mpv  ", timeout=5)
            self.notify_status(str(exc))
            return
        # Add to history
        try:
            HistoryRepository().add(
                video.video_id,
                resolved.get("title") or video.title,
                resolved.get("channel") or video.channel,
                resolved.get("duration"),
            )
        except Exception:
            pass
        self.push_screen(NowPlayingScreen(video=video))

    def authenticate(self) -> None:
        """Start OAuth device flow."""
        try:
            auth.authenticate()
            self.notify("Authentication successful.")
            self.switch_panel("account")
        except Exception as exc:
            self.notify(f"Authentication failed: {exc}")

    def logout(self) -> None:
        auth.logout()
        self.notify("Logged out.")
        self.switch_panel("account")

    # ------------------------------------------------------------------ #
    # Playback actions
    # ------------------------------------------------------------------ #
    def _run_playback(self, action) -> None:
        """Run a playback action, showing a user-friendly error if mpv is not running."""
        try:
            action()
        except PlaybackError as exc:
            msg = f"  {exc}  |  Search and press Enter on a track to play first.  "
            self.notify(msg, timeout=5)
            self.notify_status(str(exc))

    def action_toggle_playback(self) -> None:
        if self._play_focused_result():
            return
        self._run_playback(playback.play_pause)

    def _play_focused_result(self) -> bool:
        """Play the highlighted search result when a results list is focused."""
        focused = self.focused
        if not isinstance(focused, ListView) or focused.id != "search-results-list":
            return False
        panel = self.current_panel
        if not isinstance(panel, SearchPanel):
            return False
        if panel.get_selected_video() is None:
            return False
        panel.play_selected()
        return True

    def action_next_track(self) -> None:
        self._run_playback(playback.next_track)

    def action_previous_track(self) -> None:
        self._run_playback(playback.previous_track)

    def action_volume_up(self) -> None:
        self._run_playback(playback.volume_up)

    def action_volume_down(self) -> None:
        self._run_playback(playback.volume_down)

    def action_speed_up(self) -> None:
        self._run_playback(playback.speed_up)

    def action_speed_down(self) -> None:
        self._run_playback(playback.speed_down)

    def action_toggle_shuffle(self) -> None:
        self._run_playback(playback.toggle_shuffle)

    def action_toggle_repeat(self) -> None:
        self._run_playback(playback.toggle_repeat)

    def action_seek_backward(self) -> None:
        self._run_playback(lambda: playback.seek(-10))

    def action_seek_forward(self) -> None:
        self._run_playback(lambda: playback.seek(10))
