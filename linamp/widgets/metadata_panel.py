"""Metadata display panel for the library manager."""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Input, Static

from linamp.metadata import read_metadata, write_metadata
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

# Fields the user can edit (subset of _FIELDS)
_EDITABLE = ["title", "artist", "album", "track", "year", "genre"]

MODE_BROWSE = "browse"
MODE_EDIT = "edit"


class MetadataPanel(Container):
    """Right pane: displays audio file metadata with inline editing."""

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
    MetadataPanel .edit-form {
        height: auto;
        padding: 0;
        background: transparent;
    }
    MetadataPanel .edit-row {
        height: auto;
    }
    MetadataPanel .edit-label {
        color: #f9e2af;
        width: auto;
        height: 1;
    }
    MetadataPanel .edit-input {
        height: 3;
        background: #45475a;
        color: #cdd6f4;
        width: 1fr;
    }
    MetadataPanel .edit-input:focus {
        background: #585b70;
        color: #f9e2af;
    }
    MetadataPanel .edit-hint {
        height: 1;
        color: #585b70;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel_edit", "Cancel", show=False, priority=True),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._mode = MODE_BROWSE
        self._current_path: Path | None = None
        self._current_meta: dict = {}

    def compose(self) -> ComposeResult:
        yield Static("Select a file to view info", classes="meta-placeholder", id="meta-placeholder")
        yield Static("", classes="meta-header", id="meta-header")
        for key, label in _FIELDS:
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
        if self._mode == MODE_EDIT:
            self._remove_edit_ui()

        self._current_path = path
        meta = await asyncio.to_thread(read_metadata, str(path))
        self._current_meta = meta

        self.query_one("#meta-header").update(f"{path.name}")
        for key, label in _FIELDS:
            value = meta.get(key, "")
            widget = self.query_one(f"#meta-{key}", Static)
            if value:
                widget.update(f"[#585b70]{label + ':':<14}[/] {value}")
            else:
                widget.update(f"[#585b70]{label + ':':<14}[/] [#45475a]\u2014[/]")

        self._set_fields_visible(True)

    def clear_metadata(self) -> None:
        """Reset to placeholder state."""
        if self._mode == MODE_EDIT:
            self._remove_edit_ui()
        self._current_path = None
        self._current_meta = {}
        self._set_fields_visible(False)

    async def action_edit(self) -> None:
        """Enter edit mode — replace editable fields with Input widgets."""
        if self._mode != MODE_BROWSE or self._current_path is None:
            return

        self._mode = MODE_EDIT

        # Hide the editable Static rows
        for key in _EDITABLE:
            self.query_one(f"#meta-{key}").display = False

        # Build edit form
        form = Vertical(classes="edit-form", id="edit-form")
        await self.mount(form, before=self.query_one("#meta-duration"))

        for key in _EDITABLE:
            label_text = dict(_FIELDS)[key]
            row = Vertical(classes="edit-row")
            await form.mount(row)
            label = Static(f"{label_text}:", classes="edit-label")
            inp = Input(
                value=self._current_meta.get(key, ""),
                id=f"edit-{key}",
                classes="edit-input",
            )
            await row.mount(label)
            await row.mount(inp)

        hint = Static("[#585b70]Tab[/] next  [#585b70]Enter[/] save  [#585b70]Esc[/] cancel", classes="edit-hint")
        await form.mount(hint)

        # Focus first input
        self.query_one(f"#edit-{_EDITABLE[0]}", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter pressed in an Input — save all edits."""
        if self._mode != MODE_EDIT or self._current_path is None:
            return

        # Collect values from all edit inputs
        tags = {}
        for key in _EDITABLE:
            inp = self.query_one(f"#edit-{key}", Input)
            tags[key] = inp.value

        # Write to file in background thread
        await asyncio.to_thread(write_metadata, str(self._current_path), tags)

        # Remove edit UI and reload
        self._remove_edit_ui()
        await self.update_metadata(self._current_path)

    def action_cancel_edit(self) -> None:
        """Escape pressed — cancel edit, restore display."""
        if self._mode != MODE_EDIT:
            return
        self._remove_edit_ui()
        # Restore the editable Static rows
        for key in _EDITABLE:
            self.query_one(f"#meta-{key}").display = True

    def _remove_edit_ui(self) -> None:
        """Remove edit form and restore browse mode."""
        for widget in self.query("#edit-form"):
            widget.remove()
        self._mode = MODE_BROWSE
