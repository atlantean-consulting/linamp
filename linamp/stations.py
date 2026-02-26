import json
from dataclasses import dataclass, asdict, field
from pathlib import Path


@dataclass
class Station:
    name: str
    url: str
    genre: str = ""


@dataclass
class Folder:
    name: str
    stations: list[Station] = field(default_factory=list)


def all_stations(folders: list[Folder]) -> list[Station]:
    """Flatten a folder list into a single station list."""
    return [s for f in folders for s in f.stations]


DEFAULT_LIBRARY: list[Folder] = [
    Folder("Radio", [
        Station("WEQX 102.7", "https://stream.surfernetwork.com/cc6a319f460vv", "Alternative"),
        Station("WMHT 89.1", "https://wmht.streamguys1.com/wmht1", "Classical"),
        Station("SomaFM Groove Salad", "https://ice2.somafm.com/groovesalad-256-mp3", "Ambient"),
        Station("SomaFM Drone Zone", "https://ice2.somafm.com/dronezone-256-mp3", "Ambient"),
        Station("SomaFM DEF CON", "https://ice2.somafm.com/defcon-256-mp3", "Electronic"),
        Station("WFMU", "https://stream0.wfmu.org/freeform-128k", "Freeform"),
        Station("KEXP 90.3", "https://kexp-mp3-128.streamguys1.com/kexp128.mp3", "Indie"),
        Station("NTS Radio 1", "https://stream-relay-geo.ntslive.net/stream", "Eclectic"),
    ]),
    Folder("YouTube", []),
]

STATIONS_PATH = Path.home() / ".config" / "linamp" / "stations.json"


def _migrate_flat_list(data: list[dict]) -> list[dict]:
    """Migrate old flat station list into folder structure."""
    from linamp.player import AudioPlayer
    radio = []
    youtube = []
    for entry in data:
        url = entry.get("url", "")
        if AudioPlayer._is_ytdl_url(url):
            youtube.append(entry)
        else:
            radio.append(entry)
    folders = [{"name": "Radio", "stations": radio}]
    if youtube:
        folders.append({"name": "YouTube", "stations": youtube})
    return folders


def load_library() -> list[Folder]:
    """Load folder/station library from JSON, with migration from flat format."""
    if STATIONS_PATH.exists():
        try:
            data = json.loads(STATIONS_PATH.read_text())
            # Detect old flat format (list of station dicts)
            if isinstance(data, list) and data and "url" in data[0]:
                data = {"folders": _migrate_flat_list(data)}
            if isinstance(data, dict) and "folders" in data:
                folders = []
                for fd in data["folders"]:
                    stations = [Station(**s) for s in fd.get("stations", [])]
                    folders.append(Folder(fd["name"], stations))
                return folders
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    return [Folder(f.name, [Station(s.name, s.url, s.genre) for s in f.stations])
            for f in DEFAULT_LIBRARY]


def save_library(folders: list[Folder]) -> None:
    """Save folder/station library to JSON."""
    STATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "folders": [
            {"name": f.name, "stations": [asdict(s) for s in f.stations]}
            for f in folders
        ]
    }
    STATIONS_PATH.write_text(json.dumps(data, indent=2) + "\n")


# Legacy aliases for any remaining imports
def load_stations() -> list[Station]:
    return all_stations(load_library())

def save_stations(stations: list[Station]) -> None:
    save_library([Folder("Radio", stations)])

DEFAULT_STATIONS = all_stations(DEFAULT_LIBRARY)
STATIONS = DEFAULT_STATIONS
