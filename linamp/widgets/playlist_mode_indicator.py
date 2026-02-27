"""Playlist mode indicator — thin bar between visualizer and playlist."""

from __future__ import annotations

from textual.widgets import Static

from linamp.messages import PlaylistModeChanged


class PlaylistModeIndicator(Static):
    """1-line indicator showing current playlist mode (Radio/Local)."""

    DEFAULT_CSS = """
    PlaylistModeIndicator {
        height: 1;
        background: #313244;
        color: #cdd6f4;
        padding: 0 1;
    }
    """

    def __init__(self, mode: str = "radio", **kwargs) -> None:
        super().__init__(self._format(mode, 0), **kwargs)
        self._mode = mode

    @staticmethod
    def _format(mode: str, count: int) -> str:
        if mode == "radio":
            return "\U0001f4fb Radio"
        return f"\U0001f4be Local ({count} tracks)" if count else "\U0001f4be Local"

    def on_playlist_mode_changed(self, event: PlaylistModeChanged) -> None:
        self._mode = event.mode
        self.update(self._format(event.mode, len(event.stations)))
