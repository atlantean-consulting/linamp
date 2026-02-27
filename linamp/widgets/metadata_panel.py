"""Metadata display panel for the library manager."""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from linamp.metadata import read_metadata
from linamp.widgets.file_browser import AUDIO_EXTENSIONS


# Fields to display, in order: (key, label)
_FIELDS = [
    ("title", "Title"),
    ("artist", "Artist"),
    ("album", "Album"),
    ("track", "Track"),
    ("year", "Year"),
    ("genre", "Genre"),
    ("duration", "Duration"),
    ("bitrate", "Bitrate"),
    ("sample_rate", "Sample Rate"),
    ("format", "Format"),
    ("file_size", "File Size"),
]


class MetadataPanel(Container):
    """Right pane: displays audio file metadata."""

    DEFAULT_CSS = """
    MetadataPanel {
        width: 1fr;
        border: round $primary;
        padding: 0 1;
        overflow-y: auto;
    }
    MetadataPanel .meta-placeholder {
        color: #585b70;
        width: 1fr;
        content-align: center middle;
        height: 1fr;
    }
    MetadataPanel .meta-header {
        color: #f9e2af;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
    }
    MetadataPanel .meta-row {
        height: 1;
    }
    MetadataPanel .meta-label {
        color: #585b70;
        width: 14;
    }
    MetadataPanel .meta-value {
        color: #cdd6f4;
    }
    MetadataPanel .meta-title-value {
        color: #f9e2af;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Select a file to view info", classes="meta-placeholder", id="meta-placeholder")
        yield Static("", classes="meta-header", id="meta-header")
        for key, label in _FIELDS:
            value_class = "meta-title-value" if key == "title" else "meta-value"
            yield Static(
                f"[#585b70]{label + ':':<14}[/]",
                classes="meta-row",
                id=f"meta-{key}",
            )

    def on_mount(self) -> None:
        """Hide metadata fields initially, show placeholder."""
        self._set_fields_visible(False)

    def _set_fields_visible(self, visible: bool) -> None:
        """Toggle between placeholder and metadata fields."""
        self.query_one("#meta-placeholder").display = not visible
        self.query_one("#meta-header").display = visible
        for key, _ in _FIELDS:
            self.query_one(f"#meta-{key}").display = visible

    async def update_metadata(self, path: Path) -> None:
        """Load and display metadata for the given file."""
        meta = await asyncio.to_thread(read_metadata, str(path))

        self.query_one("#meta-header").update(f"{path.name}")
        for key, label in _FIELDS:
            value = meta.get(key, "")
            widget = self.query_one(f"#meta-{key}", Static)
            if value:
                widget.update(f"[#585b70]{label + ':':<14}[/] {value}")
            else:
                widget.update(f"[#585b70]{label + ':':<14}[/] [#45475a]—[/]")

        self._set_fields_visible(True)

    def clear_metadata(self) -> None:
        """Reset to placeholder state."""
        self._set_fields_visible(False)
