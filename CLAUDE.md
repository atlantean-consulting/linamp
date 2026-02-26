# Linamp

Terminal music player — the love child of Winamp and Midnight Commander.

## Stack
- **Python 3.11+** with **Textual 8.0** (TUI framework)
- **mpv** via **python-mpv** (audio backend)
- **yt-dlp** (YouTube and web stream extraction)
- System dependency: `sudo apt install mpv libmpv-dev` (libmpv2)

## Running
```bash
pip install -r requirements.txt
python -m linamp
```

## Architecture

### Two views (toggle with Tab)
1. **Player View** (default) — Winamp-style compact player: now-playing, progress bar, transport controls, volume, visualizer, playlist
2. **Browser View** — MC-style dual pane: folder/station tree (left) + flat play queue (right) + now-playing bar + command hints (bottom)

### Key modules
- `linamp/app.py` — Main Textual App. Owns `AudioPlayer` singleton (`self.audio`) and `self.library` (list of `Folder`). Manages modes via `MODES` dict + `DEFAULT_MODE`. Polls player state every 500ms via `set_interval`. `flat_stations` property flattens library for playlist panels. Handles `LibraryChanged` by saving to disk and re-broadcasting to sibling `PlaylistPanel` widgets (Textual messages only bubble up, not sideways).
- `linamp/player.py` — mpv wrapper. Critical flags: `video=False, terminal=False, input_terminal=False, ytdl_format="bestaudio/best"`. URL resolution pipeline: YouTube URLs pass directly to mpv's ytdl hook (avoids expired signed URLs); direct stream URLs (containing "ice", "stream", ".mp3", etc.) skip resolution; other URLs try yt-dlp extraction with 15s timeout, falling back to raw URL. `_is_ytdl_url()` classmethod identifies YouTube domains. `YTDL_DOMAINS` tuple lists recognized domains.
- `linamp/stations.py` — `Station` dataclass (name, url, genre) + `Folder` dataclass (name, stations). `load_library()` reads `~/.config/linamp/stations.json` with auto-migration from old flat format. `save_library()` writes folder structure. `all_stations()` helper flattens folders. `_migrate_flat_list()` auto-categorizes stations into Radio/YouTube folders based on URL. Legacy `load_stations()`/`save_stations()`/`STATIONS` aliases kept for backwards compat.
- `linamp/messages.py` — `PlayerStateUpdate` (broadcast by poll timer), `StationSelected` (from UI interaction), `LibraryChanged` (from station management CRUD, carries `list[Folder]`).
- `linamp/screens/player_view.py` — PlayerView screen. Passes `self.app.flat_stations` to PlaylistPanel.
- `linamp/screens/browser_view.py` — BrowserView screen with `NowPlayingBar` (now-playing status), `CommandHints` (MC-style key hints using Rich markup), and dual-pane layout. Passes `self.app.library` to StationList and `self.app.flat_stations` to PlaylistPanel.
- `linamp/widgets/station_list.py` — Left pane browser. Uses Textual `Tree` widget (not ListView) with folder nodes (📁) and station leaves (📻 for radio, 🎵 for YouTube). Full CRUD: add/delete/rename/edit stations and folders, move stations within folders. Inline `Input` widgets for editing. YouTube URL auto-detection: fetches title via yt-dlp in background thread (`asyncio.to_thread`), auto-fills name and genre. Add flow is URL-first to enable auto-detection. Delete requires double-press confirmation.
- `linamp/widgets/playlist_panel.py` — Right pane flat play queue. Shows all stations across all folders. Highlights active station with ▶ icon. Handles `LibraryChanged` to rebuild list (must `await lv.clear()` before appending — see Textual notes).
- `linamp/widgets/transport.py` — Transport controls using `Static` widgets with `border: round` (not Textual `Button` which has pseudo-3D styling that clashes with box-drawing UI).
- `linamp/widgets/` — All widgets extend `Container` (not `Widget`) because Textual 8.0 requires container semantics for widgets that compose children.

### Data persistence
- **Path**: `~/.config/linamp/stations.json`
- **Format**: `{"folders": [{"name": "Radio", "stations": [{"name": "...", "url": "...", "genre": "..."}]}]}`
- **Migration**: Old flat format `[{"name": "...", "url": "...", "genre": "..."}]` auto-detected and migrated on first load, splitting stations into Radio/YouTube folders based on URL domain.
- **Defaults**: If no JSON file exists, `DEFAULT_LIBRARY` provides 8 radio stations in a Radio folder and an empty YouTube folder.

