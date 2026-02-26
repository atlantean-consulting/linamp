from textual.containers import Container
from textual.widgets import Static
from textual.app import ComposeResult

from linamp.messages import PlayerStateUpdate


class PlayerProgress(Container):
    """Shows elapsed time and a progress bar."""

    DEFAULT_CSS = """
    PlayerProgress {
        height: 1;
        padding: 0 1;
    }
    PlayerProgress Static {
        color: $success;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("─" * 40, id="progress-display")

    def _format_time(self, seconds: float | None) -> str:
        if seconds is None or seconds < 0:
            return "--:--"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def on_player_state_update(self, event: PlayerStateUpdate) -> None:
        display = self.query_one("#progress-display", Static)
        elapsed = self._format_time(event.time_pos)

        if event.is_stopped:
            bar = "─" * 38
            display.update(f"╶{bar}╴")
        else:
            bar = "━" * 38
            display.update(f"╶{bar}╴ {elapsed}")
