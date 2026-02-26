from textual.app import ComposeResult
from textual.containers import Horizontal, Container
from textual.widgets import Static


class TransportControls(Container):
    """Play/pause, stop, prev, next buttons."""

    DEFAULT_CSS = """
    TransportControls {
        height: 3;
        align: center middle;
    }
    TransportControls Horizontal {
        align: center middle;
        height: 3;
    }
    TransportControls .transport-btn {
        width: 5;
        height: 3;
        content-align: center middle;
        text-align: center;
        margin: 0 1;
        border: round #585b70;
    }
    TransportControls #btn-play {
        color: #4eb97a;
        border: round #4eb97a;
    }
    TransportControls #btn-stop {
        color: #b93c5b;
        border: round #b93c5b;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static("⏮", id="btn-prev", classes="transport-btn")
            yield Static("⏵", id="btn-play", classes="transport-btn")
            yield Static("⏹", id="btn-stop", classes="transport-btn")
            yield Static("⏭", id="btn-next", classes="transport-btn")
