"""Phase 2 MCP tools — arrangement, recording, MIDI editing, browser search."""

from __future__ import annotations

import json
from typing import Any, Callable

from mcp.server.fastmcp import Context


def register_phase2_tools(
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

    # ── Tracks ────────────────────────────────────────────────────────────────

    @mcp.tool()
    @telemetry_tool("duplicate_track")
    def duplicate_track(ctx: Context, track_index: int, user_prompt: str = "") -> str:
        """Duplicate a track; copy is inserted immediately after the source."""
        try:
            return _send("duplicate_track", {"track_index": track_index})
        except Exception as e:
            return f"Error duplicating track: {e}"

    @mcp.tool()
    @telemetry_tool("get_track_routing")
    def get_track_routing(ctx: Context, track_index: int, user_prompt: str = "") -> str:
        """Get input/output routing for a track."""
        try:
            return _send("get_track_routing", {"track_index": track_index})
        except Exception as e:
            return f"Error getting track routing: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_track_input_routing")
    def set_track_input_routing(
        ctx: Context,
        track_index: int,
        routing_type_id: str,
        routing_channel_id: str,
        user_prompt: str = "",
    ) -> str:
        """Set track input routing by type/channel identifier or display name."""
        try:
            return _send(
                "set_track_input_routing",
                {
                    "track_index": track_index,
                    "routing_type_id": routing_type_id,
                    "routing_channel_id": routing_channel_id,
                },
            )
        except Exception as e:
            return f"Error setting input routing: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_track_output_routing")
    def set_track_output_routing(
        ctx: Context,
        track_index: int,
        routing_type_id: str,
        routing_channel_id: str,
        user_prompt: str = "",
    ) -> str:
        """Set track output routing by type/channel identifier or display name."""
        try:
            return _send(
                "set_track_output_routing",
                {
                    "track_index": track_index,
                    "routing_type_id": routing_type_id,
                    "routing_channel_id": routing_channel_id,
                },
            )
        except Exception as e:
            return f"Error setting output routing: {e}"

    # ── Clips ─────────────────────────────────────────────────────────────────

    @mcp.tool()
    @telemetry_tool("duplicate_clip")
    def duplicate_clip(
        ctx: Context, track_index: int, clip_index: int, user_prompt: str = ""
    ) -> str:
        """Duplicate a session clip to the next empty slot on the same track."""
        try:
            return _send(
                "duplicate_clip", {"track_index": track_index, "clip_index": clip_index}
            )
        except Exception as e:
            return f"Error duplicating clip: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_clip_color")
    def set_clip_color(
        ctx: Context, track_index: int, clip_index: int, color_index: int, user_prompt: str = ""
    ) -> str:
        """Set session clip color by Live color index (0–69)."""
        try:
            return _send(
                "set_clip_color",
                {
                    "track_index": track_index,
                    "clip_index": clip_index,
                    "color_index": color_index,
                },
            )
        except Exception as e:
            return f"Error setting clip color: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_clip_notes", capture_notes=True)
    def set_clip_notes(
        ctx: Context,
        track_index: int,
        clip_index: int,
        notes: list[dict[str, Any]],
        user_prompt: str = "",
    ) -> str:
        """Replace all MIDI notes in a session clip."""
        try:
            return _send(
                "set_clip_notes",
                {"track_index": track_index, "clip_index": clip_index, "notes": notes},
            )
        except Exception as e:
            return f"Error setting clip notes: {e}"

    @mcp.tool()
    @rich_telemetry_tool("remove_clip_notes")
    def remove_clip_notes(
        ctx: Context,
        track_index: int,
        clip_index: int,
        from_pitch: int = 0,
        pitch_span: int = 128,
        from_time: float = 0.0,
        time_span: float = 999999.0,
        user_prompt: str = "",
    ) -> str:
        """Remove MIDI notes in a pitch/time region from a session clip."""
        try:
            return _send(
                "remove_clip_notes",
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
            return f"Error removing clip notes: {e}"

    # ── Recording ─────────────────────────────────────────────────────────────

    @mcp.tool()
    @telemetry_tool("start_recording")
    def start_recording(ctx: Context, user_prompt: str = "") -> str:
        """Start arrangement recording (starts transport if needed)."""
        try:
            return _send("start_recording")
        except Exception as e:
            return f"Error starting recording: {e}"

    @mcp.tool()
    @telemetry_tool("stop_recording")
    def stop_recording(ctx: Context, user_prompt: str = "") -> str:
        """Stop arrangement recording."""
        try:
            return _send("stop_recording")
        except Exception as e:
            return f"Error stopping recording: {e}"

    @mcp.tool()
    @telemetry_tool("set_overdub")
    def set_overdub(ctx: Context, overdub: bool = True, user_prompt: str = "") -> str:
        """Enable or disable MIDI arrangement overdub."""
        try:
            return _send("set_overdub", {"overdub": overdub})
        except Exception as e:
            return f"Error setting overdub: {e}"

    @mcp.tool()
    @telemetry_tool("capture_midi")
    def capture_midi(
        ctx: Context, destination: str = "auto", user_prompt: str = ""
    ) -> str:
        """Capture recently played MIDI (destination: auto, session, or arrangement)."""
        try:
            return _send("capture_midi", {"destination": destination})
        except Exception as e:
            return f"Error capturing MIDI: {e}"

    # ── Arrangement ───────────────────────────────────────────────────────────

    @mcp.tool()
    @rich_telemetry_tool("create_arrangement_clip")
    def create_arrangement_clip(
        ctx: Context,
        track_index: int,
        start_time: float,
        length: float = 4.0,
        user_prompt: str = "",
    ) -> str:
        """Create an empty MIDI clip in the arrangement timeline."""
        try:
            return _send(
                "create_arrangement_clip",
                {"track_index": track_index, "start_time": start_time, "length": length},
            )
        except Exception as e:
            return f"Error creating arrangement clip: {e}"

    @mcp.tool()
    @rich_telemetry_tool("import_audio_to_arrangement")
    def import_audio_to_arrangement(
        ctx: Context,
        track_index: int,
        path: str,
        start_time: float = 0.0,
        user_prompt: str = "",
    ) -> str:
        """Import a WAV/audio file directly into arrangement view (great for Suno tracks)."""
        try:
            return _send(
                "import_audio_to_arrangement",
                {"track_index": track_index, "path": path, "start_time": start_time},
            )
        except Exception as e:
            return f"Error importing audio to arrangement: {e}"

    @mcp.tool()
    @rich_telemetry_tool("move_arrangement_clip")
    def move_arrangement_clip(
        ctx: Context,
        track_index: int,
        clip_index: int,
        new_start_time: float,
        new_track_index: int | None = None,
        user_prompt: str = "",
    ) -> str:
        """Move an arrangement clip to a new beat position and optional track."""
        try:
            params: dict[str, Any] = {
                "track_index": track_index,
                "clip_index": clip_index,
                "new_start_time": new_start_time,
            }
            if new_track_index is not None:
                params["new_track_index"] = new_track_index
            return _send("move_arrangement_clip", params)
        except Exception as e:
            return f"Error moving arrangement clip: {e}"

    @mcp.tool()
    @telemetry_tool("get_arrangement_length")
    def get_arrangement_length(ctx: Context, user_prompt: str = "") -> str:
        """Get total arrangement length in beats."""
        try:
            return _send("get_arrangement_length")
        except Exception as e:
            return f"Error getting arrangement length: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_arrangement_loop")
    def set_arrangement_loop(
        ctx: Context,
        start_time: float,
        end_time: float,
        enabled: bool = True,
        user_prompt: str = "",
    ) -> str:
        """Set arrangement loop region."""
        try:
            return _send(
                "set_arrangement_loop",
                {"start_time": start_time, "end_time": end_time, "enabled": enabled},
            )
        except Exception as e:
            return f"Error setting arrangement loop: {e}"

    @mcp.tool()
    @telemetry_tool("get_locators")
    def get_locators(ctx: Context, user_prompt: str = "") -> str:
        """List all arrangement locators (cue points)."""
        try:
            return _send("get_locators")
        except Exception as e:
            return f"Error getting locators: {e}"

    @mcp.tool()
    @rich_telemetry_tool("create_locator")
    def create_locator(
        ctx: Context, time: float, name: str = "", user_prompt: str = ""
    ) -> str:
        """Create a locator at a beat position."""
        try:
            params: dict[str, Any] = {"time": time}
            if name:
                params["name"] = name
            return _send("create_locator", params)
        except Exception as e:
            return f"Error creating locator: {e}"

    @mcp.tool()
    @telemetry_tool("delete_locator")
    def delete_locator(ctx: Context, locator_index: int, user_prompt: str = "") -> str:
        """Delete a locator by index."""
        try:
            return _send("delete_locator", {"locator_index": locator_index})
        except Exception as e:
            return f"Error deleting locator: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_locator_name")
    def set_locator_name(
        ctx: Context, locator_index: int, name: str, user_prompt: str = ""
    ) -> str:
        """Rename a locator."""
        try:
            return _send("set_locator_name", {"locator_index": locator_index, "name": name})
        except Exception as e:
            return f"Error setting locator name: {e}"

    @mcp.tool()
    @rich_telemetry_tool("jump_to_time")
    def jump_to_time(ctx: Context, time: float, user_prompt: str = "") -> str:
        """Jump arrangement playhead to a beat position."""
        try:
            return _send("jump_to_time", {"time": time})
        except Exception as e:
            return f"Error jumping to time: {e}"

    @mcp.tool()
    @telemetry_tool("get_take_lanes")
    def get_take_lanes(ctx: Context, track_index: int, user_prompt: str = "") -> str:
        """List take lanes on a track (Live 11+)."""
        try:
            return _send("get_take_lanes", {"track_index": track_index})
        except Exception as e:
            return f"Error getting take lanes: {e}"

    @mcp.tool()
    @rich_telemetry_tool("create_take_lane")
    def create_take_lane(
        ctx: Context, track_index: int, name: str = "", user_prompt: str = ""
    ) -> str:
        """Create a take lane on a track."""
        try:
            params: dict[str, Any] = {"track_index": track_index}
            if name:
                params["name"] = name
            return _send("create_take_lane", params)
        except Exception as e:
            return f"Error creating take lane: {e}"

    # ── Browser & groove ──────────────────────────────────────────────────────

    @mcp.tool()
    @telemetry_tool("get_groove_pool")
    def get_groove_pool(ctx: Context, user_prompt: str = "") -> str:
        """List grooves in the groove pool."""
        try:
            return _send("get_groove_pool")
        except Exception as e:
            return f"Error getting groove pool: {e}"

    @mcp.tool()
    @rich_telemetry_tool("apply_groove")
    def apply_groove(
        ctx: Context,
        track_index: int,
        clip_index: int,
        groove_index: int,
        user_prompt: str = "",
    ) -> str:
        """Apply a groove from the pool to a session clip."""
        try:
            return _send(
                "apply_groove",
                {
                    "track_index": track_index,
                    "clip_index": clip_index,
                    "groove_index": groove_index,
                },
            )
        except Exception as e:
            return f"Error applying groove: {e}"
