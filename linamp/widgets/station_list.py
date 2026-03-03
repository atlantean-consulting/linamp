import asyncio
import logging
import shutil
import subprocess

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Tree, Input, Static

from linamp.messages import StationSelected, LibraryChanged
from linamp.player import AudioPlayer
from linamp.stations import Station, Folder, DEFAULT_LIBRARY, save_library

log = logging.getLogger(__name__)


class StationList(Container):
    """Station browser with folder tree for the MC-style left pane."""

    CHANNEL_PAGE_SIZE = 25

    BINDINGS = [
        Binding("f", "new_folder", "Folder", priority=True),
        Binding("a", "add_station", "Add", priority=True),
        Binding("c", "import_channel", "Channel", priority=True),
        Binding("m", "load_more", "More", priority=True),
        Binding("w", "save_to_library", "Save", priority=True),
        Binding("d", "delete_item", "Delete", priority=True),
        Binding("r", "rename_item", "Rename", priority=True),
        Binding("e", "edit_station", "Edit", priority=True),
        Binding("ctrl+up", "move_up", "Move Up", priority=True),
        Binding("ctrl+down", "move_down", "Move Down", priority=True),
        Binding("escape", "cancel_edit", "Cancel", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    StationList {
        height: 1fr;
        border: round $accent;
    }
    StationList Tree {
        height: 1fr;
    }
    StationList .edit-form {
        height: auto;
        max-height: 6;
        padding: 0 1;
        background: #313244;
    }
    StationList .edit-form Input {
        margin: 0;
        height: 1;
        border: none;
        padding: 0;
        background: #45475a;
    }
    StationList .edit-form .edit-label {
        height: 1;
        color: $warning;
    }
    StationList .delete-confirm {
        height: 1;
        padding: 0 1;
        color: $error;
        text-style: bold;
        background: #313244;
    }
    """

    MODE_BROWSE = "browse"
    MODE_ADD = "add"
    MODE_RENAME = "rename"
    MODE_EDIT = "edit"
    MODE_DELETE_CONFIRM = "delete_confirm"
    MODE_NEW_FOLDER = "new_folder"
    MODE_IMPORT_CHANNEL = "import_channel"

    def __init__(self, library: list[Folder] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._library = list(library or DEFAULT_LIBRARY)
        self._mode = self.MODE_BROWSE
        self._channel_meta: dict[str, dict] = {}

    def compose(self) -> ComposeResult:
        tree: Tree[Folder | Station] = Tree("Library")
        tree.show_root = False
        self._populate_tree(tree)
        yield tree

    def _populate_tree(self, tree: Tree) -> None:
        """Build tree nodes from library."""
        tree.clear()
        for folder in self._library:
            folder_node = tree.root.add(f"📁 {folder.name}", data=folder, expand=True)
            for station in folder.stations:
                icon = "🎵" if AudioPlayer._is_ytdl_url(station.url) else "📻"
                folder_node.add_leaf(f"{icon} {station.name}", data=station)

    def _rebuild_tree(self) -> None:
        """Rebuild the tree from the current library state."""
        tree = self.query_one(Tree)
        self._populate_tree(tree)

    def _save_and_broadcast(self) -> None:
        save_library(self._library)
        self.post_message(LibraryChanged(list(self._library)))

    def _remove_edit_ui(self) -> None:
        for widget in self.query(".edit-form, .delete-confirm"):
            widget.remove()
        self._mode = self.MODE_BROWSE

    def _selected_node(self):
        """Get the currently highlighted tree node."""
        try:
            tree = self.query_one(Tree)
            return tree.cursor_node
        except Exception:
            return None

    def _find_folder_for_node(self, node) -> Folder | None:
        """Get the folder that a node belongs to (or is)."""
        if node is None:
            return None
        if isinstance(node.data, Folder):
            return node.data
        if isinstance(node.data, Station) and node.parent and isinstance(node.parent.data, Folder):
            return node.parent.data
        return None

    # --- Play on select ---

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if self._mode != self.MODE_BROWSE:
            return
        node = event.node
        if isinstance(node.data, Station):
            self.post_message(StationSelected(node.data))

    # --- New folder ---

    async def action_new_folder(self) -> None:
        if self._mode != self.MODE_BROWSE:
            return
        self._mode = self.MODE_NEW_FOLDER
        form = Vertical(
            Static("New Folder:", classes="edit-label"),
            Input(placeholder="Folder name", id="input-name"),
            classes="edit-form",
        )
        await self.mount(form)
        self.query_one("#input-name", Input).focus()

    def _commit_new_folder(self) -> None:
        name = self.query_one("#input-name", Input).value.strip()
        if not name:
            return
        self._library.append(Folder(name))
        self._remove_edit_ui()
        self._rebuild_tree()
        self._save_and_broadcast()

    # --- Add station ---

    async def action_add_station(self) -> None:
        if self._mode != self.MODE_BROWSE:
            return
        node = self._selected_node()
        folder = self._find_folder_for_node(node)
        if folder is None:
            return
        self._mode = self.MODE_ADD
        form = Vertical(
            Static(f"Add to '{folder.name}' (URL first):", classes="edit-label"),
            Input(placeholder="URL", id="input-url"),
            Input(placeholder="Name (auto-filled for YouTube)", id="input-name"),
            Input(placeholder="Genre (optional)", id="input-genre"),
            classes="edit-form",
        )
        await self.mount(form)
        self.query_one("#input-url", Input).focus()

    def _fetch_youtube_title(self, url: str) -> str | None:
        ytdlp = shutil.which("yt-dlp")
        if not ytdlp:
            return None
        try:
            result = subprocess.run(
                [ytdlp, "--no-download", "--print", "title", url],
                capture_output=True, text=True, timeout=15,
            )
            title = result.stdout.strip().splitlines()
            if result.returncode == 0 and title and title[0]:
                return title[0]
        except (subprocess.TimeoutExpired, OSError):
            pass
        return None

    async def _on_add_url_submitted(self) -> None:
        url = self.query_one("#input-url", Input).value.strip()
        name_input = self.query_one("#input-name", Input)
        if url and AudioPlayer._is_ytdl_url(url) and not name_input.value.strip():
            try:
                label = self.query_one(".edit-form .edit-label", Static)
                label.update("Fetching title...")
            except Exception:
                pass
            title = await asyncio.to_thread(self._fetch_youtube_title, url)
            if title:
                name_input.value = title
                genre_input = self.query_one("#input-genre", Input)
                if not genre_input.value.strip():
                    genre_input.value = "YouTube"
            try:
                label = self.query_one(".edit-form .edit-label", Static)
                label.update("Add Station:")
            except Exception:
                pass
        name_input.focus()

    async def _commit_add(self) -> None:
        name = self.query_one("#input-name", Input).value.strip()
        url = self.query_one("#input-url", Input).value.strip()
        genre = self.query_one("#input-genre", Input).value.strip()
        if not name or not url:
            return
        node = self._selected_node()
        folder = self._find_folder_for_node(node)
        if folder is None and self._library:
            folder = self._library[0]
        if folder is None:
            return
        folder.stations.append(Station(name, url, genre))
        self._remove_edit_ui()
        self._rebuild_tree()
        self._save_and_broadcast()

    # --- Import YouTube channel ---

    async def action_import_channel(self) -> None:
        if self._mode != self.MODE_BROWSE:
            return
        self._mode = self.MODE_IMPORT_CHANNEL
        form = Vertical(
            Static("Import YouTube channel/playlist URL:", classes="edit-label"),
            Input(placeholder="https://www.youtube.com/@channel", id="input-url"),
            classes="edit-form",
        )
        await self.mount(form)
        self.query_one("#input-url", Input).focus()

    def _fetch_channel_entries(
        self, url: str, limit: int, offset: int
    ) -> tuple[str, list[tuple[str, str]]]:
        """Fetch video entries from a YouTube channel/playlist. Returns (channel_name, [(title, url)])."""
        ytdlp = shutil.which("yt-dlp")
        if not ytdlp:
            return ("", [])
        start = offset + 1  # yt-dlp uses 1-based indexing
        end = offset + limit
        try:
            result = subprocess.run(
                [
                    ytdlp, "--flat-playlist", "--no-download",
                    "--playlist-start", str(start),
                    "--playlist-end", str(end),
                    "--print", "%(playlist_title)s\t%(title)s\t%(webpage_url)s",
                    url,
                ],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return ("", [])
            entries = []
            channel_name = ""
            for line in result.stdout.strip().splitlines():
                parts = line.split("\t", 2)
                if len(parts) == 3:
                    if not channel_name and parts[0] and parts[0] != "NA":
                        channel_name = parts[0]
                    title = parts[1] if parts[1] and parts[1] != "NA" else "Untitled"
                    video_url = parts[2] if parts[2] and parts[2] != "NA" else ""
                    if video_url:
                        entries.append((title, video_url))
            return (channel_name, entries)
        except (subprocess.TimeoutExpired, OSError):
            return ("", [])

    async def _commit_import_channel(self) -> None:
        url = self.query_one("#input-url", Input).value.strip()
        if not url:
            return
        try:
            label = self.query_one(".edit-form .edit-label", Static)
            label.update(f"Fetching channel ({self.CHANNEL_PAGE_SIZE} videos)...")
        except Exception:
            pass
        channel_name, entries = await asyncio.to_thread(
            self._fetch_channel_entries, url, self.CHANNEL_PAGE_SIZE, 0
        )
        self._remove_edit_ui()
        if not entries:
            return
        if not channel_name:
            channel_name = url.rstrip("/").split("/")[-1]
        folder = Folder(channel_name, [Station(t, u, "YouTube") for t, u in entries], channel_url=url)
        self._library.append(folder)
        self._channel_meta[channel_name] = {
            "offset": len(entries),
            "exhausted": len(entries) < self.CHANNEL_PAGE_SIZE,
        }
        self._rebuild_tree()
        self._save_and_broadcast()

    def _get_channel_meta(self, folder: Folder) -> dict:
        """Get or initialize channel pagination state for a channel folder."""
        if folder.name not in self._channel_meta:
            self._channel_meta[folder.name] = {
                "offset": len(folder.stations),
                "exhausted": False,
            }
        return self._channel_meta[folder.name]

    async def action_load_more(self) -> None:
        if self._mode != self.MODE_BROWSE:
            return
        node = self._selected_node()
        folder = self._find_folder_for_node(node)
        if folder is None or not folder.is_channel:
            return
        meta = self._get_channel_meta(folder)
        if meta.get("exhausted"):
            return
        self._mode = self.MODE_IMPORT_CHANNEL
        form = Vertical(
            Static(f"Loading more from '{folder.name}'...", classes="edit-label"),
            classes="edit-form",
        )
        await self.mount(form)
        _, entries = await asyncio.to_thread(
            self._fetch_channel_entries, folder.channel_url, self.CHANNEL_PAGE_SIZE, meta["offset"]
        )
        self._remove_edit_ui()
        if not entries:
            meta["exhausted"] = True
            return
        for title, video_url in entries:
            folder.stations.append(Station(title, video_url, "YouTube"))
        meta["offset"] += len(entries)
        if len(entries) < self.CHANNEL_PAGE_SIZE:
            meta["exhausted"] = True
        self._rebuild_tree()
        self._save_and_broadcast()

    # --- Save channel video to library ---

    async def action_save_to_library(self) -> None:
        if self._mode != self.MODE_BROWSE:
            return
        node = self._selected_node()
        if node is None or not isinstance(node.data, Station):
            return
        folder = self._find_folder_for_node(node)
        if folder is None or not folder.is_channel:
            return
        station = node.data
        # Find or create the YouTube folder (non-channel)
        yt_folder = None
        for f in self._library:
            if f.name == "YouTube" and not f.is_channel:
                yt_folder = f
                break
        if yt_folder is None:
            yt_folder = Folder("YouTube")
            self._library.append(yt_folder)
        yt_folder.stations.append(Station(station.name, station.url, station.genre))
        self._rebuild_tree()
        self._save_and_broadcast()

    # --- Delete ---

    async def action_delete_item(self) -> None:
        node = self._selected_node()
        if node is None:
            return
        if self._mode == self.MODE_DELETE_CONFIRM:
            self._remove_edit_ui()
            if isinstance(node.data, Station):
                folder = self._find_folder_for_node(node)
                if folder and node.data in folder.stations:
                    folder.stations.remove(node.data)
            elif isinstance(node.data, Folder):
                if node.data in self._library:
                    self._library.remove(node.data)
            self._rebuild_tree()
            self._save_and_broadcast()
        elif self._mode == self.MODE_BROWSE:
            self._mode = self.MODE_DELETE_CONFIRM
            if isinstance(node.data, Folder):
                count = len(node.data.stations)
                msg = f"Delete folder '{node.data.name}' ({count} stations)? Press d to confirm"
            else:
                msg = f"Delete '{node.data.name}'? Press d to confirm, Esc to cancel"
            self.mount(Static(msg, classes="delete-confirm"))

    # --- Rename ---

    async def action_rename_item(self) -> None:
        if self._mode != self.MODE_BROWSE:
            return
        node = self._selected_node()
        if node is None or not hasattr(node.data, "name"):
            return
        self._mode = self.MODE_RENAME
        label = "Rename folder:" if isinstance(node.data, Folder) else f"Rename '{node.data.name}':"
        form = Vertical(
            Static(label, classes="edit-label"),
            Input(value=node.data.name, id="input-name"),
            classes="edit-form",
        )
        await self.mount(form)
        self.query_one("#input-name", Input).focus()

    def _commit_rename(self) -> None:
        name = self.query_one("#input-name", Input).value.strip()
        node = self._selected_node()
        if not name or node is None:
            return
        node.data.name = name
        self._remove_edit_ui()
        self._rebuild_tree()
        self._save_and_broadcast()

    # --- Edit URL/Genre ---

    async def action_edit_station(self) -> None:
        if self._mode != self.MODE_BROWSE:
            return
        node = self._selected_node()
        if node is None or not isinstance(node.data, Station):
            return
        self._mode = self.MODE_EDIT
        station = node.data
        form = Vertical(
            Static(f"Edit '{station.name}':", classes="edit-label"),
            Input(value=station.url, placeholder="URL", id="input-url"),
            Input(value=station.genre, placeholder="Genre", id="input-genre"),
            classes="edit-form",
        )
        await self.mount(form)
        self.query_one("#input-url", Input).focus()

    def _commit_edit(self) -> None:
        url = self.query_one("#input-url", Input).value.strip()
        genre = self.query_one("#input-genre", Input).value.strip()
        node = self._selected_node()
        if not url or node is None or not isinstance(node.data, Station):
            return
        node.data.url = url
        node.data.genre = genre
        self._remove_edit_ui()
        self._rebuild_tree()
        self._save_and_broadcast()

    # --- Move up/down ---

    def action_move_up(self) -> None:
        if self._mode != self.MODE_BROWSE:
            return
        node = self._selected_node()
        if node is None or not isinstance(node.data, Station):
            return
        folder = self._find_folder_for_node(node)
        if folder is None:
            return
        idx = folder.stations.index(node.data)
        if idx <= 0:
            return
        folder.stations[idx - 1], folder.stations[idx] = folder.stations[idx], folder.stations[idx - 1]
        self._rebuild_tree()
        self._save_and_broadcast()

    def action_move_down(self) -> None:
        if self._mode != self.MODE_BROWSE:
            return
        node = self._selected_node()
        if node is None or not isinstance(node.data, Station):
            return
        folder = self._find_folder_for_node(node)
        if folder is None:
            return
        idx = folder.stations.index(node.data)
        if idx >= len(folder.stations) - 1:
            return
        folder.stations[idx], folder.stations[idx + 1] = folder.stations[idx + 1], folder.stations[idx]
        self._rebuild_tree()
        self._save_and_broadcast()

    # --- Cancel ---

    def action_cancel_edit(self) -> None:
        if self._mode != self.MODE_BROWSE:
            self._remove_edit_ui()

    # --- Input submission ---

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._mode == self.MODE_ADD:
            if event.input.id == "input-url":
                await self._on_add_url_submitted()
            elif event.input.id == "input-name":
                self.query_one("#input-genre", Input).focus()
            else:
                await self._commit_add()
        elif self._mode == self.MODE_RENAME:
            self._commit_rename()
        elif self._mode == self.MODE_EDIT:
            if event.input.id == "input-url":
                self.query_one("#input-genre", Input).focus()
            else:
                self._commit_edit()
        elif self._mode == self.MODE_IMPORT_CHANNEL:
            await self._commit_import_channel()
        elif self._mode == self.MODE_NEW_FOLDER:
            self._commit_new_folder()
