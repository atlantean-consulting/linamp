from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Static

from linamp.messages import PlayerStateUpdate
from linamp.widgets.station_list import StationList
from linamp.widgets.playlist_panel import PlaylistPanel


class NowPlayingBar(Static):
    """Compact now-playing status bar for browser view."""

    DEFAULT_CSS = """
    NowPlayingBar {
        height: 1;
        dock: bottom;
        background: $accent;
        color: $text;
        padding: 0 1;
    }
    """

    def on_player_state_update(self, event: PlayerStateUpdate) -> None:
        if event.station and event.is_playing:
            title = event.icy_title or event.station.genre
            self.update(f"▶ {event.station.name}  ·  {title}")
        elif event.station and event.is_paused:
            self.update(f"⏸ {event.station.name}")
        else:
            self.update("■ Stopped")


class CommandHints(Static):
    """MC-style command hint bar for browser view."""

    DEFAULT_CSS = """
    CommandHints {
        height: 1;
        dock: bottom;
        background: #313244;
        color: #cdd6f4;
        padding: 0 1;
    }
    CommandHints .hint-key {
        color: #f9e2af;
        text-style: bold;
    }
    """

    def __init__(self) -> None:
        hints = (
            "[b #f9e2af]f[/] Folder  "
            "[b #f9e2af]a[/] Add  "
            "[b #f9e2af]d[/] Delete  "
            "[b #f9e2af]r[/] Rename  "
            "[b #f9e2af]e[/] Edit  "
            "[b #f9e2af]C-↑↓[/] Move  "
            "[b #f9e2af]Enter[/] Play  "
            "[b #f9e2af]Tab[/] View"
        )
        super().__init__(hints)


class BrowserView(Screen):
    """MC-style dual-pane browser view."""

    DEFAULT_CSS = """
    BrowserView {
        layout: vertical;
    }
    BrowserView Horizontal {
        height: 1fr;
    }
    BrowserView StationList {
        width: 1fr;
    }
    BrowserView PlaylistPanel {
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield StationList(library=self.app.library)
            yield PlaylistPanel(stations=self.app.flat_stations)
        yield NowPlayingBar("■ Stopped")
        yield CommandHints()
