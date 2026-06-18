"""Phase 4 MCP tools — racks, macros, device chains, presets, M4L introspection."""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

from mcp.server.fastmcp import Context


def register_phase4_tools(
    mcp,
    *,
    get_ableton_connection: Callable[[], Any],
    telemetry_tool: Callable,
    rich_telemetry_tool: Callable,
) -> None:
    def _send(command_type: str, params: dict | None = None) -> str:
        ableton = get_ableton_connection()
        result = ableton.send_command(command_type, params or {})
        return json.dumps(result, indent=2)

    @mcp.tool()
    @rich_telemetry_tool("insert_device")
    def insert_device(
        ctx: Context,
        track_index: int,
        device_name: str,
        position: int = -1,
        device_index: Optional[int] = None,
        chain_index: Optional[int] = None,
        user_prompt: str = "",
    ) -> str:
        """Insert a native Live device on a track or inside a rack chain (Live 12.3+).

        position: 0-based chain index, or -1 to append. When chain_index is set,
        device_index identifies the rack on the track.
        """
        try:
            params = {
                "track_index": track_index,
                "device_name": device_name,
                "position": position,
            }
            if device_index is not None:
                params["device_index"] = device_index
            if chain_index is not None:
                params["chain_index"] = chain_index
            return _send("insert_device", params)
        except Exception as e:
            return f"Error inserting device: {e}"

    @mcp.tool()
    @rich_telemetry_tool("delete_device")
    def delete_device(
        ctx: Context, track_index: int, device_index: int, user_prompt: str = ""
    ) -> str:
        """Delete a device from a track's device chain."""
        try:
            return _send("delete_device", {"track_index": track_index, "device_index": device_index})
        except Exception as e:
            return f"Error deleting device: {e}"

    @mcp.tool()
    @rich_telemetry_tool("load_preset_by_path")
    def load_preset_by_path(
        ctx: Context, track_index: int, path: str, user_prompt: str = ""
    ) -> str:
        """Load a .adg/.adv preset or rack from a filesystem path via the browser."""
        try:
            return _send("load_preset_by_path", {"track_index": track_index, "path": path})
        except Exception as e:
            return f"Error loading preset: {e}"

    @mcp.tool()
    @telemetry_tool("find_browser_by_path")
    def find_browser_by_path(
        ctx: Context, path: str, max_results: int = 10, user_prompt: str = ""
    ) -> str:
        """Search the Ableton browser for items matching a filesystem path or filename."""
        try:
            return _send("find_browser_by_path", {"path": path, "max_results": max_results})
        except Exception as e:
            return f"Error finding browser item: {e}"

    @mcp.tool()
    @telemetry_tool("get_device_info")
    def get_device_info(
        ctx: Context, track_index: int, device_index: int, user_prompt: str = ""
    ) -> str:
        """Get extended info for a device (type, rack flags, M4L/plugin detection)."""
        try:
            return _send("get_device_info", {"track_index": track_index, "device_index": device_index})
        except Exception as e:
            return f"Error getting device info: {e}"

    @mcp.tool()
    @telemetry_tool("get_device_tree")
    def get_device_tree(
        ctx: Context, track_index: int, device_index: int, user_prompt: str = ""
    ) -> str:
        """Get a recursive device tree for racks (chains and nested devices)."""
        try:
            return _send("get_device_tree", {"track_index": track_index, "device_index": device_index})
        except Exception as e:
            return f"Error getting device tree: {e}"

    @mcp.tool()
    @telemetry_tool("get_device_parameters_detailed")
    def get_device_parameters_detailed(
        ctx: Context,
        track_index: int,
        device_index: int = 0,
        rack_index: Optional[int] = None,
        chain_index: Optional[int] = None,
        chain_device_index: Optional[int] = None,
        user_prompt: str = "",
    ) -> str:
        """Get full parameter list with display values, original names, and M4L metadata.

        For devices inside a rack chain, pass rack_index, chain_index, and chain_device_index
        instead of device_index.
        """
        try:
            params: dict[str, Any] = {"track_index": track_index, "device_index": device_index}
            if rack_index is not None:
                params["rack_index"] = rack_index
            if chain_index is not None:
                params["chain_index"] = chain_index
            if chain_device_index is not None:
                params["chain_device_index"] = chain_device_index
            return _send("get_device_parameters_detailed", params)
        except Exception as e:
            return f"Error getting detailed parameters: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_device_parameter_by_name")
    def set_device_parameter_by_name(
        ctx: Context,
        track_index: int,
        device_index: int,
        parameter_name: str,
        value: float,
        user_prompt: str = "",
    ) -> str:
        """Set a device parameter by name (useful for M4L devices like Missing Reflections)."""
        try:
            return _send(
                "set_device_parameter_by_name",
                {
                    "track_index": track_index,
                    "device_index": device_index,
                    "parameter_name": parameter_name,
                    "value": value,
                },
            )
        except Exception as e:
            return f"Error setting parameter by name: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_chain_device_parameter")
    def set_chain_device_parameter(
        ctx: Context,
        track_index: int,
        rack_index: int,
        chain_index: int,
        chain_device_index: int,
        value: float,
        parameter_index: Optional[int] = None,
        parameter_name: Optional[str] = None,
        user_prompt: str = "",
    ) -> str:
        """Set a parameter on a device nested inside a rack chain."""
        try:
            params: dict[str, Any] = {
                "track_index": track_index,
                "rack_index": rack_index,
                "chain_index": chain_index,
                "chain_device_index": chain_device_index,
                "value": value,
            }
            if parameter_index is not None:
                params["parameter_index"] = parameter_index
            if parameter_name is not None:
                params["parameter_name"] = parameter_name
            return _send("set_chain_device_parameter", params)
        except Exception as e:
            return f"Error setting chain device parameter: {e}"

    @mcp.tool()
    @telemetry_tool("get_rack_info")
    def get_rack_info(
        ctx: Context, track_index: int, device_index: int, user_prompt: str = ""
    ) -> str:
        """Get rack metadata: chains, macro count, drum pads, variations."""
        try:
            return _send("get_rack_info", {"track_index": track_index, "device_index": device_index})
        except Exception as e:
            return f"Error getting rack info: {e}"

    @mcp.tool()
    @telemetry_tool("get_rack_macros")
    def get_rack_macros(
        ctx: Context, track_index: int, device_index: int, user_prompt: str = ""
    ) -> str:
        """Read rack macro values and labels."""
        try:
            return _send("get_rack_macros", {"track_index": track_index, "device_index": device_index})
        except Exception as e:
            return f"Error getting rack macros: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_rack_macro")
    def set_rack_macro(
        ctx: Context,
        track_index: int,
        device_index: int,
        macro_index: int,
        value: float,
        user_prompt: str = "",
    ) -> str:
        """Set a rack macro value (0-based macro_index; normalized 0.0–1.0)."""
        try:
            return _send(
                "set_rack_macro",
                {
                    "track_index": track_index,
                    "device_index": device_index,
                    "macro_index": macro_index,
                    "value": value,
                },
            )
        except Exception as e:
            return f"Error setting rack macro: {e}"

    @mcp.tool()
    @telemetry_tool("get_macro_mappings")
    def get_macro_mappings(
        ctx: Context, track_index: int, device_index: int, user_prompt: str = ""
    ) -> str:
        """Read macro mapping hints (LOM cannot create new mappings — load pre-mapped presets)."""
        try:
            return _send("get_macro_mappings", {"track_index": track_index, "device_index": device_index})
        except Exception as e:
            return f"Error getting macro mappings: {e}"

    @mcp.tool()
    @rich_telemetry_tool("add_rack_macro")
    def add_rack_macro(
        ctx: Context, track_index: int, device_index: int, user_prompt: str = ""
    ) -> str:
        """Add one visible macro to a rack (Live 11+, max 16)."""
        try:
            return _send("add_rack_macro", {"track_index": track_index, "device_index": device_index})
        except Exception as e:
            return f"Error adding rack macro: {e}"

    @mcp.tool()
    @rich_telemetry_tool("remove_rack_macro")
    def remove_rack_macro(
        ctx: Context, track_index: int, device_index: int, user_prompt: str = ""
    ) -> str:
        """Remove the last visible macro from a rack (Live 11+)."""
        try:
            return _send("remove_rack_macro", {"track_index": track_index, "device_index": device_index})
        except Exception as e:
            return f"Error removing rack macro: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_rack_visible_macros")
    def set_rack_visible_macros(
        ctx: Context, track_index: int, device_index: int, count: int, user_prompt: str = ""
    ) -> str:
        """Set visible macro count on a rack (1–16, Live 11+)."""
        try:
            return _send(
                "set_rack_visible_macros",
                {"track_index": track_index, "device_index": device_index, "count": count},
            )
        except Exception as e:
            return f"Error setting visible macros: {e}"

    @mcp.tool()
    @rich_telemetry_tool("randomize_rack_macros")
    def randomize_rack_macros(
        ctx: Context, track_index: int, device_index: int, user_prompt: str = ""
    ) -> str:
        """Randomize mapped rack macro values (Live 11+)."""
        try:
            return _send("randomize_rack_macros", {"track_index": track_index, "device_index": device_index})
        except Exception as e:
            return f"Error randomizing macros: {e}"

    @mcp.tool()
    @telemetry_tool("get_rack_variations")
    def get_rack_variations(
        ctx: Context, track_index: int, device_index: int, user_prompt: str = ""
    ) -> str:
        """Get rack macro variation count and selected index (Live 11+)."""
        try:
            return _send("get_rack_variations", {"track_index": track_index, "device_index": device_index})
        except Exception as e:
            return f"Error getting rack variations: {e}"

    @mcp.tool()
    @rich_telemetry_tool("store_rack_variation")
    def store_rack_variation(
        ctx: Context, track_index: int, device_index: int, user_prompt: str = ""
    ) -> str:
        """Store current rack macro values as a new variation (Live 11+)."""
        try:
            return _send("store_rack_variation", {"track_index": track_index, "device_index": device_index})
        except Exception as e:
            return f"Error storing rack variation: {e}"

    @mcp.tool()
    @rich_telemetry_tool("recall_rack_variation")
    def recall_rack_variation(
        ctx: Context,
        track_index: int,
        device_index: int,
        variation_index: int,
        user_prompt: str = "",
    ) -> str:
        """Recall a stored rack macro variation (Live 11+)."""
        try:
            return _send(
                "recall_rack_variation",
                {
                    "track_index": track_index,
                    "device_index": device_index,
                    "variation_index": variation_index,
                },
            )
        except Exception as e:
            return f"Error recalling rack variation: {e}"

    @mcp.tool()
    @rich_telemetry_tool("delete_rack_variation")
    def delete_rack_variation(
        ctx: Context,
        track_index: int,
        device_index: int,
        variation_index: int,
        user_prompt: str = "",
    ) -> str:
        """Delete a rack macro variation (Live 11+)."""
        try:
            return _send(
                "delete_rack_variation",
                {
                    "track_index": track_index,
                    "device_index": device_index,
                    "variation_index": variation_index,
                },
            )
        except Exception as e:
            return f"Error deleting rack variation: {e}"

    @mcp.tool()
    @rich_telemetry_tool("insert_rack_chain")
    def insert_rack_chain(
        ctx: Context,
        track_index: int,
        device_index: int,
        position: int = -1,
        user_prompt: str = "",
    ) -> str:
        """Insert a new chain into a rack (Live 12.3+)."""
        try:
            return _send(
                "insert_rack_chain",
                {"track_index": track_index, "device_index": device_index, "position": position},
            )
        except Exception as e:
            return f"Error inserting rack chain: {e}"

    @mcp.tool()
    @telemetry_tool("get_rack_chains")
    def get_rack_chains(
        ctx: Context, track_index: int, device_index: int, user_prompt: str = ""
    ) -> str:
        """List chains in a rack with volume, pan, mute, solo, and nested devices."""
        try:
            return _send("get_rack_chains", {"track_index": track_index, "device_index": device_index})
        except Exception as e:
            return f"Error getting rack chains: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_chain_name")
    def set_chain_name(
        ctx: Context,
        track_index: int,
        device_index: int,
        chain_index: int,
        name: str,
        user_prompt: str = "",
    ) -> str:
        """Rename a chain inside a rack."""
        try:
            return _send(
                "set_chain_name",
                {
                    "track_index": track_index,
                    "device_index": device_index,
                    "chain_index": chain_index,
                    "name": name,
                },
            )
        except Exception as e:
            return f"Error setting chain name: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_chain_volume")
    def set_chain_volume(
        ctx: Context,
        track_index: int,
        device_index: int,
        chain_index: int,
        volume: Optional[float] = None,
        pan: Optional[float] = None,
        mute: Optional[bool] = None,
        solo: Optional[bool] = None,
        user_prompt: str = "",
    ) -> str:
        """Set volume, pan, mute, or solo on a rack chain."""
        try:
            params: dict[str, Any] = {
                "track_index": track_index,
                "device_index": device_index,
                "chain_index": chain_index,
            }
            if volume is not None:
                params["volume"] = volume
            if pan is not None:
                params["pan"] = pan
            if mute is not None:
                params["mute"] = mute
            if solo is not None:
                params["solo"] = solo
            return _send("set_chain_volume", params)
        except Exception as e:
            return f"Error setting chain volume: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_drum_chain_note")
    def set_drum_chain_note(
        ctx: Context,
        track_index: int,
        device_index: int,
        chain_index: int,
        note: int,
        user_prompt: str = "",
    ) -> str:
        """Assign a MIDI note trigger to a Drum Rack chain (Live 12.3+, e.g. 36 = C1 kick)."""
        try:
            return _send(
                "set_drum_chain_note",
                {
                    "track_index": track_index,
                    "device_index": device_index,
                    "chain_index": chain_index,
                    "note": note,
                },
            )
        except Exception as e:
            return f"Error setting drum chain note: {e}"
