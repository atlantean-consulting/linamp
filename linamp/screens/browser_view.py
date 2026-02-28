from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Static, Input, ListView

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
    "[b #f9e2af]e[/] Edit playlist  "
    "[b #f9e2af]p[/] Play  "
    "[b #f9e2af]Tab[/] View  "
    "[b #f9e2af]F1[/] Radio"
)

EDIT_HINTS = (
    "[b #f9e2af]↑↓[/] Select  "
    "[b #f9e2af]←→[/] Move  "
    "[b #f9e2af]d[/] Delete  "
    "[b #f9e2af]w[/] Save M3U  "
    "[b #f9e2af]P[/] Play sel  "
    "[b #f9e2af]p[/] Play all  "
    "[b #f9e2af]x[/] Exit"
)

SAVE_HINTS = (
    "[b #f9e2af]Enter[/] Save  "
    "[b #f9e2af]Escape[/] Cancel"
)

PLAYLISTS_DIR = Path("~/Music/PLAYLISTS").expanduser()


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


class SaveInput(Input):
    """Input widget for M3U playlist name."""

    DEFAULT_CSS = """
    SaveInput {
        dock: bottom;
        height: 3;
        margin: 0 1;
        background: #313244;
        color: #cdd6f4;
        border: round #f9e2af;
    }
    """


class BrowserView(Screen):
    """MC-style dual-pane browser view — mode-aware.

    Radio mode: StationList (left) + PlaylistPanel (right)
    Local mode: FileBrowser (left) + PlaylistPanel (right)
    Local edit mode: PlaylistPanel focused with track reordering/deletion
    """

    BINDINGS = [
        Binding("e", "edit_playlist", "Edit", priority=True),
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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._edit_mode: bool = False
        self._save_mode: bool = False

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
        if self._edit_mode:
            self._exit_edit_mode()
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
        if self._edit_mode:
            self._exit_edit_mode()
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

    # --- Edit mode ---

    def action_edit_playlist(self) -> None:
        """Enter playlist edit mode (local mode only)."""
        if self.app.playlist_mode != "local":
            return
        if self._edit_mode:
            return
        if not self.app.local_queue:
            return
        self._edit_mode = True
        hints = self.query_one(CommandHints)
        hints.update(EDIT_HINTS)
        # Focus the playlist's ListView
        panel = self.query_one(PlaylistPanel)
        lv = panel.query_one(ListView)
        lv.focus()

    def _exit_edit_mode(self) -> None:
        """Leave playlist edit mode, sync changes, return focus to file browser."""
        self._edit_mode = False
        self._save_mode = False
        # Remove save input if present
        for widget in self.query(SaveInput):
            widget.remove()
        # Sync edits back to app
        panel = self.query_one(PlaylistPanel)
        self.app.local_queue = list(panel.stations)
        # Restore hints and focus
        hints = self.query_one(CommandHints)
        hints.update(LOCAL_HINTS)
        self.query_one(FileBrowser).focus()

    async def on_key(self, event: Key) -> None:
        """Intercept keys in edit mode before they reach global bindings."""
        if not self._edit_mode:
            return

        # While save input is shown, only intercept Escape to cancel
        if self._save_mode:
            if event.key == "escape":
                self._leave_save_mode()
                event.stop()
                event.prevent_default()
            return

        key = event.key
        panel = self.query_one(PlaylistPanel)

        if key == "left":
            await panel.move_track(-1)
            self._sync_queue_from_panel()
        elif key == "right":
            await panel.move_track(1)
            self._sync_queue_from_panel()
        elif key == "d":
            await panel.delete_track()
            self._sync_queue_from_panel()
            if not panel.stations:
                self._exit_edit_mode()
        elif key == "w":
            self._enter_save_mode()
        elif key == "P" or key == "shift+p":
            idx = panel.selected_index
            if idx is not None:
                self._sync_queue_from_panel()
                self.app.audio.play(self.app.local_queue[idx])
                self._edit_mode = False
                self.app.action_toggle_view()
        elif key == "p":
            if self.app.local_queue:
                self._sync_queue_from_panel()
                self.app.audio.play(self.app.local_queue[0])
                self._edit_mode = False
                self.app.action_toggle_view()
        elif key == "x" or key == "escape":
            self._exit_edit_mode()
        else:
            return  # Let ↑/↓ etc propagate to ListView

        event.stop()
        event.prevent_default()

    def _sync_queue_from_panel(self) -> None:
        """Sync app.local_queue from PlaylistPanel's current station list."""
        panel = self.query_one(PlaylistPanel)
        self.app.local_queue = list(panel.stations)

    # --- Save M3U ---

    def _enter_save_mode(self) -> None:
        """Show an input widget for the M3U playlist name."""
        self._save_mode = True
        hints = self.query_one(CommandHints)
        hints.update(SAVE_HINTS)
        save_input = SaveInput(placeholder="Playlist name (without .m3u)")
        self.mount(save_input)
        save_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Save the M3U file when the user presses Enter in the save input."""
        if not self._save_mode:
            return
        name = event.value.strip()
        if name:
            self._write_m3u(name)
        self._leave_save_mode()

    def _leave_save_mode(self) -> None:
        """Remove save input and return to edit mode."""
        self._save_mode = False
        for widget in self.query(SaveInput):
            widget.remove()
        hints = self.query_one(CommandHints)
        hints.update(EDIT_HINTS)
        # Re-focus the playlist
        panel = self.query_one(PlaylistPanel)
        lv = panel.query_one(ListView)
        lv.focus()

    def _write_m3u(self, name: str) -> None:
        """Write the current local queue as an M3U playlist file."""
        PLAYLISTS_DIR.mkdir(parents=True, exist_ok=True)
        path = PLAYLISTS_DIR / f"{name}.m3u"
        lines = ["#EXTM3U"]
        for station in self.app.local_queue:
            lines.append(f"#EXTINF:-1,{station.name}")
            lines.append(station.url)
        path.write_text("\n".join(lines) + "\n")

    # --- Play commands ---

    def action_play_queue(self) -> None:
        """Start playing the local queue from the beginning."""
        if self.app.playlist_mode != "local":
            return
        if not self.app.local_queue:
            return
        if self._edit_mode:
            self._sync_queue_from_panel()
            self._edit_mode = False
        self.app.audio.play(self.app.local_queue[0])
        self.app.action_toggle_view()
