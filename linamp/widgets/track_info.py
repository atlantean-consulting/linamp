from textual.containers import Container
from textual.app import ComposeResult
from textual.widgets import Static

from linamp.messages import PlayerStateUpdate


class TrackInfo(Container):
    """Displays the currently playing track between controls and playlist.

    Priority: ICY stream title (artist - track) > media title > station name.
    """

    DEFAULT_CSS = """
    TrackInfo {
        height: 4;
        border: round #585b70;
        padding: 0 1;
    }
    TrackInfo .track-label {
        color: #585b70;
        height: 1;
    }
    TrackInfo .track-title {
        color: #f9e2af;
        text-style: bold;
        height: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("NOW PLAYING", classes="track-label", id="track-label")
        yield Static("", classes="track-title", id="track-title")

    def _best_title(self, event: PlayerStateUpdate) -> str:
        """Pick the best available title for the current track."""
        # ICY title is the gold standard — real-time artist/track from the stream
        if event.icy_title:
            return event.icy_title
        # media_title is mpv's synthesized title (may come from ytdl or stream)
        # Only use it if it differs from the station name (otherwise it's redundant)
        if event.media_title and event.station and event.media_title != event.station.name:
            return event.media_title
        # Fall back to station name
        if event.station:
            return event.station.name
        return ""

    def on_player_state_update(self, event: PlayerStateUpdate) -> None:
        label = self.query_one("#track-label", Static)
        title = self.query_one("#track-title", Static)

        if event.is_playing:
            label.update("NOW PLAYING")
            title.update(self._best_title(event))
        elif event.is_paused:
            label.update("PAUSED")
            title.update(self._best_title(event))
        else:
            label.update("NOW PLAYING")
            title.update("")
