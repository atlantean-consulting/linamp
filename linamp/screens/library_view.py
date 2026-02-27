from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Static

from linamp.widgets.file_browser import FileBrowser
from linamp.widgets.now_playing_bar import NowPlayingBar


class LibraryCommandHints(Static):
    """MC-style command hint bar for library view."""

    DEFAULT_CSS = """
    LibraryCommandHints {
        height: 1;
        dock: bottom;
        background: #313244;
        color: #cdd6f4;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        hints = (
            "[b #f9e2af]Enter[/] Play  "
            "[b #f9e2af]Tab[/] Player  "
            "[b #f9e2af]F5[/] Library  "
            "[b #f9e2af]q[/] Quit"
        )
        super().__init__(hints)


class LibraryView(Screen):
    """Local music library browser — MC-style dual pane."""

    DEFAULT_CSS = """
    LibraryView {
        layout: vertical;
    }
    LibraryView Horizontal {
        height: 1fr;
    }
    LibraryView #file-info {
        width: 1fr;
        border: round $primary;
        padding: 1 2;
        color: #585b70;
    }
    """

    def compose(self) -> ComposeResult:
        root = Path(self.app.config.music_root).expanduser()
        with Horizontal():
            yield FileBrowser(root=root)
            yield Static("Select a file to view info", id="file-info")
        yield NowPlayingBar("\u25a0 Stopped")
        yield LibraryCommandHints()
