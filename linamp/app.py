from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

import json
import subprocess
import sys

from linamp.config import load_config, QUEUE_PATH
from linamp.messages import PlayerStateUpdate, PlaylistModeChanged, StationSelected, LibraryChanged
from linamp.player import AudioPlayer
from linamp.stations import Station, load_library, save_library, all_stations
from linamp.screens.player_view import PlayerView
from linamp.screens.browser_view import BrowserView


class LinampApp(App):
    """Terminal music player - the love child of Winamp and Midnight Commander."""

    TITLE = "linamp"

    BINDINGS = [
        Binding("tab", "toggle_view", "View", priority=True),
        Binding("space", "toggle_pause", "Play/Pause", priority=True),
        Binding("s", "stop", "Stop", priority=True),
        Binding("plus,equal", "volume_up", "Vol+", priority=True),
        Binding("minus", "volume_down", "Vol-", priority=True),
        Binding("f1", "radio_mode", "Radio", priority=True),
        Binding("f2", "local_mode", "Local", priority=True),
        Binding("f5", "open_library", "Library", priority=True),
        Binding("q", "quit", "Quit", priority=True),
    ]

    MODES = {
        "player": PlayerView,
        "browser": BrowserView,
    }

    DEFAULT_MODE = "player"

    CSS = """
    Screen {
        background: #1e1e2e;
        color: #cdd6f4;
    }
    Footer {
        background: #313244;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.audio = AudioPlayer()
        self.config = load_config()
        self.library = load_library()
        self.playlist_mode: str = "radio"
        self.local_queue: list[Station] = []

    @property
    def flat_stations(self) -> list:
        return all_stations(self.library)

    @property
    def active_playlist(self) -> list[Station]:
        if self.playlist_mode == "local":
            return self.local_queue
        return self.flat_stations

    def on_mount(self) -> None:
        self.set_interval(0.5, self._poll_player_state)

    def compose(self) -> ComposeResult:
        yield Footer()

    def _poll_player_state(self) -> None:
        state = dict(
            is_playing=self.audio.is_playing,
            is_paused=self.audio.is_paused,
            is_stopped=self.audio.is_stopped,
            station=self.audio.current_station,
            icy_title=self.audio.icy_title,
            media_title=self.audio.media_title,
            time_pos=self.audio.time_pos,
            volume=self.audio.volume,
        )
        # Broadcast to all widgets that handle PlayerStateUpdate.
        # post_message only reaches the target + ancestors (bubbles up),
        # so we must create a fresh message per widget to avoid
        # stop-propagation from a prior recipient killing delivery.
        if self.screen:
            for widget in self.screen.walk_children():
                handler = getattr(widget, "on_player_state_update", None)
                if handler is not None:
                    widget.post_message(PlayerStateUpdate(**state))

    def action_toggle_view(self) -> None:
        if self.current_mode == "player":
            self.switch_mode("browser")
        else:
            self.switch_mode("player")

    async def action_open_library(self) -> None:
        """Suspend TUI and launch the library manager as a subprocess.

        Audio playback continues — mpv runs independently of the TUI.
        On return, import any queued tracks into the local playlist.
        """
        # Clear any stale queue file before launching
        if QUEUE_PATH.exists():
            QUEUE_PATH.unlink()

        with self.suspend():
            subprocess.run([sys.executable, "-m", "linamp.library"])

        # Import queued tracks from library manager
        await self._import_queue()

    def action_toggle_pause(self) -> None:
        self.audio.toggle_pause()

    def action_stop(self) -> None:
        self.audio.stop()

    def action_volume_up(self) -> None:
        self.audio.volume_up()

    def action_volume_down(self) -> None:
        self.audio.volume_down()

    async def action_radio_mode(self) -> None:
        """Switch to radio playlist mode."""
        if self.playlist_mode == "radio":
            return
        self.playlist_mode = "radio"
        await self._broadcast_mode_change()

    async def action_local_mode(self) -> None:
        """Switch to local playlist mode."""
        if self.playlist_mode == "local":
            return
        self.playlist_mode = "local"
        await self._broadcast_mode_change()

    async def _import_queue(self) -> None:
        """Read queued tracks from library manager and add to local playlist."""
        if not QUEUE_PATH.exists():
            return
        try:
            data = json.loads(QUEUE_PATH.read_text())
            QUEUE_PATH.unlink()
        except Exception:
            return
        if not data:
            return

        added = False
        first_new = None
        for entry in data:
            station = Station(
                name=entry.get("name", ""),
                url=entry.get("url", ""),
                genre=entry.get("genre", ""),
            )
            if not any(s.url == station.url for s in self.local_queue):
                self.local_queue.append(station)
                if first_new is None:
                    first_new = station
                added = True

        if added:
            # Switch to local mode and start playing the first new track
            self.playlist_mode = "local"
            await self._broadcast_mode_change()
            if first_new:
                self.audio.play(first_new)

    async def _broadcast_mode_change(self) -> None:
        """Update all PlaylistPanels and mode indicators with new mode."""
        stations = self.active_playlist
        # Update playlist panels
        for panel in self.query("PlaylistPanel"):
            await panel.set_stations(stations)
        # Broadcast to mode indicators (fresh message per widget)
        for widget in self.screen.walk_children():
            handler = getattr(widget, "on_playlist_mode_changed", None)
            if handler is not None:
                widget.post_message(PlaylistModeChanged(self.playlist_mode, stations))

    def on_station_selected(self, event: StationSelected) -> None:
        # Auto-add local files to the local queue
        if event.station.url.startswith("/"):
            if not any(s.url == event.station.url for s in self.local_queue):
                self.local_queue.append(event.station)
        self.audio.play(event.station)

    async def on_library_changed(self, event: LibraryChanged) -> None:
        self.library = list(event.folders)
        save_library(self.library)
        # Re-broadcast to all PlaylistPanels (siblings don't receive bubbled messages)
        for panel in self.query("PlaylistPanel"):
            await panel.on_library_changed(event)

    def on_unmount(self) -> None:
        self.audio.shutdown()
