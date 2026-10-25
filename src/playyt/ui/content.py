"""Content panels for the main content area (swappable)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import Input, ListItem, ListView, Static

from ..database import HistoryRepository, PlaylistRepository, QueueRepository
from ..models.video import Video
from ..services.authentication import auth
from ..services.playback import playback
from ..services.search import SearchService
from ..services.youtube import youtube
from ..utils.errors import YouTubeAPIError
from ..utils.logging import get_logger

logger = get_logger("content")

NAV_ITEMS = [
    ("home", "Home"),
    ("search", "Search"),
    ("queue", "Queue"),
    ("playlists", "Playlists"),
    ("liked", "Liked"),
    ("history", "History"),
    ("subscriptions", "Subscriptions"),
    ("library", "Library"),
    ("account", "Account"),
    ("settings", "Settings"),
]


class ContentPanel(Widget):
    """Base content panel."""

    def __init__(self, app_ref, **kwargs) -> None:
        super().__init__(**kwargs)
        self.app_ref = app_ref

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        pass


class HomePanel(ContentPanel):
    """Home panel showing recently played and playlists."""

    def compose(self) -> ComposeResult:
        with Container(classes="panel panel-purple"):
            yield Static("Home", classes="panel-header")
            yield Static("")
            with VerticalScroll(id="home-scroll"):
                yield Static("Recently Played", classes="section")
                yield Static(id="home-recent-list")
                yield Static("")
                yield Static("Your Playlists", classes="section")
                yield Static(id="home-playlist-list")
                yield Static("")
                yield Static("Quick Start", classes="section")
                yield Static(
                    "Use Search to find music, or open Account to log in.",
                    id="home-quickstart",
                )

    def refresh_content(self) -> None:
        self._refresh_recent()
        self._refresh_playlists()

    def _refresh_recent(self) -> None:
        try:
            repo = HistoryRepository()
            items = repo.recent(8)
            widget = self.query_one("#home-recent-list", Static)
            if not items:
                widget.update("(empty)")
                return
            lines = []
            for item in items:
                title = item.get("title", "Unknown")
                channel = item.get("channel") or ""
                line = f"  {title}"
                if channel:
                    line += f"  ·  {channel}"
                lines.append(line)
            widget.update("\n".join(lines))
        except Exception as exc:
            logger.warning("Failed to load recent history: %s", exc)
            self.query_one("#home-recent-list", Static).update(f"(error loading: {exc})")

    def _refresh_playlists(self) -> None:
        try:
            repo = PlaylistRepository()
            items = repo.list()
            widget = self.query_one("#home-playlist-list", Static)
            if not items:
                widget.update("(none)")
                return
            lines = []
            for item in items:
                title = item.get("title", "Unknown")
                count = item.get("video_count", 0)
                lines.append(f"  {title}  ({count} videos)")
            widget.update("\n".join(lines))
        except Exception as exc:
            logger.warning("Failed to load playlists: %s", exc)
            self.query_one("#home-playlist-list", Static).update(f"(error loading: {exc})")


class SearchPanel(ContentPanel):
    """Search panel with input and results list."""

    def __init__(self, app_ref, **kwargs) -> None:
        super().__init__(app_ref, **kwargs)
        self.search_service = SearchService()
        self.results: list = []
        self.selected_index = 0
        self._searching = False

    def compose(self) -> ComposeResult:
        with Container(classes="panel panel-orange"):
            yield Static("Search YouTube", classes="panel-header")
            yield Static("")
            yield Static("Type a query and press Enter:", id="search-hint")
            yield Input(placeholder="Search YouTube...", id="search-input")
            yield Static(id="search-query-display")
            yield Static("")
            yield Static("Results", classes="section")
            with VerticalScroll(id="search-scroll"):
                yield ListView(id="search-results-list")
            yield Static(id="search-status")
            yield Static(id="search-spinner")

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#search-results-list", ListView).can_focus = True

    def refresh_content(self) -> None:
        pass

    def set_query(self, query: str) -> None:
        self.query_one("#search-query-display", Static).update(f"Query: {query}")

    def _start_spinner(self) -> None:
        self._searching = True
        self._spinner_frames = [
            "[=>   ]",
            "[==>  ]",
            "[===> ]",
            "[====>]",
            "[ ===>]",
            "[  ==>]",
            "[   =>]",
            "[    >]",
        ]
        self._spinner_idx = 0
        self._spinner_interval = self.set_interval(0.08, self._tick_spinner)
        self.query_one("#search-spinner", Static).update("  searching...  ")

    def _stop_spinner(self) -> None:
        self._searching = False
        if hasattr(self, "_spinner_interval"):
            self._spinner_interval.stop()
        self.query_one("#search-spinner", Static).update("")

    def _tick_spinner(self) -> None:
        if not self._searching:
            return
        frame = self._spinner_frames[self._spinner_idx % len(self._spinner_frames)]
        self.query_one("#search-spinner", Static).update(f"  {frame} searching YouTube...  ")
        self._spinner_idx += 1

    def run_search(self, query: str) -> None:
        if not query.strip():
            return
        self.set_query(query)
        self._start_spinner()
        self.query_one("#search-results-list", ListView).clear()
        self.query_one("#search-status", Static).update("")
        try:
            self.results = self.search_service.search(query)
        except YouTubeAPIError as exc:
            self._stop_spinner()
            self.query_one("#search-status", Static).update(f"Search failed: {exc}")
            return
        except Exception as exc:
            self._stop_spinner()
            self.query_one("#search-status", Static).update(f"Search failed: {exc}")
            return

        self._stop_spinner()
        list_view = self.query_one("#search-results-list", ListView)
        list_view.clear()
        self.selected_index = 0
        for idx, video in enumerate(self.results):
            if idx > 0:
                list_view.append(ListItem(Static("  " + "-" * 35), id=f"sep_{idx}"))
            label = f"  {video.title}"
            if video.channel:
                label += f"  ·  {video.channel}"
            if video.duration:
                mins, secs = divmod(int(video.duration), 60)
                label += f"  ({mins}:{secs:02d})"
            list_view.append(ListItem(Static(label), id=f"vid_{video.video_id}"))
        self.query_one("#search-status", Static).update(f"{len(self.results)} results")

    def get_selected_video(self) -> Video | None:
        list_view = self.query_one("#search-results-list", ListView)
        highlighted = list_view.highlighted_child
        if highlighted is None:
            return None
        item_id = highlighted.id or ""
        if item_id.startswith("sep_"):
            return None
        video_id = item_id[len("vid_") :] if item_id.startswith("vid_") else item_id
        if not video_id:
            return None
        return next((v for v in self.results if v.video_id == video_id), None)

    def play_selected(self) -> None:
        video = self.get_selected_video()
        if video is None:
            self.query_one("#search-status", Static).update("No result selected")
            return
        self.query_one("#search-status", Static).update(f"Loading: {video.title}...")
        self.app_ref.play_video(video)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "search-input":
            return
        self.run_search(event.value)


class QueuePanel(ContentPanel):
    """Queue panel showing the playback queue."""

    def compose(self) -> ComposeResult:
        with Container(classes="panel panel-orange"):
            yield Static("Queue", classes="panel-header")
            yield Static("")
            with VerticalScroll(id="queue-scroll"):
                yield Static(id="queue-list")

    def refresh_content(self) -> None:
        try:
            repo = QueueRepository()
            items = repo.list()
            widget = self.query_one("#queue-list", Static)
            if not items:
                widget.update("(empty)")
                return
            lines = []
            for idx, item in enumerate(items, start=1):
                title = item.get("title", "Unknown")
                channel = item.get("channel") or ""
                line = f"  {idx}  {title}"
                if channel:
                    line += f"  ·  {channel}"
                lines.append(line)
            widget.update("\n".join(lines))
        except Exception as exc:
            logger.warning("Failed to load queue: %s", exc)
            self.query_one("#queue-list", Static).update(f"(error loading: {exc})")


class AccountPanel(ContentPanel):
    """Account panel showing auth status."""

    def compose(self) -> ComposeResult:
        self.auth = auth
        with Container(classes="panel panel-green"):
            yield Static("Account", classes="panel-header")
            yield Static("")
            with VerticalScroll(id="account-scroll"):
                yield Static(id="account-status")
                yield Static("")
                yield Static(id="account-hint")
                yield Static("")
                yield Static(id="account-actions")

    def refresh_content(self) -> None:
        status_widget = self.query_one("#account-status", Static)
        hint_widget = self.query_one("#account-hint", Static)
        actions_widget = self.query_one("#account-actions", Static)

        if self.auth.is_authenticated():
            status_widget.update("Status: Connected")
            hint_widget.update("Your YouTube account is linked.")
            actions_widget.update("Use Playlists, Subscriptions, Liked to browse your content.")
        else:
            status_widget.update("Status: Not connected")
            hint_widget.update("")
            actions_widget.update(
                "Set PLAYYT_CLIENT_ID and PLAYYT_CLIENT_SECRET, then authenticate."
            )


class PlaylistsPanel(ContentPanel):
    """Playlists panel showing user playlists."""

    def compose(self) -> ComposeResult:
        with Container(classes="panel panel-magenta"):
            yield Static("Playlists", classes="panel-header")
            yield Static("")
            with VerticalScroll(id="playlists-scroll"):
                yield Static(id="playlists-list")

    def refresh_content(self) -> None:
        try:
            repo = PlaylistRepository()
            items = repo.list()
            widget = self.query_one("#playlists-list", Static)
            if not items:
                widget.update("(none)")
                return
            lines = []
            for item in items:
                title = item.get("title", "Unknown")
                count = item.get("video_count", 0)
                lines.append(f"  {title}  ({count} videos)")
            widget.update("\n".join(lines))
        except Exception as exc:
            logger.warning("Failed to load playlists: %s", exc)
            self.query_one("#playlists-list", Static).update(f"(error loading: {exc})")


class LikedPanel(ContentPanel):
    """Liked videos panel."""

    def compose(self) -> ComposeResult:
        with Container(classes="panel panel-magenta"):
            yield Static("Liked", classes="panel-header")
            yield Static("")
            with VerticalScroll(id="liked-scroll"):
                yield Static(id="liked-list")

    def refresh_content(self) -> None:
        widget = self.query_one("#liked-list", Static)
        if not self.app_ref.auth.is_authenticated():
            widget.update("Authentication required to view liked videos.")
            return
        try:
            data = youtube.videos_list("myRating=like") if hasattr(youtube, "videos_list") else {}
            items = data.get("items", [])
            if not items:
                widget.update("(none)")
                return
            lines = []
            for item in items:
                snippet = item.get("snippet", {})
                title = snippet.get("title", "Unknown")
                channel = snippet.get("channelTitle", "")
                lines.append(f"  {title}")
                if channel:
                    lines[-1] += f"  ·  {channel}"
            widget.update("\n".join(lines))
        except Exception as exc:
            logger.warning("Failed to load liked videos: %s", exc)
            widget.update(f"(error loading: {exc})")


class HistoryPanel(ContentPanel):
    """Local history panel."""

    def compose(self) -> ComposeResult:
        with Container(classes="panel panel-green"):
            yield Static("History", classes="panel-header")
            yield Static("")
            with VerticalScroll(id="history-scroll"):
                yield Static(id="history-list")

    def refresh_content(self) -> None:
        try:
            repo = HistoryRepository()
            items = repo.recent(20)
            widget = self.query_one("#history-list", Static)
            if not items:
                widget.update("(empty)")
                return
            lines = []
            for item in items:
                title = item.get("title", "Unknown")
                channel = item.get("channel") or ""
                line = f"  {title}"
                if channel:
                    line += f"  ·  {channel}"
                lines.append(line)
            widget.update("\n".join(lines))
        except Exception as exc:
            logger.warning("Failed to load history: %s", exc)
            self.query_one("#history-list", Static).update(f"(error loading: {exc})")


class SubscriptionsPanel(ContentPanel):
    """Subscriptions panel."""

    def compose(self) -> ComposeResult:
        with Container(classes="panel panel-purple"):
            yield Static("Subscriptions", classes="panel-header")
            yield Static("")
            with VerticalScroll(id="subscriptions-scroll"):
                yield Static(id="subscriptions-list")

    def refresh_content(self) -> None:
        widget = self.query_one("#subscriptions-list", Static)
        if not self.app_ref.auth.is_authenticated():
            widget.update("Authentication required to view subscriptions.")
            return
        try:
            data = youtube.subscriptions_list()
            items = data.get("items", [])
            if not items:
                widget.update("(none)")
                return
            lines = []
            for item in items:
                snippet = item.get("snippet", {})
                title = snippet.get("title", "Unknown")
                lines.append(f"  {title}")
            widget.update("\n".join(lines))
        except Exception as exc:
            logger.warning("Failed to load subscriptions: %s", exc)
            widget.update(f"(error loading: {exc})")


class LibraryPanel(ContentPanel):
    """Library panel."""

    def compose(self) -> ComposeResult:
        with Container(classes="panel panel-purple"):
            yield Static("Library", classes="panel-header")
            yield Static("")
            with VerticalScroll(id="library-scroll"):
                yield Static(id="library-list")

    def refresh_content(self) -> None:
        widget = self.query_one("#library-list", Static)
        widget.update("Your saved content will appear here.")


class SettingsPanel(ContentPanel):
    """Settings panel."""

    def compose(self) -> ComposeResult:
        with Container(classes="panel panel-purple"):
            yield Static("Settings", classes="panel-header")
            yield Static("")
            with VerticalScroll(id="settings-scroll"):
                yield Static(id="settings-list")

    def refresh_content(self) -> None:
        widget = self.query_one("#settings-list", Static)
        lines = [
            "  Volume: " + str(playback.state.volume) + "%",
            "  Speed: " + str(playback.state.speed) + "x",
            "  Shuffle: " + ("on" if playback.state.shuffle else "off"),
            "  Repeat: " + playback.state.repeat,
        ]
        widget.update("\n".join(lines))
