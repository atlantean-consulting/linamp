# Linamp

Terminal music player — the love child of Winamp and Midnight Commander.

## Stack
- **Python 3.11+** with **Textual 8.0** (TUI framework)
- **mpv** via **python-mpv** (audio backend)
- **yt-dlp** (YouTube and web stream extraction)
- **mutagen** (audio metadata read/write — MP3/FLAC/M4A/OGG tags)
- System dependency: `sudo apt install mpv libmpv-dev` (libmpv2)

## Running
```bash
pip install -r requirements.txt
python -m linamp              # Player + radio browser
python -m linamp --library    # Standalone library manager
python -m linamp.library      # Standalone library manager (direct)
```

## Architecture

### Two apps
1. **LinampApp** (`linamp/app.py`) — Player + radio browser. Two views toggled with Tab:
   - **Player View** (default) — Winamp-style compact player: now-playing, progress bar, transport controls, volume, visualizer, playlist
   - **Browser View** — MC-style dual pane: folder/station tree (left) + flat play queue (right) + now-playing bar + command hints (bottom)
2. **LibraryApp** (`linamp/library.py`) — Standalone local music library manager. MC-style dual pane: directory tree filtered to audio files (left) + metadata panel (right, shows tags via mutagen with inline editing). Launched via `python -m linamp.library`, `python -m linamp --library`, or F5 from within LinampApp (suspends TUI, audio keeps playing).

