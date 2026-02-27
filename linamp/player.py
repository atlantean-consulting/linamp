from __future__ import annotations

import logging
import shutil
import subprocess

import mpv

from linamp.stations import Station

log = logging.getLogger(__name__)


class AudioPlayer:
    """Wraps mpv into a simple interface for the TUI layer."""

    def __init__(self) -> None:
        self._mpv = mpv.MPV(
            video=False,
            terminal=False,
            input_terminal=False,
            ytdl_format="bestaudio/best",
        )
        self._current_station: Station | None = None
        self._stopped = True

    def play(self, station: Station) -> None:
        self._current_station = station
        self._stopped = False
        url = self._resolve_url(station.url)
        self._mpv.play(url)

    # Domains where mpv's built-in ytdl hook handles playback natively.
    # We pass these URLs straight through — pre-resolving would produce
    # temporary signed URLs that expire before mpv can use them.
    YTDL_DOMAINS = (
        "youtube.com", "youtu.be", "youtube-nocookie.com",
        "music.youtube.com",
    )

    @classmethod
    def _is_ytdl_url(cls, url: str) -> bool:
        """Check if a URL should be handled by mpv's ytdl hook."""
        from urllib.parse import urlparse
        try:
            host = urlparse(url).hostname or ""
            return any(host == d or host.endswith("." + d) for d in cls.YTDL_DOMAINS)
        except Exception:
            return False

    @classmethod
    def _resolve_url(cls, url: str) -> str:
        """Try yt-dlp to extract a direct stream URL, fall back to raw URL.

        YouTube URLs are passed through directly — mpv's ytdl hook handles
        them better than pre-resolved temporary URLs that expire quickly.
        """
        # Let mpv's ytdl hook handle known video platforms directly
        if cls._is_ytdl_url(url):
            return url
        # Skip resolution for direct stream URLs (icecast/shoutcast/raw audio)
        if any(h in url for h in ("ice", "stream", ".mp3", ".aac", ".ogg", ".m3u", ".pls")):
            return url
        ytdlp = shutil.which("yt-dlp")
        if not ytdlp:
            return url
        try:
            result = subprocess.run(
                [ytdlp, "--no-download", "--print", "urls", "-f", "bestaudio/best", url],
                capture_output=True, text=True, timeout=15,
            )
            resolved = result.stdout.strip().splitlines()
            if result.returncode == 0 and resolved and resolved[0]:
                log.info("yt-dlp resolved %s → %s", url, resolved[0])
                return resolved[0]
        except (subprocess.TimeoutExpired, OSError) as exc:
            log.debug("yt-dlp failed for %s: %s", url, exc)
        return url

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
    def media_title(self) -> str:
        """Get mpv's synthesized media title (incorporates stream metadata)."""
        try:
            return self._mpv.media_title or ""
        except Exception:
            return ""

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
