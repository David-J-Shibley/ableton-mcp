"""Extended MCP tools — Phase 1 feature additions."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from mcp.server.fastmcp import Context

logger = logging.getLogger("AbletonMCPServer")


def register_extended_tools(
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
    @telemetry_tool("create_audio_track")
    def create_audio_track(ctx: Context, index: int = -1, user_prompt: str = "") -> str:
        """Create a new audio track. Use for importing Suno WAVs."""
        try:
            result = json.loads(_send("create_audio_track", {"index": index}))
            return f"Created audio track {result.get('index')}: {result.get('name')}"
        except Exception as e:
            return f"Error creating audio track: {e}"

    @mcp.tool()
    @telemetry_tool("delete_track")
    def delete_track(ctx: Context, track_index: int, user_prompt: str = "") -> str:
        """Delete a track by index."""
        try:
            result = json.loads(_send("delete_track", {"track_index": track_index}))
            return f"Deleted track {result.get('deleted_index')}: {result.get('name')}"
        except Exception as e:
            return f"Error deleting track: {e}"

    @mcp.tool()
    @telemetry_tool("set_track_mute")
    def set_track_mute(
        ctx: Context, track_index: int, mute: bool = True, user_prompt: str = ""
    ) -> str:
        """Mute or unmute a track."""
        try:
            _send("set_track_mute", {"track_index": track_index, "mute": mute})
            return f"Track {track_index} mute={mute}"
        except Exception as e:
            return f"Error setting track mute: {e}"

    @mcp.tool()
    @telemetry_tool("set_track_solo")
    def set_track_solo(
        ctx: Context, track_index: int, solo: bool = True, user_prompt: str = ""
    ) -> str:
        """Solo or unsolo a track."""
        try:
            _send("set_track_solo", {"track_index": track_index, "solo": solo})
            return f"Track {track_index} solo={solo}"
        except Exception as e:
            return f"Error setting track solo: {e}"

    @mcp.tool()
    @telemetry_tool("set_track_arm")
    def set_track_arm(
        ctx: Context, track_index: int, arm: bool = True, user_prompt: str = ""
    ) -> str:
        """Arm or disarm a track for recording."""
        try:
            _send("set_track_arm", {"track_index": track_index, "arm": arm})
            return f"Track {track_index} arm={arm}"
        except Exception as e:
            return f"Error setting track arm: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_track_volume")
    def set_track_volume(
        ctx: Context, track_index: int, volume: float, user_prompt: str = ""
    ) -> str:
        """Set track volume (0.0–1.0, Live's normalized range)."""
        try:
            return _send("set_track_volume", {"track_index": track_index, "volume": volume})
        except Exception as e:
            return f"Error setting track volume: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_track_pan")
    def set_track_pan(
        ctx: Context, track_index: int, pan: float, user_prompt: str = ""
    ) -> str:
        """Set track pan (-1.0 left to 1.0 right)."""
        try:
            return _send("set_track_pan", {"track_index": track_index, "pan": pan})
        except Exception as e:
            return f"Error setting track pan: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_send_level")
    def set_send_level(
        ctx: Context,
        track_index: int,
        send_index: int,
        level: float,
        user_prompt: str = "",
    ) -> str:
        """Set a track send level (0.0–1.0). send_index 0 = first return."""
        try:
            return _send(
                "set_send_level",
                {"track_index": track_index, "send_index": send_index, "level": level},
            )
        except Exception as e:
            return f"Error setting send level: {e}"

    @mcp.tool()
    @telemetry_tool("get_return_tracks")
    def get_return_tracks(ctx: Context, user_prompt: str = "") -> str:
        """List return tracks with volume and pan."""
        try:
            return _send("get_return_tracks")
        except Exception as e:
            return f"Error getting return tracks: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_master_volume")
    def set_master_volume(ctx: Context, volume: float, user_prompt: str = "") -> str:
        """Set master track volume (0.0–1.0)."""
        try:
            return _send("set_master_volume", {"volume": volume})
        except Exception as e:
            return f"Error setting master volume: {e}"

    @mcp.tool()
    @telemetry_tool("get_device_parameters")
    def get_device_parameters(
        ctx: Context, track_index: int, device_index: int, user_prompt: str = ""
    ) -> str:
        """List all parameters for a device on a track (EQ, compressor, synth, etc.)."""
        try:
            return _send(
                "get_device_parameters",
                {"track_index": track_index, "device_index": device_index},
            )
        except Exception as e:
            return f"Error getting device parameters: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_device_parameter")
    def set_device_parameter(
        ctx: Context,
        track_index: int,
        device_index: int,
        parameter_index: int,
        value: float,
        user_prompt: str = "",
    ) -> str:
        """Set a device parameter value (use get_device_parameters for ranges)."""
        try:
            return _send(
                "set_device_parameter",
                {
                    "track_index": track_index,
                    "device_index": device_index,
                    "parameter_index": parameter_index,
                    "value": value,
                },
            )
        except Exception as e:
            return f"Error setting device parameter: {e}"

    @mcp.tool()
    @telemetry_tool("get_scenes")
    def get_scenes(ctx: Context, user_prompt: str = "") -> str:
        """List all scenes in the session."""
        try:
            return _send("get_scenes")
        except Exception as e:
            return f"Error getting scenes: {e}"

    @mcp.tool()
    @rich_telemetry_tool("create_scene")
    def create_scene(
        ctx: Context, index: int = -1, name: str = "", user_prompt: str = ""
    ) -> str:
        """Create a scene (-1 = append). Optionally set name."""
        try:
            params: dict[str, Any] = {"index": index}
            if name:
                params["name"] = name
            return _send("create_scene", params)
        except Exception as e:
            return f"Error creating scene: {e}"

    @mcp.tool()
    @telemetry_tool("fire_scene")
    def fire_scene(ctx: Context, scene_index: int, user_prompt: str = "") -> str:
        """Launch a scene (all clips in that row)."""
        try:
            return _send("fire_scene", {"scene_index": scene_index})
        except Exception as e:
            return f"Error firing scene: {e}"

    @mcp.tool()
    @telemetry_tool("stop_scene")
    def stop_scene(ctx: Context, scene_index: int, user_prompt: str = "") -> str:
        """Stop all clips in a scene row."""
        try:
            return _send("stop_scene", {"scene_index": scene_index})
        except Exception as e:
            return f"Error stopping scene: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_scene_name")
    def set_scene_name(
        ctx: Context, scene_index: int, name: str, user_prompt: str = ""
    ) -> str:
        """Rename a scene."""
        try:
            return _send("set_scene_name", {"scene_index": scene_index, "name": name})
        except Exception as e:
            return f"Error setting scene name: {e}"

    @mcp.tool()
    @telemetry_tool("get_clip_info")
    def get_clip_info(
        ctx: Context, track_index: int, clip_index: int, user_prompt: str = ""
    ) -> str:
        """Get metadata for a session clip."""
        try:
            return _send("get_clip_info", {"track_index": track_index, "clip_index": clip_index})
        except Exception as e:
            return f"Error getting clip info: {e}"

    @mcp.tool()
    @telemetry_tool("get_clip_notes")
    def get_clip_notes(
        ctx: Context, track_index: int, clip_index: int, user_prompt: str = ""
    ) -> str:
        """Read all MIDI notes from a session clip."""
        try:
            return _send("get_clip_notes", {"track_index": track_index, "clip_index": clip_index})
        except Exception as e:
            return f"Error getting clip notes: {e}"

    @mcp.tool()
    @telemetry_tool("delete_clip")
    def delete_clip(
        ctx: Context, track_index: int, clip_index: int, user_prompt: str = ""
    ) -> str:
        """Delete a clip from a session clip slot."""
        try:
            return _send("delete_clip", {"track_index": track_index, "clip_index": clip_index})
        except Exception as e:
            return f"Error deleting clip: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_clip_loop")
    def set_clip_loop(
        ctx: Context,
        track_index: int,
        clip_index: int,
        loop_start: float,
        loop_end: float,
        looping: bool = True,
        user_prompt: str = "",
    ) -> str:
        """Set loop region and looping state on a session clip."""
        try:
            return _send(
                "set_clip_loop",
                {
                    "track_index": track_index,
                    "clip_index": clip_index,
                    "loop_start": loop_start,
                    "loop_end": loop_end,
                    "looping": looping,
                },
            )
        except Exception as e:
            return f"Error setting clip loop: {e}"

    @mcp.tool()
    @rich_telemetry_tool("set_time_signature")
    def set_time_signature(
        ctx: Context, numerator: int, denominator: int, user_prompt: str = ""
    ) -> str:
        """Set song time signature (denominator: 1, 2, 4, 8, 16, or 32)."""
        try:
            return _send(
                "set_time_signature", {"numerator": numerator, "denominator": denominator}
            )
        except Exception as e:
            return f"Error setting time signature: {e}"

    @mcp.tool()
    @telemetry_tool("get_playback_position")
    def get_playback_position(ctx: Context, user_prompt: str = "") -> str:
        """Get current playhead position in beats, bars, and seconds."""
        try:
            return _send("get_playback_position")
        except Exception as e:
            return f"Error getting playback position: {e}"

    @mcp.tool()
    @telemetry_tool("undo")
    def undo(ctx: Context, user_prompt: str = "") -> str:
        """Undo the last song-level change."""
        try:
            return _send("undo")
        except Exception as e:
            return f"Error undoing: {e}"

    @mcp.tool()
    @telemetry_tool("redo")
    def redo(ctx: Context, user_prompt: str = "") -> str:
        """Redo the last undone change."""
        try:
            return _send("redo")
        except Exception as e:
            return f"Error redoing: {e}"
