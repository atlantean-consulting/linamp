from textual.app import ComposeResult
from textual.screen import Screen

from linamp.widgets.now_playing import NowPlaying
from linamp.widgets.progress_bar import PlayerProgress
from linamp.widgets.transport import TransportControls
from linamp.widgets.volume_bar import VolumeBar
from linamp.widgets.visualizer import Visualizer
from linamp.widgets.playlist_panel import PlaylistPanel


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
        yield PlaylistPanel()
