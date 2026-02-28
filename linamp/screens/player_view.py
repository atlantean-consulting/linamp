from textual.app import ComposeResult
from textual.screen import Screen

from linamp.messages import PlaylistModeChanged
from linamp.widgets.now_playing import NowPlaying
from linamp.widgets.progress_bar import PlayerProgress
from linamp.widgets.transport import TransportControls
from linamp.widgets.volume_bar import VolumeBar
from linamp.widgets.visualizer import Visualizer
from linamp.widgets.playlist_panel import PlaylistPanel
from linamp.widgets.playlist_mode_indicator import PlaylistModeIndicator


class PlayerView(Screen):
    """Winamp-style compact player view."""

    DEFAULT_CSS = """
    PlayerView {
        layout: vertical;
    }
    """

    def compose(self) -> ComposeResult:
        yield NowPlaying()
        yield PlayerProgress()
        yield TransportControls()
        yield VolumeBar()
        yield Visualizer()
        yield PlaylistModeIndicator(mode=self.app.playlist_mode)
        yield PlaylistPanel(stations=self.app.active_playlist)

    async def on_screen_resume(self) -> None:
        """Refresh playlist and mode indicator when returning to this screen."""
        panel = self.query_one(PlaylistPanel)
        await panel.set_stations(self.app.active_playlist)
        indicator = self.query_one(PlaylistModeIndicator)
        indicator.post_message(
            PlaylistModeChanged(self.app.playlist_mode, self.app.active_playlist)
        )
