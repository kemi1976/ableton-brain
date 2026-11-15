"""
Ableton Brain - Phase 2: Reaper Adapter
Reaper-specific implementation using ReaScript API
"""

import asyncio
import json
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from core.adapters.base_adapter import BaseDAWAdapter, TrackType, TrackInfo, DeviceInfo, ProjectInfo


class ReaperAdapter(BaseDAWAdapter):
    """Reaper-specific implementation using ReaScript (Python) API"""
    
    def __init__(self):
        super().__init__('Reaper')
        self.reaper_path = self._find_reaper()
        self.script_dir = Path(__file__).parent / "reascripts"
        self.script_dir.mkdir(exist_ok=True)
        self._api_available = False
    
    def _find_reaper(self) -> Optional[str]:
        """Find Reaper installation"""
        possible_paths = [
            r"C:\Program Files\REAPER\reaper.exe",
            r"C:\Program Files (x86)\REAPER\reaper.exe",
            os.path.expandvars(r"%APPDATA%\REAPER\reaper.exe"),
        ]
        for path in possible_paths:
            if Path(path).exists():
                return path
        return None
    
    def _create_reascript(self, script_content: str) -> str:
        """Create a temporary ReaScript file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script_content)
            return f.name
    
    async def _run_reascript(self, script: str) -> Dict:
        """Execute a ReaScript and return JSON result"""
        if not self.reaper_path:
            return {"success": False, "error": "Reaper not found"}
        
        script_path = self._create_reascript(script)
        
        try:
            # Run Reaper with script (using -nosplash for faster startup)
            cmd = [self.reaper_path, "-nosplash", "-script", script_path]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            
            # Clean up temp script
            try:
                os.unlink(script_path)
            except:
                pass
            
            if process.returncode == 0:
                try:
                    return json.loads(stdout.decode().strip())
                except json.JSONDecodeError:
                    return {"success": True, "output": stdout.decode().strip()}
            else:
                return {"success": False, "error": stderr.decode().strip()}
                
        except asyncio.TimeoutError:
            return {"success": False, "error": "ReaScript timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def connect(self) -> bool:
        """Test Reaper connection"""
        if not self.reaper_path:
            return False
        
        # Simple test script
        test_script = '''
import sys
sys.path.insert(0, r"C:\\Program Files\\REAPER\\Scripts")  # Adjust as needed

try:
    import reaper_python as RPR
    print(json.dumps({"success": True, "version": RPR.GetAppVersion()}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
'''
        result = await self._run_reascript(test_script)
        self._api_available = result.get("success", False)
        self.connected = self._api_available
        return self.connected
    
    async def disconnect(self) -> bool:
        self.connected = False
        return True
    
    # Project operations
    async def get_project_info(self) -> Optional[ProjectInfo]:
        script = '''
import json
import sys
try:
    import reaper_python as RPR
    
    # Get project info
    proj = RPR.EnumProjects(-1, "")
    name, _ = RPR.GetProjectName(proj, "")
    path = RPR.GetProjectPath("")
    tempo = RPR.Master_GetTempo()
    
    # Get tracks
    tracks = []
    for i in range(RPR.CountTracks(proj)):
        track = RPR.GetTrack(proj, i)
        _, name = RPR.GetTrackName(track, "")
        _, guid = RPR.GetTrackGUID(track)
        volume = RPR.GetMediaTrackInfo_Value(track, "D_VOL")
        pan = RPR.GetMediaTrackInfo_Value(track, "D_PAN")
        mute = RPR.GetMediaTrackInfo_Value(track, "B_MUTE")
        solo = RPR.GetMediaTrackInfo_Value(track, "B_SOLO")
        rec_arm = RPR.GetMediaTrackInfo_Value(track, "I_RECARM")
        
        tracks.append({
            "id": guid,
            "name": name,
            "type": "midi" if RPR.GetMediaTrackInfo_Value(track, "I_RECMODE") == 1 else "audio",
            "armed": bool(rec_arm),
            "solo": bool(solo),
            "mute": bool(mute),
            "volume": volume,
            "pan": pan
        })
    
    print(json.dumps({
        "success": True,
        "name": name,
        "path": path,
        "tempo": tempo,
        "tracks": tracks
    }))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
'''
        result = await self._run_reascript(script)
        if result.get("success"):
            self.project = ProjectInfo(
                name=result["name"],
                path=result["path"],
                tempo=result["tempo"],
                tracks=[TrackInfo(**t) for t in result["tracks"]]
            )
            return self.project
        return None
    
    async def create_track(self, name: str, track_type: TrackType = TrackType.MIDI) -> str:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    
    proj = RPR.EnumProjects(-1, "")
    idx = RPR.CountTracks(proj)
    RPR.InsertTrackAtIndex(idx, True)
    track = RPR.GetTrack(proj, idx)
    RPR.GetSetMediaTrackInfo_String(track, "P_NAME", "{name}", True)
    
    # Set track type
    if "{track_type.value}" == "midi":
        RPR.SetMediaTrackInfo_Value(track, "I_RECMODE", 1)  # MIDI
    else:
        RPR.SetMediaTrackInfo_Value(track, "I_RECMODE", 0)  # Audio
    
    _, guid = RPR.GetTrackGUID(track)
    print(json.dumps({{"success": True, "track_id": guid, "index": idx}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        if result.get("success"):
            return result["track_id"]
        raise Exception(result.get("error", "Failed to create track"))
    
    async def delete_track(self, track_id: str) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    for i in range(RPR.CountTracks(proj)):
        track = RPR.GetTrack(proj, i)
        _, guid = RPR.GetTrackGUID(track)
        if guid == "{track_id}":
            RPR.DeleteTrack(track)
            print(json.dumps({{"success": True}}))
            break
    else:
        print(json.dumps({{"success": False, "error": "Track not found"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def rename_track(self, track_id: str, name: str) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    for i in range(RPR.CountTracks(proj)):
        track = RPR.GetTrack(proj, i)
        _, guid = RPR.GetTrackGUID(track)
        if guid == "{track_id}":
            RPR.GetSetMediaTrackInfo_String(track, "P_NAME", "{name}", True)
            print(json.dumps({{"success": True}}))
            break
    else:
        print(json.dumps({{"success": False, "error": "Track not found"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    # Track controls
    async def arm_track(self, track_id: str, arm: bool = True) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    for i in range(RPR.CountTracks(proj)):
        track = RPR.GetTrack(proj, i)
        _, guid = RPR.GetTrackGUID(track)
        if guid == "{track_id}":
            RPR.SetMediaTrackInfo_Value(track, "I_RECARM", 1 if {str(arm).lower()} else 0)
            print(json.dumps({{"success": True}}))
            break
    else:
        print(json.dumps({{"success": False, "error": "Track not found"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def solo_track(self, track_id: str, solo: bool = True) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    for i in range(RPR.CountTracks(proj)):
        track = RPR.GetTrack(proj, i)
        _, guid = RPR.GetTrackGUID(track)
        if guid == "{track_id}":
            RPR.SetMediaTrackInfo_Value(track, "B_SOLO", 1 if {str(solo).lower()} else 0)
            print(json.dumps({{"success": True}}))
            break
    else:
        print(json.dumps({{"success": False, "error": "Track not found"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def mute_track(self, track_id: str, mute: bool = True) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    for i in range(RPR.CountTracks(proj)):
        track = RPR.GetTrack(proj, i)
        _, guid = RPR.GetTrackGUID(track)
        if guid == "{track_id}":
            RPR.SetMediaTrackInfo_Value(track, "B_MUTE", 1 if {str(mute).lower()} else 0)
            print(json.dumps({{"success": True}}))
            break
    else:
        print(json.dumps({{"success": False, "error": "Track not found"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def set_track_volume(self, track_id: str, volume: float) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    for i in range(RPR.CountTracks(proj)):
        track = RPR.GetTrack(proj, i)
        _, guid = RPR.GetTrackGUID(track)
        if guid == "{track_id}":
            RPR.SetMediaTrackInfo_Value(track, "D_VOL", {volume})
            print(json.dumps({{"success": True}}))
            break
    else:
        print(json.dumps({{"success": False, "error": "Track not found"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def set_track_pan(self, track_id: str, pan: float) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    for i in range(RPR.CountTracks(proj)):
        track = RPR.GetTrack(proj, i)
        _, guid = RPR.GetTrackGUID(track)
        if guid == "{track_id}":
            RPR.SetMediaTrackInfo_Value(track, "D_PAN", {pan})
            print(json.dumps({{"success": True}}))
            break
    else:
        print(json.dumps({{"success": False, "error": "Track not found"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    # Instruments and effects
    async def load_instrument(self, track_id: str, instrument_name: str, 
                             preset: Optional[str] = None) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    for i in range(RPR.CountTracks(proj)):
        track = RPR.GetTrack(proj, i)
        _, guid = RPR.GetTrackGUID(track)
        if guid == "{track_id}":
            # Add instrument FX
            fx_idx = RPR.TrackFX_AddByName(track, "{instrument_name}", False, -1)
            if fx_idx >= 0 and "{preset or ''}":
                RPR.TrackFX_SetPreset(track, fx_idx, "{preset}")
            print(json.dumps({{"success": True, "fx_index": fx_idx}}))
            break
    else:
        print(json.dumps({{"success": False, "error": "Track not found"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def add_audio_effect(self, track_id: str, effect_name: str, 
                              position: int = -1) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    for i in range(RPR.CountTracks(proj)):
        track = RPR.GetTrack(proj, i)
        _, guid = RPR.GetTrackGUID(track)
        if guid == "{track_id}":
            fx_idx = RPR.TrackFX_AddByName(track, "{effect_name}", False, {position})
            print(json.dumps({{"success": True, "fx_index": fx_idx}}))
            break
    else:
        print(json.dumps({{"success": False, "error": "Track not found"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def add_midi_effect(self, track_id: str, effect_name: str,
                             position: int = -1) -> bool:
        # In Reaper, MIDI effects are just FX on the track
        return await self.add_audio_effect(track_id, effect_name, position)
    
    async def set_device_parameter(self, track_id: str, device_id: str,
                                  param_name: str, value: float) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    for i in range(RPR.CountTracks(proj)):
        track = RPR.GetTrack(proj, i)
        _, guid = RPR.GetTrackGUID(track)
        if guid == "{track_id}":
            # Find FX by name
            for fx_i in range(RPR.TrackFX_GetCount(track)):
                _, fx_name = RPR.TrackFX_GetFXName(track, fx_i, "", 256)
                if "{device_id}" in fx_name:
                    # Find parameter
                    for param_i in range(RPR.TrackFX_GetNumParams(track, fx_i)):
                        _, p_name = RPR.TrackFX_GetParamName(track, fx_i, param_i, "", 256)
                        if p_name == "{param_name}":
                            RPR.TrackFX_SetParamNormalized(track, fx_i, param_i, {value})
                            print(json.dumps({{"success": True}}))
                            break
                    break
            else:
                print(json.dumps({{"success": False, "error": "Device not found"}}))
            break
    else:
        print(json.dumps({{"success": False, "error": "Track not found"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def get_device_parameters(self, track_id: str, device_id: str) -> Dict:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    params = {{}}
    for i in range(RPR.CountTracks(proj)):
        track = RPR.GetTrack(proj, i)
        _, guid = RPR.GetTrackGUID(track)
        if guid == "{track_id}":
            for fx_i in range(RPR.TrackFX_GetCount(track)):
                _, fx_name = RPR.TrackFX_GetFXName(track, fx_i, "", 256)
                if "{device_id}" in fx_name:
                    for param_i in range(RPR.TrackFX_GetNumParams(track, fx_i)):
                        _, p_name = RPR.TrackFX_GetParamName(track, fx_i, param_i, "", 256)
                        val = RPR.TrackFX_GetParamNormalized(track, fx_i, param_i)
                        params[p_name] = val
                    break
                    break
            print(json.dumps({{"success": True, "parameters": params}}))
            break
    else:
        print(json.dumps({{"success": False, "error": "Track not found"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        if result.get("success"):
            return result.get("parameters", {})
        return {}
    
    # Transport
    async def start_playback(self) -> bool:
        script = '''
import json
import sys
try:
    import reaper_python as RPR
    RPR.Main_OnCommand(1007, 0)  # Play
    print(json.dumps({"success": True}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def stop_playback(self) -> bool:
        script = '''
import json
import sys
try:
    import reaper_python as RPR
    RPR.Main_OnCommand(1016, 0)  # Stop
    print(json.dumps({"success": True}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def set_tempo(self, tempo: float) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    RPR.Master_SetTempo({tempo}, False)
    print(json.dumps({{"success": True}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def set_time_signature(self, numerator: int, denominator: int) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    RPR.SetTimeSignature(proj, {numerator}, {denominator}, 0, 0, False)
    print(json.dumps({{"success": True}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    # MIDI clips
    async def create_clip(self, track_id: str, start_time: float, 
                         duration: float, notes: List[Dict]) -> str:
        # Build note insertion script
        notes_json = json.dumps(notes)
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    clip_guid = ""
    for i in range(RPR.CountTracks(proj)):
        track = RPR.GetTrack(proj, i)
        _, guid = RPR.GetTrackGUID(track)
        if guid == "{track_id}":
            # Create new MIDI item
            item = RPR.CreateNewMIDIItemInProj(track, {start_time}, {start_time + duration}, False)
            take = RPR.GetActiveTake(item)
            if take:
                _, guid = RPR.GetSetMediaItemTakeInfo_String(take, "P_GUID", "", False)
                clip_guid = guid
                
                # Add notes
                for note in {notes_json}:
                    RPR.MIDI_InsertNote(take, False, False, 
                                      int(note["start"] * 960),  # Convert to ticks
                                      int((note["start"] + note["duration"]) * 960),
                                      note["channel"], note["pitch"], note["velocity"], False)
                RPR.MIDI_Sort(take)
            break
    print(json.dumps({{"success": True, "clip_id": clip_guid}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        if result.get("success"):
            return result.get("clip_id", "")
        raise Exception(result.get("error", "Failed to create clip"))
    
    async def quantize_clip(self, clip_id: str, grid: str = "1/16") -> bool:
        # Grid mapping: 1/4=960, 1/8=480, 1/16=240, 1/32=120
        grid_ticks = {"1/4": 960, "1/8": 480, "1/16": 240, "1/32": 120}.get(grid, 240)
        
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    proj = RPR.EnumProjects(-1, "")
    for i in range(RPR.CountMediaItems(0)):
        item = RPR.GetMediaItem(0, i)
        take = RPR.GetActiveTake(item)
        if take:
            _, guid = RPR.GetSetMediaItemTakeInfo_String(take, "P_GUID", "", False)
            if guid == "{clip_id}":
                RPR.MIDI_Quantize(take, {grid_ticks}, 1.0, True, True, False, False, 0)
                print(json.dumps({{"success": True}}))
                break
        else:
            print(json.dumps({{"success": False, "error": "Clip not found"}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    # Export
    async def export_audio(self, output_path: str, format: str = "wav",
                          sample_rate: int = 44100, bit_depth: int = 24) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    # Set render settings
    RPR.GetSetProjectInfo_String(0, "RENDER_FILE", "{output_path}", True)
    RPR.GetSetProjectInfo(0, "RENDER_SRATE", {sample_rate}, True)
    RPR.GetSetProjectInfo(0, "RENDER_BITDEPTH", {bit_depth}, True)
    
    # Render
    RPR.Main_OnCommand(42230, 0)  # Render project
    print(json.dumps({{"success": True}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def save_project(self, path: Optional[str] = None) -> bool:
        script = f'''
import json
import sys
try:
    import reaper_python as RPR
    if "{path or ''}":
        RPR.Main_SaveProject(0, "{path}", False)
    else:
        RPR.Main_OnCommand(40026, 0)  # Save project
    print(json.dumps({{"success": True}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def undo(self) -> bool:
        script = '''
import json
import sys
try:
    import reaper_python as RPR
    RPR.Main_OnCommand(40029, 0)  # Undo
    print(json.dumps({"success": True}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)
    
    async def redo(self) -> bool:
        script = '''
import json
import sys
try:
    import reaper_python as RPR
    RPR.Main_OnCommand(40030, 0)  # Redo
    print(json.dumps({"success": True}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
'''
        result = await self._run_reascript(script)
        return result.get("success", False)


if __name__ == "__main__":
    print("Reaper Adapter - Phase 2")
    print("Requires Reaper with ReaScript Python API enabled")
    print("Install: Options -> Preferences -> Plug-ins -> ReaScript -> Enable Python")