# Setup on Another Machine

## Prerequisites

- Ableton Live 10+ (12 recommended for audio clip import)
- Python 3.10+
- Cursor or another MCP client

## Install

```bash
git clone https://github.com/David-J-Shibley/ableton-mcp.git
cd ableton-mcp
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
python scripts/install_remote_script.py
```

## Ableton

1. Open Ableton Live
2. **Preferences → Link, Tempo & MIDI**
3. Control Surface: **AbletonMCP** (Input/Output: **None**)
4. Restart Ableton if you updated the Remote Script

## Cursor MCP config

Add to `~/.cursor/mcp.json`:

```json
"ableton": {
  "command": "/ABSOLUTE/PATH/TO/ableton-mcp/.venv/bin/ableton-mcp",
  "cwd": "/ABSOLUTE/PATH/TO/ableton-mcp",
  "env": {
    "ABLETON_MCP_DISABLE_TELEMETRY": "true"
  }
}
```

On Apple Silicon Mac with Homebrew Python 3.14, you may also need:

```json
"DYLD_LIBRARY_PATH": "/opt/homebrew/opt/expat/lib"
```

## Verify

1. Open Ableton with any set loaded
2. Reload MCP servers in Cursor
3. Ask: "get session info" or "get playback position"

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Connection failed | Control Surface must show AbletonMCP; restart Live |
| Unknown command | Re-run `python scripts/install_remote_script.py` and restart Live |
| Timeout on audio import | Large WAVs need Live 12.0.5+; wait up to 60s |
