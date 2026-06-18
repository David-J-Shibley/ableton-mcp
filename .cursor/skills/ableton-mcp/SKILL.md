---
name: ableton-mcp
description: Control Ableton Live through AI for music production. Use when the user asks about Ableton, Live, DAW production, MIDI clips, arrangement, mixing in Live, importing Suno WAVs, or exporting masters for DistroKid. Part of the Suno → Ableton → SoundCloud → DistroKid pipeline.
---

# Ableton MCP

Fork of [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp) for David Shibley's music pipeline.

## Prerequisites

1. **Ableton Live** open with a set loaded
2. **Remote Script installed** — run `python scripts/install_remote_script.py`
3. **Control Surface** — Preferences → Link, Tempo & MIDI → `AbletonMCP` (Input/Output: None)
4. **MCP server running** — configured in `~/.cursor/mcp.json`

Only run **one** Ableton MCP instance (Cursor or Claude Desktop, not both).

## Pipeline role

```
Suno (generate WAV) → Ableton (arrange, mix, master) → SoundCloud → DistroKid
```

| Stage | MCP server | Typical action |
|-------|------------|----------------|
| Generate | suno-mcp | Download WAV to `~/.suno-mcp/downloads/` |
| Produce | **ableton-mcp** | Import WAV, arrange, mix, export master |
| Preview | soundcloud-mcp | Upload preview |
| Distribute | distrokid-mcp | Prefill album/single release |

Default export path for masters: `~/.distrokid-mcp/prepared-audio/`

## Available tools (73)

| Category | Tools |
|----------|-------|
| Session | `get_session_info`, `set_tempo`, `set_time_signature`, `get_playback_position`, `undo`, `redo`, `start_recording`, `stop_recording`, `set_overdub`, `capture_midi` |
| Tracks | `get_track_info`, `create_midi_track`, `create_audio_track`, `delete_track`, `duplicate_track`, `set_track_name`, `set_track_mute`, `set_track_solo`, `set_track_arm`, `get_track_routing`, `set_track_input_routing`, `set_track_output_routing` |
| Mixer | `set_track_volume`, `set_track_pan`, `set_send_level`, `set_master_volume`, `get_return_tracks` |
| Devices | `get_device_parameters`, `set_device_parameter` |
| Clips | `create_clip`, `create_audio_clip`, `add_notes_to_clip`, `get_clip_info`, `get_clip_notes`, `set_clip_notes`, `remove_clip_notes`, `delete_clip`, `duplicate_clip`, `set_clip_name`, `set_clip_color`, `set_clip_loop`, `fire_clip`, `stop_clip` |
| Scenes | `get_scenes`, `create_scene`, `fire_scene`, `stop_scene`, `set_scene_name` |
| Transport | `start_playback`, `stop_playback` |
| Browser | `get_browser_tree`, `get_browser_items_at_path`, `search_browser`, `load_instrument_or_effect`, `load_drum_kit` |
| Arrangement | `switch_to_arrangement_view`, `set_arrangement_time`, `jump_to_time`, `get_arrangement_clips`, `get_arrangement_length`, `set_arrangement_loop`, `duplicate_to_arrangement`, `create_arrangement_clip`, `import_audio_to_arrangement`, `move_arrangement_clip`, `get_locators`, `create_locator`, `delete_locator`, `set_locator_name`, `get_take_lanes`, `create_take_lane` |
| Groove | `get_groove_pool`, `apply_groove` |

See `docs/FEATURE_GAP.md` for Phase 3 roadmap.

## Common workflows

### Import a Suno track for mixing

1. Confirm WAV path (from suno-mcp download)
2. `create_midi_track` or use an existing audio track index
3. `create_audio_clip` with the WAV path, or `load_instrument_or_effect` for MIDI rework
4. `set_track_name` to match album track title
5. Mix with browser effects (`load_instrument_or_effect` on return/master as needed)

### Build an album session

1. `get_session_info` — inspect current set
2. For each track: `create_audio_clip` with numbered WAV from import dir
3. `set_clip_name` / `set_track_name` for album order
4. `switch_to_arrangement_view` + `duplicate_to_arrangement` for full-length layout

### Import a Suno album into arrangement view

1. `create_audio_track` for each song (or one track per stem)
2. `import_audio_to_arrangement(track_index, wav_path, start_time)` — place each track on the timeline
3. `create_locator` at section boundaries (intro, verse, drop, etc.)
4. `set_arrangement_loop` to loop a section while mixing with `set_device_parameter`

### Export for DistroKid

Audio export is still manual (File → Export in Live). Save masters to `ABLETON_EXPORT_DIR` for distrokid-mcp.

## Troubleshooting

- **Connection failed**: Remote Script not loaded — check Control Surface dropdown shows `AbletonMCP`
- **Timeout**: Break complex requests into smaller tool calls
- **Restart**: Quit and reopen Ableton + reload MCP server in Cursor
