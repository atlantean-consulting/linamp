from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import ListView, ListItem, Label

from linamp.messages import PlayerStateUpdate, StationSelected, LibraryChanged
from linamp.stations import Station, all_stations, DEFAULT_LIBRARY


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
        self._stations = stations or all_stations(DEFAULT_LIBRARY)
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

    async def set_stations(self, stations: list[Station]) -> None:
        """Replace the playlist with a new station list."""
        self._stations = list(stations)
        self._active_index = None
        lv = self.query_one(ListView)
        await lv.clear()
        for i, station in enumerate(self._stations):
            label = Label(f"  {station.name} [{station.genre}]")
            lv.append(ListItem(label, id=f"station-{i}"))

    @property
    def selected_index(self) -> int | None:
        """Return the currently highlighted index in the ListView."""
        lv = self.query_one(ListView)
        idx = lv.index
        if idx is not None and 0 <= idx < len(self._stations):
            return idx
        return None

    @property
    def stations(self) -> list[Station]:
        """Return the current station list."""
        return list(self._stations)

    async def move_track(self, direction: int) -> None:
        """Move the selected track up (direction=-1) or down (direction=1)."""
        idx = self.selected_index
        if idx is None:
            return
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self._stations):
            return
        # Swap in the data list
        self._stations[idx], self._stations[new_idx] = (
            self._stations[new_idx],
            self._stations[idx],
        )
        # Rebuild and re-select at new position
        await self._rebuild_list(select_index=new_idx)

    async def delete_track(self) -> None:
        """Delete the currently selected track."""
        idx = self.selected_index
        if idx is None:
            return
        self._stations.pop(idx)
        # Select the next item (or previous if at end)
        new_idx = min(idx, len(self._stations) - 1) if self._stations else None
        await self._rebuild_list(select_index=new_idx)

    async def _rebuild_list(self, select_index: int | None = None) -> None:
        """Rebuild the ListView from _stations and optionally select an index."""
        self._active_index = None
        lv = self.query_one(ListView)
        await lv.clear()
        for i, station in enumerate(self._stations):
            label = Label(f"  {station.name} [{station.genre}]")
            lv.append(ListItem(label, id=f"station-{i}"))
        if select_index is not None and 0 <= select_index < len(self._stations):
            lv.index = select_index

    async def on_library_changed(self, event: LibraryChanged) -> None:
        await self.set_stations(all_stations(event.folders))
