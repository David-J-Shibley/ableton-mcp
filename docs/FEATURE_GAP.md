# Ableton MCP — Feature Gap Analysis

**Indexing:** 0-based track/clip/scene/device/locator indices.

## Complete — v1.5.0 (85 tools)

All planned MCP features except `export_audio` (no stable Live LOM API).

| Phase | Highlights |
|-------|------------|
| Original + Phase 1 | Session, tracks, mixer, devices, scenes, clips, arrangement basics |
| Phase 2 | `duplicate_track`, routing, recording, arrangement import/locators, `search_browser`, grooves |
| Phase 3 | `set_clip_gain/pitch/warp_mode`, clip automation, `load_effect`, arrangement MIDI edit, take-lane import, `get_master_info` |

## Not implemented

- **export_audio** — Live has no public render/export API via Remote Script. Export manually (File → Export) to `ABLETON_EXPORT_DIR`.

## Upstream

Fork of [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp). Remote: `upstream`.
