"""
ABLETON BRAIN - MCP Server
External Python server that connects to Ableton Remote Script via TCP
Run: python mcp_server.py
"""
import json
import socket
import threading
import asyncio
import time
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Add brain directory to path
BRAIN_DIR = Path(__file__).parent
sys.path.insert(0, str(BRAIN_DIR))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    import mcp.types as types
except ImportError:
    print("Installing MCP dependencies...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "mcp", "fastapi", "uvicorn"], check=True)
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

# Try to import analyzer bridge
try:
    from analyzer_bridge import get_analyzer_bridge, start_analyzer_bridge
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False
    print("[MCP] Analyzer bridge not available (install pythonosc)")

# HTTP/WS Server support
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, Request
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from contextlib import asynccontextmanager
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    print("[MCP] FastAPI not available (install fastapi uvicorn)")

class AbletonConnection:
    """TCP connection to Ableton Remote Script"""

    def __init__(self, host='127.0.0.1', port=9877):
        self.host = host
        self.port = port
        self.socket = None
        self.request_id = 0
        self.pending = {}
        self.lock = threading.Lock()
        self.connected = False
        self._connect()

    def _connect(self):
        """Establish connection to Ableton"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.host, self.port))
            self.connected = True
            threading.Thread(target=self._listen, daemon=True).start()
            print(f"[MCP] Connected to Ableton on {self.host}:{self.port}")
        except Exception as e:
            self.connected = False
            print(f"[MCP] Connection failed: {e}")

    def _listen(self):
        """Listen for responses from Ableton"""
        buffer = ""
        while self.connected:
            try:
                data = self.socket.recv(8192).decode('utf-8')
                if not data:
                    self.connected = False
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self._handle_response(line.strip())
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[MCP] Listen error: {e}")
                self.connected = False
                break

    def _handle_response(self, line):
        """Process response from Ableton"""
        try:
            response = json.loads(line)
            request_id = response.get('id')
            if request_id in self.pending:
                future = self.pending.pop(request_id)
                if response.get('status') == 'success':
                    future.set_result(response.get('result'))
                else:
                    future.set_exception(Exception(response.get('error', 'Unknown error')))
        except Exception as e:
            print(f"[MCP] Response error: {e}")

    def send_command(self, command: str, params: Dict = None) -> Any:
        """Send command to Ableton and wait for response"""
        if not self.connected:
            self._connect()
            if not self.connected:
                raise ConnectionError("Not connected to Ableton")

        self.request_id += 1
        request_id = str(self.request_id)

        future = asyncio.Future()
        with self.lock:
            self.pending[request_id] = future

        message = {
            'id': request_id,
            'command': command,
            'params': params or {}
        }

        try:
            self.socket.send((json.dumps(message) + '\n').encode('utf-8'))
            result = future.result(timeout=30)
            return result
        except asyncio.TimeoutError:
            with self.lock:
                self.pending.pop(request_id, None)
            raise TimeoutError(f"Command {command} timed out")
        except Exception as e:
            with self.lock:
                self.pending.pop(request_id, None)
            raise

    def close(self):
        self.connected = False
        if self.socket:
            self.socket.close()


class AbletonBrainMCP:
    """MCP Server for Ableton Brain - exposes tools to AI clients"""

    def __init__(self):
        self.connection = AbletonConnection()
        self._tool_handlers = {}
        self._tool_definitions = self._get_tool_definitions()
        self.server = Server(
            "ableton-brain",
            on_list_tools=self._list_tools,
            on_call_tool=self._call_tool
        )

    async def _list_tools(self, context, params):
        return types.ListToolsResult(tools=self._tool_definitions)

    async def _call_tool(self, context, params):
        name = params.name
        arguments = params.arguments or {}
        handler = self._tool_handlers.get(name)
        if handler:
            result = await handler(arguments)
            return types.CallToolResult(content=result)
        return types.CallToolResult(
            content=[TextContent(type="text", text=json.dumps({"error": f"Tool not found: {name}", "success": False}, indent=2))]
        )

    def _get_tool_definitions(self) -> List[Tool]:
        return [
            # Session/Transport
            Tool(name="get_session_info", description="Get current session info (tempo, tracks, playing state)",
                 inputSchema={"type": "object", "properties": {}}),
            Tool(name="set_tempo", description="Set session tempo (BPM)",
                 inputSchema={"type": "object", "properties": {"tempo": {"type": "number", "minimum": 20, "maximum": 999}}, "required": ["tempo"]}),
            Tool(name="play", description="Start playback", inputSchema={"type": "object", "properties": {}}),
            Tool(name="stop", description="Stop playback", inputSchema={"type": "object", "properties": {}}),
            Tool(name="record", description="Start recording", inputSchema={"type": "object", "properties": {}}),

            # Tracks
            Tool(name="create_midi_track", description="Create a new MIDI track",
                 inputSchema={"type": "object", "properties": {"name": {"type": "string"}, "index": {"type": "integer"}}, "required": ["name"]}),
            Tool(name="create_audio_track", description="Create a new audio track",
                 inputSchema={"type": "object", "properties": {"name": {"type": "string"}, "index": {"type": "integer"}}, "required": ["name"]}),
            Tool(name="get_tracks", description="List all tracks with info", inputSchema={"type": "object", "properties": {}}),
            Tool(name="arm_track", description="Arm/disarm track for recording",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "arm": {"type": "boolean"}}, "required": ["track_index"]}),
            Tool(name="set_track_volume", description="Set track volume (0-1)",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "volume": {"type": "number", "minimum": 0, "maximum": 1}}, "required": ["track_index", "volume"]}),
            Tool(name="set_track_pan", description="Set track pan (-1 to 1)",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "pan": {"type": "number", "minimum": -1, "maximum": 1}}, "required": ["track_index", "pan"]}),

            # Clips
            Tool(name="create_midi_clip", description="Create empty MIDI clip on track",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "clip_index": {"type": "integer"}, "length": {"type": "number"}}, "required": ["track_index"]}),
            Tool(name="create_audio_clip", description="Load audio file into clip slot",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "clip_index": {"type": "integer"}, "file_path": {"type": "string"}}, "required": ["track_index", "file_path"]}),
            Tool(name="get_clip_notes", description="Get MIDI notes from clip",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "clip_index": {"type": "integer"}}, "required": ["track_index", "clip_index"]}),
            Tool(name="add_notes_to_clip", description="Add MIDI notes to clip",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "clip_index": {"type": "integer"}, "notes": {"type": "array", "items": {"type": "object", "properties": {"pitch": {"type": "integer"}, "start_time": {"type": "number"}, "duration": {"type": "number"}, "velocity": {"type": "integer"}, "muted": {"type": "boolean"}}}}}, "required": ["track_index", "clip_index", "notes"]}),
            Tool(name="fire_clip", description="Launch clip",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "clip_index": {"type": "integer"}}, "required": ["track_index", "clip_index"]}),
            Tool(name="stop_clip", description="Stop all clips on track",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}}, "required": ["track_index"]}),

            # Devices
            Tool(name="load_instrument", description="Load instrument on track",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "device_name": {"type": "string"}}, "required": ["track_index", "device_name"]}),
            Tool(name="load_audio_effect", description="Load audio effect on track",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "device_name": {"type": "string"}}, "required": ["track_index", "device_name"]}),
            Tool(name="load_midi_effect", description="Load MIDI effect on track",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "device_name": {"type": "string"}}, "required": ["track_index", "device_name"]}),
            Tool(name="get_device_parameters", description="Get all parameters of a device",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "device_index": {"type": "integer"}}, "required": ["track_index", "device_index"]}),
            Tool(name="set_device_parameter", description="Set device parameter (0-1 normalized)",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "device_index": {"type": "integer"}, "parameter_index": {"type": "integer"}, "value": {"type": "number", "minimum": 0, "maximum": 1}}, "required": ["track_index", "device_index", "parameter_index", "value"]}),
            Tool(name="batch_set_device_parameters", description="Set multiple device parameters",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "device_index": {"type": "integer"}, "parameter_indices": {"type": "array", "items": {"type": "integer"}}, "values": {"type": "array", "items": {"type": "number"}}}, "required": ["track_index", "device_index", "parameter_indices", "values"]}),

            # Drum Rack
            Tool(name="create_drum_rack", description="Create Drum Rack on track",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}}, "required": ["track_index"]}),
            Tool(name="replace_sample", description="Replace sample in Drum Rack pad",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "device_index": {"type": "integer"}, "pad": {"type": "integer"}, "sample_path": {"type": "string"}}, "required": ["track_index", "device_index", "pad", "sample_path"]}),
            Tool(name="create_drum_pattern", description="Create drum pattern in clip",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "clip_index": {"type": "integer"}, "pattern": {"type": "array"}}, "required": ["track_index", "clip_index", "pattern"]}),

            # Scenes/Arrangement
            Tool(name="create_scene", description="Create new scene", inputSchema={"type": "object", "properties": {"index": {"type": "integer"}}}),
            Tool(name="delete_clip", description="Delete clip",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "clip_index": {"type": "integer"}}, "required": ["track_index", "clip_index"]}),
            Tool(name="copy_clip", description="Copy clip between slots",
                 inputSchema={"type": "object", "properties": {"src_track": {"type": "integer"}, "src_clip": {"type": "integer"}, "dst_track": {"type": "integer"}, "dst_clip": {"type": "integer"}}, "required": ["src_track", "src_clip", "dst_track", "dst_clip"]}),
            Tool(name="set_clip_envelope", description="Set automation envelope on clip",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "clip_index": {"type": "integer"}, "parameter": {"type": "string"}, "points": {"type": "array"}}, "required": ["track_index", "clip_index", "parameter", "points"]}),

            # Samples/Browser
            Tool(name="list_samples", description="Scan folder for audio samples",
                 inputSchema={"type": "object", "properties": {"folder": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["folder"]}),
            Tool(name="analyze_sample", description="Analyze audio file (duration, sample rate, etc.)",
                 inputSchema={"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}),

            # VST/AU Plugin Control
            Tool(name="probe_plugin_parameters", description="Enumerate all VST/AU plugin parameters",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "device_index": {"type": "integer"}}, "required": ["track_index", "device_index"]}),
            Tool(name="expose_plugin_parameters", description="Map plugin parameters to macros for automation",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "device_index": {"type": "integer"}, "parameter_indices": {"type": "array", "items": {"type": "integer"}}}, "required": ["track_index", "device_index", "parameter_indices"]}),

            # Serum Specific
            Tool(name="get_serum_fx", description="Get Serum FX rack state",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "device_index": {"type": "integer"}}, "required": ["track_index", "device_index"]}),
            Tool(name="set_serum_fx_param", description="Set Serum FX parameter",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "device_index": {"type": "integer"}, "parameter_index": {"type": "integer"}, "value": {"type": "number"}}, "required": ["track_index", "device_index", "parameter_index", "value"]}),
            Tool(name="get_serum_patch", description="Get Serum patch state blob",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "device_index": {"type": "integer"}}, "required": ["track_index", "device_index"]}),
            Tool(name="create_serum_patch", description="Create full Serum patch from components",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "device_index": {"type": "integer"}, "oscillators": {"type": "array"}, "filters": {"type": "array"}, "envelopes": {"type": "array"}, "lfos": {"type": "array"}, "macros": {"type": "array"}, "mod_matrix": {"type": "array"}}, "required": ["track_index", "device_index"]}),

            # Audio Analysis & Mixing (requires Max for Live + Analyzer device)
            Tool(name="install_analyzer", description="Install AbletonMCP Analyzer device on track (requires Max for Live)",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "track_name": {"type": "string"}}, "required": ["track_index"]}),
            Tool(name="read_analyzer", description="Read real-time audio metrics from analyzer (LUFS, true peak, stereo, spectrum, tempo, key)",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}}, "required": ["track_index"]}),
            Tool(name="get_all_analyzers", description="Get metrics from all installed analyzers", inputSchema={"type": "object", "properties": {}}),
            Tool(name="mix_doctor", description="Analyze mix for problems: masking, low-end issues, phase, loudness, tonal balance",
                 inputSchema={"type": "object", "properties": {"section_bars": {"type": "integer", "default": 8}, "include_stems": {"type": "boolean", "default": False}}, "required": []}),
            Tool(name="compare_to_reference", description="Compare current mix to reference track, suggest EQ Eight settings",
                 inputSchema={"type": "object", "properties": {"reference_path": {"type": "string"}, "target_lufs": {"type": "number", "default": -14.0}}, "required": ["reference_path"]}),
            Tool(name="capture_stems", description="Record individual track stems for external processing",
                 inputSchema={"type": "object", "properties": {"track_indices": {"type": "array", "items": {"type": "integer"}}, "length_bars": {"type": "number", "default": 8}}, "required": ["track_indices"]}),

            # AI Generation
            Tool(name="generate_midi_magenta", description="Generate MIDI using Magenta Studio (Generate, Continue, Interpolate, Groove, Drumify)",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "clip_index": {"type": "integer"}, "model": {"type": "string", "enum": ["generate", "continue", "interpolate", "groove", "drumify"]}, "temperature": {"type": "number", "default": 1.0}}, "required": ["track_index", "clip_index"]}),
            Tool(name="generate_audio_stable", description="Generate audio using Stable Audio Open (text-to-audio, 47s max)",
                 inputSchema={"type": "object", "properties": {"prompt": {"type": "string"}, "duration_seconds": {"type": "integer", "default": 30, "maximum": 47}, "tempo": {"type": "integer"}, "steps": {"type": "integer", "default": 50}}, "required": ["prompt"]}),
            Tool(name="separate_stems_demucs", description="Separate stems using Demucs (drums, bass, vocals, other)",
                 inputSchema={"type": "object", "properties": {"audio_path": {"type": "string"}, "model": {"type": "string", "default": "htdemucs"}, "stems": {"type": "array", "items": {"type": "string"}}}, "required": ["audio_path"]}),
            Tool(name="style_transfer_magenta", description="DDSP timbre transfer via Magenta",
                 inputSchema={"type": "object", "properties": {"source_path": {"type": "string"}, "target_path": {"type": "string"}}, "required": ["source_path", "target_path"]}),
            Tool(name="create_track_from_prompt", description="High-level: create full track from text prompt",
                 inputSchema={"type": "object", "properties": {"prompt": {"type": "string"}, "genre": {"type": "string"}, "length_bars": {"type": "integer", "default": 64}}, "required": ["prompt"]}),

            # NEW: Vocal Synthesis (ACE-Step / YuE)
            Tool(name="generate_vocals", description="Generate singing vocals from lyrics using ACE-Step or YuE (requires GPU)",
                 inputSchema={"type": "object", "properties": {"lyrics": {"type": "string"}, "style": {"type": "string", "default": "pop"}, "gender": {"type": "string", "default": "female"}, "tempo": {"type": "number", "default": 120}, "key": {"type": "string", "default": "C"}, "backend": {"type": "string", "enum": ["ace_step", "yue"], "default": "ace_step"}, "duration_seconds": {"type": "number", "default": 180}}, "required": ["lyrics"]}),

            # NEW: Lyric Generation
            Tool(name="generate_lyrics", description="Generate song lyrics from topic/genre/mood using AI",
                 inputSchema={"type": "object", "properties": {"topic": {"type": "string"}, "genre": {"type": "string", "default": "pop"}, "mood": {"type": "string", "default": "energetic"}, "structure": {"type": "string", "default": "verse-chorus"}, "language": {"type": "string", "default": "english"}}, "required": []}),

            # NEW: AI Mastering Assistant
            Tool(name="ai_master", description="Ozone-style AI mastering: analyze mix, build mastering chain, apply EQ/comp/limiter",
                 inputSchema={"type": "object", "properties": {"genre": {"type": "string", "default": "electronic"}, "target_lufs": {"type": "number", "default": -14}, "target_peak": {"type": "number", "default": -1}, "eq_match": {"type": "boolean", "default": True}, "multiband_comp": {"type": "boolean", "default": True}, "stereo_enhance": {"type": "boolean", "default": True}, "saturation": {"type": "boolean", "default": False}, "limiter_ceiling": {"type": "number", "default": -0.3}}, "required": []}),

            # NEW: Sound Similarity Search
            Tool(name="find_similar_samples", description="Find samples in your library that sound similar to a reference (AI audio fingerprinting)",
                 inputSchema={"type": "object", "properties": {"reference_path": {"type": "string"}, "sample_folder": {"type": "string"}, "limit": {"type": "integer", "default": 10}, "min_similarity": {"type": "number", "default": 0.7}}, "required": ["reference_path", "sample_folder"]}),

            # NEW: Phase 2 - Masking Detection (Neutron Unmask style)
            Tool(name="detect_masking", description="Detect frequency masking between two tracks (Neutron Unmask style)",
                 inputSchema={"type": "object", "properties": {"track_a_path": {"type": "string"}, "track_b_path": {"type": "string"}, "track_a_name": {"type": "string", "default": ""}, "track_b_name": {"type": "string", "default": ""}, "masking_threshold_db": {"type": "number", "default": -6.0}}, "required": ["track_a_path", "track_b_path"]}),
            Tool(name="analyze_project_masking", description="Analyze frequency masking across all track pairs in a project",
                 inputSchema={"type": "object", "properties": {"track_paths": {"type": "object", "additionalProperties": {"type": "string"}}, "masking_threshold_db": {"type": "number", "default": -6.0}}, "required": ["track_paths"]}),
            Tool(name="suggest_unmask", description="Get EQ/panning/level suggestions to resolve masking between two tracks",
                 inputSchema={"type": "object", "properties": {"track_a_path": {"type": "string"}, "track_b_path": {"type": "string"}, "track_a_name": {"type": "string", "default": ""}, "track_b_name": {"type": "string", "default": ""}}, "required": ["track_a_path", "track_b_path"]}),

            # NEW: Phase 2 - Enhanced Mix Doctor (Neutron/Ozone style)
            Tool(name="analyze_track", description="Analyze single track: loudness, dynamics, spectrum, stereo, instrument profile compliance",
                 inputSchema={"type": "object", "properties": {"audio_path": {"type": "string"}, "track_name": {"type": "string", "default": ""}, "instrument_hint": {"type": "string"}}, "required": ["audio_path"]}),
            Tool(name="analyze_mix", description="Full mix analysis from stems: tonal balance, stereo, dynamics, compliance (streaming/club/broadcast)",
                 inputSchema={"type": "object", "properties": {"track_paths": {"type": "object", "additionalProperties": {"type": "string"}}, "master_path": {"type": "string"}, "genre": {"type": "string", "default": "electronic"}}, "required": ["track_paths"]}),
            Tool(name="compare_to_reference", description="Compare mix to reference track: band differences, EQ recommendations",
                 inputSchema={"type": "object", "properties": {"mix_path": {"type": "string"}, "reference_path": {"type": "string"}, "genre": {"type": "string", "default": "electronic"}}, "required": ["mix_path", "reference_path"]}),

            # NEW: Phase 3 - Arrangement Assistant
            Tool(name="analyze_arrangement", description="Analyze project arrangement from stems",
                 inputSchema={"type": "object", "properties": {"stem_paths": {"type": "object", "additionalProperties": {"type": "string"}}, "tempo": {"type": "number", "default": 120}}, "required": ["stem_paths"]}),
            Tool(name="suggest_arrangement", description="Get arrangement improvement suggestions",
                 inputSchema={"type": "object", "properties": {"stem_paths": {"type": "object", "additionalProperties": {"type": "string"}}, "tempo": {"type": "number", "default": 120}}, "required": ["stem_paths"]}),
            Tool(name="generate_arrangement_template", description="Generate arrangement template for genre",
                 inputSchema={"type": "object", "properties": {"genre": {"type": "string", "default": "electronic"}, "length_bars": {"type": "integer", "default": 64}}, "required": []}),
            Tool(name="generate_structure", description="Generate full arrangement structure plan",
                 inputSchema={"type": "object", "properties": {"genre": {"type": "string", "default": "electronic"}, "bpm": {"type": "integer", "default": 120}, "key": {"type": "string", "default": "C"}, "length_bars": {"type": "integer", "default": 64}}, "required": []}),

            # Automation
            Tool(name="apply_automation_recipe", description="Apply named automation recipe (filter_sweep_up, sidechain_pump, dub_throw, etc.)",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "clip_index": {"type": "integer"}, "recipe_name": {"type": "string"}, "param_name": {"type": "string"}}, "required": ["track_index", "clip_index", "recipe_name"]}),
            Tool(name="generate_automation_curve", description="Generate raw automation curve (linear, exponential, sine, sidechain, etc.)",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "clip_index": {"type": "integer"}, "param_name": {"type": "string"}, "curve_type": {"type": "string"}, "start_beat": {"type": "number"}, "end_beat": {"type": "number"}, "min_value": {"type": "number"}, "max_value": {"type": "number"}}, "required": ["track_index", "clip_index", "param_name", "curve_type"]}),
            Tool(name="write_arrangement_automation", description="Write timeline automation (arrangement view)",
                 inputSchema={"type": "object", "properties": {"track_index": {"type": "integer"}, "parameter": {"type": "string"}, "points": {"type": "array"}}, "required": ["track_index", "parameter", "points"]}),

            # Plugin Corpus
            Tool(name="detect_plugins", description="Scan VST3/AU/CLAP plugin folders",
                 inputSchema={"type": "object", "properties": {"use_auval": {"type": "boolean", "default": False}}}),
            Tool(name="load_plugin_map", description="Load semantic parameter map for plugin",
                 inputSchema={"type": "object", "properties": {"plugin_id": {"type": "string"}}, "required": ["plugin_id"]}),
            Tool(name="get_params_by_category", description="Get plugin parameters filtered by category (oscillator, filter, envelope, lfo, macro, fx)",
                 inputSchema={"type": "object", "properties": {"plugin_id": {"type": "string"}, "category": {"type": "string"}}, "required": ["plugin_id", "category"]}),
            Tool(name="create_patch_from_map", description="Create patch from high-level spec using semantic map",
                 inputSchema={"type": "object", "properties": {"plugin_id": {"type": "string"}, "spec": {"type": "object"}}, "required": ["plugin_id", "spec"]}),

            # Fleet
            Tool(name="submit_task", description="Offload task to GPU node, mobile, or DAW",
                 inputSchema={"type": "object", "properties": {"action": {"type": "string"}, "params": {"type": "object"}, "target": {"type": "string", "enum": ["gpu", "mobile", "daw"]}}, "required": ["action", "params"]}),
            Tool(name="get_fleet_status", description="Get status of all fleet nodes", inputSchema={"type": "object", "properties": {}}),
            Tool(name="start_ble_midi_bridge", description="Start BlueMIDI bridge for mobile controllers", inputSchema={"type": "object", "properties": {}}),
            Tool(name="setup_ableton_link", description="Setup Ableton Link tempo sync across devices", inputSchema={"type": "object", "properties": {}}),

            # Workflow
            Tool(name="create_project_from_template", description="Create project from genre template (dnb, house, techno, ambient, trap)",
                 inputSchema={"type": "object", "properties": {"template_id": {"type": "string"}, "project_name": {"type": "string"}}, "required": ["template_id"]}),
            Tool(name="create_snapshot", description="Save full mix state for A/B comparison",
                 inputSchema={"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}, "required": ["name"]}),
            Tool(name="recall_snapshot", description="Instant recall a mix snapshot",
                 inputSchema={"type": "object", "properties": {"snapshot_id": {"type": "string"}}, "required": ["snapshot_id"]}),
            Tool(name="compare_snapshots", description="Diff two snapshots",
                 inputSchema={"type": "object", "properties": {"snapshot_a": {"type": "string"}, "snapshot_b": {"type": "string"}}, "required": ["snapshot_a", "snapshot_b"]}),
            Tool(name="create_export_job", description="Create multi-format export job with loudness targets",
                 inputSchema={"type": "object", "properties": {"name": {"type": "string"}, "formats": {"type": "array", "items": {"type": "string"}}, "loudness_target": {"type": "string"}, "start_bar": {"type": "integer"}, "end_bar": {"type": "integer"}, "normalize": {"type": "boolean", "default": True}, "metadata": {"type": "object"}}, "required": ["name"]}),
            Tool(name="execute_export", description="Execute export job (render, normalize, embed metadata)",
                 inputSchema={"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}),
            Tool(name="prepare_metadata", description="Prepare metadata for export (ISRC, UPC, credits)",
                 inputSchema={"type": "object", "properties": {"title": {"type": "string"}, "artist": {"type": "string"}, "genre": {"type": "string"}, "bpm": {"type": "number"}, "key": {"type": "string"}, "isrc": {"type": "string"}, "upc": {"type": "string"}, "credits": {"type": "object"}}, "required": ["title", "artist"]}),

            # File Operations
            Tool(name="inspect_als", description="Inspect .als project file",
                 inputSchema={"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]}),
            Tool(name="render_audio", description="Render audio from session", inputSchema={"type": "object", "properties": {"length": {"type": "number"}}}),
        ]

    async def run_stdio(self):
        """Run MCP server over stdio"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())


# =========================================================================
# HIGH-LEVEL COMPOSITION WORKFLOWS
# =========================================================================

class AbletonBrainComposer:
    """High-level composition workflows using the MCP tools"""

    def __init__(self, mcp: AbletonBrainMCP):
        self.mcp = mcp

    async def make_track_from_samples(self, sample_folder: str, genre: str = "electronic") -> Dict:
        samples_result = self.mcp.connection.send_command('list_samples', {'folder': sample_folder, 'limit': 200})
        samples = samples_result.get('samples', [])

        loops = [s for s in samples if 'loop' in s['name'].lower()]
        one_shots = [s for s in samples if any(kw in s['name'].lower() for kw in ['kick', 'snare', 'hihat', 'hat', 'clap', 'perc', 'tom'])]
        bass = [s for s in samples if 'bass' in s['name'].lower()]
        melody = [s for s in samples if any(kw in s['name'].lower() for kw in ['melody', 'lead', 'synth', 'pad', 'chord'])]

        main_loop = loops[0] if loops else samples[0] if samples else None
        if main_loop:
            analysis = self.mcp.connection.send_command('analyze_sample', {'file_path': main_loop['path']})
            tempo = 120
            key = 'C'

        self.mcp.connection.send_command('set_tempo', {'tempo': tempo})
        self.mcp.connection.send_command('create_midi_track', {'name': 'Drums', 'index': 0})
        self.mcp.connection.send_command('create_drum_rack', {'track_index': 0})
        for i, shot in enumerate(one_shots[:16]):
            self.mcp.connection.send_command('replace_sample', {
                'track_index': 0, 'device_index': 0, 'pad': i, 'sample_path': shot['path']
            })
        kick_pattern = {'note': 36, 'steps': [1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0], 'velocity': 100}
        snare_pattern = {'note': 38, 'steps': [0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0], 'velocity': 90}
        self.mcp.connection.send_command('create_drum_pattern', {'track_index': 0, 'clip_index': 0, 'pattern': [kick_pattern, snare_pattern]})

        if bass:
            self.mcp.connection.send_command('create_audio_track', {'name': 'Bass', 'index': 1})
            self.mcp.connection.send_command('create_audio_clip', {'track_index': 1, 'clip_index': 0, 'file_path': bass[0]['path']})

        for i, loop in enumerate(loops[:4]):
            track_idx = i + 2
            self.mcp.connection.send_command('create_audio_track', {'name': f'Loop {i+1}', 'index': track_idx})
            self.mcp.connection.send_command('create_audio_clip', {'track_index': track_idx, 'clip_index': 0, 'file_path': loop['path']})

        scenes = ['Intro', 'Build', 'Drop', 'Break', 'Outro']
        for scene_name in scenes:
            self.mcp.connection.send_command('create_scene', {'index': -1})

        return {
            'genre': genre, 'tempo': tempo,
            'tracks_created': 3 + len(loops[:4]),
            'samples_used': len(samples),
            'loops': len(loops), 'one_shots': len(one_shots)
        }


# =========================================================================
# HTTP / WEBSOCKET SERVER (Dashboard)
# =========================================================================

if HTTP_AVAILABLE:
    class ConnectionManager:
        def __init__(self):
            self.active_connections: List[WebSocket] = []
            self.analyzer_data = {}
            self.fleet_data = {}

        async def connect(self, websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)

        def disconnect(self, websocket: WebSocket):
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

        async def broadcast(self, message: dict):
            for connection in self.active_connections[:]:
                try:
                    await connection.send_json(message)
                except:
                    self.disconnect(connection)

        async def send_personal(self, websocket: WebSocket, message: dict):
            try:
                await websocket.send_json(message)
            except:
                self.disconnect(websocket)

    manager = ConnectionManager()

    class ToolCall(BaseModel):
        name: str
        arguments: Dict = {}

    class ExportJobRequest(BaseModel):
        name: str
        formats: List[str] = ["wav_24", "mp3_320"]
        loudness_target: str = "streaming"
        start_bar: int = 1
        end_bar: int = 65
        normalize: bool = True
        metadata: Dict = {}

    mcp_instance: AbletonBrainMCP = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global mcp_instance
        mcp_instance = AbletonBrainMCP()
        if ANALYZER_AVAILABLE:
            try:
                start_analyzer_bridge()
                print("[HTTP] Analyzer bridge started on port 9878")
            except Exception as e:
                print(f"[HTTP] Analyzer bridge failed: {e}")
        print("[HTTP] Server ready on http://0.0.0.0:8050")
        yield
        if mcp_instance:
            mcp_instance.connection.close()

    app = FastAPI(title="Ableton Brain API", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.mount("/static", StaticFiles(directory=BRAIN_DIR), name="static")

    @app.get("/")
    async def root():
        return FileResponse(BRAIN_DIR / "ableton-brain-dashboard.html")

    @app.get("/health")
    async def health():
        return {"status": "ok", "mcp_connected": mcp_instance.connection.connected if mcp_instance else False}

    @app.post("/tools/{tool_name}")
    async def call_tool_http(tool_name: str, request: ToolCall):
        if not mcp_instance:
            raise HTTPException(503, "MCP not initialized")
        try:
            result = mcp_instance.connection.send_command(tool_name, request.arguments)
            return result
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.post("/tools/batch")
    async def call_tools_batch(request: List[ToolCall]):
        if not mcp_instance:
            raise HTTPException(503, "MCP not initialized")
        results = []
        for call in request:
            try:
                result = mcp_instance.connection.send_command(call.name, call.arguments)
                results.append({"tool": call.name, "success": True, "result": result})
            except Exception as e:
                results.append({"tool": call.name, "success": False, "error": str(e)})
        return results

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            await websocket.send_json({"type": "init", "analyzer": manager.analyzer_data, "fleet": manager.fleet_data})
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "subscribe":
                    pass
        except WebSocketDisconnect:
            manager.disconnect(websocket)
        except Exception as e:
            print(f"[WS] Error: {e}")
            manager.disconnect(websocket)

    async def analyzer_broadcaster():
        while True:
            await asyncio.sleep(1)
            if mcp_instance and mcp_instance.connection.connected:
                try:
                    result = mcp_instance.connection.send_command("get_all_analyzers", {})
                    if result and "analyzers" in result:
                        manager.analyzer_data = result["analyzers"]
                        await manager.broadcast({"type": "analyzer_update", "data": result["analyzers"]})
                except:
                    pass
            try:
                fleet_result = mcp_instance.connection.send_command("get_fleet_status", {})
                if fleet_result:
                    manager.fleet_data = fleet_result
                    await manager.broadcast({"type": "fleet_status", "data": fleet_result})
            except:
                pass

    @app.on_event("startup")
    async def start_background_tasks():
        asyncio.create_task(analyzer_broadcaster())

    @app.get("/api/session")
    async def get_session():
        return await call_tool_http("get_session_info", ToolCall(name="get_session_info"))

    @app.get("/api/tracks")
    async def get_tracks():
        return await call_tool_http("get_tracks", ToolCall(name="get_tracks"))

    @app.get("/api/analyzers")
    async def get_analyzers():
        return await call_tool_http("get_all_analyzers", ToolCall(name="get_all_analyzers"))

    @app.post("/api/mix-doctor")
    async def mix_doctor(section_bars: int = 8):
        return await call_tool_http("mix_doctor", ToolCall(name="mix_doctor", arguments={"section_bars": section_bars}))

    @app.get("/api/templates")
    async def list_templates():
        return {
            "dnb": {"name": "Drum & Bass", "tempo": 174, "key": "F#", "tracks": 8},
            "house": {"name": "House", "tempo": 124, "key": "G", "tracks": 8},
            "techno": {"name": "Techno", "tempo": 130, "key": "E", "tracks": 7},
            "ambient": {"name": "Ambient", "tempo": 80, "key": "C", "tracks": 6},
            "trap": {"name": "Trap", "tempo": 140, "key": "Bb", "tracks": 7},
        }

    @app.get("/api/recipes")
    async def list_recipes():
        return {
            "filter_sweep_up": {"name": "Filter Sweep ↑", "param": "Filter Freq", "curve": "exponential", "bars": 8},
            "filter_sweep_down": {"name": "Filter Sweep ↓", "param": "Filter Freq", "curve": "exponential_fall", "bars": 8},
            "filter_sweep_bandpass": {"name": "Bandpass Sweep", "param": "Filter Freq", "curve": "sine", "bars": 16},
            "sidechain_pump": {"name": "Sidechain Pump", "param": "Volume", "curve": "sidechain", "bars": 1},
            "sidechain_subtle": {"name": "Subtle Sidechain", "param": "Volume", "curve": "sidechain", "bars": 1},
            "reverb_swell": {"name": "Reverb Swell", "param": "Send A", "curve": "s_curve", "bars": 8},
            "dub_throw": {"name": "Dub Throw", "param": "Send B", "curve": "ping_pong", "bars": 4},
            "delay_feedback_rise": {"name": "Delay Feedback ↑", "param": "Feedback", "curve": "exponential_rise", "bars": 8},
            "pitch_riser": {"name": "Pitch Riser", "param": "Transpose", "curve": "linear", "bars": 8},
            "noise_riser": {"name": "Noise Riser", "param": "Filter Freq", "curve": "exponential", "bars": 8},
            "downlifter": {"name": "Downlifter", "param": "Transpose", "curve": "linear", "bars": 4},
            "stutter_gate": {"name": "Stutter Gate", "param": "Volume", "curve": "square", "bars": 2},
            "tape_stop": {"name": "Tape Stop", "param": "Transpose", "curve": "exponential_fall", "bars": 2},
            "formant_shift": {"name": "Formant Shift", "param": "Formant", "curve": "sine", "bars": 8},
            "auto_pan": {"name": "Auto Pan", "param": "Pan", "curve": "sine", "bars": 32},
            "width_swell": {"name": "Width Swell", "param": "Width", "curve": "s_curve", "bars": 8},
            "limiter_ceiling_ride": {"name": "Limiter Ride", "param": "Ceiling", "curve": "inverse_s_curve", "bars": 16},
        }

    @app.get("/api/fleet")
    async def get_fleet():
        return await call_tool_http("get_fleet_status", ToolCall(name="get_fleet_status"))


# =========================================================================
# MAIN ENTRY POINT
# =========================================================================

def main():
    """Run MCP server (stdio) or HTTP server"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        if not HTTP_AVAILABLE:
            print("FastAPI not installed. Run: pip install fastapi uvicorn")
            return
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8050)
    else:
        async def run_stdio():
            mcp = AbletonBrainMCP()
            print("[MCP] Ableton Brain MCP Server starting...")
            print("[MCP] Available tools: 83")
            print("[MCP] Connect to Ableton Remote Script on port 9877")
            print("[MCP] For HTTP dashboard: python mcp_server.py --http")
            await mcp.run_stdio()
        asyncio.run(run_stdio())


if __name__ == '__main__':
    main()
