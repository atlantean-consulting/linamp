"""Standalone library manager app — browse and manage local music files."""

import json

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer

from linamp.config import load_config, QUEUE_PATH, CONFIG_DIR
from linamp.messages import StationSelected
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
        self._queued: list[dict] = []

    def on_station_selected(self, event: StationSelected) -> None:
        """Append selected file to the queue file for LinampApp to pick up."""
        entry = {"name": event.station.name, "url": event.station.url, "genre": event.station.genre}
        # Dedup by URL
        if not any(q["url"] == entry["url"] for q in self._queued):
            self._queued.append(entry)
        self._write_queue()

    def _write_queue(self) -> None:
        """Persist queued tracks for LinampApp to read on resume."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        QUEUE_PATH.write_text(json.dumps(self._queued, indent=2) + "\n")

    def compose(self) -> ComposeResult:
        yield Footer()


def main():
    app = LibraryApp()
    app.run()


if __name__ == "__main__":
    main()
