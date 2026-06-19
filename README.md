# AbletonMCP

Connect [Ableton Live](https://www.ableton.com/) to AI assistants through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io). Control sessions, tracks, clips, devices, racks, and arrangement view from Claude, Cursor, or other MCP clients.

Extended fork of [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp) with additional tools for racks, presets, device chains, and arrangement editing. See `docs/FEATURE_GAP.md` for the full tool list and known limits.

[![smithery badge](https://smithery.ai/badge/@ahujasid/ableton-mcp)](https://smithery.ai/server/@ahujasid/ableton-mcp)

## Features

- **119 MCP tools** — session, tracks, mixer, clips, scenes, browser, arrangement, grooves, racks, macros, and **Serum 2** (128 curated params)
- **Two-way socket bridge** — MCP server ↔ Remote Script running inside Live
- **Browser integration** — search and load instruments, effects, and presets
- **Rack control** — macros, chains, variations (Live 11+), native device insertion (Live 12.3+)
- **Telemetry opt-out** — disable with `ABLETON_MCP_DISABLE_TELEMETRY=true`

## Quick start

### 1. Install the MCP server

```bash
git clone https://github.com/David-J-Shibley/ableton-mcp.git
cd ableton-mcp
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
python scripts/install_remote_script.py
```

### 2. Enable the Remote Script in Ableton

1. Open Ableton Live
2. **Preferences → Link, Tempo & MIDI**
3. Control Surface: **AbletonMCP**
4. Input / Output: **None**

After updating the Remote Script, re-run `python scripts/install_remote_script.py` and **restart Ableton**.

### 3. Configure your MCP client

Use the **local install** (not `uvx ableton-mcp` from PyPI — that is the upstream package without this fork's extra tools). Replace `/ABSOLUTE/PATH/TO/ableton-mcp` with your clone path.

**Only run one MCP instance at a time** — Cursor or Claude, not both.

#### Cursor

Add to `~/.cursor/mcp.json` inside `mcpServers`:

```json
"ableton": {
  "command": "/ABSOLUTE/PATH/TO/ableton-mcp/.venv/bin/ableton-mcp",
  "cwd": "/ABSOLUTE/PATH/TO/ableton-mcp",
  "env": {
    "ABLETON_MCP_DISABLE_TELEMETRY": "true",
    "DYLD_LIBRARY_PATH": "/opt/homebrew/opt/expat/lib"
  }
}
```

Reload MCP servers in Cursor settings after saving.

#### Claude Desktop

1. **Claude → Settings → Developer → Edit Config**
2. Edit `claude_desktop_config.json`:
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
3. Add (merge with any existing `mcpServers`):

```json
{
  "mcpServers": {
    "ableton": {
      "command": "/ABSOLUTE/PATH/TO/ableton-mcp/.venv/bin/ableton-mcp",
      "cwd": "/ABSOLUTE/PATH/TO/ableton-mcp",
      "env": {
        "ABLETON_MCP_DISABLE_TELEMETRY": "true",
        "DYLD_LIBRARY_PATH": "/opt/homebrew/opt/expat/lib"
      }
    }
  }
}
```

4. Quit Claude completely and reopen
5. Confirm the connector shows `ableton` as connected

**Verify:** Ask the assistant to run `get_session_info` (Ableton must be open with a set loaded).

**Logs:** `~/Library/Logs/Claude/` (macOS) or `%APPDATA%\Claude\logs\` (Windows)

#### Claude Code (CLI)

```bash
claude mcp add-json ableton '{
  "type": "stdio",
  "command": "/ABSOLUTE/PATH/TO/ableton-mcp/.venv/bin/ableton-mcp",
  "cwd": "/ABSOLUTE/PATH/TO/ableton-mcp",
  "env": {
    "ABLETON_MCP_DISABLE_TELEMETRY": "true",
    "DYLD_LIBRARY_PATH": "/opt/homebrew/opt/expat/lib"
  }
}' --scope global
```

Run `/mcp` in a session to confirm the server is connected.

On Apple Silicon Mac, keep `DYLD_LIBRARY_PATH` if Python fails to start. Omit on other platforms if not needed.

## Prerequisites

- Ableton Live 10 or newer (Live 12 recommended; some tools require Live 11+ or 12.3+)
- Python 3.10+

Multi-machine setup: `docs/SETUP_OTHER_MACHINE.md` · Serum 2: `docs/SERUM2_SETUP.md`

## Usage

1. Open Ableton with a set loaded and the AbletonMCP control surface enabled
2. Start your MCP client (Claude Desktop, Claude Code, or Cursor)
3. Ask the assistant to control Live — e.g. "Get session info", "Create a MIDI track", "Set tempo to 128"

### Example prompts

- "Get information about the current Ableton session"
- "Create a new MIDI track with Operator"
- "Add reverb to my drums"
- "Create a 4-bar MIDI clip with a simple melody"
- "Set the tempo to 120 BPM"
- "Load a drum rack on track 0"
- "Build an arrangement with intro, verse, and chorus locators"

[Demo video](https://youtu.be/iJWJqyVuPS8) · [Synthwave demo](https://youtu.be/VH9g66e42XA)

## Architecture

| Component | Role |
|-----------|------|
| `AbletonMCP_Remote_Script/` | MIDI Remote Script inside Live; receives JSON commands over TCP |
| `MCP_Server/` | MCP server that exposes tools and forwards commands to Live |

Commands are JSON objects with `type` and optional `params`. Responses include `status` and `result` or `message`.

Default socket port: **9877** (override with `ABLETON_PORT`).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Connection failed | Control Surface must be **AbletonMCP**; restart Live |
| Unknown command | Re-run `python scripts/install_remote_script.py` and restart Live |
| `insert_device` not supported | Stale Remote Script, or Live version below 12.3 |
| Timeout on audio import | Large files may take up to 60s; use Live 12+ |
| Works in one client only | Disable ableton in the other client's MCP config |

## Telemetry

Anonymous usage stats (tool names, error rates) are collected by default. No audio or project content is sent.

```bash
export ABLETON_MCP_DISABLE_TELEMETRY=true
```

Or add `"ABLETON_MCP_DISABLE_TELEMETRY": "true"` to the `env` block in your MCP config.

## Contributing

Contributions welcome — open a Pull Request on [GitHub](https://github.com/David-J-Shibley/ableton-mcp).

Upstream: [ahujasid/ableton-mcp](https://github.com/ahujasid/ableton-mcp) · Community: [Discord](https://discord.gg/3ZrMyGKnaU)

## Disclaimer

Third-party integration — not affiliated with Ableton.
