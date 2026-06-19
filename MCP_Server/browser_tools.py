"""Browser search and preset loading tools."""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

from mcp.server.fastmcp import Context


def register_browser_tools(
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
    @rich_telemetry_tool("search_browser")
    def search_browser(
        ctx: Context,
        query: str,
        category_type: str = "all",
        max_results: int = 25,
        loadable_only: bool = False,
        user_prompt: str = "",
    ) -> str:
        """Search Ableton's browser by name or path substring.

        Searches user_library, packs, instruments, sounds, drums, audio_effects,
        midi_effects, max_for_live, plugins, samples, and current_project.

        category_type: filter to one root (e.g. "user_library", "audio_effects") or "all".
        Returns matching items with name, browser path, uri, is_loadable, is_device, and source.
        Use the uri with load_instrument_or_effect to load a result onto a track.
        """
        try:
            return _send(
                "search_browser",
                {
                    "query": query,
                    "category_type": category_type,
                    "max_results": max_results,
                    "loadable_only": loadable_only,
                },
            )
        except Exception as e:
            return f"Error searching browser: {e}"

    @mcp.tool()
    @telemetry_tool("find_browser_by_path")
    def find_browser_by_path(
        ctx: Context,
        path: str,
        max_results: int = 10,
        user_prompt: str = "",
    ) -> str:
        """Find browser items matching a filesystem path or filename.

        Matches by exact source path, filename, or browser path substring.
        Use before load_preset_by_path when you know the file location but need the browser uri.
        Returns name, path, uri, source, is_loadable, and is_device for each match.
        """
        try:
            return _send("find_browser_by_path", {"path": path, "max_results": max_results})
        except Exception as e:
            return f"Error finding browser item: {e}"

    @mcp.tool()
    @rich_telemetry_tool("load_preset_by_path")
    def load_preset_by_path(
        ctx: Context,
        track_index: int,
        path: str,
        user_prompt: str = "",
    ) -> str:
        """Load a .adg, .adv, or other browser preset onto a track from a filesystem path.

        The file must be indexed in Ableton's browser (User Library, Packs, etc.).
        Accepts absolute paths or paths with ~ (e.g. ~/Music/Ableton/User Library/Presets/MyRack.adg).
        Falls back to filename matching if the exact path is not found.
        """
        try:
            return _send("load_preset_by_path", {"track_index": track_index, "path": path})
        except Exception as e:
            return f"Error loading preset: {e}"
