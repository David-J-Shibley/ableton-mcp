# AbletonMCP/init.py
from __future__ import absolute_import, print_function, unicode_literals

from _Framework.ControlSurface import ControlSurface
import os
import socket
import json
import threading
import time
import traceback

# Change queue import for Python 2
try:
    import Queue as queue  # Python 2
except ImportError:
    import queue  # Python 3

# Constants for socket communication
DEFAULT_PORT = 9877
HOST = "0.0.0.0"

def create_instance(c_instance):
    """Create and return the AbletonMCP script instance"""
    return AbletonMCP(c_instance)

class AbletonMCP(ControlSurface):
    """AbletonMCP Remote Script for Ableton Live"""
    
    def __init__(self, c_instance):
        """Initialize the control surface"""
        ControlSurface.__init__(self, c_instance)
        self.log_message("AbletonMCP Remote Script initializing...")
        
        # Socket server for communication
        self.server = None
        self.client_threads = []
        self.server_thread = None
        self.running = False
        
        # Cache the song reference for easier access
        self._song = self.song()
        
        # Start the socket server
        self.start_server()
        
        self.log_message("AbletonMCP initialized")
        
        # Show a message in Ableton
        self.show_message("AbletonMCP: Listening for commands on port " + str(DEFAULT_PORT))
    
    def disconnect(self):
        """Called when Ableton closes or the control surface is removed"""
        self.log_message("AbletonMCP disconnecting...")
        self.running = False
        
        # Stop the server
        if self.server:
            try:
                self.server.close()
            except:
                pass
        
        # Wait for the server thread to exit
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(1.0)
            
        # Clean up any client threads
        for client_thread in self.client_threads[:]:
            if client_thread.is_alive():
                # We don't join them as they might be stuck
                self.log_message("Client thread still alive during disconnect")
        
        ControlSurface.disconnect(self)
        self.log_message("AbletonMCP disconnected")
    
    def start_server(self):
        """Start the socket server in a separate thread"""
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((HOST, DEFAULT_PORT))
            self.server.listen(5)  # Allow up to 5 pending connections
            
            self.running = True
            self.server_thread = threading.Thread(target=self._server_thread)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            self.log_message("Server started on port " + str(DEFAULT_PORT))
        except Exception as e:
            self.log_message("Error starting server: " + str(e))
            self.show_message("AbletonMCP: Error starting server - " + str(e))
    
    def _server_thread(self):
        """Server thread implementation - handles client connections"""
        try:
            self.log_message("Server thread started")
            # Set a timeout to allow regular checking of running flag
            self.server.settimeout(1.0)
            
            while self.running:
                try:
                    # Accept connections with timeout
                    client, address = self.server.accept()
                    self.log_message("Connection accepted from " + str(address))
                    self.show_message("AbletonMCP: Client connected")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                    # Keep track of client threads
                    self.client_threads.append(client_thread)
                    
                    # Clean up finished client threads
                    self.client_threads = [t for t in self.client_threads if t.is_alive()]
                    
                except socket.timeout:
                    # No connection yet, just continue
                    continue
                except Exception as e:
                    if self.running:  # Only log if still running
                        self.log_message("Server accept error: " + str(e))
                    time.sleep(0.5)
            
            self.log_message("Server thread stopped")
        except Exception as e:
            self.log_message("Server thread error: " + str(e))
    
    def _handle_client(self, client):
        """Handle communication with a connected client"""
        self.log_message("Client handler started")
        client.settimeout(None)  # No timeout for client socket
        buffer = ''  # Changed from b'' to '' for Python 2
        
        try:
            while self.running:
                try:
                    # Receive data
                    data = client.recv(8192)
                    
                    if not data:
                        # Client disconnected
                        self.log_message("Client disconnected")
                        break
                    
                    # Accumulate data in buffer with explicit encoding/decoding
                    try:
                        # Python 3: data is bytes, decode to string
                        buffer += data.decode('utf-8')
                    except AttributeError:
                        # Python 2: data is already string
                        buffer += data
                    
                    try:
                        # Try to parse command from buffer
                        command = json.loads(buffer)  # Removed decode('utf-8')
                        buffer = ''  # Clear buffer after successful parse
                        
                        self.log_message("Received command: " + str(command.get("type", "unknown")))
                        
                        # Process the command and get response
                        response = self._process_command(command)
                        
                        # Send the response with explicit encoding
                        try:
                            # Python 3: encode string to bytes
                            client.sendall(json.dumps(response).encode('utf-8'))
                        except AttributeError:
                            # Python 2: string is already bytes
                            client.sendall(json.dumps(response))
                    except ValueError:
                        # Incomplete data, wait for more
                        continue
                        
                except Exception as e:
                    self.log_message("Error handling client data: " + str(e))
                    self.log_message(traceback.format_exc())
                    
                    # Send error response if possible
                    error_response = {
                        "status": "error",
                        "message": str(e)
                    }
                    try:
                        # Python 3: encode string to bytes
                        client.sendall(json.dumps(error_response).encode('utf-8'))
                    except AttributeError:
                        # Python 2: string is already bytes
                        client.sendall(json.dumps(error_response))
                    except:
                        # If we can't send the error, the connection is probably dead
                        break
                    
                    # For serious errors, break the loop
                    if not isinstance(e, ValueError):
                        break
        except Exception as e:
            self.log_message("Error in client handler: " + str(e))
        finally:
            try:
                client.close()
            except:
                pass
            self.log_message("Client handler stopped")
    
    def _process_command(self, command):
        """Process a command from the client and return a response"""
        command_type = command.get("type", "")
        params = command.get("params", {})
        
        # Initialize response
        response = {
            "status": "success",
            "result": {}
        }
        
        try:
            # Route the command to the appropriate handler
            if command_type == "get_session_info":
                response["result"] = self._get_session_info()
            elif command_type == "get_track_info":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_track_info(track_index)
            # Commands that modify Live's state should be scheduled on the main thread
            elif command_type in ["create_midi_track", "create_audio_track", "delete_track",
                                 "duplicate_track", "set_track_input_routing", "set_track_output_routing",
                                 "set_track_name", "set_track_mute", "set_track_solo", "set_track_arm",
                                 "set_track_volume", "set_track_pan", "set_send_level", "set_master_volume",
                                 "create_clip", "create_audio_clip", "add_notes_to_clip", "set_clip_name",
                                 "delete_clip", "duplicate_clip", "set_clip_color", "set_clip_notes",
                                 "remove_clip_notes", "set_clip_loop", "apply_groove",
                                 "set_clip_gain", "set_clip_pitch", "set_clip_warp_mode",
                                 "set_clip_automation", "load_effect",
                                 "set_tempo", "set_time_signature", "fire_clip", "stop_clip",
                                 "start_playback", "stop_playback", "start_recording", "stop_recording",
                                 "set_overdub", "capture_midi", "load_browser_item",
                                 "set_device_parameter",
                                 "create_scene", "fire_scene", "stop_scene", "set_scene_name",
                                 "undo", "redo",
                                 # Arrangement view – must run on the main thread
                                 "switch_to_arrangement_view", "set_current_song_time", "jump_to_time",
                                 "duplicate_session_clip_to_arrangement",
                                 "create_arrangement_clip", "import_audio_to_arrangement",
                                 "move_arrangement_clip", "set_arrangement_loop",
                                 "create_locator", "delete_locator", "set_locator_name",
                                 "create_take_lane", "import_audio_to_take_lane",
                                 "add_notes_to_arrangement_clip", "set_arrangement_clip_notes",
                                 "remove_arrangement_clip_notes",
                                 # Phase 4 — devices, racks, presets
                                 "insert_device", "delete_device", "load_preset_by_path",
                                 "set_rack_macro", "add_rack_macro", "remove_rack_macro",
                                 "set_rack_visible_macros", "randomize_rack_macros",
                                 "store_rack_variation", "recall_rack_variation",
                                 "delete_rack_variation", "insert_rack_chain",
                                 "set_chain_name", "set_chain_volume", "set_drum_chain_note",
                                 "set_device_parameter_by_name", "set_chain_device_parameter"]:
                # Use a thread-safe approach with a response queue
                response_queue = queue.Queue()
                
                # Define a function to execute on the main thread
                def main_thread_task():
                    try:
                        result = None
                        if command_type == "create_midi_track":
                            index = params.get("index", -1)
                            result = self._create_midi_track(index)
                        elif command_type == "create_audio_track":
                            index = params.get("index", -1)
                            result = self._create_audio_track(index)
                        elif command_type == "delete_track":
                            track_index = params.get("track_index", 0)
                            result = self._delete_track(track_index)
                        elif command_type == "set_track_name":
                            track_index = params.get("track_index", 0)
                            name = params.get("name", "")
                            result = self._set_track_name(track_index, name)
                        elif command_type == "set_track_mute":
                            result = self._set_track_mute(
                                params.get("track_index", 0), params.get("mute", True))
                        elif command_type == "set_track_solo":
                            result = self._set_track_solo(
                                params.get("track_index", 0), params.get("solo", True))
                        elif command_type == "set_track_arm":
                            result = self._set_track_arm(
                                params.get("track_index", 0), params.get("arm", True))
                        elif command_type == "set_track_volume":
                            result = self._set_track_volume(
                                params.get("track_index", 0), params.get("volume", 0.85))
                        elif command_type == "set_track_pan":
                            result = self._set_track_pan(
                                params.get("track_index", 0), params.get("pan", 0.0))
                        elif command_type == "set_send_level":
                            result = self._set_send_level(
                                params.get("track_index", 0),
                                params.get("send_index", 0),
                                params.get("level", 0.0))
                        elif command_type == "set_master_volume":
                            result = self._set_master_volume(params.get("volume", 0.85))
                        elif command_type == "set_device_parameter":
                            result = self._set_device_parameter(
                                params.get("track_index", 0),
                                params.get("device_index", 0),
                                params.get("parameter_index", 0),
                                params.get("value", 0.0))
                        elif command_type == "create_scene":
                            result = self._create_scene(params.get("index", -1), params.get("name"))
                        elif command_type == "fire_scene":
                            result = self._fire_scene(params.get("scene_index", 0))
                        elif command_type == "stop_scene":
                            result = self._stop_scene(params.get("scene_index", 0))
                        elif command_type == "set_scene_name":
                            result = self._set_scene_name(
                                params.get("scene_index", 0), params.get("name", ""))
                        elif command_type == "set_time_signature":
                            result = self._set_time_signature(
                                params.get("numerator", 4), params.get("denominator", 4))
                        elif command_type == "undo":
                            result = self._undo()
                        elif command_type == "redo":
                            result = self._redo()
                        elif command_type == "delete_clip":
                            result = self._delete_clip(
                                params.get("track_index", 0), params.get("clip_index", 0))
                        elif command_type == "set_clip_loop":
                            result = self._set_clip_loop(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("loop_start", 0.0),
                                params.get("loop_end", 4.0),
                                params.get("looping", True))
                        elif command_type == "create_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            length = params.get("length", 4.0)
                            result = self._create_clip(track_index, clip_index, length)
                        elif command_type == "create_audio_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            path = params.get("path", "")
                            result = self._create_audio_clip(track_index, clip_index, path)
                        elif command_type == "add_notes_to_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            notes = params.get("notes", [])
                            result = self._add_notes_to_clip(track_index, clip_index, notes)
                        elif command_type == "set_clip_name":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            name = params.get("name", "")
                            result = self._set_clip_name(track_index, clip_index, name)
                        elif command_type == "set_tempo":
                            tempo = params.get("tempo", 120.0)
                            result = self._set_tempo(tempo)
                        elif command_type == "fire_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            result = self._fire_clip(track_index, clip_index)
                        elif command_type == "stop_clip":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            result = self._stop_clip(track_index, clip_index)
                        elif command_type == "start_playback":
                            result = self._start_playback()
                        elif command_type == "stop_playback":
                            result = self._stop_playback()
                        elif command_type == "load_instrument_or_effect":
                            track_index = params.get("track_index", 0)
                            uri = params.get("uri", "")
                            result = self._load_browser_item(track_index, uri)
                        elif command_type == "load_browser_item":
                            track_index = params.get("track_index", 0)
                            item_uri = params.get("item_uri", "")
                            result = self._load_browser_item(track_index, item_uri)
                        # ── Arrangement view commands ──────────────────────────────
                        elif command_type == "switch_to_arrangement_view":
                            result = self._switch_to_arrangement_view()
                        elif command_type == "set_current_song_time":
                            time_val = params.get("time", 0.0)
                            result = self._set_current_song_time(time_val)
                        elif command_type == "duplicate_session_clip_to_arrangement":
                            track_index = params.get("track_index", 0)
                            clip_index = params.get("clip_index", 0)
                            destination_time = params.get("destination_time", 0.0)
                            result = self._duplicate_session_clip_to_arrangement(
                                track_index, clip_index, destination_time)
                        elif command_type == "duplicate_track":
                            result = self._duplicate_track(params.get("track_index", 0))
                        elif command_type == "set_track_input_routing":
                            result = self._set_track_input_routing(
                                params.get("track_index", 0),
                                params.get("routing_type_id", ""),
                                params.get("routing_channel_id", ""))
                        elif command_type == "set_track_output_routing":
                            result = self._set_track_output_routing(
                                params.get("track_index", 0),
                                params.get("routing_type_id", ""),
                                params.get("routing_channel_id", ""))
                        elif command_type == "duplicate_clip":
                            result = self._duplicate_clip(
                                params.get("track_index", 0), params.get("clip_index", 0))
                        elif command_type == "set_clip_color":
                            result = self._set_clip_color(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("color_index", 0))
                        elif command_type == "set_clip_notes":
                            result = self._set_clip_notes(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("notes", []))
                        elif command_type == "remove_clip_notes":
                            result = self._remove_clip_notes(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("from_pitch", 0),
                                params.get("pitch_span", 128),
                                params.get("from_time", 0.0),
                                params.get("time_span", 999999.0))
                        elif command_type == "start_recording":
                            result = self._start_recording()
                        elif command_type == "stop_recording":
                            result = self._stop_recording()
                        elif command_type == "set_overdub":
                            result = self._set_overdub(params.get("overdub", True))
                        elif command_type == "capture_midi":
                            result = self._capture_midi(params.get("destination", "auto"))
                        elif command_type == "create_arrangement_clip":
                            result = self._create_arrangement_clip(
                                params.get("track_index", 0),
                                params.get("start_time", 0.0),
                                params.get("length", 4.0))
                        elif command_type == "import_audio_to_arrangement":
                            result = self._import_audio_to_arrangement(
                                params.get("track_index", 0),
                                params.get("path", ""),
                                params.get("start_time", 0.0))
                        elif command_type == "move_arrangement_clip":
                            result = self._move_arrangement_clip(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("new_start_time", 0.0),
                                params.get("new_track_index"))
                        elif command_type == "set_arrangement_loop":
                            result = self._set_arrangement_loop(
                                params.get("start_time", 0.0),
                                params.get("end_time", 4.0),
                                params.get("enabled", True))
                        elif command_type == "jump_to_time":
                            result = self._set_current_song_time(params.get("time", 0.0))
                        elif command_type == "create_locator":
                            result = self._create_locator(
                                params.get("time", 0.0), params.get("name"))
                        elif command_type == "delete_locator":
                            result = self._delete_locator(params.get("locator_index", 0))
                        elif command_type == "set_locator_name":
                            result = self._set_locator_name(
                                params.get("locator_index", 0), params.get("name", ""))
                        elif command_type == "create_take_lane":
                            result = self._create_take_lane(
                                params.get("track_index", 0), params.get("name"))
                        elif command_type == "apply_groove":
                            result = self._apply_groove(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("groove_index", 0))
                        elif command_type == "set_clip_gain":
                            result = self._set_clip_gain(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("gain", 1.0))
                        elif command_type == "set_clip_pitch":
                            result = self._set_clip_pitch(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("semitones", 0))
                        elif command_type == "set_clip_warp_mode":
                            result = self._set_clip_warp_mode(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("warp_mode", 0))
                        elif command_type == "set_clip_automation":
                            result = self._set_clip_automation(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("device_index", 0),
                                params.get("parameter_index", 0),
                                params.get("points", []))
                        elif command_type == "load_effect":
                            result = self._load_effect(
                                params.get("track_index", 0),
                                params.get("uri", ""))
                        elif command_type == "import_audio_to_take_lane":
                            result = self._import_audio_to_take_lane(
                                params.get("track_index", 0),
                                params.get("take_lane_index", 0),
                                params.get("path", ""),
                                params.get("start_time", 0.0))
                        elif command_type == "add_notes_to_arrangement_clip":
                            result = self._add_notes_to_arrangement_clip(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("notes", []))
                        elif command_type == "set_arrangement_clip_notes":
                            result = self._set_arrangement_clip_notes(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("notes", []))
                        elif command_type == "remove_arrangement_clip_notes":
                            result = self._remove_arrangement_clip_notes(
                                params.get("track_index", 0),
                                params.get("clip_index", 0),
                                params.get("from_pitch", 0),
                                params.get("pitch_span", 128),
                                params.get("from_time", 0.0),
                                params.get("time_span", 999999.0))
                        elif command_type == "insert_device":
                            result = self._insert_device(
                                params.get("track_index", 0),
                                params.get("device_name", ""),
                                params.get("position", -1),
                                params.get("device_index"),
                                params.get("chain_index"))
                        elif command_type == "delete_device":
                            result = self._delete_device(
                                params.get("track_index", 0),
                                params.get("device_index", 0))
                        elif command_type == "load_preset_by_path":
                            result = self._load_preset_by_path(
                                params.get("track_index", 0),
                                params.get("path", ""))
                        elif command_type == "set_rack_macro":
                            result = self._set_rack_macro(
                                params.get("track_index", 0),
                                params.get("device_index", 0),
                                params.get("macro_index", 0),
                                params.get("value", 0.0))
                        elif command_type == "add_rack_macro":
                            result = self._add_rack_macro(
                                params.get("track_index", 0),
                                params.get("device_index", 0))
                        elif command_type == "remove_rack_macro":
                            result = self._remove_rack_macro(
                                params.get("track_index", 0),
                                params.get("device_index", 0))
                        elif command_type == "set_rack_visible_macros":
                            result = self._set_rack_visible_macros(
                                params.get("track_index", 0),
                                params.get("device_index", 0),
                                params.get("count", 8))
                        elif command_type == "randomize_rack_macros":
                            result = self._randomize_rack_macros(
                                params.get("track_index", 0),
                                params.get("device_index", 0))
                        elif command_type == "store_rack_variation":
                            result = self._store_rack_variation(
                                params.get("track_index", 0),
                                params.get("device_index", 0))
                        elif command_type == "recall_rack_variation":
                            result = self._recall_rack_variation(
                                params.get("track_index", 0),
                                params.get("device_index", 0),
                                params.get("variation_index", 0))
                        elif command_type == "delete_rack_variation":
                            result = self._delete_rack_variation(
                                params.get("track_index", 0),
                                params.get("device_index", 0),
                                params.get("variation_index", 0))
                        elif command_type == "insert_rack_chain":
                            result = self._insert_rack_chain(
                                params.get("track_index", 0),
                                params.get("device_index", 0),
                                params.get("position", -1))
                        elif command_type == "set_chain_name":
                            result = self._set_chain_name(
                                params.get("track_index", 0),
                                params.get("device_index", 0),
                                params.get("chain_index", 0),
                                params.get("name", ""))
                        elif command_type == "set_chain_volume":
                            result = self._set_chain_volume(
                                params.get("track_index", 0),
                                params.get("device_index", 0),
                                params.get("chain_index", 0),
                                params.get("volume"),
                                params.get("pan"),
                                params.get("mute"),
                                params.get("solo"))
                        elif command_type == "set_drum_chain_note":
                            result = self._set_drum_chain_note(
                                params.get("track_index", 0),
                                params.get("device_index", 0),
                                params.get("chain_index", 0),
                                params.get("note", 36))
                        elif command_type == "set_device_parameter_by_name":
                            result = self._set_device_parameter_by_name(
                                params.get("track_index", 0),
                                params.get("device_index", 0),
                                params.get("parameter_name", ""),
                                params.get("value", 0.0))
                        elif command_type == "set_chain_device_parameter":
                            result = self._set_chain_device_parameter(
                                params.get("track_index", 0),
                                params.get("rack_index", 0),
                                params.get("chain_index", 0),
                                params.get("chain_device_index", 0),
                                params.get("parameter_index", 0),
                                params.get("value", 0.0),
                                params.get("parameter_name"))

                        # Put the result in the queue
                        response_queue.put({"status": "success", "result": result})
                    except Exception as e:
                        self.log_message("Error in main thread task: " + str(e))
                        self.log_message(traceback.format_exc())
                        response_queue.put({"status": "error", "message": str(e)})
                
                # Schedule the task to run on the main thread
                try:
                    self.schedule_message(0, main_thread_task)
                except AssertionError:
                    # If we're already on the main thread, execute directly
                    main_thread_task()
                
                # Wait for the response with a timeout. Some commands (notably
                # create_audio_clip, which decodes/imports the audio file on
                # the main thread) can take longer than the default 10s on
                # larger files — give them more headroom.
                long_running_commands = {
                    "create_audio_clip": 60.0,
                    "import_audio_to_arrangement": 60.0,
                    "import_audio_to_take_lane": 60.0,
                }
                queue_timeout = long_running_commands.get(command_type, 10.0)
                try:
                    task_response = response_queue.get(timeout=queue_timeout)
                    if task_response.get("status") == "error":
                        response["status"] = "error"
                        response["message"] = task_response.get("message", "Unknown error")
                    else:
                        response["result"] = task_response.get("result", {})
                except queue.Empty:
                    response["status"] = "error"
                    response["message"] = "Timeout waiting for operation to complete"
            elif command_type == "get_browser_item":
                uri = params.get("uri", None)
                path = params.get("path", None)
                response["result"] = self._get_browser_item(uri, path)
            elif command_type == "get_browser_categories":
                category_type = params.get("category_type", "all")
                response["result"] = self._get_browser_categories(category_type)
            elif command_type == "get_browser_items":
                path = params.get("path", "")
                item_type = params.get("item_type", "all")
                response["result"] = self._get_browser_items(path, item_type)
            # Add the new browser commands
            elif command_type == "get_browser_tree":
                category_type = params.get("category_type", "all")
                response["result"] = self.get_browser_tree(category_type)
            elif command_type == "get_browser_items_at_path":
                path = params.get("path", "")
                response["result"] = self.get_browser_items_at_path(path)
            # Read-only arrangement command – no main-thread scheduling required
            elif command_type == "get_arrangement_clips":
                track_index = params.get("track_index", 0)
                response["result"] = self._get_arrangement_clips(track_index)
            elif command_type == "get_device_parameters":
                response["result"] = self._get_device_parameters(
                    params.get("track_index", 0), params.get("device_index", 0))
            elif command_type == "get_scenes":
                response["result"] = self._get_scenes()
            elif command_type == "get_clip_info":
                response["result"] = self._get_clip_info(
                    params.get("track_index", 0), params.get("clip_index", 0))
            elif command_type == "get_clip_notes":
                response["result"] = self._get_clip_notes(
                    params.get("track_index", 0), params.get("clip_index", 0))
            elif command_type == "get_playback_position":
                response["result"] = self._get_playback_position()
            elif command_type == "get_return_tracks":
                response["result"] = self._get_return_tracks()
            elif command_type == "get_track_routing":
                response["result"] = self._get_track_routing(params.get("track_index", 0))
            elif command_type == "get_arrangement_length":
                response["result"] = self._get_arrangement_length()
            elif command_type == "get_locators":
                response["result"] = self._get_locators()
            elif command_type == "get_take_lanes":
                response["result"] = self._get_take_lanes(params.get("track_index", 0))
            elif command_type == "get_groove_pool":
                response["result"] = self._get_groove_pool()
            elif command_type == "search_browser":
                response["result"] = self._search_browser(
                    params.get("query", ""),
                    params.get("category_type", "all"),
                    params.get("max_results", 25),
                    params.get("loadable_only", False))
            elif command_type == "get_clip_automation":
                response["result"] = self._get_clip_automation(
                    params.get("track_index", 0),
                    params.get("clip_index", 0),
                    params.get("device_index", 0),
                    params.get("parameter_index", 0))
            elif command_type == "get_arrangement_clip_notes":
                response["result"] = self._get_arrangement_clip_notes(
                    params.get("track_index", 0), params.get("clip_index", 0))
            elif command_type == "get_master_info":
                response["result"] = self._get_master_info()
            elif command_type == "get_device_info":
                response["result"] = self._get_device_info(
                    params.get("track_index", 0), params.get("device_index", 0))
            elif command_type == "get_device_tree":
                response["result"] = self._get_device_tree(
                    params.get("track_index", 0), params.get("device_index", 0))
            elif command_type == "get_device_parameters_detailed":
                response["result"] = self._get_device_parameters_detailed(
                    params.get("track_index", 0), params.get("device_index", 0),
                    params.get("rack_index"), params.get("chain_index"),
                    params.get("chain_device_index"))
            elif command_type == "get_rack_info":
                response["result"] = self._get_rack_info(
                    params.get("track_index", 0), params.get("device_index", 0))
            elif command_type == "get_rack_macros":
                response["result"] = self._get_rack_macros(
                    params.get("track_index", 0), params.get("device_index", 0))
            elif command_type == "get_macro_mappings":
                response["result"] = self._get_macro_mappings(
                    params.get("track_index", 0), params.get("device_index", 0))
            elif command_type == "get_rack_variations":
                response["result"] = self._get_rack_variations(
                    params.get("track_index", 0), params.get("device_index", 0))
            elif command_type == "get_rack_chains":
                response["result"] = self._get_rack_chains(
                    params.get("track_index", 0), params.get("device_index", 0))
            elif command_type == "find_browser_by_path":
                response["result"] = self._find_browser_by_path(
                    params.get("path", ""), params.get("max_results", 10))
            else:
                response["status"] = "error"
                response["message"] = "Unknown command: " + command_type
        except Exception as e:
            self.log_message("Error processing command: " + str(e))
            self.log_message(traceback.format_exc())
            response["status"] = "error"
            response["message"] = str(e)
        
        return response
    
    # Command implementations
    
    def _safe_song_property(self, attr, cast, default):
        """Read self._song.<attr> with cast, returning default on common failures.
        Catches only narrow exceptions so genuine bugs still surface."""
        try:
            return cast(getattr(self._song, attr))
        except (AttributeError, TypeError, ValueError):
            return default

    def _get_session_info(self):
        """Get information about the current session"""
        try:
            result = {
                "tempo": self._song.tempo,
                "signature_numerator": self._song.signature_numerator,
                "signature_denominator": self._song.signature_denominator,
                "track_count": len(self._song.tracks),
                "return_track_count": len(self._song.return_tracks),
                "master_track": {
                    "name": "Master",
                    "volume": self._song.master_track.mixer_device.volume.value,
                    "panning": self._song.master_track.mixer_device.panning.value
                },
                # Transport / playback state — lets clients render a live
                # playhead without polling separately. Each property is read
                # via _safe_song_property so an attribute missing on a given
                # Live version falls back to its default rather than breaking
                # the response shape.
                "is_playing":        self._safe_song_property("is_playing",        bool,  False),
                "current_song_time": self._safe_song_property("current_song_time", float, 0.0),
                "song_length":       self._safe_song_property("song_length",       float, 0.0),
                "loop":              self._safe_song_property("loop",              bool,  False),
                "loop_start":        self._safe_song_property("loop_start",        float, 0.0),
                "loop_length":       self._safe_song_property("loop_length",       float, 0.0),
            }
            return result
        except Exception as e:
            self.log_message("Error getting session info: " + str(e))
            raise
    
    def _get_track_info(self, track_index):
        """Get information about a track"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            # Get clip slots
            clip_slots = []
            for slot_index, slot in enumerate(track.clip_slots):
                clip_info = None
                if slot.has_clip:
                    clip = slot.clip
                    clip_info = {
                        "name": clip.name,
                        "length": clip.length,
                        "is_playing": clip.is_playing,
                        "is_recording": clip.is_recording
                    }
                
                clip_slots.append({
                    "index": slot_index,
                    "has_clip": slot.has_clip,
                    "clip": clip_info
                })
            
            # Get devices
            devices = []
            for device_index, device in enumerate(track.devices):
                devices.append({
                    "index": device_index,
                    "name": device.name,
                    "class_name": device.class_name,
                    "type": self._get_device_type(device)
                })
            
            result = {
                "index": track_index,
                "name": track.name,
                "is_audio_track": track.has_audio_input,
                "is_midi_track": track.has_midi_input,
                "mute": track.mute,
                "solo": track.solo,
                "arm": track.arm,
                "volume": track.mixer_device.volume.value,
                "panning": track.mixer_device.panning.value,
                "clip_slots": clip_slots,
                "devices": devices
            }
            return result
        except Exception as e:
            self.log_message("Error getting track info: " + str(e))
            raise
    
    def _create_midi_track(self, index):
        """Create a new MIDI track at the specified index"""
        try:
            # Create the track
            self._song.create_midi_track(index)
            
            # Get the new track
            new_track_index = len(self._song.tracks) - 1 if index == -1 else index
            new_track = self._song.tracks[new_track_index]
            
            result = {
                "index": new_track_index,
                "name": new_track.name
            }
            return result
        except Exception as e:
            self.log_message("Error creating MIDI track: " + str(e))
            raise
    
    
    def _set_track_name(self, track_index, name):
        """Set the name of a track"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            # Set the name
            track = self._song.tracks[track_index]
            track.name = name
            
            result = {
                "name": track.name
            }
            return result
        except Exception as e:
            self.log_message("Error setting track name: " + str(e))
            raise
    
    def _create_clip(self, track_index, clip_index, length):
        """Create a new MIDI clip in the specified track and clip slot"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            # Check if the clip slot already has a clip
            if clip_slot.has_clip:
                raise Exception("Clip slot already has a clip")
            
            # Create the clip
            clip_slot.create_clip(length)
            
            result = {
                "name": clip_slot.clip.name,
                "length": clip_slot.clip.length
            }
            return result
        except Exception as e:
            self.log_message("Error creating clip: " + str(e))
            raise

    def _create_audio_clip(self, track_index, clip_index, path):
        """Create an audio clip in the specified audio track clip slot by importing a file.

        Requires Ableton Live 12.0.5 or newer (the underlying
        ClipSlot.create_audio_clip Live API was introduced in 12.0.5 — it is
        not available in earlier 12.0.x releases).
        """
        try:
            if not path:
                raise ValueError("Audio file path is required")

            if not os.path.isabs(path):
                raise ValueError("Audio file path must be absolute (got: %s)" % path)

            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")

            track = self._song.tracks[track_index]

            # Must be an audio track. Audio tracks expose audio input; MIDI
            # tracks don't. Reject MIDI / return tracks up front so the caller
            # gets a clear error instead of a Live API exception.
            if getattr(track, "has_midi_input", False) or not getattr(track, "has_audio_input", True):
                raise ValueError("Track %d is not an audio track" % track_index)

            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")

            clip_slot = track.clip_slots[clip_index]

            if clip_slot.has_clip:
                raise Exception("Clip slot already has a clip")

            if not hasattr(clip_slot, "create_audio_clip"):
                raise Exception(
                    "ClipSlot.create_audio_clip is unavailable in this Ableton Live "
                    "version. Requires Live 12.0.5 or newer."
                )

            clip_slot.create_audio_clip(path)

            result = {
                "name": clip_slot.clip.name,
                "length": clip_slot.clip.length,
                "is_audio_clip": clip_slot.clip.is_audio_clip
            }
            return result
        except Exception as e:
            self.log_message("Error creating audio clip: " + str(e))
            raise

    def _add_notes_to_clip(self, track_index, clip_index, notes):
        """Add MIDI notes to a clip"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            
            clip = clip_slot.clip
            
            # Convert note data to Live's format
            live_notes = []
            for note in notes:
                pitch = note.get("pitch", 60)
                start_time = note.get("start_time", 0.0)
                duration = note.get("duration", 0.25)
                velocity = note.get("velocity", 100)
                mute = note.get("mute", False)
                
                live_notes.append((pitch, start_time, duration, velocity, mute))
            
            # Add the notes
            clip.set_notes(tuple(live_notes))
            
            result = {
                "note_count": len(notes)
            }
            return result
        except Exception as e:
            self.log_message("Error adding notes to clip: " + str(e))
            raise
    
    def _set_clip_name(self, track_index, clip_index, name):
        """Set the name of a clip"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            
            clip = clip_slot.clip
            clip.name = name
            
            result = {
                "name": clip.name
            }
            return result
        except Exception as e:
            self.log_message("Error setting clip name: " + str(e))
            raise
    
    def _set_tempo(self, tempo):
        """Set the tempo of the session"""
        try:
            self._song.tempo = tempo
            
            result = {
                "tempo": self._song.tempo
            }
            return result
        except Exception as e:
            self.log_message("Error setting tempo: " + str(e))
            raise
    
    def _fire_clip(self, track_index, clip_index):
        """Fire a clip"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            
            clip_slot.fire()
            
            result = {
                "fired": True
            }
            return result
        except Exception as e:
            self.log_message("Error firing clip: " + str(e))
            raise
    
    def _stop_clip(self, track_index, clip_index):
        """Stop a clip"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip index out of range")
            
            clip_slot = track.clip_slots[clip_index]
            
            clip_slot.stop()
            
            result = {
                "stopped": True
            }
            return result
        except Exception as e:
            self.log_message("Error stopping clip: " + str(e))
            raise
    
    
    def _start_playback(self):
        """Start playing the session"""
        try:
            self._song.start_playing()
            
            result = {
                "playing": self._song.is_playing
            }
            return result
        except Exception as e:
            self.log_message("Error starting playback: " + str(e))
            raise
    
    def _stop_playback(self):
        """Stop playing the session"""
        try:
            self._song.stop_playing()
            
            result = {
                "playing": self._song.is_playing
            }
            return result
        except Exception as e:
            self.log_message("Error stopping playback: " + str(e))
            raise

    def _track_or_raise(self, track_index):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index out of range")
        return self._song.tracks[track_index]

    def _clip_slot_or_raise(self, track_index, clip_index):
        track = self._track_or_raise(track_index)
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        return track, track.clip_slots[clip_index]

    def _create_audio_track(self, index):
        try:
            self._song.create_audio_track(index)
            new_track_index = len(self._song.tracks) - 1 if index == -1 else index
            new_track = self._song.tracks[new_track_index]
            return {"index": new_track_index, "name": new_track.name}
        except Exception as e:
            self.log_message("Error creating audio track: " + str(e))
            raise

    def _delete_track(self, track_index):
        try:
            track = self._track_or_raise(track_index)
            name = track.name
            self._song.delete_track(track_index)
            return {"deleted_index": track_index, "name": name}
        except Exception as e:
            self.log_message("Error deleting track: " + str(e))
            raise

    def _set_track_mute(self, track_index, mute):
        try:
            track = self._track_or_raise(track_index)
            track.mute = bool(mute)
            return {"track_index": track_index, "mute": track.mute}
        except Exception as e:
            self.log_message("Error setting track mute: " + str(e))
            raise

    def _set_track_solo(self, track_index, solo):
        try:
            track = self._track_or_raise(track_index)
            track.solo = bool(solo)
            return {"track_index": track_index, "solo": track.solo}
        except Exception as e:
            self.log_message("Error setting track solo: " + str(e))
            raise

    def _set_track_arm(self, track_index, arm):
        try:
            track = self._track_or_raise(track_index)
            track.arm = bool(arm)
            return {"track_index": track_index, "arm": track.arm}
        except Exception as e:
            self.log_message("Error setting track arm: " + str(e))
            raise

    def _set_track_volume(self, track_index, volume):
        try:
            track = self._track_or_raise(track_index)
            volume = max(0.0, min(1.0, float(volume)))
            track.mixer_device.volume.value = volume
            return {"track_index": track_index, "volume": track.mixer_device.volume.value}
        except Exception as e:
            self.log_message("Error setting track volume: " + str(e))
            raise

    def _set_track_pan(self, track_index, pan):
        try:
            track = self._track_or_raise(track_index)
            pan = max(-1.0, min(1.0, float(pan)))
            track.mixer_device.panning.value = pan
            return {"track_index": track_index, "pan": track.mixer_device.panning.value}
        except Exception as e:
            self.log_message("Error setting track pan: " + str(e))
            raise

    def _set_send_level(self, track_index, send_index, level):
        try:
            track = self._track_or_raise(track_index)
            sends = track.mixer_device.sends
            if send_index < 0 or send_index >= len(sends):
                raise IndexError("Send index out of range")
            level = max(0.0, min(1.0, float(level)))
            sends[send_index].value = level
            return {
                "track_index": track_index,
                "send_index": send_index,
                "level": sends[send_index].value,
            }
        except Exception as e:
            self.log_message("Error setting send level: " + str(e))
            raise

    def _set_master_volume(self, volume):
        try:
            volume = max(0.0, min(1.0, float(volume)))
            mixer = self._song.master_track.mixer_device
            mixer.volume.value = volume
            return {"volume": mixer.volume.value}
        except Exception as e:
            self.log_message("Error setting master volume: " + str(e))
            raise

    def _get_return_tracks(self):
        try:
            return_tracks = []
            for index, return_track in enumerate(self._song.return_tracks):
                return_tracks.append({
                    "index": index,
                    "name": return_track.name,
                    "volume": return_track.mixer_device.volume.value,
                    "pan": return_track.mixer_device.panning.value,
                })
            return {"return_tracks": return_tracks}
        except Exception as e:
            self.log_message("Error getting return tracks: " + str(e))
            raise

    def _device_or_raise(self, track_index, device_index):
        track = self._track_or_raise(track_index)
        devices = list(track.devices)
        if device_index < 0 or device_index >= len(devices):
            raise IndexError("Device index out of range")
        return devices[device_index]

    def _get_device_parameters(self, track_index, device_index):
        try:
            device = self._device_or_raise(track_index, device_index)
            parameters = []
            for parameter_index, parameter in enumerate(device.parameters):
                parameters.append({
                    "index": parameter_index,
                    "name": parameter.name,
                    "value": parameter.value,
                    "min": parameter.min,
                    "max": parameter.max,
                    "is_quantized": parameter.is_quantized,
                })
            return {
                "track_index": track_index,
                "device_index": device_index,
                "device_name": device.name,
                "parameters": parameters,
            }
        except Exception as e:
            self.log_message("Error getting device parameters: " + str(e))
            raise

    def _set_device_parameter(self, track_index, device_index, parameter_index, value):
        try:
            device = self._device_or_raise(track_index, device_index)
            parameters = list(device.parameters)
            if parameter_index < 0 or parameter_index >= len(parameters):
                raise IndexError("Parameter index out of range")
            parameter = parameters[parameter_index]
            value = float(value)
            if value < parameter.min or value > parameter.max:
                raise ValueError(
                    "Value must be between %s and %s" % (parameter.min, parameter.max))
            parameter.value = value
            return {
                "track_index": track_index,
                "device_index": device_index,
                "parameter_index": parameter_index,
                "value": parameter.value,
            }
        except Exception as e:
            self.log_message("Error setting device parameter: " + str(e))
            raise

    def _get_scenes(self):
        try:
            scenes = []
            for scene_index, scene in enumerate(self._song.scenes):
                scenes.append({
                    "index": scene_index,
                    "name": scene.name,
                    "is_empty": scene.is_empty,
                    "is_triggered": scene.is_triggered,
                })
            return {"scenes": scenes}
        except Exception as e:
            self.log_message("Error getting scenes: " + str(e))
            raise

    def _create_scene(self, index, name=None):
        try:
            self._song.create_scene(index)
            scene_index = len(self._song.scenes) - 1 if index == -1 else index
            scene = self._song.scenes[scene_index]
            if name:
                scene.name = name
            return {"index": scene_index, "name": scene.name}
        except Exception as e:
            self.log_message("Error creating scene: " + str(e))
            raise

    def _fire_scene(self, scene_index):
        try:
            if scene_index < 0 or scene_index >= len(self._song.scenes):
                raise IndexError("Scene index out of range")
            scene = self._song.scenes[scene_index]
            scene.fire()
            return {"scene_index": scene_index, "name": scene.name}
        except Exception as e:
            self.log_message("Error firing scene: " + str(e))
            raise

    def _stop_scene(self, scene_index):
        try:
            if scene_index < 0 or scene_index >= len(self._song.scenes):
                raise IndexError("Scene index out of range")
            for track in self._song.tracks:
                if scene_index < len(track.clip_slots):
                    track.clip_slots[scene_index].stop()
            return {"scene_index": scene_index, "stopped": True}
        except Exception as e:
            self.log_message("Error stopping scene: " + str(e))
            raise

    def _set_scene_name(self, scene_index, name):
        try:
            if scene_index < 0 or scene_index >= len(self._song.scenes):
                raise IndexError("Scene index out of range")
            scene = self._song.scenes[scene_index]
            scene.name = name
            return {"scene_index": scene_index, "name": scene.name}
        except Exception as e:
            self.log_message("Error setting scene name: " + str(e))
            raise

    def _set_time_signature(self, numerator, denominator):
        try:
            self._song.signature_numerator = int(numerator)
            self._song.signature_denominator = int(denominator)
            return {
                "numerator": self._song.signature_numerator,
                "denominator": self._song.signature_denominator,
            }
        except Exception as e:
            self.log_message("Error setting time signature: " + str(e))
            raise

    def _undo(self):
        try:
            if not self._song.can_undo:
                raise Exception("No undo history available")
            self._song.undo()
            return {"can_undo": self._song.can_undo, "can_redo": self._song.can_redo}
        except Exception as e:
            self.log_message("Error undoing: " + str(e))
            raise

    def _redo(self):
        try:
            if not self._song.can_redo:
                raise Exception("No redo history available")
            self._song.redo()
            return {"can_undo": self._song.can_undo, "can_redo": self._song.can_redo}
        except Exception as e:
            self.log_message("Error redoing: " + str(e))
            raise

    def _get_playback_position(self):
        try:
            current_time = self._song.current_song_time
            numerator = self._song.signature_numerator
            tempo = self._song.tempo
            return {
                "beats": current_time,
                "bar": int(current_time // numerator) + 1,
                "beat_in_bar": (current_time % numerator) + 1,
                "time_seconds": current_time * 60.0 / tempo,
                "is_playing": self._song.is_playing,
            }
        except Exception as e:
            self.log_message("Error getting playback position: " + str(e))
            raise

    def _get_clip_info(self, track_index, clip_index):
        try:
            track, clip_slot = self._clip_slot_or_raise(track_index, clip_index)
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            clip = clip_slot.clip
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "name": clip.name,
                "length": clip.length,
                "is_audio_clip": clip.is_audio_clip,
                "is_midi_clip": clip.is_midi_clip,
                "is_playing": clip.is_playing,
                "is_recording": clip.is_recording,
                "looping": getattr(clip, "looping", False),
                "loop_start": getattr(clip, "loop_start", 0.0),
                "loop_end": getattr(clip, "loop_end", clip.length),
            }
        except Exception as e:
            self.log_message("Error getting clip info: " + str(e))
            raise

    def _get_clip_notes(self, track_index, clip_index):
        try:
            track, clip_slot = self._clip_slot_or_raise(track_index, clip_index)
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            clip = clip_slot.clip
            if not clip.is_midi_clip:
                raise Exception("Clip is not a MIDI clip")
            raw_notes = clip.get_notes(0.0, clip.length, 0, 128)
            notes = []
            for note in raw_notes:
                notes.append({
                    "pitch": note[0],
                    "start_time": note[1],
                    "duration": note[2],
                    "velocity": note[3],
                    "mute": note[4],
                })
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "note_count": len(notes),
                "notes": notes,
            }
        except Exception as e:
            self.log_message("Error getting clip notes: " + str(e))
            raise

    def _delete_clip(self, track_index, clip_index):
        try:
            track, clip_slot = self._clip_slot_or_raise(track_index, clip_index)
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            clip_slot.delete_clip()
            return {"track_index": track_index, "clip_index": clip_index, "deleted": True}
        except Exception as e:
            self.log_message("Error deleting clip: " + str(e))
            raise

    def _set_clip_loop(self, track_index, clip_index, loop_start, loop_end, looping):
        try:
            track, clip_slot = self._clip_slot_or_raise(track_index, clip_index)
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            clip = clip_slot.clip
            loop_start = float(loop_start)
            loop_end = float(loop_end)
            if loop_end <= loop_start:
                raise ValueError("loop_end must be greater than loop_start")
            clip.loop_start = loop_start
            clip.loop_end = loop_end
            clip.looping = bool(looping)
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "loop_start": clip.loop_start,
                "loop_end": clip.loop_end,
                "looping": clip.looping,
            }
        except Exception as e:
            self.log_message("Error setting clip loop: " + str(e))
            raise
    

    def _duplicate_track(self, track_index):
        try:
            track = self._track_or_raise(track_index)
            name = track.name
            self._song.duplicate_track(track_index)
            return {
                "source_track_index": track_index,
                "new_track_index": track_index + 1,
                "source_name": name,
            }
        except Exception as e:
            self.log_message("Error duplicating track: " + str(e))
            raise

    def _routing_display(self, option):
        try:
            return str(option.display_name)
        except Exception:
            return str(option)

    def _get_track_routing(self, track_index):
        try:
            track = self._track_or_raise(track_index)
            return {
                "track_index": track_index,
                "input_routing_type": self._routing_display(track.input_routing_type),
                "input_routing_channel": self._routing_display(track.input_routing_channel),
                "output_routing_type": self._routing_display(track.output_routing_type),
                "output_routing_channel": self._routing_display(track.output_routing_channel),
            }
        except Exception as e:
            self.log_message("Error getting track routing: " + str(e))
            raise

    def _find_routing_option(self, options, identifier):
        for option in options:
            try:
                if str(option.identifier) == str(identifier):
                    return option
            except Exception:
                pass
            if self._routing_display(option).lower() == str(identifier).lower():
                return option
        raise ValueError("Routing option not found: " + str(identifier))

    def _set_track_input_routing(self, track_index, routing_type_id, routing_channel_id):
        try:
            track = self._track_or_raise(track_index)
            target_type = self._find_routing_option(
                track.available_input_routing_types, routing_type_id)
            track.available_input_routing_channels = target_type
            target_channel = self._find_routing_option(
                track.available_input_routing_channels, routing_channel_id)
            track.input_routing_type = target_type
            track.input_routing_channel = target_channel
            return self._get_track_routing(track_index)
        except Exception as e:
            self.log_message("Error setting input routing: " + str(e))
            raise

    def _set_track_output_routing(self, track_index, routing_type_id, routing_channel_id):
        try:
            track = self._track_or_raise(track_index)
            target_type = self._find_routing_option(
                track.available_output_routing_types, routing_type_id)
            track.available_output_routing_channels = target_type
            target_channel = self._find_routing_option(
                track.available_output_routing_channels, routing_channel_id)
            track.output_routing_type = target_type
            track.output_routing_channel = target_channel
            return self._get_track_routing(track_index)
        except Exception as e:
            self.log_message("Error setting output routing: " + str(e))
            raise

    def _duplicate_clip(self, track_index, clip_index):
        try:
            track, clip_slot = self._clip_slot_or_raise(track_index, clip_index)
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            before = [slot.has_clip for slot in track.clip_slots]
            track.duplicate_clip_slot(clip_index)
            new_clip_index = None
            for i, (had, has) in enumerate(zip(before, [s.has_clip for s in track.clip_slots])):
                if has and not had:
                    new_clip_index = i
                    break
            return {
                "track_index": track_index,
                "source_clip_index": clip_index,
                "new_clip_index": new_clip_index,
            }
        except Exception as e:
            self.log_message("Error duplicating clip: " + str(e))
            raise

    def _set_clip_color(self, track_index, clip_index, color_index):
        try:
            track, clip_slot = self._clip_slot_or_raise(track_index, clip_index)
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            clip_slot.clip.color_index = int(color_index)
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "color_index": clip_slot.clip.color_index,
            }
        except Exception as e:
            self.log_message("Error setting clip color: " + str(e))
            raise

    def _notes_to_live(self, notes):
        live_notes = []
        for note in notes:
            live_notes.append((
                int(note.get("pitch", 60)),
                float(note.get("start_time", 0.0)),
                float(note.get("duration", 0.25)),
                int(note.get("velocity", 100)),
                bool(note.get("mute", False)),
            ))
        return tuple(live_notes)

    def _set_clip_notes(self, track_index, clip_index, notes):
        try:
            track, clip_slot = self._clip_slot_or_raise(track_index, clip_index)
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            clip = clip_slot.clip
            if not clip.is_midi_clip:
                raise Exception("Clip is not a MIDI clip")
            clip.set_notes(self._notes_to_live(notes))
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "note_count": len(notes),
            }
        except Exception as e:
            self.log_message("Error setting clip notes: " + str(e))
            raise

    def _remove_clip_notes(
        self, track_index, clip_index, from_pitch=0, pitch_span=128, from_time=0.0, time_span=999999.0
    ):
        try:
            track, clip_slot = self._clip_slot_or_raise(track_index, clip_index)
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            clip = clip_slot.clip
            if not clip.is_midi_clip:
                raise Exception("Clip is not a MIDI clip")
            raw = clip.get_notes(0.0, clip.length, 0, 128)
            kept = []
            removed = 0
            for note in raw:
                pitch, start, duration, velocity, mute = note
                in_pitch = from_pitch <= pitch < from_pitch + pitch_span
                in_time = from_time <= start < from_time + time_span
                if in_pitch and in_time:
                    removed += 1
                else:
                    kept.append((pitch, start, duration, velocity, mute))
            clip.set_notes(tuple(kept))
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "removed_count": removed,
                "remaining_count": len(kept),
            }
        except Exception as e:
            self.log_message("Error removing clip notes: " + str(e))
            raise

    def _start_recording(self):
        try:
            self._song.record_mode = True
            if not self._song.is_playing:
                self._song.start_playing()
            return {"is_recording": self._song.record_mode, "is_playing": self._song.is_playing}
        except Exception as e:
            self.log_message("Error starting recording: " + str(e))
            raise

    def _stop_recording(self):
        try:
            self._song.record_mode = False
            return {"is_recording": self._song.record_mode}
        except Exception as e:
            self.log_message("Error stopping recording: " + str(e))
            raise

    def _set_overdub(self, overdub):
        try:
            self._song.overdub = bool(overdub)
            return {"overdub": self._song.overdub}
        except Exception as e:
            self.log_message("Error setting overdub: " + str(e))
            raise

    def _capture_midi(self, destination="auto"):
        try:
            dest_map = {"auto": 0, "session": 1, "arrangement": 2}
            if destination not in dest_map:
                raise ValueError("destination must be auto, session, or arrangement")
            if not self._song.can_capture_midi:
                raise Exception("No MIDI available to capture")
            self._song.capture_midi(dest_map[destination])
            return {"destination": destination, "captured": True}
        except Exception as e:
            self.log_message("Error capturing MIDI: " + str(e))
            raise

    def _arrangement_clip_or_raise(self, track_index, clip_index):
        track = self._track_or_raise(track_index)
        clips = list(track.arrangement_clips)
        if clip_index < 0 or clip_index >= len(clips):
            raise IndexError("Arrangement clip index out of range")
        return track, clips[clip_index]

    def _create_arrangement_clip(self, track_index, start_time, length):
        try:
            track = self._track_or_raise(track_index)
            if not track.has_midi_input:
                raise ValueError("Track %d is not a MIDI track" % track_index)
            before = len(list(track.arrangement_clips))
            track.create_midi_clip(float(start_time), float(length))
            after_clips = list(track.arrangement_clips)
            clip_index = len(after_clips) - 1
            clip = after_clips[clip_index]
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "start_time": float(clip.start_time),
                "length": float(clip.length),
                "name": clip.name,
            }
        except Exception as e:
            self.log_message("Error creating arrangement clip: " + str(e))
            raise

    def _import_audio_to_arrangement(self, track_index, path, start_time):
        try:
            if not path or not os.path.isabs(path):
                raise ValueError("Audio file path must be absolute")
            track = self._track_or_raise(track_index)
            if not track.has_audio_input:
                raise ValueError("Track %d is not an audio track" % track_index)
            before = list(track.arrangement_clips)
            track.create_audio_clip(path, float(start_time))
            after = list(track.arrangement_clips)
            new_clip = after[-1] if len(after) > len(before) else after[-1]
            clip_index = after.index(new_clip)
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "path": path,
                "start_time": float(new_clip.start_time),
                "length": float(new_clip.length),
                "name": new_clip.name,
            }
        except Exception as e:
            self.log_message("Error importing audio to arrangement: " + str(e))
            raise

    def _move_arrangement_clip(
        self, track_index, clip_index, new_start_time, new_track_index=None
    ):
        try:
            if new_track_index is None:
                new_track_index = track_index
            source_track, source_clip = self._arrangement_clip_or_raise(track_index, clip_index)
            target_track = self._track_or_raise(new_track_index)
            before = list(target_track.arrangement_clips)
            target_track.duplicate_clip_to_arrangement(source_clip, float(new_start_time))
            after = list(target_track.arrangement_clips)
            moved = after[-1] if len(after) > len(before) else after[-1]
            source_track.delete_clip(source_clip)
            return {
                "source_track_index": track_index,
                "source_clip_index": clip_index,
                "target_track_index": new_track_index,
                "start_time": float(moved.start_time),
                "name": moved.name,
            }
        except Exception as e:
            self.log_message("Error moving arrangement clip: " + str(e))
            raise

    def _get_arrangement_length(self):
        try:
            return {"song_length": float(self._song.song_length)}
        except Exception as e:
            self.log_message("Error getting arrangement length: " + str(e))
            raise

    def _set_arrangement_loop(self, start_time, end_time, enabled=True):
        try:
            start_time = float(start_time)
            end_time = float(end_time)
            if end_time <= start_time:
                raise ValueError("end_time must be greater than start_time")
            self._song.loop_start = start_time
            self._song.loop_length = end_time - start_time
            self._song.loop = bool(enabled)
            return {
                "start_time": self._song.loop_start,
                "end_time": self._song.loop_start + self._song.loop_length,
                "enabled": self._song.loop,
            }
        except Exception as e:
            self.log_message("Error setting arrangement loop: " + str(e))
            raise

    def _get_locators(self):
        try:
            locators = []
            for index, cue in enumerate(self._song.cue_points):
                locators.append({
                    "index": index,
                    "name": cue.name,
                    "time": float(cue.time),
                })
            return {"locators": locators}
        except Exception as e:
            self.log_message("Error getting locators: " + str(e))
            raise

    def _create_locator(self, time_val, name=None):
        try:
            original = self._song.current_song_time
            self._song.current_song_time = float(time_val)
            self._song.set_or_delete_cue()
            cue = None
            for candidate in self._song.cue_points:
                if abs(float(candidate.time) - float(time_val)) < 0.001:
                    cue = candidate
                    break
            if cue is None:
                raise Exception("Failed to create locator at beat %s" % time_val)
            if name:
                cue.name = name
            self._song.current_song_time = original
            index = list(self._song.cue_points).index(cue)
            return {"index": index, "name": cue.name, "time": float(cue.time)}
        except Exception as e:
            self.log_message("Error creating locator: " + str(e))
            raise

    def _delete_locator(self, locator_index):
        try:
            cues = list(self._song.cue_points)
            if locator_index < 0 or locator_index >= len(cues):
                raise IndexError("Locator index out of range")
            cue = cues[locator_index]
            original = self._song.current_song_time
            self._song.current_song_time = float(cue.time)
            self._song.set_or_delete_cue()
            self._song.current_song_time = original
            return {"deleted_index": locator_index, "name": cue.name}
        except Exception as e:
            self.log_message("Error deleting locator: " + str(e))
            raise

    def _set_locator_name(self, locator_index, name):
        try:
            cues = list(self._song.cue_points)
            if locator_index < 0 or locator_index >= len(cues):
                raise IndexError("Locator index out of range")
            cues[locator_index].name = name
            return {"index": locator_index, "name": name}
        except Exception as e:
            self.log_message("Error setting locator name: " + str(e))
            raise

    def _get_take_lanes(self, track_index):
        try:
            track = self._track_or_raise(track_index)
            lanes = []
            if hasattr(track, "take_lanes"):
                for index, lane in enumerate(track.take_lanes):
                    lanes.append({"index": index, "name": lane.name})
            return {"track_index": track_index, "take_lanes": lanes}
        except Exception as e:
            self.log_message("Error getting take lanes: " + str(e))
            raise

    def _create_take_lane(self, track_index, name=None):
        try:
            track = self._track_or_raise(track_index)
            if not hasattr(track, "create_take_lane"):
                raise Exception("Take lanes not supported in this Live version")
            before = len(list(track.take_lanes))
            track.create_take_lane()
            lane = track.take_lanes[-1]
            if name:
                lane.name = name
            return {"track_index": track_index, "take_lane_index": before, "name": lane.name}
        except Exception as e:
            self.log_message("Error creating take lane: " + str(e))
            raise

    def _get_groove_pool(self):
        try:
            grooves = []
            pool = self._song.groove_pool
            for index, groove in enumerate(pool.grooves):
                grooves.append({
                    "index": index,
                    "name": groove.name,
                    "quantization_amount": float(groove.quantization_amount),
                    "timing_amount": float(groove.timing_amount),
                    "random_amount": float(groove.random_amount),
                    "velocity_amount": float(groove.velocity_amount),
                })
            return {"grooves": grooves}
        except Exception as e:
            self.log_message("Error getting groove pool: " + str(e))
            raise

    def _apply_groove(self, track_index, clip_index, groove_index):
        try:
            track, clip_slot = self._clip_slot_or_raise(track_index, clip_index)
            if not clip_slot.has_clip:
                raise Exception("No clip in slot")
            grooves = list(self._song.groove_pool.grooves)
            if groove_index < 0 or groove_index >= len(grooves):
                raise IndexError("Groove index out of range")
            clip_slot.clip.groove = grooves[groove_index]
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "groove_index": groove_index,
                "groove_name": grooves[groove_index].name,
            }
        except Exception as e:
            self.log_message("Error applying groove: " + str(e))
            raise

    def _search_browser(self, query, category_type="all", max_results=25, loadable_only=False):
        try:
            app = self.application()
            if not app or not hasattr(app, "browser"):
                raise RuntimeError("Browser is not available")
            browser = app.browser
            results = []
            query_lower = (query or "").strip().lower()
            if not query_lower:
                raise ValueError("query is required")
            max_results = max(1, min(100, int(max_results)))

            def walk(item, path, depth):
                if depth > 14 or len(results) >= max_results:
                    return
                name = str(getattr(item, "name", "") or "")
                is_loadable = bool(getattr(item, "is_loadable", False))
                if loadable_only and not is_loadable:
                    pass
                elif query_lower in name.lower() or query_lower in path.lower():
                    source = None
                    if hasattr(item, "source"):
                        try:
                            source = str(item.source)
                        except Exception:
                            pass
                    results.append({
                        "name": name,
                        "path": path,
                        "uri": getattr(item, "uri", None),
                        "is_loadable": is_loadable,
                        "is_device": bool(getattr(item, "is_device", False)),
                        "source": source,
                    })
                if hasattr(item, "children") and item.children:
                    for child in item.children:
                        child_name = str(getattr(child, "name", "") or "")
                        walk(child, path + "/" + child_name, depth + 1)

            for root_name, root_item in self._browser_category_roots(browser):
                if category_type != "all" and category_type != root_name:
                    continue
                walk(root_item, root_name, 0)

            return {
                "query": query,
                "category": category_type,
                "max_results": max_results,
                "loadable_only": bool(loadable_only),
                "items": results,
            }
        except Exception as e:
            self.log_message("Error searching browser: " + str(e))
            raise

    def _session_clip_or_raise(self, track_index, clip_index):
        track, clip_slot = self._clip_slot_or_raise(track_index, clip_index)
        if not clip_slot.has_clip:
            raise Exception("No clip in slot")
        return clip_slot.clip

    def _audio_clip_or_raise(self, track_index, clip_index):
        clip = self._session_clip_or_raise(track_index, clip_index)
        if not clip.is_audio_clip:
            raise Exception("Clip is not an audio clip")
        return clip

    def _midi_arrangement_clip_or_raise(self, track_index, clip_index):
        track, clip = self._arrangement_clip_or_raise(track_index, clip_index)
        if not clip.is_midi_clip:
            raise Exception("Arrangement clip is not a MIDI clip")
        return track, clip

    def _set_clip_gain(self, track_index, clip_index, gain):
        try:
            clip = self._audio_clip_or_raise(track_index, clip_index)
            gain = max(0.0, min(1.0, float(gain)))
            clip.gain = gain
            return {"track_index": track_index, "clip_index": clip_index, "gain": float(clip.gain)}
        except Exception as e:
            self.log_message("Error setting clip gain: " + str(e))
            raise

    def _set_clip_pitch(self, track_index, clip_index, semitones):
        try:
            clip = self._audio_clip_or_raise(track_index, clip_index)
            semitones = max(-48, min(48, int(semitones)))
            clip.pitch_coarse = semitones
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "semitones": int(clip.pitch_coarse),
            }
        except Exception as e:
            self.log_message("Error setting clip pitch: " + str(e))
            raise

    def _set_clip_warp_mode(self, track_index, clip_index, warp_mode):
        try:
            clip = self._audio_clip_or_raise(track_index, clip_index)
            if hasattr(clip, "warping") and not clip.warping:
                clip.warping = True
            clip.warp_mode = int(warp_mode)
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "warp_mode": int(clip.warp_mode),
            }
        except Exception as e:
            self.log_message("Error setting clip warp mode: " + str(e))
            raise

    def _automation_envelope(self, clip, parameter):
        get_envelope = getattr(clip, "automation_envelope", None)
        if callable(get_envelope):
            return get_envelope(parameter)
        return None

    def _create_automation_envelope(self, clip, parameter):
        envelope = self._automation_envelope(clip, parameter)
        if envelope is not None:
            return envelope
        create = getattr(clip, "create_automation_envelope", None)
        if not callable(create):
            raise Exception("Clip automation not supported in this Live version")
        return create(parameter) or self._automation_envelope(clip, parameter)

    def _get_clip_automation(self, track_index, clip_index, device_index, parameter_index):
        try:
            track = self._track_or_raise(track_index)
            clip = self._session_clip_or_raise(track_index, clip_index)
            device = self._device_or_raise(track_index, device_index)
            parameters = list(device.parameters)
            if parameter_index < 0 or parameter_index >= len(parameters):
                raise IndexError("Parameter index out of range")
            parameter = parameters[parameter_index]
            envelope = self._automation_envelope(clip, parameter)
            points = []
            if envelope is not None and hasattr(envelope, "events_in_range"):
                for start, end in [
                    (clip.loop_start, clip.loop_end),
                    (0.0, clip.length),
                ]:
                    try:
                        for event in envelope.events_in_range(start, end):
                            points.append({
                                "time": float(event.time),
                                "value": float(event.value),
                                "step_length": float(getattr(event, "step_length", 0.0)),
                            })
                        break
                    except Exception:
                        continue
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "device_index": device_index,
                "parameter_index": parameter_index,
                "device_name": device.name,
                "parameter_name": parameter.name,
                "points": points,
            }
        except Exception as e:
            self.log_message("Error getting clip automation: " + str(e))
            raise

    def _set_clip_automation(
        self, track_index, clip_index, device_index, parameter_index, points
    ):
        try:
            track = self._track_or_raise(track_index)
            clip = self._session_clip_or_raise(track_index, clip_index)
            device = self._device_or_raise(track_index, device_index)
            parameters = list(device.parameters)
            parameter = parameters[parameter_index]
            clear = getattr(clip, "clear_envelope", None)
            if callable(clear):
                clear(parameter)
            envelope = self._create_automation_envelope(clip, parameter)
            if envelope is None:
                raise Exception("Could not create automation envelope")
            for point in points:
                envelope.insert_step(
                    float(point.get("time", 0.0)),
                    float(point.get("step_length", 0.0)),
                    float(point.get("value", 0.0)),
                )
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "parameter_index": parameter_index,
                "point_count": len(points),
            }
        except Exception as e:
            self.log_message("Error setting clip automation: " + str(e))
            raise

    def _get_arrangement_clip_notes(self, track_index, clip_index):
        try:
            track, clip = self._midi_arrangement_clip_or_raise(track_index, clip_index)
            raw = clip.get_notes(0.0, clip.length, 0, 128)
            notes = [{
                "pitch": n[0], "start_time": n[1], "duration": n[2],
                "velocity": n[3], "mute": n[4],
            } for n in raw]
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "note_count": len(notes),
                "notes": notes,
            }
        except Exception as e:
            self.log_message("Error getting arrangement clip notes: " + str(e))
            raise

    def _add_notes_to_arrangement_clip(self, track_index, clip_index, notes):
        try:
            track, clip = self._midi_arrangement_clip_or_raise(track_index, clip_index)
            existing = clip.get_notes(0.0, clip.length, 0, 128)
            merged = list(existing) + [
                (
                    int(n.get("pitch", 60)),
                    float(n.get("start_time", 0.0)),
                    float(n.get("duration", 0.25)),
                    int(n.get("velocity", 100)),
                    bool(n.get("mute", False)),
                )
                for n in notes
            ]
            clip.set_notes(tuple(merged))
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "added_count": len(notes),
                "total_count": len(merged),
            }
        except Exception as e:
            self.log_message("Error adding arrangement clip notes: " + str(e))
            raise

    def _set_arrangement_clip_notes(self, track_index, clip_index, notes):
        try:
            track, clip = self._midi_arrangement_clip_or_raise(track_index, clip_index)
            clip.set_notes(self._notes_to_live(notes))
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "note_count": len(notes),
            }
        except Exception as e:
            self.log_message("Error setting arrangement clip notes: " + str(e))
            raise

    def _remove_arrangement_clip_notes(
        self, track_index, clip_index, from_pitch=0, pitch_span=128,
        from_time=0.0, time_span=999999.0,
    ):
        try:
            track, clip = self._midi_arrangement_clip_or_raise(track_index, clip_index)
            raw = clip.get_notes(0.0, clip.length, 0, 128)
            kept, removed = [], 0
            for note in raw:
                pitch, start, duration, velocity, mute = note
                if (from_pitch <= pitch < from_pitch + pitch_span and
                        from_time <= start < from_time + time_span):
                    removed += 1
                else:
                    kept.append(note)
            clip.set_notes(tuple(kept))
            return {
                "track_index": track_index,
                "clip_index": clip_index,
                "removed_count": removed,
                "remaining_count": len(kept),
            }
        except Exception as e:
            self.log_message("Error removing arrangement clip notes: " + str(e))
            raise

    def _import_audio_to_take_lane(self, track_index, take_lane_index, path, start_time):
        try:
            if not path or not os.path.isabs(path):
                raise ValueError("Audio file path must be absolute")
            track = self._track_or_raise(track_index)
            if not track.has_audio_input:
                raise ValueError("Track %d is not an audio track" % track_index)
            if not hasattr(track, "take_lanes"):
                raise Exception("Take lanes not supported")
            lanes = list(track.take_lanes)
            if take_lane_index < 0 or take_lane_index >= len(lanes):
                raise IndexError("Take lane index out of range")
            lane = lanes[take_lane_index]
            before = list(lane.arrangement_clips)
            lane.create_audio_clip(path, float(start_time))
            after = list(lane.arrangement_clips)
            clip = after[-1] if len(after) > len(before) else after[-1]
            return {
                "track_index": track_index,
                "take_lane_index": take_lane_index,
                "path": path,
                "start_time": float(clip.start_time),
                "length": float(clip.length),
                "name": clip.name,
            }
        except Exception as e:
            self.log_message("Error importing audio to take lane: " + str(e))
            raise

    def _load_effect(self, track_index, uri):
        try:
            return self._load_browser_item(track_index, uri)
        except Exception as e:
            self.log_message("Error loading effect: " + str(e))
            raise

    # ── Phase 4: devices, racks, presets, M4L introspection ────────────────

    def _serialize_parameter(self, parameter, parameter_index):
        info = {
            "index": parameter_index,
            "name": str(parameter.name),
            "value": float(parameter.value),
            "min": float(parameter.min),
            "max": float(parameter.max),
            "is_quantized": bool(parameter.is_quantized),
        }
        for attr in ("original_name", "display_value", "default_value", "is_enabled", "automation_state", "state"):
            if hasattr(parameter, attr):
                try:
                    val = getattr(parameter, attr)
                    if attr in ("display_value", "default_value", "value"):
                        info[attr] = float(val)
                    elif attr in ("is_enabled", "is_quantized"):
                        info[attr] = bool(val)
                    else:
                        info[attr] = val if isinstance(val, (int, float, bool)) else str(val)
                except Exception:
                    pass
        if parameter.is_quantized and hasattr(parameter, "value_items"):
            try:
                info["value_items"] = [str(v) for v in parameter.value_items]
            except Exception:
                pass
        if hasattr(parameter, "str_for_value"):
            try:
                info["display_string"] = str(parameter.str_for_value(parameter.value))
            except Exception:
                pass
        return info

    def _rack_or_raise(self, track_index, device_index):
        device = self._device_or_raise(track_index, device_index)
        if not device.can_have_chains:
            raise ValueError("Device is not a rack")
        return device

    def _chain_or_raise(self, track_index, rack_index, chain_index):
        rack = self._rack_or_raise(track_index, rack_index)
        chains = list(rack.chains)
        if chain_index < 0 or chain_index >= len(chains):
            raise IndexError("Chain index out of range")
        return rack, chains[chain_index]

    def _chain_device_or_raise(self, track_index, rack_index, chain_index, chain_device_index):
        rack, chain = self._chain_or_raise(track_index, rack_index, chain_index)
        devices = list(chain.devices)
        if chain_device_index < 0 or chain_device_index >= len(devices):
            raise IndexError("Chain device index out of range")
        return rack, chain, devices[chain_device_index]

    def _rack_macro_parameters(self, rack):
        macros = []
        for index, parameter in enumerate(rack.parameters):
            original = str(getattr(parameter, "original_name", parameter.name) or "")
            name = str(parameter.name or "")
            if original.startswith("Macro ") or name.startswith("Macro "):
                macros.append((index, parameter))
        return macros

    def _browser_category_roots(self, browser):
        roots = []
        for attr in (
            "user_library", "packs", "instruments", "sounds", "drums",
            "audio_effects", "midi_effects", "max_for_live", "plugins",
            "samples", "clips", "current_project",
        ):
            if hasattr(browser, attr):
                try:
                    roots.append((attr, getattr(browser, attr)))
                except Exception:
                    pass
        return roots

    def _normalize_filesystem_path(self, path):
        return os.path.normpath(os.path.expanduser(path or ""))

    def _find_browser_item_by_path(self, browser, file_path, max_depth=14):
        target = self._normalize_filesystem_path(file_path)
        target_base = os.path.basename(target).lower()

        def matches(item):
            if not getattr(item, "is_loadable", False):
                return False
            if hasattr(item, "source"):
                try:
                    source = self._normalize_filesystem_path(str(item.source))
                    if source == target:
                        return True
                except Exception:
                    pass
            name = str(getattr(item, "name", "") or "").lower()
            if name == target_base or name == target_base.rsplit(".", 1)[0]:
                return True
            return False

        def walk(item, depth, path_parts):
            if depth > max_depth:
                return None
            if matches(item):
                return item
            if hasattr(item, "children") and item.children:
                for child in item.children:
                    child_name = str(getattr(child, "name", "") or "")
                    found = walk(child, depth + 1, path_parts + [child_name])
                    if found:
                        return found
            return None

        for root_name, root_item in self._browser_category_roots(browser):
            found = walk(root_item, 0, [root_name])
            if found:
                return found
        return None

    def _find_browser_by_path(self, path, max_results=10):
        try:
            app = self.application()
            if not app or not hasattr(app, "browser"):
                raise RuntimeError("Browser is not available")
            browser = app.browser
            target = self._normalize_filesystem_path(path)
            target_base = os.path.basename(target).lower()
            target_lower = target.lower()
            results = []

            def walk(item, depth, browser_path):
                if depth > 14 or len(results) >= max_results:
                    return
                name = str(getattr(item, "name", "") or "")
                uri = getattr(item, "uri", None)
                source = None
                if hasattr(item, "source"):
                    try:
                        source = str(item.source)
                    except Exception:
                        pass
                source_norm = self._normalize_filesystem_path(source) if source else ""
                matched = False
                if target_base and name.lower() == target_base:
                    matched = True
                elif source_norm and (source_norm == target or source_norm.lower().endswith(target_lower)):
                    matched = True
                elif target_lower in browser_path.lower():
                    matched = True
                if matched:
                    results.append({
                        "name": name,
                        "path": browser_path,
                        "uri": uri,
                        "source": source,
                        "is_loadable": bool(getattr(item, "is_loadable", False)),
                        "is_device": bool(getattr(item, "is_device", False)),
                    })
                if hasattr(item, "children") and item.children:
                    for child in item.children:
                        child_name = str(getattr(child, "name", "") or "")
                        walk(child, depth + 1, browser_path + "/" + child_name)

            for root_name, root_item in self._browser_category_roots(browser):
                walk(root_item, 0, root_name)

            return {"path": path, "items": results}
        except Exception as e:
            self.log_message("Error finding browser by path: " + str(e))
            raise

    def _load_preset_by_path(self, track_index, path):
        try:
            track = self._track_or_raise(track_index)
            app = self.application()
            item = self._find_browser_item_by_path(app.browser, path)
            resolved_via = "path"
            if not item:
                matches = self._find_browser_by_path(path, max_results=10).get("items", [])
                target_base = os.path.basename(self._normalize_filesystem_path(path)).lower()
                for candidate in matches:
                    if not candidate.get("is_loadable") or not candidate.get("uri"):
                        continue
                    name = str(candidate.get("name", "")).lower()
                    if name == target_base or name == target_base.rsplit(".", 1)[0]:
                        item = self._find_browser_item_by_uri(app.browser, candidate["uri"])
                        if item:
                            resolved_via = "filename"
                            break
            if not item:
                raise ValueError("Preset not found in browser for path: " + str(path))
            devices_before = len(list(track.devices))
            self._song.view.selected_track = track
            app.browser.load_item(item)
            devices_after = len(list(track.devices))
            return {
                "loaded": True,
                "path": path,
                "resolved_via": resolved_via,
                "item_name": str(item.name),
                "uri": getattr(item, "uri", None),
                "track_index": track_index,
                "track_name": track.name,
                "devices_before": devices_before,
                "devices_after": devices_after,
            }
        except Exception as e:
            self.log_message("Error loading preset by path: " + str(e))
            raise

    def _insert_device(self, track_index, device_name, position=-1, rack_index=None, chain_index=None):
        try:
            if not device_name:
                raise ValueError("device_name is required")
            track = self._track_or_raise(track_index)
            if rack_index is not None and chain_index is not None:
                rack, chain = self._chain_or_raise(track_index, rack_index, chain_index)
                if not hasattr(chain, "insert_device"):
                    raise RuntimeError("chain.insert_device requires Live 12.3+")
                before = len(list(chain.devices))
                if position is None or int(position) < 0:
                    chain.insert_device(device_name)
                else:
                    chain.insert_device(device_name, int(position))
                after = list(chain.devices)
                return {
                    "track_index": track_index,
                    "rack_index": rack_index,
                    "chain_index": chain_index,
                    "device_name": device_name,
                    "position": position,
                    "devices_before": before,
                    "devices_after": len(after),
                    "new_device_name": after[-1].name if len(after) > before else None,
                }
            if not hasattr(track, "insert_device"):
                raise RuntimeError("track.insert_device requires Live 12.3+")
            before = len(list(track.devices))
            if position is None or int(position) < 0:
                track.insert_device(device_name)
            else:
                track.insert_device(device_name, int(position))
            after = list(track.devices)
            return {
                "track_index": track_index,
                "device_name": device_name,
                "position": position,
                "devices_before": before,
                "devices_after": len(after),
                "new_device_name": after[-1].name if len(after) > before else None,
            }
        except Exception as e:
            self.log_message("Error inserting device: " + str(e))
            raise

    def _delete_device(self, track_index, device_index):
        try:
            track = self._track_or_raise(track_index)
            devices = list(track.devices)
            if device_index < 0 or device_index >= len(devices):
                raise IndexError("Device index out of range")
            name = devices[device_index].name
            track.delete_device(device_index)
            return {
                "track_index": track_index,
                "deleted_index": device_index,
                "name": name,
                "devices_remaining": len(list(track.devices)),
            }
        except Exception as e:
            self.log_message("Error deleting device: " + str(e))
            raise

    def _get_device_info(self, track_index, device_index):
        try:
            device = self._device_or_raise(track_index, device_index)
            info = {
                "track_index": track_index,
                "device_index": device_index,
                "name": str(device.name),
                "class_name": str(device.class_name),
                "class_display_name": str(getattr(device, "class_display_name", device.name)),
                "type": self._get_device_type(device),
                "can_have_chains": bool(device.can_have_chains),
                "can_have_drum_pads": bool(getattr(device, "can_have_drum_pads", False)),
                "parameter_count": len(list(device.parameters)),
                "is_active": bool(getattr(device, "is_active", True)),
            }
            if device.can_have_chains:
                rack = device
                info.update({
                    "chain_count": len(list(rack.chains)),
                    "return_chain_count": len(list(rack.return_chains)),
                    "visible_macro_count": int(getattr(rack, "visible_macro_count", 0)),
                    "has_macro_mappings": bool(getattr(rack, "has_macro_mappings", False)),
                    "has_drum_pads": bool(getattr(rack, "has_drum_pads", False)),
                    "variation_count": int(getattr(rack, "variation_count", 0)),
                })
            if str(device.class_name) == "PluginDevice" or "MxDevice" in str(device.class_name):
                info["is_plugin_or_m4l"] = True
            return info
        except Exception as e:
            self.log_message("Error getting device info: " + str(e))
            raise

    def _build_device_tree_node(self, device, depth=0, path=""):
        node = {
            "path": path,
            "depth": depth,
            "name": str(device.name),
            "class_name": str(device.class_name),
            "class_display_name": str(getattr(device, "class_display_name", device.name)),
            "type": self._get_device_type(device),
            "parameter_count": len(list(device.parameters)),
            "can_have_chains": bool(device.can_have_chains),
        }
        children = []
        if device.can_have_chains:
            for chain_index, chain in enumerate(device.chains):
                for dev_index, nested in enumerate(chain.devices):
                    child_path = "%s/%d/%d" % (path, chain_index, dev_index)
                    children.append(self._build_device_tree_node(nested, depth + 1, child_path))
        node["children"] = children
        return node

    def _get_device_tree(self, track_index, device_index):
        try:
            device = self._device_or_raise(track_index, device_index)
            return {
                "track_index": track_index,
                "device_index": device_index,
                "tree": self._build_device_tree_node(device, 0, str(device_index)),
            }
        except Exception as e:
            self.log_message("Error getting device tree: " + str(e))
            raise

    def _get_device_parameters_detailed(
        self, track_index, device_index, rack_index=None, chain_index=None, chain_device_index=None
    ):
        try:
            if rack_index is not None and chain_index is not None and chain_device_index is not None:
                _, _, device = self._chain_device_or_raise(
                    track_index, rack_index, chain_index, chain_device_index)
                resolved = {
                    "rack_index": rack_index,
                    "chain_index": chain_index,
                    "chain_device_index": chain_device_index,
                }
            else:
                device = self._device_or_raise(track_index, device_index)
                resolved = {"device_index": device_index}
            parameters = []
            for index, parameter in enumerate(device.parameters):
                parameters.append(self._serialize_parameter(parameter, index))
            return {
                "track_index": track_index,
                "device_name": str(device.name),
                "class_name": str(device.class_name),
                "class_display_name": str(getattr(device, "class_display_name", device.name)),
                "parameters": parameters,
                **resolved,
            }
        except Exception as e:
            self.log_message("Error getting detailed device parameters: " + str(e))
            raise

    def _set_device_parameter_by_name(self, track_index, device_index, parameter_name, value):
        try:
            device = self._device_or_raise(track_index, device_index)
            target = (parameter_name or "").strip().lower()
            if not target:
                raise ValueError("parameter_name is required")
            for index, parameter in enumerate(device.parameters):
                names = [str(parameter.name).lower()]
                if hasattr(parameter, "original_name"):
                    names.append(str(parameter.original_name).lower())
                if target in names:
                    return self._set_device_parameter(track_index, device_index, index, value)
            raise ValueError("Parameter not found: " + parameter_name)
        except Exception as e:
            self.log_message("Error setting device parameter by name: " + str(e))
            raise

    def _set_chain_device_parameter(
        self, track_index, rack_index, chain_index, chain_device_index,
        parameter_index=None, value=0.0, parameter_name=None
    ):
        try:
            _, _, device = self._chain_device_or_raise(
                track_index, rack_index, chain_index, chain_device_index)
            if parameter_name:
                target = parameter_name.strip().lower()
                for index, parameter in enumerate(device.parameters):
                    names = [str(parameter.name).lower()]
                    if hasattr(parameter, "original_name"):
                        names.append(str(parameter.original_name).lower())
                    if target in names:
                        parameter_index = index
                        break
                if parameter_index is None:
                    raise ValueError("Parameter not found in chain device: " + parameter_name)
            parameters = list(device.parameters)
            if parameter_index < 0 or parameter_index >= len(parameters):
                raise IndexError("Parameter index out of range")
            parameter = parameters[parameter_index]
            value = float(value)
            if value < parameter.min or value > parameter.max:
                raise ValueError(
                    "Value must be between %s and %s" % (parameter.min, parameter.max))
            parameter.value = value
            return {
                "track_index": track_index,
                "rack_index": rack_index,
                "chain_index": chain_index,
                "chain_device_index": chain_device_index,
                "device_name": str(device.name),
                "parameter_index": parameter_index,
                "parameter_name": str(parameter.name),
                "value": float(parameter.value),
            }
        except Exception as e:
            self.log_message("Error setting chain device parameter: " + str(e))
            raise

    def _get_rack_info(self, track_index, device_index):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            return {
                "track_index": track_index,
                "device_index": device_index,
                "name": str(rack.name),
                "chain_count": len(list(rack.chains)),
                "return_chain_count": len(list(rack.return_chains)),
                "visible_macro_count": int(getattr(rack, "visible_macro_count", 0)),
                "has_macro_mappings": bool(getattr(rack, "has_macro_mappings", False)),
                "has_drum_pads": bool(getattr(rack, "has_drum_pads", False)),
                "variation_count": int(getattr(rack, "variation_count", 0)),
                "selected_variation_index": int(getattr(rack, "selected_variation_index", -1)),
                "can_show_chains": bool(getattr(rack, "can_show_chains", False)),
                "is_showing_chains": bool(getattr(rack, "is_showing_chains", False)),
            }
        except Exception as e:
            self.log_message("Error getting rack info: " + str(e))
            raise

    def _get_rack_macros(self, track_index, device_index):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            macros = []
            for macro_index, (parameter_index, parameter) in enumerate(self._rack_macro_parameters(rack)):
                macros.append({
                    "macro_index": macro_index,
                    "parameter_index": parameter_index,
                    "name": str(parameter.name),
                    "original_name": str(getattr(parameter, "original_name", parameter.name)),
                    "value": float(parameter.value),
                    "min": float(parameter.min),
                    "max": float(parameter.max),
                    "is_enabled": bool(getattr(parameter, "is_enabled", True)),
                })
            return {
                "track_index": track_index,
                "device_index": device_index,
                "visible_macro_count": int(getattr(rack, "visible_macro_count", len(macros))),
                "has_macro_mappings": bool(getattr(rack, "has_macro_mappings", False)),
                "macros": macros,
            }
        except Exception as e:
            self.log_message("Error getting rack macros: " + str(e))
            raise

    def _get_macro_mappings(self, track_index, device_index):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            mappings = []
            macro_params = self._rack_macro_parameters(rack)
            for macro_index, (parameter_index, parameter) in enumerate(macro_params):
                original = str(getattr(parameter, "original_name", parameter.name))
                name = str(parameter.name)
                mapped_to = None
                if original.startswith("Macro ") and name != original:
                    mapped_to = name
                mappings.append({
                    "macro_index": macro_index,
                    "parameter_index": parameter_index,
                    "macro_label": name,
                    "original_name": original,
                    "mapped_to": mapped_to,
                    "value": float(parameter.value),
                    "has_mapping": mapped_to is not None,
                })
            controlled = []
            for chain_index, chain in enumerate(rack.chains):
                for dev_index, nested in enumerate(chain.devices):
                    for param_index, param in enumerate(nested.parameters):
                        if hasattr(param, "is_enabled") and not param.is_enabled:
                            controlled.append({
                                "chain_index": chain_index,
                                "chain_device_index": dev_index,
                                "device_name": str(nested.name),
                                "parameter_index": param_index,
                                "parameter_name": str(param.name),
                                "original_name": str(getattr(param, "original_name", param.name)),
                                "value": float(param.value),
                            })
            return {
                "track_index": track_index,
                "device_index": device_index,
                "has_macro_mappings": bool(getattr(rack, "has_macro_mappings", False)),
                "note": "LOM cannot create new macro mappings programmatically; load pre-mapped .adg/.adv presets instead.",
                "macros": mappings,
                "macro_controlled_parameters": controlled,
            }
        except Exception as e:
            self.log_message("Error getting macro mappings: " + str(e))
            raise

    def _set_rack_macro(self, track_index, device_index, macro_index, value):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            macros = self._rack_macro_parameters(rack)
            if macro_index < 0 or macro_index >= len(macros):
                raise IndexError("Macro index out of range")
            parameter_index, parameter = macros[macro_index]
            value = float(value)
            if value < parameter.min or value > parameter.max:
                raise ValueError(
                    "Value must be between %s and %s" % (parameter.min, parameter.max))
            parameter.value = value
            return {
                "track_index": track_index,
                "device_index": device_index,
                "macro_index": macro_index,
                "parameter_index": parameter_index,
                "name": str(parameter.name),
                "value": float(parameter.value),
            }
        except Exception as e:
            self.log_message("Error setting rack macro: " + str(e))
            raise

    def _add_rack_macro(self, track_index, device_index):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            if not hasattr(rack, "add_macro"):
                raise RuntimeError("add_macro requires Live 11+")
            before = int(getattr(rack, "visible_macro_count", 0))
            rack.add_macro()
            after = int(getattr(rack, "visible_macro_count", before + 1))
            return {"visible_macro_count": after}
        except Exception as e:
            self.log_message("Error adding rack macro: " + str(e))
            raise

    def _remove_rack_macro(self, track_index, device_index):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            if not hasattr(rack, "remove_macro"):
                raise RuntimeError("remove_macro requires Live 11+")
            before = int(getattr(rack, "visible_macro_count", 0))
            rack.remove_macro()
            after = int(getattr(rack, "visible_macro_count", max(0, before - 1)))
            return {"visible_macro_count": after}
        except Exception as e:
            self.log_message("Error removing rack macro: " + str(e))
            raise

    def _set_rack_visible_macros(self, track_index, device_index, count):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            count = max(1, min(16, int(count)))
            if not hasattr(rack, "add_macro") or not hasattr(rack, "remove_macro"):
                raise RuntimeError("Macro count control requires Live 11+")
            current = int(getattr(rack, "visible_macro_count", 8))
            while current < count:
                rack.add_macro()
                current = int(getattr(rack, "visible_macro_count", current + 1))
            while current > count:
                rack.remove_macro()
                current = int(getattr(rack, "visible_macro_count", current - 1))
            return {"visible_macro_count": int(getattr(rack, "visible_macro_count", count))}
        except Exception as e:
            self.log_message("Error setting rack visible macros: " + str(e))
            raise

    def _randomize_rack_macros(self, track_index, device_index):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            if not hasattr(rack, "randomize_macros"):
                raise RuntimeError("randomize_macros requires Live 11+")
            rack.randomize_macros()
            return self._get_rack_macros(track_index, device_index)
        except Exception as e:
            self.log_message("Error randomizing rack macros: " + str(e))
            raise

    def _get_rack_variations(self, track_index, device_index):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            return {
                "variation_count": int(getattr(rack, "variation_count", 0)),
                "selected_variation_index": int(getattr(rack, "selected_variation_index", -1)),
                "visible_macro_count": int(getattr(rack, "visible_macro_count", 0)),
            }
        except Exception as e:
            self.log_message("Error getting rack variations: " + str(e))
            raise

    def _store_rack_variation(self, track_index, device_index):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            if not hasattr(rack, "store_variation"):
                raise RuntimeError("store_variation requires Live 11+")
            rack.store_variation()
            return self._get_rack_variations(track_index, device_index)
        except Exception as e:
            self.log_message("Error storing rack variation: " + str(e))
            raise

    def _recall_rack_variation(self, track_index, device_index, variation_index):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            if not hasattr(rack, "recall_selected_variation"):
                raise RuntimeError("recall_selected_variation requires Live 11+")
            rack.selected_variation_index = int(variation_index)
            rack.recall_selected_variation()
            return self._get_rack_variations(track_index, device_index)
        except Exception as e:
            self.log_message("Error recalling rack variation: " + str(e))
            raise

    def _delete_rack_variation(self, track_index, device_index, variation_index):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            if not hasattr(rack, "delete_selected_variation"):
                raise RuntimeError("delete_selected_variation requires Live 11+")
            rack.selected_variation_index = int(variation_index)
            rack.delete_selected_variation()
            return self._get_rack_variations(track_index, device_index)
        except Exception as e:
            self.log_message("Error deleting rack variation: " + str(e))
            raise

    def _insert_rack_chain(self, track_index, device_index, position=-1):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            if not hasattr(rack, "insert_chain"):
                raise RuntimeError("insert_chain requires Live 12.3+")
            before = len(list(rack.chains))
            if position is None or int(position) < 0:
                rack.insert_chain()
            else:
                rack.insert_chain(int(position))
            after = list(rack.chains)
            return {
                "chain_count": len(after),
                "new_chain_index": len(after) - 1 if len(after) > before else None,
                "new_chain_name": after[-1].name if len(after) > before else None,
            }
        except Exception as e:
            self.log_message("Error inserting rack chain: " + str(e))
            raise

    def _get_rack_chains(self, track_index, device_index):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            chains = []
            for chain_index, chain in enumerate(rack.chains):
                mixer = chain.mixer_device
                entry = {
                    "chain_index": chain_index,
                    "name": str(chain.name),
                    "mute": bool(chain.mute),
                    "solo": bool(chain.solo),
                    "device_count": len(list(chain.devices)),
                    "devices": [str(d.name) for d in chain.devices],
                }
                if hasattr(mixer, "volume"):
                    entry["volume"] = float(mixer.volume.value)
                if hasattr(mixer, "panning"):
                    entry["pan"] = float(mixer.panning.value)
                if hasattr(chain, "in_note"):
                    entry["in_note"] = int(chain.in_note)
                chains.append(entry)
            return {
                "track_index": track_index,
                "device_index": device_index,
                "chains": chains,
            }
        except Exception as e:
            self.log_message("Error getting rack chains: " + str(e))
            raise

    def _set_chain_name(self, track_index, device_index, chain_index, name):
        try:
            _, chain = self._chain_or_raise(track_index, device_index, chain_index)
            chain.name = name
            return {
                "chain_index": chain_index,
                "name": str(chain.name),
            }
        except Exception as e:
            self.log_message("Error setting chain name: " + str(e))
            raise

    def _set_chain_volume(self, track_index, device_index, chain_index, volume=None, pan=None, mute=None, solo=None):
        try:
            _, chain = self._chain_or_raise(track_index, device_index, chain_index)
            result = {"chain_index": chain_index}
            if mute is not None:
                chain.mute = bool(mute)
                result["mute"] = bool(chain.mute)
            if solo is not None:
                chain.solo = bool(solo)
                result["solo"] = bool(chain.solo)
            mixer = chain.mixer_device
            if volume is not None and hasattr(mixer, "volume"):
                mixer.volume.value = max(0.0, min(1.0, float(volume)))
                result["volume"] = float(mixer.volume.value)
            if pan is not None and hasattr(mixer, "panning"):
                mixer.panning.value = max(-1.0, min(1.0, float(pan)))
                result["pan"] = float(mixer.panning.value)
            return result
        except Exception as e:
            self.log_message("Error setting chain volume: " + str(e))
            raise

    def _set_drum_chain_note(self, track_index, device_index, chain_index, note):
        try:
            rack = self._rack_or_raise(track_index, device_index)
            if not getattr(rack, "has_drum_pads", False):
                raise ValueError("Device is not a Drum Rack")
            _, chain = self._chain_or_raise(track_index, device_index, chain_index)
            if not hasattr(chain, "in_note"):
                raise RuntimeError("Drum chain in_note requires Live 12.3+")
            chain.in_note = int(note)
            return {
                "chain_index": chain_index,
                "in_note": int(chain.in_note),
            }
        except Exception as e:
            self.log_message("Error setting drum chain note: " + str(e))
            raise

    def _get_master_info(self):
        try:
            mixer = self._song.master_track.mixer_device
            return {
                "name": self._song.master_track.name,
                "volume": float(mixer.volume.value),
                "pan": float(mixer.panning.value),
            }
        except Exception as e:
            self.log_message("Error getting master info: " + str(e))
            raise
    # ── Arrangement view implementations ──────────────────────────────────────

    def _switch_to_arrangement_view(self):
        """Switch Ableton's main window to the Arrangement view"""
        try:
            self.application().view.show_view("Arranger")
            return {"view": "Arranger"}
        except Exception as e:
            self.log_message("Error switching to arrangement view: " + str(e))
            raise

    def _set_current_song_time(self, time_val):
        """Move the arrangement playhead to a position in beats"""
        try:
            self._song.current_song_time = float(time_val)
            return {"current_song_time": self._song.current_song_time}
        except Exception as e:
            self.log_message("Error setting current song time: " + str(e))
            raise

    def _get_arrangement_clips(self, track_index):
        """Return all clips placed in the Arrangement timeline for a track.

        Each clip dict contains:
          name, start_time, end_time, length, color,
          is_midi_clip, is_audio_clip, is_playing
        """
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")

            track = self._song.tracks[track_index]
            clips = []

            # track.arrangement_clips is available in Live 11 / 12
            for clip in track.arrangement_clips:
                clips.append({
                    "name": clip.name,
                    "start_time": clip.start_time,
                    "end_time": clip.end_time,
                    "length": clip.length,
                    "color": clip.color,
                    "is_midi_clip": clip.is_midi_clip,
                    "is_audio_clip": clip.is_audio_clip,
                    "is_playing": clip.is_playing
                })

            return {
                "track_index": track_index,
                "track_name": track.name,
                "clip_count": len(clips),
                "clips": clips
            }
        except Exception as e:
            self.log_message("Error getting arrangement clips: " + str(e))
            raise

    def _duplicate_session_clip_to_arrangement(self, track_index, clip_index, destination_time):
        """Copy a Session-view clip into the Arrangement timeline.

        Uses the real Live API:
          track.duplicate_clip_to_arrangement(clip, destination_time)

        Available in Live 11 / 12.  destination_time is in beats from the
        start of the arrangement.
        """
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")

            track = self._song.tracks[track_index]

            if clip_index < 0 or clip_index >= len(track.clip_slots):
                raise IndexError("Clip slot index out of range")

            clip_slot = track.clip_slots[clip_index]

            if not clip_slot.has_clip:
                raise Exception(
                    "No clip in slot " + str(clip_index) +
                    " on track " + str(track_index)
                )

            clip = clip_slot.clip

            # Duplicate to arrangement at the requested beat position
            track.duplicate_clip_to_arrangement(clip, float(destination_time))

            return {
                "success": True,
                "track_index": track_index,
                "track_name": track.name,
                "clip_name": clip.name,
                "destination_time": destination_time
            }
        except Exception as e:
            self.log_message("Error duplicating clip to arrangement: " + str(e))
            raise

    # ── Browser implementations ───────────────────────────────────────────────

    def _get_browser_item(self, uri, path):
        """Get a browser item by URI or path"""
        try:
            # Access the application's browser instance instead of creating a new one
            app = self.application()
            if not app:
                raise RuntimeError("Could not access Live application")
                
            result = {
                "uri": uri,
                "path": path,
                "found": False
            }
            
            # Try to find by URI first if provided
            if uri:
                item = self._find_browser_item_by_uri(app.browser, uri)
                if item:
                    result["found"] = True
                    result["item"] = {
                        "name": item.name,
                        "is_folder": item.is_folder,
                        "is_device": item.is_device,
                        "is_loadable": item.is_loadable,
                        "uri": item.uri
                    }
                    return result
            
            # If URI not provided or not found, try by path
            if path:
                # Parse the path and navigate to the specified item
                path_parts = path.split("/")
                
                # Determine the root based on the first part
                current_item = None
                if path_parts[0].lower() == "instruments":
                    current_item = app.browser.instruments
                elif path_parts[0].lower() == "sounds":
                    current_item = app.browser.sounds
                elif path_parts[0].lower() == "drums":
                    current_item = app.browser.drums
                elif path_parts[0].lower() == "audio_effects":
                    current_item = app.browser.audio_effects
                elif path_parts[0].lower() == "midi_effects":
                    current_item = app.browser.midi_effects
                else:
                    # Default to instruments if not specified
                    current_item = app.browser.instruments
                    # Don't skip the first part in this case
                    path_parts = ["instruments"] + path_parts
                
                # Navigate through the path
                for i in range(1, len(path_parts)):
                    part = path_parts[i]
                    if not part:  # Skip empty parts
                        continue
                    
                    found = False
                    for child in current_item.children:
                        if child.name.lower() == part.lower():
                            current_item = child
                            found = True
                            break
                    
                    if not found:
                        result["error"] = "Path part '{0}' not found".format(part)
                        return result
                
                # Found the item
                result["found"] = True
                result["item"] = {
                    "name": current_item.name,
                    "is_folder": current_item.is_folder,
                    "is_device": current_item.is_device,
                    "is_loadable": current_item.is_loadable,
                    "uri": current_item.uri
                }
            
            return result
        except Exception as e:
            self.log_message("Error getting browser item: " + str(e))
            self.log_message(traceback.format_exc())
            raise   
    
    
    
    def _load_browser_item(self, track_index, item_uri):
        """Load a browser item onto a track by its URI"""
        try:
            if track_index < 0 or track_index >= len(self._song.tracks):
                raise IndexError("Track index out of range")
            
            track = self._song.tracks[track_index]
            
            # Access the application's browser instance instead of creating a new one
            app = self.application()
            
            # Find the browser item by URI
            item = self._find_browser_item_by_uri(app.browser, item_uri)
            
            if not item:
                raise ValueError("Browser item with URI '{0}' not found".format(item_uri))
            
            # Select the track
            self._song.view.selected_track = track
            
            # Load the item
            app.browser.load_item(item)
            
            result = {
                "loaded": True,
                "item_name": item.name,
                "track_name": track.name,
                "uri": item_uri
            }
            return result
        except Exception as e:
            self.log_message("Error loading browser item: {0}".format(str(e)))
            self.log_message(traceback.format_exc())
            raise
    
    # Substring markers that point a URI at a likely root. If no marker
    # matches we fall back to the default order, so this is purely an
    # optimisation — never a correctness change.
    _URI_ROOT_HINTS = (
        ('plugins',       ('vst:', 'vst3:', 'au:', 'query:plugins', 'plugin#')),
        ('max_for_live',  ('max for live', 'maxforlive', 'm4l', 'query:max')),
        ('user_library',  ('user library', 'userlibrary', 'query:user library', 'query:user-library')),
        ('packs',         ('query:packs', '/packs/')),
        ('samples',       ('query:samples', 'sample:', '/samples/')),
        ('drums',         ('query:drums', '/drums/')),
        ('instruments',   ('query:instruments', '/instruments/')),
        ('sounds',        ('query:sounds', '/sounds/')),
        ('audio_effects', ('query:audio effects', 'audioeffects', '/audio_effects/')),
        ('midi_effects',  ('query:midi effects', 'midieffects', '/midi_effects/')),
    )

    def _order_roots_by_uri(self, roots, uri):
        """Reorder ``roots`` so the URI's likely root is walked first."""
        if not isinstance(uri, (bytes, str)) or not uri:
            return roots
        lowered = uri.lower()
        for attr, markers in self._URI_ROOT_HINTS:
            if any(m in lowered for m in markers):
                head = [(a, r) for (a, r) in roots if a == attr]
                tail = [(a, r) for (a, r) in roots if a != attr]
                return head + tail
        return roots

    def _find_browser_item_by_uri(self, browser_or_item, uri, max_depth=10, current_depth=0):
        """Find a browser item by its URI.

        Top-level lookups are memoised on ``self._uri_cache`` so repeated
        loads of the same URI don't re-walk the entire browser tree.
        """
        if current_depth == 0:
            cache = getattr(self, '_uri_cache', None)
            if cache is None:
                self._uri_cache = cache = {}
            if uri in cache:
                return cache[uri]
            result = self._walk_browser_for_uri(browser_or_item, uri, max_depth, 0)
            if result is not None:
                cache[uri] = result
            return result
        return self._walk_browser_for_uri(browser_or_item, uri, max_depth, current_depth)

    def _walk_browser_for_uri(self, browser_or_item, uri, max_depth, current_depth):
        """Recursive walk used by :py:meth:`_find_browser_item_by_uri`."""
        try:
            # Check if this is the item we're looking for
            if hasattr(browser_or_item, 'uri') and browser_or_item.uri == uri:
                return browser_or_item

            # Stop recursion if we've reached max depth
            if current_depth >= max_depth:
                return None

            # Check if this is a browser with root categories
            if hasattr(browser_or_item, 'instruments'):
                roots = [
                    ('instruments', browser_or_item.instruments),
                    ('sounds', browser_or_item.sounds),
                    ('drums', browser_or_item.drums),
                    ('audio_effects', browser_or_item.audio_effects),
                    ('midi_effects', browser_or_item.midi_effects),
                ]
                for extra_attr in ('plugins', 'max_for_live', 'user_library', 'packs', 'samples'):
                    if hasattr(browser_or_item, extra_attr):
                        try:
                            roots.append((extra_attr, getattr(browser_or_item, extra_attr)))
                        except (AttributeError, RuntimeError) as e:
                            self.log_message("Could not access browser.{0}: {1}".format(extra_attr, str(e)))

                for _attr, category in self._order_roots_by_uri(roots, uri):
                    item = self._find_browser_item_by_uri(category, uri, max_depth, current_depth + 1)
                    if item:
                        return item

                return None

            # Check if this item has children
            if hasattr(browser_or_item, 'children') and browser_or_item.children:
                for child in browser_or_item.children:
                    item = self._find_browser_item_by_uri(child, uri, max_depth, current_depth + 1)
                    if item:
                        return item

            return None
        except Exception as e:
            self.log_message("Error finding browser item by URI: {0}".format(str(e)))
            return None
    
    # Helper methods
    
    def _get_device_type(self, device):
        """Get the type of a device"""
        try:
            # Simple heuristic - in a real implementation you'd look at the device class
            if device.can_have_drum_pads:
                return "drum_machine"
            elif device.can_have_chains:
                return "rack"
            elif "instrument" in device.class_display_name.lower():
                return "instrument"
            elif "audio_effect" in device.class_name.lower():
                return "audio_effect"
            elif "midi_effect" in device.class_name.lower():
                return "midi_effect"
            else:
                return "unknown"
        except:
            return "unknown"
    
    def get_browser_tree(self, category_type="all"):
        """
        Get a simplified tree of browser categories.
        
        Args:
            category_type: Type of categories to get ('all', 'instruments', 'sounds', etc.)
            
        Returns:
            Dictionary with the browser tree structure
        """
        try:
            # Access the application's browser instance instead of creating a new one
            app = self.application()
            if not app:
                raise RuntimeError("Could not access Live application")
                
            # Check if browser is available
            if not hasattr(app, 'browser') or app.browser is None:
                raise RuntimeError("Browser is not available in the Live application")
            
            # Log available browser attributes to help diagnose issues
            browser_attrs = [attr for attr in dir(app.browser) if not attr.startswith('_')]
            self.log_message("Available browser attributes: {0}".format(browser_attrs))
            
            result = {
                "type": category_type,
                "categories": [],
                "available_categories": browser_attrs
            }
            
            # Helper function to process a browser item and its children
            def process_item(item, depth=0):
                if not item:
                    return None
                
                result = {
                    "name": item.name if hasattr(item, 'name') else "Unknown",
                    "is_folder": hasattr(item, 'children') and bool(item.children),
                    "is_device": hasattr(item, 'is_device') and item.is_device,
                    "is_loadable": hasattr(item, 'is_loadable') and item.is_loadable,
                    "uri": item.uri if hasattr(item, 'uri') else None,
                    "children": []
                }
                
                
                return result
            
            # Process based on category type and available attributes
            if (category_type == "all" or category_type == "instruments") and hasattr(app.browser, 'instruments'):
                try:
                    instruments = process_item(app.browser.instruments)
                    if instruments:
                        instruments["name"] = "Instruments"  # Ensure consistent naming
                        result["categories"].append(instruments)
                except Exception as e:
                    self.log_message("Error processing instruments: {0}".format(str(e)))
            
            if (category_type == "all" or category_type == "sounds") and hasattr(app.browser, 'sounds'):
                try:
                    sounds = process_item(app.browser.sounds)
                    if sounds:
                        sounds["name"] = "Sounds"  # Ensure consistent naming
                        result["categories"].append(sounds)
                except Exception as e:
                    self.log_message("Error processing sounds: {0}".format(str(e)))
            
            if (category_type == "all" or category_type == "drums") and hasattr(app.browser, 'drums'):
                try:
                    drums = process_item(app.browser.drums)
                    if drums:
                        drums["name"] = "Drums"  # Ensure consistent naming
                        result["categories"].append(drums)
                except Exception as e:
                    self.log_message("Error processing drums: {0}".format(str(e)))
            
            if (category_type == "all" or category_type == "audio_effects") and hasattr(app.browser, 'audio_effects'):
                try:
                    audio_effects = process_item(app.browser.audio_effects)
                    if audio_effects:
                        audio_effects["name"] = "Audio Effects"  # Ensure consistent naming
                        result["categories"].append(audio_effects)
                except Exception as e:
                    self.log_message("Error processing audio_effects: {0}".format(str(e)))
            
            if (category_type == "all" or category_type == "midi_effects") and hasattr(app.browser, 'midi_effects'):
                try:
                    midi_effects = process_item(app.browser.midi_effects)
                    if midi_effects:
                        midi_effects["name"] = "MIDI Effects"
                        result["categories"].append(midi_effects)
                except Exception as e:
                    self.log_message("Error processing midi_effects: {0}".format(str(e)))
            
            # Try to process other potentially available categories
            for attr in browser_attrs:
                if attr not in ['instruments', 'sounds', 'drums', 'audio_effects', 'midi_effects'] and \
                   (category_type == "all" or category_type == attr):
                    try:
                        item = getattr(app.browser, attr)
                        if hasattr(item, 'children') or hasattr(item, 'name'):
                            category = process_item(item)
                            if category:
                                category["name"] = attr.capitalize()
                                result["categories"].append(category)
                    except Exception as e:
                        self.log_message("Error processing {0}: {1}".format(attr, str(e)))
            
            self.log_message("Browser tree generated for {0} with {1} root categories".format(
                category_type, len(result['categories'])))
            return result
            
        except Exception as e:
            self.log_message("Error getting browser tree: {0}".format(str(e)))
            self.log_message(traceback.format_exc())
            raise
    
    def get_browser_items_at_path(self, path):
        """
        Get browser items at a specific path.
        
        Args:
            path: Path in the format "category/folder/subfolder"
                 where category is one of: instruments, sounds, drums, audio_effects, midi_effects
                 or any other available browser category
                 
        Returns:
            Dictionary with items at the specified path
        """
        try:
            # Access the application's browser instance instead of creating a new one
            app = self.application()
            if not app:
                raise RuntimeError("Could not access Live application")
                
            # Check if browser is available
            if not hasattr(app, 'browser') or app.browser is None:
                raise RuntimeError("Browser is not available in the Live application")
            
            # Log available browser attributes to help diagnose issues
            browser_attrs = [attr for attr in dir(app.browser) if not attr.startswith('_')]
            self.log_message("Available browser attributes: {0}".format(browser_attrs))
                
            # Parse the path
            path_parts = path.split("/")
            if not path_parts:
                raise ValueError("Invalid path")
            
            # Determine the root category
            root_category = path_parts[0].lower()
            current_item = None
            
            # Check standard categories first
            if root_category == "instruments" and hasattr(app.browser, 'instruments'):
                current_item = app.browser.instruments
            elif root_category == "sounds" and hasattr(app.browser, 'sounds'):
                current_item = app.browser.sounds
            elif root_category == "drums" and hasattr(app.browser, 'drums'):
                current_item = app.browser.drums
            elif root_category == "audio_effects" and hasattr(app.browser, 'audio_effects'):
                current_item = app.browser.audio_effects
            elif root_category == "midi_effects" and hasattr(app.browser, 'midi_effects'):
                current_item = app.browser.midi_effects
            else:
                # Try to find the category in other browser attributes
                found = False
                for attr in browser_attrs:
                    if attr.lower() == root_category:
                        try:
                            current_item = getattr(app.browser, attr)
                            found = True
                            break
                        except Exception as e:
                            self.log_message("Error accessing browser attribute {0}: {1}".format(attr, str(e)))
                
                if not found:
                    # If we still haven't found the category, return available categories
                    return {
                        "path": path,
                        "error": "Unknown or unavailable category: {0}".format(root_category),
                        "available_categories": browser_attrs,
                        "items": []
                    }
            
            # Navigate through the path
            for i in range(1, len(path_parts)):
                part = path_parts[i]
                if not part:  # Skip empty parts
                    continue
                
                if not hasattr(current_item, 'children'):
                    return {
                        "path": path,
                        "error": "Item at '{0}' has no children".format('/'.join(path_parts[:i])),
                        "items": []
                    }
                
                found = False
                for child in current_item.children:
                    if hasattr(child, 'name') and child.name.lower() == part.lower():
                        current_item = child
                        found = True
                        break
                
                if not found:
                    return {
                        "path": path,
                        "error": "Path part '{0}' not found".format(part),
                        "items": []
                    }
            
            # Get items at the current path
            items = []
            if hasattr(current_item, 'children'):
                for child in current_item.children:
                    item_info = {
                        "name": child.name if hasattr(child, 'name') else "Unknown",
                        "is_folder": hasattr(child, 'children') and bool(child.children),
                        "is_device": hasattr(child, 'is_device') and child.is_device,
                        "is_loadable": hasattr(child, 'is_loadable') and child.is_loadable,
                        "uri": child.uri if hasattr(child, 'uri') else None
                    }
                    items.append(item_info)
            
            result = {
                "path": path,
                "name": current_item.name if hasattr(current_item, 'name') else "Unknown",
                "uri": current_item.uri if hasattr(current_item, 'uri') else None,
                "is_folder": hasattr(current_item, 'children') and bool(current_item.children),
                "is_device": hasattr(current_item, 'is_device') and current_item.is_device,
                "is_loadable": hasattr(current_item, 'is_loadable') and current_item.is_loadable,
                "items": items
            }
            
            self.log_message("Retrieved {0} items at path: {1}".format(len(items), path))
            return result
            
        except Exception as e:
            self.log_message("Error getting browser items at path: {0}".format(str(e)))
            self.log_message(traceback.format_exc())
            raise
