from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

from linamp.messages import PlayerStateUpdate, StationSelected, LibraryChanged
from linamp.player import AudioPlayer
from linamp.stations import load_library, save_library, all_stations
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
        self.library = load_library()

    @property
    def flat_stations(self) -> list:
        return all_stations(self.library)

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

    def action_toggle_pause(self) -> None:
        self.audio.toggle_pause()

    def action_stop(self) -> None:
        self.audio.stop()

    def action_volume_up(self) -> None:
        self.audio.volume_up()

    def action_volume_down(self) -> None:
        self.audio.volume_down()

    def on_station_selected(self, event: StationSelected) -> None:
        self.audio.play(event.station)

    async def on_library_changed(self, event: LibraryChanged) -> None:
        self.library = list(event.folders)
        save_library(self.library)
        # Re-broadcast to all PlaylistPanels (siblings don't receive bubbled messages)
        for panel in self.query("PlaylistPanel"):
            await panel.on_library_changed(event)

    def on_unmount(self) -> None:
        self.audio.shutdown()
