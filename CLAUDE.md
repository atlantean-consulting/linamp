# Linamp

Terminal music player — the love child of Winamp and Midnight Commander.

## Stack
- **Python 3.11+** with **Textual 8.0** (TUI framework)
- **mpv** via **python-mpv** (audio backend)
- System dependency: `sudo apt install mpv libmpv-dev` (libmpv2)

## Running
```bash
pip install -e .
python -m linamp
```

## Architecture

### Two views (toggle with Tab)
1. **Player View** (default) — Winamp-style compact player: now-playing, progress bar, transport controls, volume, visualizer, playlist
2. **Browser View** — MC-style dual pane: station browser (left) + play queue (right) + now-playing bar (bottom)

### Key modules
- `linamp/app.py` — Main Textual App. Owns `AudioPlayer` singleton (`self.audio`). Manages modes via `MODES` dict + `DEFAULT_MODE`. Polls player state every 500ms via `set_interval`.
- `linamp/player.py` — mpv wrapper. Critical flags: `video=False, terminal=False, input_terminal=False`. Synchronous API (mpv handles I/O on its own threads).
- `linamp/stations.py` — `Station` dataclass + hardcoded `STATIONS` list.
- `linamp/messages.py` — `PlayerStateUpdate` (broadcast by poll timer) and `StationSelected` (from UI interaction).
- `linamp/screens/` — `PlayerView` and `BrowserView` screens.
- `linamp/widgets/` — All widgets extend `Container` (not `Widget`) because Textual 8.0 requires container semantics for widgets that compose children.

### Important Textual 8.0 notes
- Do NOT use `Widget` as base class for widgets that `compose()` children — use `Container`. Textual 8.0 calls `render()` on non-container Widgets which returns `css_identifier_styled` instead of delegating to children, causing `AttributeError: 'str' object has no attribute 'render_strips'`.
- Do NOT set `self._current_mode` directly — it's Textual's internal attribute. Use `DEFAULT_MODE` class attribute for initial mode, and `self.current_mode` property to read current mode.
- Use `Binding("key", "action", "label", priority=True)` for global keybindings that must work regardless of focus.

## Keybindings
| Key | Action |
|-----|--------|
| Tab | Toggle player/browser view |
| Space | Play/pause |
| s | Stop |
| +/= | Volume up |
| - | Volume down |
| Enter | Play selected station |
| Up/Down | Navigate list |
| q | Quit |

## Phase Roadmap
1. **Internet Radio** ✅ (Phase 1 — current) — 8 stations, streaming via mpv
2. **YouTube** — yt-dlp integration, specifically "Meditative Mind" binaural beats channel
3. **Local Library** — Browse/play local music collection (user plans 150GB+ collection)
4. **Apple Music** — TBD, DRM challenges

## Stations
Stream URLs are embedded in `stations.py`. Notable:
- WEQX 102.7: `https://stream.surfernetwork.com/cc6a319f460vv` (extracted from lightningstream.com player page JS — the old radio-browser.info URLs are stale)
- WMHT 89.1: `https://wmht.streamguys1.com/wmht1` (confirmed working)
- SomaFM stations use `ice2.somafm.com` URLs
- Other stations (WFMU, KEXP, NTS) need testing

## Dev Notes
- Visualizer is simulated (random bars that pulse during playback). Real FFT from mpv is complex — deferred to later phase.
- Player state is polled (500ms interval) rather than using mpv property observer callbacks, to avoid threading issues between mpv threads and Textual's asyncio loop.
- `AudioPlayer` is a singleton on the App, accessed via `self.app.audio` from screens/widgets.
