from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Static

from linamp.messages import FileHighlighted
from linamp.widgets.file_browser import FileBrowser
from linamp.widgets.metadata_panel import MetadataPanel
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
            "[b #f9e2af]e[/] Edit tags  "
            "[b #f9e2af]Tab[/] Player  "
            "[b #f9e2af]F5[/] Library  "
            "[b #f9e2af]q[/] Quit"
        )
        super().__init__(hints)


class LibraryView(Screen):
    """Local music library browser — MC-style dual pane."""

    BINDINGS = [
        Binding("e", "edit_tags", "Edit tags", priority=True),
    ]

    DEFAULT_CSS = """
    LibraryView {
        layout: vertical;
    }
    LibraryView Horizontal {
        height: 1fr;
    }
    """

    async def action_edit_tags(self) -> None:
        """Delegate edit to the metadata panel."""
        await self.query_one(MetadataPanel).action_edit()

    def compose(self) -> ComposeResult:
        root = Path(self.app.config.music_root).expanduser()
        with Horizontal():
            yield FileBrowser(root=root)
            yield MetadataPanel()
        yield NowPlayingBar("\u25a0 Stopped")
        yield LibraryCommandHints()

    async def on_file_highlighted(self, event: FileHighlighted) -> None:
        """Update metadata panel when file cursor moves."""
        panel = self.query_one(MetadataPanel)
        if event.path is not None:
            await panel.update_metadata(event.path)
        else:
            panel.clear_metadata()
