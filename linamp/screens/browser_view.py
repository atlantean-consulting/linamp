from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Static

from linamp.config import load_config
from linamp.messages import PlaylistModeChanged, StationSelected
from linamp.widgets.now_playing_bar import NowPlayingBar
from linamp.widgets.station_list import StationList
from linamp.widgets.playlist_panel import PlaylistPanel
from linamp.widgets.file_browser import FileBrowser


RADIO_HINTS = (
    "[b #f9e2af]f[/] Folder  "
    "[b #f9e2af]a[/] Add  "
    "[b #f9e2af]d[/] Delete  "
    "[b #f9e2af]r[/] Rename  "
    "[b #f9e2af]e[/] Edit  "
    "[b #f9e2af]C-↑↓[/] Move  "
    "[b #f9e2af]Enter[/] Play  "
    "[b #f9e2af]Tab[/] View"
)

LOCAL_HINTS = (
    "[b #f9e2af]Enter[/] Add to queue  "
    "[b #f9e2af]p[/] Play  "
    "[b #f9e2af]Tab[/] View  "
    "[b #f9e2af]F1[/] Radio"
)


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
    """


class BrowserView(Screen):
    """MC-style dual-pane browser view — mode-aware.

    Radio mode: StationList (left) + PlaylistPanel (right)
    Local mode: FileBrowser (left) + PlaylistPanel (right)
    """

    BINDINGS = [
        Binding("p", "play_queue", "Play", priority=True),
    ]

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
    BrowserView FileBrowser {
        width: 1fr;
    }
    BrowserView PlaylistPanel {
        width: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        is_local = self.app.playlist_mode == "local"
        config = load_config()
        music_root = Path(config.music_root).expanduser()

        with Horizontal():
            station_list = StationList(library=self.app.library)
            station_list.display = not is_local
            yield station_list

            file_browser = FileBrowser(root=music_root)
            file_browser.display = is_local
            yield file_browser

            yield PlaylistPanel(stations=self.app.active_playlist)

        yield NowPlayingBar("■ Stopped")
        yield CommandHints(LOCAL_HINTS if is_local else RADIO_HINTS)

    async def on_screen_resume(self) -> None:
        """Refresh pane visibility and playlist when returning to this screen."""
        self._sync_mode()
        panel = self.query_one(PlaylistPanel)
        await panel.set_stations(self.app.active_playlist)

    def _sync_mode(self) -> None:
        """Sync left pane visibility and hints to the current playlist mode."""
        is_local = self.app.playlist_mode == "local"

        station_list = self.query_one(StationList)
        file_browser = self.query_one(FileBrowser)
        station_list.display = not is_local
        file_browser.display = is_local

        hints = self.query_one(CommandHints)
        hints.update(LOCAL_HINTS if is_local else RADIO_HINTS)

    def on_playlist_mode_changed(self, event: PlaylistModeChanged) -> None:
        """Toggle left pane and hints when playlist mode switches."""
        self._sync_mode()

        # Focus the visible left pane
        if self.app.playlist_mode == "local":
            self.query_one(FileBrowser).focus()
        else:
            self.query_one(StationList).focus()

    async def on_station_selected(self, event: StationSelected) -> None:
        """In local mode, queue files without playing."""
        if self.app.playlist_mode != "local":
            return  # Let it bubble to app for radio mode (play behavior)

        if not event.station.url.startswith("/"):
            return  # Not a local file, let it bubble

        # Add to local queue (deduplicate by URL)
        if not any(s.url == event.station.url for s in self.app.local_queue):
            self.app.local_queue.append(event.station)

        # Refresh the playlist panel
        panel = self.query_one(PlaylistPanel)
        await panel.set_stations(self.app.local_queue)

        # Stop propagation — don't let app.on_station_selected play it
        event.stop()

    def action_play_queue(self) -> None:
        """Start playing the local queue from the beginning."""
        if self.app.playlist_mode != "local":
            return
        if not self.app.local_queue:
            return
        self.app.audio.play(self.app.local_queue[0])
        self.app.action_toggle_view()
