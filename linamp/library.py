"""Standalone library manager app — browse and manage local music files."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

from linamp.config import load_config
from linamp.screens.library_view import LibraryView


class LibraryApp(App):
    """Local music library manager — standalone TUI."""

    TITLE = "linamp library"

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
    ]

    MODES = {
        "library": LibraryView,
    }

    DEFAULT_MODE = "library"

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
        self.config = load_config()

    def compose(self) -> ComposeResult:
        yield Footer()


def main():
    app = LibraryApp()
    app.run()


if __name__ == "__main__":
    main()
