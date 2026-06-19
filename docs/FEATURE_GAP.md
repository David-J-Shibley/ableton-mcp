# Ableton MCP — Feature Gap Analysis

**Indexing:** 0-based track/clip/scene/device/locator/macro/chain indices.

## Complete — v1.7.0 (119 tools)

| Phase | Highlights |
|-------|------------|
| Original + Phase 1 | Session, tracks, mixer, devices, scenes, clips, arrangement basics |
| Phase 2 | `duplicate_track`, routing, recording, arrangement import/locators, `search_browser`, grooves |
| Phase 3 | `set_clip_gain/pitch/warp_mode`, clip automation, `load_effect`, arrangement MIDI edit, take-lane import, `get_master_info` |
| Phase 4 | `insert_device`, `delete_device`, `load_preset_by_path`, rack chains/macros/variations, `get_device_parameters_detailed`, `set_device_parameter_by_name`, M4L introspection |
| Serum 2 | `list_serum_param_aliases`, `load_serum`, `get_serum_params`, `set_serum_param(s)`, `list_serum_presets`, `set_serum_preset` — curated 128 params; see `docs/SERUM2_SETUP.md` |

## Partially closed (Phase 4)

| Gap | Status |
|-----|--------|
| Load `.adg` / `.adv` presets | **Yes** — `load_preset_by_path`, `find_browser_by_path` (browser must index the file) |
| Device chain insert at index | **Yes** — `insert_device` (Live 12.3+), `delete_device` |
| Rack chains / drum kit building | **Yes** — `insert_rack_chain`, `get_rack_chains`, `set_drum_chain_note`, chain volume/mute |
| Macro value control | **Yes** — `get_rack_macros`, `set_rack_macro`, variations, randomize |
| Macro mapping assignment | **Read-only** — `get_macro_mappings`; LOM cannot create new mappings; load pre-mapped presets |
| M4L / custom device params | **Yes** — `get_device_parameters_detailed`, `set_device_parameter_by_name`, `get_device_tree` |
| Complex effect rack architecture | **Partial** — build via `insert_device` + chains; save `.adg` still manual in Live UI |
| Live 12 Clip Generators (Transform/Generate) | **No** — not exposed in Remote Script API |

## Not implemented

- **export_audio** — Live has no public render/export API via Remote Script. Export manually (File → Export) to `ABLETON_EXPORT_DIR`.
- **Programmatic macro mapping** — use pre-built `.adg`/`.adv` racks from User Library.
- **Clip Generators** — no LOM access.

## Upstream

Fork of [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp). Remote: `upstream`.
