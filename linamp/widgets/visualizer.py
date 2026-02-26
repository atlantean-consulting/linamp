import random

from textual.containers import Container
from textual.app import ComposeResult
from textual.widgets import Static

from linamp.messages import PlayerStateUpdate


BARS = " ▁▂▃▄▅▆▇█"


class Visualizer(Container):
    """Simulated spectrum visualizer that pulses during playback."""

    DEFAULT_CSS = """
    Visualizer {
        height: 3;
        padding: 0 1;
        border: round $primary;
    }
    Visualizer Static {
        color: $success;
        text-align: center;
        height: 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._num_bars = 32
        self._levels: list[float] = [0.0] * self._num_bars
        self._playing = False

    def compose(self) -> ComposeResult:
        yield Static("", id="viz-display")

    def _render_bars(self) -> str:
        return "".join(BARS[int(level * (len(BARS) - 1))] for level in self._levels)

    def _tick(self) -> None:
        if self._playing:
            for i in range(self._num_bars):
                target = random.random() * 0.8 + 0.2
                self._levels[i] += (target - self._levels[i]) * 0.4
        else:
            for i in range(self._num_bars):
                self._levels[i] *= 0.85

        try:
            display = self.query_one("#viz-display", Static)
            display.update(self._render_bars())
        except Exception:
            pass

    def on_mount(self) -> None:
        self.set_interval(1 / 12, self._tick)

    def on_player_state_update(self, event: PlayerStateUpdate) -> None:
        self._playing = event.is_playing
