"""Audio file metadata extraction using mutagen."""

from __future__ import annotations

import os
from pathlib import Path

from mutagen import File
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis


def _format_duration(seconds: float) -> str:
    """Format seconds as M:SS or H:MM:SS."""
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _format_size(bytes_: int) -> str:
    """Format file size as human-readable string."""
    if bytes_ < 1024:
        return f"{bytes_} B"
    elif bytes_ < 1024 * 1024:
        return f"{bytes_ / 1024:.1f} KB"
    elif bytes_ < 1024 * 1024 * 1024:
        return f"{bytes_ / (1024 * 1024):.1f} MB"
    return f"{bytes_ / (1024 * 1024 * 1024):.1f} GB"


def _get_tag(audio, keys: list[str], default: str = "") -> str:
    """Try multiple tag keys, return first match as string."""
    for key in keys:
        val = audio.get(key)
        if val:
            if isinstance(val, list):
                return str(val[0])
            return str(val)
    return default


def _get_mp4_tag(audio: MP4, keys: list[str], default: str = "") -> str:
    """MP4/M4A tags use different key format."""
    for key in keys:
        val = audio.tags.get(key) if audio.tags else None
        if val:
            if isinstance(val, list):
                return str(val[0])
            return str(val)
    return default


def read_metadata(filepath: str) -> dict:
    """Extract normalized metadata from an audio file.

    Returns a dict with keys: title, artist, album, track, year, genre,
    duration, bitrate, sample_rate, format, file_size. All values are strings.
    Returns empty/fallback values on error (never raises).
    """
    result = {
        "title": "",
        "artist": "",
        "album": "",
        "track": "",
        "year": "",
        "genre": "",
        "duration": "",
        "bitrate": "",
        "sample_rate": "",
        "format": "",
        "file_size": "",
    }

    try:
        path = Path(filepath)
        result["file_size"] = _format_size(path.stat().st_size)
        result["format"] = path.suffix.lstrip(".").upper()

        audio = File(filepath)
        if audio is None:
            return result

        # Duration and audio info
        if hasattr(audio.info, "length") and audio.info.length:
            result["duration"] = _format_duration(audio.info.length)
        if hasattr(audio.info, "bitrate") and audio.info.bitrate:
            result["bitrate"] = f"{audio.info.bitrate // 1000} kbps"
        if hasattr(audio.info, "sample_rate") and audio.info.sample_rate:
            result["sample_rate"] = f"{audio.info.sample_rate} Hz"

        # Tag extraction varies by format
        if isinstance(audio, MP3):
            tags = audio.tags
            if tags:
                result["title"] = str(tags.get("TIT2", "")) or ""
                result["artist"] = str(tags.get("TPE1", "")) or ""
                result["album"] = str(tags.get("TALB", "")) or ""
                result["genre"] = str(tags.get("TCON", "")) or ""
                result["year"] = str(tags.get("TDRC", "")) or str(tags.get("TYER", "")) or ""
                trck = str(tags.get("TRCK", "")) or ""
                if trck:
                    result["track"] = trck.split("/")[0]
        elif isinstance(audio, MP4):
            result["title"] = _get_mp4_tag(audio, ["\xa9nam"])
            result["artist"] = _get_mp4_tag(audio, ["\xa9ART"])
            result["album"] = _get_mp4_tag(audio, ["\xa9alb"])
            result["genre"] = _get_mp4_tag(audio, ["\xa9gen"])
            result["year"] = _get_mp4_tag(audio, ["\xa9day"])
            trkn = audio.tags.get("trkn") if audio.tags else None
            if trkn:
                result["track"] = str(trkn[0][0])
        elif isinstance(audio, (FLAC, OggVorbis)):
            result["title"] = _get_tag(audio, ["title"])
            result["artist"] = _get_tag(audio, ["artist"])
            result["album"] = _get_tag(audio, ["album"])
            result["genre"] = _get_tag(audio, ["genre"])
            result["year"] = _get_tag(audio, ["date"])
            result["track"] = _get_tag(audio, ["tracknumber"])
        else:
            # Generic fallback for other formats
            result["title"] = _get_tag(audio, ["title", "TIT2"])
            result["artist"] = _get_tag(audio, ["artist", "TPE1"])
            result["album"] = _get_tag(audio, ["album", "TALB"])
            result["genre"] = _get_tag(audio, ["genre", "TCON"])
            result["year"] = _get_tag(audio, ["date", "year", "TDRC"])
            result["track"] = _get_tag(audio, ["tracknumber", "TRCK"])

        # Clean up track number (remove /total)
        if "/" in result["track"]:
            result["track"] = result["track"].split("/")[0]

    except Exception:
        pass  # Return whatever we have so far

    return result
