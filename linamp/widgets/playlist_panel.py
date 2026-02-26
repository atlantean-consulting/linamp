from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import ListView, ListItem, Label

from linamp.messages import PlayerStateUpdate, StationSelected
from linamp.stations import Station, STATIONS


class PlaylistPanel(Container):
    """Queue/playlist showing stations with active highlight."""

    DEFAULT_CSS = """
    PlaylistPanel {
        height: 1fr;
        border: round $primary;
    }
    PlaylistPanel ListView {
        height: 1fr;
    }
    PlaylistPanel .active-station {
        color: $success;
        text-style: bold;
    }
    """

    def __init__(self, stations: list[Station] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._stations = stations or STATIONS
        self._active_index: int | None = None

    def compose(self) -> ComposeResult:
        items = []
        for i, station in enumerate(self._stations):
            label = Label(f"  {station.name} [{station.genre}]")
            items.append(ListItem(label, id=f"station-{i}"))
        yield ListView(*items)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(self._stations):
            self.post_message(StationSelected(self._stations[idx]))

    def on_player_state_update(self, event: PlayerStateUpdate) -> None:
        if event.station is None:
            new_index = None
        else:
            new_index = next(
                (i for i, s in enumerate(self._stations) if s.url == event.station.url),
                None,
            )

        if new_index != self._active_index:
            # Clear old highlight
            if self._active_index is not None:
                try:
                    old_item = self.query_one(f"#station-{self._active_index}", ListItem)
                    old_label = old_item.query_one(Label)
                    old_station = self._stations[self._active_index]
                    old_label.update(f"  {old_station.name} [{old_station.genre}]")
                    old_label.remove_class("active-station")
                except Exception:
                    pass

            # Set new highlight
            if new_index is not None:
                try:
                    new_item = self.query_one(f"#station-{new_index}", ListItem)
                    new_label = new_item.query_one(Label)
                    new_station = self._stations[new_index]
                    new_label.update(f"▶ {new_station.name} [{new_station.genre}]")
                    new_label.add_class("active-station")
                except Exception:
                    pass

            self._active_index = new_index
