# Serum 2 MCP Setup

Serum 2 exposes **2,600+** VST parameters, but Ableton's plugin **Configure** panel supports **128**. This fork ships a curated list in `docs/serum2_params_128.json` mapped to friendly **aliases** (`filter1_freq`, `env1_attack`, `a_position`, etc.).

## One-time setup

1. Load Serum 2 on a MIDI track (or use the `load_serum` MCP tool).
2. In Ableton's device view, click the wrench icon (**Configure**) on the Serum title bar.
3. In Serum, right-click each control you need → **Configure** (or use Ableton's parameter list) until you've added the parameters listed in `serum2_params_128.json`.
   - Fast path: search the Configure list for names like `Filter 1 Freq`, `A Position`, `Env 1 Attack`.
   - The manifest `serum_name` field must match Serum's parameter label exactly.
4. Save as a default track preset or document your configured track for reuse.

## FX parameters (Serum 2)

Effect slot parameters are **dynamic**. After adding an effect in Serum:

1. Right-click the control → **Automate** (per [Xfer guidance](https://xferrecords.com/forums/general/serum-2-automation-on-live-12-1)).
2. Reload the plugin instance if the parameter does not appear in Live.
3. Map `FX Main Param 1`–`8` and `FX Bus 1 Param 1`–`4` in the manifest to whatever you configured.

## MCP tools

| Tool | Purpose |
|------|---------|
| `list_serum_param_aliases` | Show all 128 aliases |
| `find_serum_device` | Get `device_index` for Serum on a track |
| `load_serum` | Load Serum 2 from the browser |
| `get_serum_params` | Read curated params (reports missing Configure entries) |
| `set_serum_param` | Set one param by alias |
| `set_serum_params` | Batch set by alias dict |
| `list_serum_presets` | List plugin preset menu |
| `set_serum_preset` | Switch preset by index or name |

## Example

```
load_serum(track_index=0)
set_serum_params(track_index=0, params={
  "filter1_freq": 0.35,
  "filter1_res": 0.55,
  "a_position": 0.5,
  "env1_attack": 0.1,
  "env1_release": 0.4
})
set_serum_preset(track_index=0, preset_name="Bass - Go")
```

## Parameter source

Names verified against the [Serum 2 VST3 parameter dump](https://gist.github.com/0xdevalias/1b85af59724b79c6484f660ab6982744).
