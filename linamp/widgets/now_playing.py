from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from linamp.messages import PlayerStateUpdate


class NowPlaying(Container):
    """Displays the current station name and ICY metadata."""

    DEFAULT_CSS = """
    NowPlaying {
        height: 3;
        border: heavy $accent;
        padding: 0 1;
    }
    NowPlaying .title {
        color: $success;
        text-style: bold;
    }
    NowPlaying .meta {
        color: $warning;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("LINAMP v0.1", classes="title", id="np-title")
        yield Static("No station selected", classes="meta", id="np-meta")

    def on_player_state_update(self, event: PlayerStateUpdate) -> None:
        title = self.query_one("#np-title", Static)
        meta = self.query_one("#np-meta", Static)

        if event.station:
            title.update(f"▶ {event.station.name}" if event.is_playing else
                         f"⏸ {event.station.name}" if event.is_paused else
                         event.station.name)
            if event.icy_title:
                meta.update(event.icy_title)
            elif event.station.genre:
                meta.update(event.station.genre)
            else:
                meta.update("")
        else:
            title.update("LINAMP v0.1")
            meta.update("No station selected")
