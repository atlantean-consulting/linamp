from textual.widgets import Static

from linamp.messages import PlayerStateUpdate


class NowPlayingBar(Static):
    """Compact now-playing status bar, shared across views."""

    DEFAULT_CSS = """
    NowPlayingBar {
        height: 1;
        dock: bottom;
        background: $accent;
        color: $text;
        padding: 0 1;
    }
    """

    def on_player_state_update(self, event: PlayerStateUpdate) -> None:
        if event.station and (event.is_playing or event.is_paused):
            icon = "\u25b6" if event.is_playing else "\u23f8"
            # Prefer ICY title (real-time artist/track), then media title, then genre
            detail = event.icy_title
            if not detail and event.media_title and event.media_title != event.station.name:
                detail = event.media_title
            if not detail:
                detail = event.station.genre
            if detail:
                self.update(f"{icon} {event.station.name}  \u00b7  {detail}")
            else:
                self.update(f"{icon} {event.station.name}")
        else:
            self.update("\u25a0 Stopped")
