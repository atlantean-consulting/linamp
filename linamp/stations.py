from dataclasses import dataclass


@dataclass
class Station:
    name: str
    url: str
    genre: str = ""


STATIONS: list[Station] = [
    Station("WEQX 102.7", "https://stream.surfernetwork.com/cc6a319f460vv", "Alternative"),
    Station("WMHT 89.1", "https://wmht.streamguys1.com/wmht1", "Classical"),
    Station("SomaFM Groove Salad", "https://ice2.somafm.com/groovesalad-256-mp3", "Ambient"),
    Station("SomaFM Drone Zone", "https://ice2.somafm.com/dronezone-256-mp3", "Ambient"),
    Station("SomaFM DEF CON", "https://ice2.somafm.com/defcon-256-mp3", "Electronic"),
    Station("WFMU", "https://stream0.wfmu.org/freeform-128k", "Freeform"),
    Station("KEXP 90.3", "https://kexp-mp3-128.streamguys1.com/kexp128.mp3", "Indie"),
    Station("NTS Radio 1", "https://stream-relay-geo.ntslive.net/stream", "Eclectic"),
]
