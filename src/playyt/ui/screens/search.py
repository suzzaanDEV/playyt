"""Search screen."""

from __future__ import annotations

from typing import Any, cast

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Label, ListItem, ListView, Static

from ...services.search import SearchService


class SearchScreen(Screen):
    """Search YouTube and play results."""

    def __init__(self) -> None:
        super().__init__()
        self.search_service = SearchService()
        self.results: list = []

    def compose(self) -> ComposeResult:
        yield Static("Search YouTube", id="search-title")
        yield Static("")
        yield Input(placeholder="Search YouTube...", id="search-input")
        yield Static("")
        yield Label("Press Enter on a result to play.", id="search-hint")
        yield VerticalScroll(ListView(id="search-results"))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "search-input":
            return
        query = event.value.strip()
        if not query:
            return
        self._run_search(query)

    def _run_search(self, query: str) -> None:
        try:
            self.results = self.search_service.search(query)
        except Exception as exc:
            self.notify(f"Search failed: {exc}")
            return
        list_view = self.query_one("#search-results", ListView)
        list_view.clear()
        for video in self.results:
            label = f"{video.title}"
            if video.channel:
                label += f"  ·  {video.channel}"
            if video.duration:
                mins, secs = divmod(int(video.duration), 60)
                label += f"  ({mins}:{secs:02d})"
            list_view.append(ListItem(Label(label), id=video.video_id))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        video_id = item.id
        video = next((v for v in self.results if v.video_id == video_id), None)
        if video is None:
            return
        self.notify(f"Resolving: {video.title}")
        cast(Any, self.app).play_video(video)
