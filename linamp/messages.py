from __future__ import annotations

from pathlib import Path

from textual.message import Message

from linamp.stations import Station, Folder


class PlayerStateUpdate(Message):
    """Broadcast periodically with current player state."""

    def __init__(
        self,
        is_playing: bool,
        is_paused: bool,
        is_stopped: bool,
        station: Station | None,
        icy_title: str,
        media_title: str,
        time_pos: float | None,
        volume: float,
    ) -> None:
        super().__init__()
        self.is_playing = is_playing
        self.is_paused = is_paused
        self.is_stopped = is_stopped
        self.station = station
        self.icy_title = icy_title
        self.media_title = media_title
        self.time_pos = time_pos
        self.volume = volume


class StationSelected(Message):
    """User selected a station to play."""

    def __init__(self, station: Station) -> None:
        super().__init__()
        self.station = station


class FileHighlighted(Message):
    """User highlighted a file in the library browser."""

    def __init__(self, path: Path | None) -> None:
        super().__init__()
        self.path = path


class LibraryChanged(Message):
    """Library was modified (folders/stations added/removed/renamed/rearranged)."""

    def __init__(self, folders: list[Folder]) -> None:
        super().__init__()
        self.folders = folders