### Key modules
- `linamp/app.py` — Main Textual App (player + radio browser). Owns `AudioPlayer` singleton (`self.audio`), `self.config` (`AppConfig`), and `self.library` (list of `Folder`). Manages modes via `MODES` dict + `DEFAULT_MODE`. Polls player state every 500ms via `set_interval`, broadcasting `PlayerStateUpdate` to each widget individually via `screen.walk_children()` (creating a fresh message per widget to avoid Textual's stop-propagation). `flat_stations` property flattens library for playlist panels. Handles `LibraryChanged` by saving to disk and re-broadcasting to sibling `PlaylistPanel` widgets (Textual messages only bubble up, not sideways). F5 binding suspends TUI and launches library manager as subprocess (`subprocess.run` + `self.suspend()`); audio playback continues via mpv.
- `linamp/library.py` — Standalone library manager Textual App. Loads `AppConfig` for `music_root`. Single mode: `LibraryView`. Entry point: `main()`. Shares config, widgets, and CSS theme with LinampApp.
- `linamp/config.py` — `AppConfig` dataclass (`music_root` field, default `~/Music`) + `load_config()`/`save_config()`. Persisted at `~/.config/linamp/config.json`.
- `linamp/player.py` — mpv wrapper. Critical flags: `video=False, terminal=False, input_terminal=False, ytdl_format="bestaudio/best"`. Properties: `icy_title` (ICY stream metadata), `media_title` (mpv's synthesized title incorporating stream metadata), `metadata` (raw dict). URL resolution pipeline: local file paths (starting with `/`) pass through directly; YouTube URLs pass to mpv's ytdl hook; direct stream URLs skip resolution; other URLs try yt-dlp extraction. `_is_ytdl_url()` classmethod identifies YouTube domains. `YTDL_DOMAINS` tuple lists recognized domains.
- `linamp/stations.py` — `Station` dataclass (name, url, genre) + `Folder` dataclass (name, stations). `load_library()` reads `~/.config/linamp/stations.json` with auto-migration from old flat format. `save_library()` writes folder structure. `all_stations()` helper flattens folders. `_migrate_flat_list()` auto-categorizes stations into Radio/YouTube folders based on URL. Legacy `load_stations()`/`save_stations()`/`STATIONS` aliases kept for backwards compat.
- `linamp/metadata.py` — Audio metadata read/write via mutagen. `read_metadata(filepath)` returns normalized dict (title, artist, album, track, year, genre, duration, bitrate, sample_rate, format, file_size) across MP3/ID3, MP4, FLAC, OGG. `write_metadata(filepath, tags)` writes a subset of tags back using format-appropriate methods (ID3 frames for MP3, iTunes atoms for MP4, Vorbis comments for FLAC/OGG). Both handle format detection internally. `read_metadata` never raises; `write_metadata` raises on failure.
- `linamp/messages.py` — `PlayerStateUpdate` (broadcast by poll timer, carries `icy_title`, `media_title`, and other state), `StationSelected` (from UI interaction), `FileHighlighted` (from FileBrowser cursor movement, carries `Path | None`), `LibraryChanged` (from station management CRUD, carries `list[Folder]`).
- `linamp/screens/player_view.py` — PlayerView screen. Passes `self.app.flat_stations` to PlaylistPanel.
- `linamp/screens/browser_view.py` — BrowserView screen with `CommandHints` (MC-style key hints using Rich markup) and dual-pane layout. Passes `self.app.library` to StationList and `self.app.flat_stations` to PlaylistPanel. Uses shared `NowPlayingBar` from widgets.
- `linamp/screens/library_view.py` — LibraryView screen for the standalone library manager. Dual-pane: `FileBrowser` (left) + `MetadataPanel` (right) + `NowPlayingBar` + `LibraryCommandHints`. Handles `FileHighlighted` messages to update metadata panel on cursor movement. Owns the `e` binding for tag editing (at screen level with `priority=True` so it fires regardless of focus pane), delegating to `MetadataPanel.action_edit()`.
- `linamp/widgets/station_list.py` — Left pane browser. Uses Textual `Tree` widget (not ListView) with folder nodes (📁) and station leaves (📻 for radio, 🎵 for YouTube). Full CRUD: add/delete/rename/edit stations and folders, move stations within folders. Inline `Input` widgets for editing. YouTube URL auto-detection: fetches title via yt-dlp in background thread (`asyncio.to_thread`), auto-fills name and genre. Add flow is URL-first to enable auto-detection. Delete requires double-press confirmation.
- `linamp/widgets/playlist_panel.py` — Right pane flat play queue. Shows all stations across all folders. Highlights active station with ▶ icon. Handles `LibraryChanged` to rebuild list (must `await lv.clear()` before appending — see Textual notes).
- `linamp/widgets/now_playing_bar.py` — Shared `NowPlayingBar` widget (compact 1-line status bar with metadata priority). Used by both BrowserView and LibraryView.
- `linamp/widgets/file_browser.py` — `AudioDirectoryTree` (Textual `DirectoryTree` subclass filtered to audio extensions: .mp3, .flac, .m4a, .ogg, .opus, .wav, .aac, .wma) + `FileBrowser` container wrapper. Posts `FileHighlighted` on cursor movement (for metadata panel), and `StationSelected` on Enter (for playback). Uses Textual's built-in `on_tree_node_highlighted`/`on_tree_node_selected` handlers — does NOT override Enter with a custom `Binding` (that would steal Enter from `DirectoryTree` and prevent folder expand/collapse).
- `linamp/widgets/metadata_panel.py` — Right-pane metadata display with inline tag editing. Displays 11 fields read from mutagen (title, artist, album, track, year, genre, duration, bitrate, sample_rate, format, file_size). Edit mode (`e` key, handled at screen level): replaces editable fields (title, artist, album, track, year, genre) with `Input` widgets, Tab between fields, Enter saves via `write_metadata()`, Escape cancels. Uses `MODE_BROWSE`/`MODE_EDIT` state machine. Metadata loading is async (`asyncio.to_thread`) to avoid blocking UI.
- `linamp/widgets/track_info.py` — Standalone now-playing widget (not currently wired into any view). Shows "NOW PLAYING" label + track title with metadata priority: ICY title > media title > station name.
- `linamp/widgets/transport.py` — Transport controls using `Static` widgets with `border: round` (not Textual `Button` which has pseudo-3D styling that clashes with box-drawing UI).
- `linamp/widgets/` — All widgets extend `Container` (not `Widget`) because Textual 8.0 requires container semantics for widgets that compose children.

### Data persistence
- **Config**: `~/.config/linamp/config.json` — `{"music_root": "~/Music"}`. Loaded by both apps.
- **Stations**: `~/.config/linamp/stations.json`
- **Format**: `{"folders": [{"name": "Radio", "stations": [{"name": "...", "url": "...", "genre": "..."}]}]}`
- **Migration**: Old flat format `[{"name": "...", "url": "...", "genre": "..."}]` auto-detected and migrated on first load, splitting stations into Radio/YouTube folders based on URL domain.
- **Defaults**: If no JSON file exists, `DEFAULT_LIBRARY` provides 8 radio stations in a Radio folder and an empty YouTube folder.

### Stream metadata priority
All now-playing displays (NowPlaying widget, NowPlayingBar in browser) use this priority:
1. **ICY title** (`icy-title` from stream metadata) — real-time artist/track embedded by radio streams (e.g., `"Green Day - When I Come Around"`)
2. **mpv media title** (`media_title`) — mpv's synthesized title from ytdl or stream metadata, used only if it differs from the station name
3. **Station genre** — static genre field from station config
4. **Station name** — final fallback

### URL resolution pipeline (in `AudioPlayer._resolve_url`)
1. **Local file paths** (starts with `/`) → pass through to mpv directly
2. **YouTube/ytdl domains** → pass through to mpv (mpv's ytdl hook handles extraction internally, avoiding expired signed URLs)
3. **Direct streams** (URL contains "ice", "stream", ".mp3", ".aac", ".ogg", ".m3u", ".pls") → pass through to mpv
4. **Other URLs** → try `yt-dlp --no-download --print urls -f bestaudio/best` with 15s timeout → use extracted URL if successful
5. **Fallback** → pass raw URL to mpv

### Important Textual 8.0 notes
- Do NOT use `Widget` as base class for widgets that `compose()` children — use `Container`. Textual 8.0 calls `render()` on non-container Widgets which returns `css_identifier_styled` instead of delegating to children, causing `AttributeError: 'str' object has no attribute 'render_strips'`.
- Do NOT set `self._current_mode` directly — it's Textual's internal attribute. Use `DEFAULT_MODE` class attribute for initial mode, and `self.current_mode` property to read current mode.
- Use `Binding("key", "action", "label", priority=True)` for global keybindings that must work regardless of focus.
- `ListView.clear()` is **async** — returns `AwaitRemove`. You MUST `await lv.clear()` before appending new items with the same IDs, otherwise you get `DuplicateIds` errors. Same applies to any widget removal followed by re-adding widgets with the same IDs.
- When dynamically building widget trees (e.g., a `Vertical` with `Input` children), pass children to the constructor — do NOT call `form.mount(child)` before the form itself is mounted. Use `await self.mount(form)` then access children.
- Textual messages bubble **up** the DOM tree only (child → parent → app). Sibling widgets do NOT receive each other's messages. To propagate to siblings, handle at the App level and explicitly call methods on siblings (e.g., `panel.on_library_changed(event)`).
- `post_message()` reuses the same Message object. After the first recipient processes it and it bubbles up, Textual may set `_stop_propagation`, silently blocking delivery to subsequent recipients. When broadcasting to multiple widgets, create a **fresh Message instance per widget**.
- `$text-muted` and `$text-disabled` are NOT valid Textual CSS color variables for border colors. Use hex colors instead (e.g., `#585b70`).
- CSS `height` includes borders. A widget with `border: round` and `height: 3` has only 1 row of content (border-top + content + border-bottom). For 2 lines of content with a border, use `height: 4`.
- Action methods can be `async def` — Textual will await them automatically.
- Bindings on a widget only fire when that widget (or a descendant) has focus. For keybindings that should work regardless of which pane has focus, define the binding on the **Screen** (e.g., `LibraryView`) with `priority=True`, then delegate to the target widget's method.
- Do NOT override `DirectoryTree`'s Enter key with a custom `Binding` on a parent container — it steals the keypress before the tree can expand/collapse folders. Instead, use `on_tree_node_selected` to react after the tree has handled the event.
- Textual `Input` widgets need `height: 3` minimum to be visible (border + content + border). At `height: 1` with `border: none`, the text content area can be squeezed to zero, making typed text invisible. Set an explicit `color` on Input widgets — they may inherit a muted color that blends with the background.

## Keybindings

### Global (both views)
| Key | Action |
|-----|--------|
| Tab | Toggle player/browser view |
| Space | Play/pause |
| s | Stop |
| +/= | Volume up |
| - | Volume down |
| F5 | Open library manager (suspends TUI, audio keeps playing) |
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

### Library manager keybindings
| Key | Action |
|-----|--------|
| Enter | Play selected file / expand-collapse folder |
| Up/Down | Navigate directory tree |
| e | Edit tags of highlighted file (enter edit mode) |
| Tab | Next field (in edit mode) |
| Enter | Save edits (in edit mode) |
| Escape | Cancel edit (in edit mode) |
| q | Quit library manager (returns to player if launched via F5) |

## Phase Roadmap
1. **Internet Radio** ✅ (Phase 1) — 8 default stations, streaming via mpv
2. **Station Management + YouTube** ✅ (Phase 1.5) — CRUD, folder tree, persistence, yt-dlp integration
3. **Local Library** 🚧 (Phase 3, in progress) — Standalone library manager with audio directory browsing, metadata display panel (mutagen), and inline tag editing. Next: next/prev track navigation, config editing.
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
- `AudioPlayer` is a singleton on LinampApp, accessed via `self.app.audio` from screens/widgets. LibraryApp does not have an AudioPlayer (it's a management tool, not a player).
- **mutagen** provides metadata read/write. `read_metadata()` normalizes tags across formats; `write_metadata()` writes back using format-native APIs (ID3 frames, MP4 atoms, Vorbis comments). Both are in `linamp/metadata.py`.
- Transport buttons use `Static` + `border: round` instead of `Button` to match the box-drawing aesthetic of the rest of the UI.
- yt-dlp must be kept up to date — YouTube frequently changes their streaming format. An outdated yt-dlp will fail with HTTP 403 errors. The version that ships with pip may be stale; run `pip install --upgrade yt-dlp` if YouTube playback breaks.
- When finding radio stream URLs: check the station's FAQ/audio help page, look for StreamGuys/Triton/SecureNet patterns, probe mount point variants (e.g., `/wext1`, `/wmht1`). HTTP 200 with `content-type: audio/*` confirms a working stream.