### URL resolution pipeline (in `AudioPlayer._resolve_url`)
1. **YouTube/ytdl domains** → pass through to mpv (mpv's ytdl hook handles extraction internally, avoiding expired signed URLs)
2. **Direct streams** (URL contains "ice", "stream", ".mp3", ".aac", ".ogg", ".m3u", ".pls") → pass through to mpv
3. **Other URLs** → try `yt-dlp --no-download --print urls -f bestaudio/best` with 15s timeout → use extracted URL if successful
4. **Fallback** → pass raw URL to mpv

### Important Textual 8.0 notes
- Do NOT use `Widget` as base class for widgets that `compose()` children — use `Container`. Textual 8.0 calls `render()` on non-container Widgets which returns `css_identifier_styled` instead of delegating to children, causing `AttributeError: 'str' object has no attribute 'render_strips'`.
- Do NOT set `self._current_mode` directly — it's Textual's internal attribute. Use `DEFAULT_MODE` class attribute for initial mode, and `self.current_mode` property to read current mode.
- Use `Binding("key", "action", "label", priority=True)` for global keybindings that must work regardless of focus.
- `ListView.clear()` is **async** — returns `AwaitRemove`. You MUST `await lv.clear()` before appending new items with the same IDs, otherwise you get `DuplicateIds` errors. Same applies to any widget removal followed by re-adding widgets with the same IDs.
- When dynamically building widget trees (e.g., a `Vertical` with `Input` children), pass children to the constructor — do NOT call `form.mount(child)` before the form itself is mounted. Use `await self.mount(form)` then access children.
- Textual messages bubble **up** the DOM tree only (child → parent → app). Sibling widgets do NOT receive each other's messages. To propagate to siblings, handle at the App level and explicitly call methods on siblings (e.g., `panel.on_library_changed(event)`).
- `$text-muted` and `$text-disabled` are NOT valid Textual CSS color variables for border colors. Use hex colors instead (e.g., `#585b70`).
- Action methods can be `async def` — Textual will await them automatically.

## Keybindings

### Global (both views)
| Key | Action |
|-----|--------|
| Tab | Toggle player/browser view |
| Space | Play/pause |
| s | Stop |
| +/= | Volume up |
| - | Volume down |
| q | Quit |

### Browser view (left pane focused)
| Key | Action |
|-----|--------|
| Enter | Play selected station / expand-collapse folder |
| Up/Down | Navigate tree |
| f | Create new folder |
| a | Add station to selected folder |
| d | Delete station or folder (press twice to confirm) |
| r | Rename station or folder |
| e | Edit station URL/genre |
| Ctrl+Up | Move station up within folder |
| Ctrl+Down | Move station down within folder |
| Escape | Cancel edit in progress |

## Phase Roadmap
1. **Internet Radio** ✅ (Phase 1) — 8 default stations, streaming via mpv
2. **Station Management + YouTube** ✅ (Phase 1.5) — CRUD, folder tree, persistence, yt-dlp integration
3. **Local Library** — Browse/play local music collection (user plans 150GB+ collection)
4. **Apple Music** — TBD, DRM challenges

## Stations
Stream URLs are persisted in `~/.config/linamp/stations.json`. Notable confirmed-working streams:
- WEQX 102.7: `https://stream.surfernetwork.com/cc6a319f460vv` (extracted from lightningstream.com player page JS)
- WMHT 89.1: `https://wmht.streamguys1.com/wmht1` (StreamGuys)
- WEXT 97.7: `https://wmht.streamguys1.com/wext1` (sister station to WMHT, same StreamGuys infra, mount point `wext1`)
- WMVY 88.7: `https://mvyradio.streamguys1.com/mvy-mp3` (StreamGuys)
- SomaFM stations: `ice2.somafm.com` URLs (256kbps MP3)
- WFMU, KEXP, NTS: confirmed working

## Dev Notes
- Visualizer is simulated (random bars that pulse during playback). Real FFT from mpv is complex — deferred to later phase.
- Player state is polled (500ms interval) rather than using mpv property observer callbacks, to avoid threading issues between mpv threads and Textual's asyncio loop.
- `AudioPlayer` is a singleton on the App, accessed via `self.app.audio` from screens/widgets.
- Transport buttons use `Static` + `border: round` instead of `Button` to match the box-drawing aesthetic of the rest of the UI.
- yt-dlp must be kept up to date — YouTube frequently changes their streaming format. An outdated yt-dlp will fail with HTTP 403 errors. The version that ships with pip may be stale; run `pip install --upgrade yt-dlp` if YouTube playback breaks.
- When finding radio stream URLs: check the station's FAQ/audio help page, look for StreamGuys/Triton/SecureNet patterns, probe mount point variants (e.g., `/wext1`, `/wmht1`). HTTP 200 with `content-type: audio/*` confirms a working stream.
