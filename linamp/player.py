from __future__ import annotations

import mpv

from linamp.stations import Station


class AudioPlayer:
    """Wraps mpv into a simple interface for the TUI layer."""

    def __init__(self) -> None:
        self._mpv = mpv.MPV(
            video=False,
            terminal=False,
            input_terminal=False,
        )
        self._current_station: Station | None = None
        self._stopped = True

    def play(self, station: Station) -> None:
        self._current_station = station
        self._stopped = False
        self._mpv.play(station.url)

    def toggle_pause(self) -> None:
        if self._stopped:
            return
        self._mpv.pause = not self._mpv.pause

    def stop(self) -> None:
        self._mpv.stop()
        self._stopped = True

    @property
    def volume(self) -> float:
        try:
            return self._mpv.volume or 100.0
        except Exception:
            return 100.0

    @volume.setter
    def volume(self, value: float) -> None:
        self._mpv.volume = max(0.0, min(150.0, value))

    def volume_up(self, step: float = 5.0) -> None:
        self.volume = self.volume + step

    def volume_down(self, step: float = 5.0) -> None:
        self.volume = self.volume - step

    @property
    def is_playing(self) -> bool:
        if self._stopped:
            return False
        try:
            return not self._mpv.pause
        except Exception:
            return False

    @property
    def is_paused(self) -> bool:
        if self._stopped:
            return False
        try:
            return bool(self._mpv.pause)
        except Exception:
            return False

    @property
    def is_stopped(self) -> bool:
        return self._stopped

    @property
    def current_station(self) -> Station | None:
        return self._current_station

    @property
    def metadata(self) -> dict:
        try:
            return dict(self._mpv.metadata or {})
        except Exception:
            return {}

    @property
    def icy_title(self) -> str:
        """Get the ICY stream title (current song on radio)."""
        meta = self.metadata
        return meta.get("icy-title", "")

    @property
    def time_pos(self) -> float | None:
        if self._stopped:
            return None
        try:
            return self._mpv.time_pos
        except Exception:
            return None

    @property
    def duration(self) -> float | None:
        if self._stopped:
            return None
        try:
            return self._mpv.duration
        except Exception:
            return None

    def shutdown(self) -> None:
        self._mpv.terminate()
