from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import ListView, ListItem, Label

from linamp.messages import StationSelected
from linamp.stations import Station, STATIONS


class StationList(Container):
    """Station browser for the MC-style left pane."""

    DEFAULT_CSS = """
    StationList {
        height: 1fr;
        border: round $accent;
    }
    StationList ListView {
        height: 1fr;
    }
    """

    def __init__(self, stations: list[Station] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._stations = stations or STATIONS

    def compose(self) -> ComposeResult:
        items = []
        for i, station in enumerate(self._stations):
            label = Label(f"📻 {station.name} [{station.genre}]")
            items.append(ListItem(label, id=f"browse-{i}"))
        yield ListView(*items)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx is not None and 0 <= idx < len(self._stations):
            self.post_message(StationSelected(self._stations[idx]))
