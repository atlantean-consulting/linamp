from textual.app import ComposeResult
from textual.containers import Horizontal, Container
from textual.widgets import Button


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
    TransportControls Button {
        min-width: 5;
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Button("⏮", id="btn-prev", variant="default")
            yield Button("⏵", id="btn-play", variant="success")
            yield Button("⏹", id="btn-stop", variant="error")
            yield Button("⏭", id="btn-next", variant="default")
