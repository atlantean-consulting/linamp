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
   - **Browser View** — Mode-aware MC-style dual pane: in Radio mode shows StationList (left) + PlaylistPanel (right); in Local mode shows FileBrowser (left) + PlaylistPanel (right). Both panes are always mounted; visibility toggled via `display` on F1/F2. + now-playing bar + context-sensitive command hints (bottom)
2. **LibraryApp** (`linamp/library.py`) — Standalone local music library manager. MC-style dual pane: directory tree filtered to audio files (left) + metadata panel (right, shows tags via mutagen with inline editing). Launched via `python -m linamp.library`, `python -m linamp --library`, or F5 from within LinampApp (suspends TUI, audio keeps playing).

### Key modules
- `linamp/app.py` — Main Textual App (player + radio browser). Owns `AudioPlayer` singleton (`self.audio`), `self.config` (`AppConfig`), and `self.library` (list of `Folder`). Manages modes via `MODES` dict + `DEFAULT_MODE`. Polls player state every 500ms via `set_interval`, broadcasting `PlayerStateUpdate` to each widget individually via `screen.walk_children()` (creating a fresh message per widget to avoid Textual's stop-propagation). Two playlist modes: `playlist_mode` ("radio" or "local"), switched via F1/F2. `active_playlist` property returns `flat_stations` (radio) or `local_queue` (local). `local_queue` accumulates local files during session. Any `StationSelected` with URL starting with `/` auto-appends to `local_queue`. F5 launches library manager subprocess; on return, reads `~/.config/linamp/queue.json` (written by LibraryApp), imports tracks to `local_queue`, switches to local mode, starts playback. `_broadcast_mode_change()` updates all PlaylistPanels and PlaylistModeIndicator widgets. Auto-advance: the poll loop detects natural track end (`idle_active` True while not user-stopped) and calls `_play_next_track()` to advance through the active playlist; stops cleanly at end of playlist. `check_action()` suppresses global bindings (`stop`, `volume_up`, `volume_down`, `toggle_pause`) when the current screen has `_edit_mode=True`, so those keys fall through to the screen's `on_key()` handler instead (see Textual binding-vs-event ordering note).
- `linamp/library.py` — Standalone library manager Textual App. Loads `AppConfig` for `music_root`. Single mode: `LibraryView`. Entry point: `main()`. Shares config, widgets, and CSS theme with LinampApp. Handles `StationSelected` by writing selected files to `~/.config/linamp/queue.json` for LinampApp to import on resume (IPC via queue file).
- `linamp/config.py` — `AppConfig` dataclass (`music_root` field, default `~/Music`) + `load_config()`/`save_config()`. Persisted at `~/.config/linamp/config.json`. Also exports `QUEUE_PATH` (`~/.config/linamp/queue.json`) for library→player IPC.
- `linamp/player.py` — mpv wrapper. Critical flags: `video=False, terminal=False, input_terminal=False, ytdl_format="bestaudio/best"`. Properties: `icy_title` (ICY stream metadata), `media_title` (mpv's synthesized title incorporating stream metadata), `metadata` (raw dict), `idle_active` (True when mpv has no file loaded — used by app's auto-advance to detect natural track end). URL resolution pipeline: local file paths (starting with `/`) pass through directly; YouTube URLs pass to mpv's ytdl hook; direct stream URLs skip resolution; other URLs try yt-dlp extraction. `_is_ytdl_url()` classmethod identifies YouTube domains. `YTDL_DOMAINS` tuple lists recognized domains.
- `linamp/stations.py` — `Station` dataclass (name, url, genre) + `Folder` dataclass (name, stations). `load_library()` reads `~/.config/linamp/stations.json` with auto-migration from old flat format. `save_library()` writes folder structure. `all_stations()` helper flattens folders. `_migrate_flat_list()` auto-categorizes stations into Radio/YouTube folders based on URL. Legacy `load_stations()`/`save_stations()`/`STATIONS` aliases kept for backwards compat.
- `linamp/metadata.py` — Audio metadata read/write via mutagen. `read_metadata(filepath)` returns normalized dict (title, artist, album, track, year, genre, duration, bitrate, sample_rate, format, file_size) across MP3/ID3, MP4, FLAC, OGG. `write_metadata(filepath, tags)` writes a subset of tags back using format-appropriate methods (ID3 frames for MP3, iTunes atoms for MP4, Vorbis comments for FLAC/OGG). Both handle format detection internally. `read_metadata` never raises; `write_metadata` raises on failure.
- `linamp/messages.py` — `PlayerStateUpdate` (broadcast by poll timer, carries `icy_title`, `media_title`, and other state), `StationSelected` (from UI interaction), `FileHighlighted` (from FileBrowser cursor movement, carries `Path | None`), `PlaylistModeChanged` (carries `mode` and `stations` list when switching Radio/Local), `LibraryChanged` (from station management CRUD, carries `list[Folder]`).
- `linamp/screens/player_view.py` — PlayerView screen. Passes `self.app.active_playlist` to PlaylistPanel. `on_screen_resume()` refreshes PlaylistPanel and PlaylistModeIndicator when Tab-returning from BrowserView.
- `linamp/screens/browser_view.py` — Mode-aware BrowserView screen. Mounts both StationList and FileBrowser in left pane; toggles visibility via `display` based on playlist mode. `_sync_mode()` helper keeps pane visibility, hints, and focus in sync. `on_screen_resume()` refreshes playlist and pane state when Tab-returning. In local mode, `on_station_selected()` intercepts file selections to queue-only (no play, stops event propagation). `p` binding starts playback from queue beginning and switches to player view. `CommandHints` shows context-sensitive hints (radio CRUD vs local queue vs edit mode). **Playlist edit mode** (`_edit_mode`): `e` enters edit mode (focuses right-pane ListView), `on_key()` intercepts ↑↓ select, ←→ reorder (`move_track`), d delete, w save M3U, P play-from-selected, p play-from-beginning, x/Esc exit. **Save M3U** (`_save_mode`): `SaveInput` widget for playlist name, writes `#EXTM3U` format to `~/Music/PLAYLISTS/<name>.m3u`. Edits sync back to `app.local_queue` via `_sync_queue_from_panel()`.
- `linamp/screens/library_view.py` — LibraryView screen for the standalone library manager. Dual-pane: `FileBrowser` (left) + `MetadataPanel` (right) + `NowPlayingBar` + `LibraryCommandHints`. Handles `FileHighlighted` messages to update metadata panel on cursor movement. Owns the `e` binding for tag editing (at screen level with `priority=True` so it fires regardless of focus pane), delegating to `MetadataPanel.action_edit()`.
- `linamp/widgets/station_list.py` — Left pane browser. Uses Textual `Tree` widget (not ListView) with folder nodes (📁) and station leaves (📻 for radio, 🎵 for YouTube). Full CRUD: add/delete/rename/edit stations and folders, move stations within folders. Inline `Input` widgets for editing. YouTube URL auto-detection: fetches title via yt-dlp in background thread (`asyncio.to_thread`), auto-fills name and genre. Add flow is URL-first to enable auto-detection. Delete requires double-press confirmation.
- `linamp/widgets/playlist_panel.py` — Right pane flat play queue. Shows stations from the active playlist (radio or local). Highlights active station with ▶ icon. `set_stations(list)` swaps the playlist dynamically (used by mode switching). Handles `LibraryChanged` to rebuild list (must `await lv.clear()` before appending — see Textual notes). Track manipulation for edit mode: `selected_index` property, `stations` property (returns copy), `move_track(direction)` swaps and rebuilds, `delete_track()` removes and rebuilds. `_rebuild_list(select_index)` shared helper.
- `linamp/widgets/playlist_mode_indicator.py` — 1-line `Static` widget between visualizer and playlist in player view. Shows `📻 Radio` or `💾 Local (N tracks)`. Handles `PlaylistModeChanged` to update display.
- `linamp/widgets/now_playing_bar.py` — Shared `NowPlayingBar` widget (compact 1-line status bar with metadata priority). Used by both BrowserView and LibraryView.
- `linamp/widgets/file_browser.py` — `AudioDirectoryTree` (Textual `DirectoryTree` subclass filtered to audio extensions: .mp3, .flac, .m4a, .ogg, .opus, .wav, .aac, .wma) + `FileBrowser` container wrapper. Posts `FileHighlighted` on cursor movement (for metadata panel), and `StationSelected` on Enter (for playback/queueing). Uses `on_tree_node_highlighted` for cursor movement and `on_directory_tree_file_selected` for Enter on files — do NOT use `on_tree_node_selected` (it doesn't reliably fire for DirectoryTree file nodes; use `DirectoryTree.FileSelected` instead).
- `linamp/widgets/metadata_panel.py` — Right-pane metadata display with inline tag editing. Displays 11 fields read from mutagen (title, artist, album, track, year, genre, duration, bitrate, sample_rate, format, file_size). Edit mode (`e` key, handled at screen level): replaces editable fields (title, artist, album, track, year, genre) with `Input` widgets, Tab between fields, Enter saves via `write_metadata()`, Escape cancels. Uses `MODE_BROWSE`/`MODE_EDIT` state machine. Metadata loading is async (`asyncio.to_thread`) to avoid blocking UI.
- `linamp/widgets/track_info.py` — Standalone now-playing widget (not currently wired into any view). Shows "NOW PLAYING" label + track title with metadata priority: ICY title > media title > station name.
- `linamp/widgets/transport.py` — Transport controls using `Static` widgets with `border: round` (not Textual `Button` which has pseudo-3D styling that clashes with box-drawing UI).
- `linamp/widgets/` — All widgets extend `Container` (not `Widget`) because Textual 8.0 requires container semantics for widgets that compose children.

### Data persistence
- **Config**: `~/.config/linamp/config.json` — `{"music_root": "~/Music"}`. Loaded by both apps.
- **Queue**: `~/.config/linamp/queue.json` — Transient IPC file. LibraryApp writes selected files here; LinampApp reads and deletes on resume from F5. Format: `[{"name": "...", "url": "/path/to/file", "genre": ""}]`.
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
- Do NOT override `DirectoryTree`'s Enter key with a custom `Binding` on a parent container — it steals the keypress before the tree can expand/collapse folders. For reacting to file selection, use `on_directory_tree_file_selected` (catches `DirectoryTree.FileSelected`) — NOT `on_tree_node_selected` (which catches `Tree.NodeSelected` and doesn't reliably fire for DirectoryTree file leaf nodes).
- Textual `Input` widgets need `height: 3` minimum to be visible (border + content + border). At `height: 1` with `border: none`, the text content area can be squeezed to zero, making typed text invisible. Set an explicit `color` on Input widgets — they may inherit a muted color that blends with the background.
- Textual's mode system caches Screen instances — `compose()` runs only once. When switching modes (e.g., Tab toggle), the screen resumes but does NOT recompose. Use `on_screen_resume()` to refresh stale state (playlist contents, pane visibility, indicators) when a screen becomes active again. The `ScreenResume` event fires automatically on mode switch.
- `_broadcast_mode_change()` broadcasts `PlaylistModeChanged` to child widgets via `screen.walk_children()`, but the **Screen itself** is not a child — it must be notified explicitly (e.g., `getattr(self.screen, "on_playlist_mode_changed", None)`).
- **Binding-vs-event ordering**: Textual processes priority `Binding`s (focused widget → parent → Screen → App) BEFORE dispatching key events (`on_key`). If an App-level `Binding("s", "stop", priority=True)` exists, a Screen's `on_key()` will never see `s`. To suppress App bindings conditionally, override `App.check_action()` and return `False` for actions that should be disabled (e.g., when a screen is in edit mode). This lets the key fall through to `on_key()`.

## Keybindings

### Global (both views)
| Key | Action |
|-----|--------|
| Tab | Toggle player/browser view |
| Space | Play/pause |
| s | Stop |
| +/= | Volume up |
| - | Volume down |
| F1 | Switch to Radio playlist mode |
| F2 | Switch to Local playlist mode |
| F5 | Open library manager (suspends TUI, audio keeps playing) |
| q | Quit |

### Browser view — Radio mode (left pane focused)
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

### Browser view — Local mode (left pane focused)
| Key | Action |
|-----|--------|
| Enter | Add file to queue (without playing) / expand-collapse folder |
| Up/Down | Navigate directory tree |
| e | Enter playlist edit mode (right pane) |
| p | Play queue from beginning and switch to player view |

### Browser view — Local edit mode (right pane focused)
| Key | Action |
|-----|--------|
| Up/Down | Select track in playlist |
| Left | Move selected track up |
| Right | Move selected track down |
| d | Delete selected track |
| w | Save playlist as M3U (to ~/Music/PLAYLISTS/) |
| P | Play from selected track and switch to player view |
| p | Play from beginning and switch to player view |
| x / Escape | Exit edit mode (return to file browser) |

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
3. **Local Library** 🚧 (Phase 3, in progress) — Standalone library manager with audio directory browsing, metadata display panel (mutagen), inline tag editing, and dual playlist modes (Radio/Local with F1/F2). Next: append-without-play in library browser, config editing.
4. **Cross-Platform** — macOS + Windows support. Key areas: platform-appropriate config dirs (`~/.config` → `~/Library/Application Support/` / `%APPDATA%`), Windows path handling (local file detection uses `/` prefix), mpv installation instructions per platform.

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
