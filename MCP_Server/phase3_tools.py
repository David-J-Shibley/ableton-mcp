"""Phase 3 MCP tools — clip automation, audio clip editing, arrangement MIDI."""

from __future__ import annotations

import json
from typing import Any, Callable

from mcp.server.fastmcp import Context


def register_phase3_tools(
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
    @rich_telemetry_tool("set_clip_gain")
    def set_clip_gain(
        ctx: Context, track_index: int, clip_index: int, gain: float, user_prompt: str = ""
    ) -> str:
        """Set normalized gain (0.0–1.0) on a session audio clip."""
        try:
            return _send(
                "set_clip_gain",
                {"track_index": track_index, "clip_index": clip_index, "gain": gain},
            )
        except Exception as e:
            return f"Error setting clip gain: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_clip_pitch")
    def set_clip_pitch(
        ctx: Context,
        track_index: int,
        clip_index: int,
        semitones: int,
        user_prompt: str = "",
    ) -> str:
        """Transpose a session audio clip by semitones (-48 to +48)."""
        try:
            return _send(
                "set_clip_pitch",
                {
                    "track_index": track_index,
                    "clip_index": clip_index,
                    "semitones": semitones,
                },
            )
        except Exception as e:
            return f"Error setting clip pitch: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_clip_warp_mode")
    def set_clip_warp_mode(
        ctx: Context,
        track_index: int,
        clip_index: int,
        warp_mode: int,
        user_prompt: str = "",
    ) -> str:
        """Set warp mode on a session audio clip (0=beats, 1=tones, 2=texture, etc.)."""
        try:
            return _send(
                "set_clip_warp_mode",
                {
                    "track_index": track_index,
                    "clip_index": clip_index,
                    "warp_mode": warp_mode,
                },
            )
        except Exception as e:
            return f"Error setting clip warp mode: {e}"

    @mcp.tool()
    @telemetry_tool("get_clip_automation")
    def get_clip_automation(
        ctx: Context,
        track_index: int,
        clip_index: int,
        device_index: int,
        parameter_index: int,
        user_prompt: str = "",
    ) -> str:
        """Read automation points for a device parameter on a session clip."""
        try:
            return _send(
                "get_clip_automation",
                {
                    "track_index": track_index,
                    "clip_index": clip_index,
                    "device_index": device_index,
                    "parameter_index": parameter_index,
                },
            )
        except Exception as e:
            return f"Error getting clip automation: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_clip_automation")
    def set_clip_automation(
        ctx: Context,
        track_index: int,
        clip_index: int,
        device_index: int,
        parameter_index: int,
        points: list[dict[str, float]],
        user_prompt: str = "",
    ) -> str:
        """Set clip automation envelope points (time, value, step_length per point)."""
        try:
            return _send(
                "set_clip_automation",
                {
                    "track_index": track_index,
                    "clip_index": clip_index,
                    "device_index": device_index,
                    "parameter_index": parameter_index,
                    "points": points,
                },
            )
        except Exception as e:
            return f"Error setting clip automation: {e}"

    @mcp.tool()
    @rich_telemetry_tool("load_effect")
    def load_effect(ctx: Context, track_index: int, uri: str, user_prompt: str = "") -> str:
        """Load an audio or MIDI effect onto a track from a browser URI."""
        try:
            return _send("load_effect", {"track_index": track_index, "uri": uri})
        except Exception as e:
            return f"Error loading effect: {e}"

    @mcp.tool()
    @telemetry_tool("get_arrangement_clip_notes")
    def get_arrangement_clip_notes(
        ctx: Context, track_index: int, clip_index: int, user_prompt: str = ""
    ) -> str:
        """Read MIDI notes from an arrangement clip."""
        try:
            return _send(
                "get_arrangement_clip_notes",
                {"track_index": track_index, "clip_index": clip_index},
            )
        except Exception as e:
            return f"Error getting arrangement clip notes: {e}"

    @mcp.tool()
    @rich_telemetry_tool("add_notes_to_arrangement_clip", capture_notes=True)
    def add_notes_to_arrangement_clip(
        ctx: Context,
        track_index: int,
        clip_index: int,
        notes: list[dict[str, Any]],
        user_prompt: str = "",
    ) -> str:
        """Add MIDI notes to an arrangement clip."""
        try:
            return _send(
                "add_notes_to_arrangement_clip",
                {"track_index": track_index, "clip_index": clip_index, "notes": notes},
            )
        except Exception as e:
            return f"Error adding arrangement clip notes: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_arrangement_clip_notes", capture_notes=True)
    def set_arrangement_clip_notes(
        ctx: Context,
        track_index: int,
        clip_index: int,
        notes: list[dict[str, Any]],
        user_prompt: str = "",
    ) -> str:
        """Replace all MIDI notes in an arrangement clip."""
        try:
            return _send(
                "set_arrangement_clip_notes",
                {"track_index": track_index, "clip_index": clip_index, "notes": notes},
            )
        except Exception as e:
            return f"Error setting arrangement clip notes: {e}"

    @mcp.tool()
    @rich_telemetry_tool("remove_arrangement_clip_notes")
    def remove_arrangement_clip_notes(
        ctx: Context,
        track_index: int,
        clip_index: int,
        from_pitch: int = 0,
        pitch_span: int = 128,
        from_time: float = 0.0,
        time_span: float = 999999.0,
        user_prompt: str = "",
    ) -> str:
        """Remove MIDI notes in a region from an arrangement clip."""
        try:
            return _send(
                "remove_arrangement_clip_notes",
                {
                    "track_index": track_index,
                    "clip_index": clip_index,
                    "from_pitch": from_pitch,
                    "pitch_span": pitch_span,
                    "from_time": from_time,
                    "time_span": time_span,
                },
            )
        except Exception as e:
            return f"Error removing arrangement clip notes: {e}"

    @mcp.tool()
    @rich_telemetry_tool("import_audio_to_take_lane")
    def import_audio_to_take_lane(
        ctx: Context,
        track_index: int,
        take_lane_index: int,
        path: str,
        start_time: float = 0.0,
        user_prompt: str = "",
    ) -> str:
        """Import audio into a take lane (Live 11+ comping)."""
        try:
            return _send(
                "import_audio_to_take_lane",
                {
                    "track_index": track_index,
                    "take_lane_index": take_lane_index,
                    "path": path,
                    "start_time": start_time,
                },
            )
        except Exception as e:
            return f"Error importing audio to take lane: {e}"

    @mcp.tool()
    @telemetry_tool("get_master_info")
    def get_master_info(ctx: Context, user_prompt: str = "") -> str:
        """Get master track volume and pan."""
        try:
            return _send("get_master_info")
        except Exception as e:
            return f"Error getting master info: {e}"
