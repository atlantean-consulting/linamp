from textual.containers import Container
from textual.widgets import Static
from textual.app import ComposeResult

from linamp.messages import PlayerStateUpdate


class VolumeBar(Container):
    """Displays volume as a horizontal bar."""

    DEFAULT_CSS = """
    VolumeBar {
        height: 1;
        padding: 0 1;
    }
    VolumeBar Static {
        color: $success;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="volume-display")

    def _render_bar(self, volume: float) -> str:
        filled = int(volume / 100 * 20)
        empty = 20 - filled
        bar = "█" * filled + "░" * empty
        return f"Vol: [{bar}] {int(volume)}%"

    def on_player_state_update(self, event: PlayerStateUpdate) -> None:
        display = self.query_one("#volume-display", Static)
        display.update(self._render_bar(event.volume))
