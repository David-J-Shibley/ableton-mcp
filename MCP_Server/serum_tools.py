"""Serum 2 MCP tools — curated 128-parameter control via Ableton."""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

from mcp.server.fastmcp import Context

from .serum_manifest import load_serum_manifest, serum_aliases


def register_serum_tools(
    mcp,
    *,
    get_ableton_connection: Callable[[], Any],
    telemetry_tool: Callable,
    rich_telemetry_tool: Callable,
) -> None:
    def _send(command_type: str, params: dict | None = None) -> dict:
        ableton = get_ableton_connection()
        return ableton.send_command(command_type, params or {})

    def _resolve_device_index(track_index: int, device_index: Optional[int]) -> int:
        if device_index is not None:
            return device_index
        result = _send("find_plugin_device", {
            "track_index": track_index,
            "name_contains": "Serum",
        })
        resolved = result.get("device_index")
        if resolved is None:
            raise ValueError(
                "No Serum device found on track {0}. Pass device_index or load Serum first.".format(
                    track_index))
        return int(resolved)

    def _index_params_by_name(detailed: dict) -> dict[str, dict]:
        indexed: dict[str, dict] = {}
        for param in detailed.get("parameters", []):
            for key in ("name", "original_name"):
                name = str(param.get(key, "") or "").strip()
                if name:
                    indexed[name.lower()] = param
        return indexed

    @mcp.tool()
    @telemetry_tool("list_serum_param_aliases")
    def list_serum_param_aliases(ctx: Context, user_prompt: str = "") -> str:
        """Return the curated 128 Serum 2 parameter aliases grouped by category."""
        try:
            manifest = load_serum_manifest()
            grouped: dict[str, list[dict]] = {}
            for entry in manifest["parameters"]:
                grouped.setdefault(entry["category"], []).append({
                    "alias": entry["alias"],
                    "serum_name": entry["serum_name"],
                    "description": entry.get("description", ""),
                })
            return json.dumps({
                "plugin": manifest["plugin"],
                "parameter_count": manifest["parameter_count"],
                "setup_note": manifest.get("setup_note"),
                "categories": grouped,
            }, indent=2)
        except Exception as e:
            return f"Error listing Serum aliases: {e}"

    @mcp.tool()
    @telemetry_tool("find_serum_device")
    def find_serum_device(
        ctx: Context, track_index: int, user_prompt: str = ""
    ) -> str:
        """Find Serum 2 on a track and return its device_index."""
        try:
            return json.dumps(
                _send("find_plugin_device", {"track_index": track_index, "name_contains": "Serum"}),
                indent=2,
            )
        except Exception as e:
            return f"Error finding Serum device: {e}"

    @mcp.tool()
    @rich_telemetry_tool("load_serum")
    def load_serum(ctx: Context, track_index: int, user_prompt: str = "") -> str:
        """Load Serum 2 onto a track from the Ableton browser."""
        try:
            search = _send("search_browser", {
                "query": "Serum 2",
                "category_type": "plugins",
                "max_results": 5,
                "loadable_only": True,
            })
            items = search.get("items", [])
            if not items:
                search = _send("search_browser", {
                    "query": "Serum",
                    "max_results": 10,
                    "loadable_only": True,
                })
                items = [
                    item for item in search.get("items", [])
                    if "serum" in str(item.get("name", "")).lower()
                ]
            if not items:
                raise ValueError("Serum 2 not found in browser")
            uri = items[0].get("uri")
            if not uri:
                raise ValueError("Serum browser item has no uri")
            result = _send("load_browser_item", {"track_index": track_index, "item_uri": uri})
            device = _send("find_plugin_device", {"track_index": track_index, "name_contains": "Serum"})
            result["device_index"] = device.get("device_index")
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error loading Serum: {e}"

    @mcp.tool()
    @telemetry_tool("get_serum_params")
    def get_serum_params(
        ctx: Context,
        track_index: int,
        device_index: Optional[int] = None,
        aliases: Optional[list[str]] = None,
        user_prompt: str = "",
    ) -> str:
        """Read curated Serum 2 parameters by alias (default: all 128)."""
        try:
            device_index = _resolve_device_index(track_index, device_index)
            detailed = _send("get_device_parameters_detailed", {
                "track_index": track_index,
                "device_index": device_index,
            })
            by_name = _index_params_by_name(detailed)
            wanted = aliases or list(serum_aliases().keys())
            values = []
            missing = []
            for alias in wanted:
                entry = serum_aliases().get(alias)
                if not entry:
                    missing.append({"alias": alias, "reason": "unknown alias"})
                    continue
                param = by_name.get(entry["serum_name"].lower())
                if not param:
                    missing.append({
                        "alias": alias,
                        "serum_name": entry["serum_name"],
                        "reason": "not exposed — add to Ableton Configure panel",
                    })
                    continue
                values.append({
                    "alias": alias,
                    "serum_name": entry["serum_name"],
                    "category": entry["category"],
                    "parameter_index": param.get("index"),
                    "value": param.get("value"),
                    "min": param.get("min"),
                    "max": param.get("max"),
                    "display_string": param.get("display_string"),
                })
            return json.dumps({
                "track_index": track_index,
                "device_index": device_index,
                "device_name": detailed.get("device_name"),
                "parameters": values,
                "missing": missing,
            }, indent=2)
        except Exception as e:
            return f"Error getting Serum params: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_serum_param")
    def set_serum_param(
        ctx: Context,
        track_index: int,
        alias: str,
        value: float,
        device_index: Optional[int] = None,
        user_prompt: str = "",
    ) -> str:
        """Set one curated Serum 2 parameter by alias (normalized 0.0–1.0)."""
        try:
            entry = serum_aliases().get(alias)
            if not entry:
                raise ValueError("Unknown Serum alias: " + alias)
            device_index = _resolve_device_index(track_index, device_index)
            result = _send("set_device_parameter_by_name", {
                "track_index": track_index,
                "device_index": device_index,
                "parameter_name": entry["serum_name"],
                "value": value,
            })
            result["alias"] = alias
            result["serum_name"] = entry["serum_name"]
            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error setting Serum param: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_serum_params")
    def set_serum_params(
        ctx: Context,
        track_index: int,
        params: dict[str, float],
        device_index: Optional[int] = None,
        user_prompt: str = "",
    ) -> str:
        """Batch-set curated Serum 2 parameters. Keys are aliases, values are 0.0–1.0."""
        try:
            device_index = _resolve_device_index(track_index, device_index)
            results = []
            errors = []
            for alias, value in params.items():
                entry = serum_aliases().get(alias)
                if not entry:
                    errors.append({"alias": alias, "error": "unknown alias"})
                    continue
                try:
                    result = _send("set_device_parameter_by_name", {
                        "track_index": track_index,
                        "device_index": device_index,
                        "parameter_name": entry["serum_name"],
                        "value": float(value),
                    })
                    results.append({
                        "alias": alias,
                        "serum_name": entry["serum_name"],
                        "value": result.get("value"),
                    })
                except Exception as exc:
                    errors.append({"alias": alias, "error": str(exc)})
            return json.dumps({
                "track_index": track_index,
                "device_index": device_index,
                "updated": results,
                "errors": errors,
            }, indent=2)
        except Exception as e:
            return f"Error setting Serum params: {e}"

    @mcp.tool()
    @telemetry_tool("list_serum_presets")
    def list_serum_presets(
        ctx: Context,
        track_index: int,
        device_index: Optional[int] = None,
        user_prompt: str = "",
    ) -> str:
        """List factory/user presets available on the Serum 2 plugin instance."""
        try:
            device_index = _resolve_device_index(track_index, device_index)
            return json.dumps(_send("get_plugin_presets", {
                "track_index": track_index,
                "device_index": device_index,
            }), indent=2)
        except Exception as e:
            return f"Error listing Serum presets: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_serum_preset")
    def set_serum_preset(
        ctx: Context,
        track_index: int,
        preset_index: Optional[int] = None,
        preset_name: Optional[str] = None,
        device_index: Optional[int] = None,
        user_prompt: str = "",
    ) -> str:
        """Switch Serum 2 preset by index or exact preset name."""
        try:
            device_index = _resolve_device_index(track_index, device_index)
            payload: dict[str, Any] = {
                "track_index": track_index,
                "device_index": device_index,
            }
            if preset_index is not None:
                payload["preset_index"] = preset_index
            if preset_name is not None:
                payload["preset_name"] = preset_name
            return json.dumps(_send("set_plugin_preset", payload), indent=2)
        except Exception as e:
            return f"Error setting Serum preset: {e}"
