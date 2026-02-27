from __future__ import annotations

from pathlib import Path
from typing import Iterable

from textual.containers import Container
from textual.app import ComposeResult
from textual.widgets import DirectoryTree

from linamp.messages import FileHighlighted, StationSelected
from linamp.stations import Station

AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".wav", ".aac", ".wma"}


class AudioDirectoryTree(DirectoryTree):
    """DirectoryTree filtered to show only directories and audio files."""

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        return [
            p for p in paths
            if p.is_dir() or p.suffix.lower() in AUDIO_EXTENSIONS
        ]


class FileBrowser(Container):
    """Left pane: audio file directory tree with configurable root."""

    DEFAULT_CSS = """
    FileBrowser {
        width: 1fr;
        border: round $primary;
    }
    FileBrowser AudioDirectoryTree {
        height: 1fr;
    }
    """

    def __init__(self, root: Path, **kwargs) -> None:
        super().__init__(**kwargs)
        self._root = root

    def compose(self) -> ComposeResult:
        yield AudioDirectoryTree(str(self._root))

    def on_tree_node_highlighted(self, event: DirectoryTree.NodeHighlighted) -> None:
        """Cursor moved — emit FileHighlighted for the metadata panel."""
        if event.node.data is None:
            self.post_message(FileHighlighted(None))
            return
        path = event.node.data.path
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            self.post_message(FileHighlighted(path))
        else:
            self.post_message(FileHighlighted(None))

    def on_tree_node_selected(self, event: DirectoryTree.NodeSelected) -> None:
        """Handle Enter on tree nodes — play audio files, let dirs expand normally."""
        if event.node.data is None:
            return
        path = event.node.data.path
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            station = Station(
                name=path.stem,
                url=str(path),
                genre="",
            )
            self.post_message(StationSelected(station))
