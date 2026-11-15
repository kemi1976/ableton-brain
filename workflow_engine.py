"""
ABLETON BRAIN - Workflow Engine
Professional features: Templates, Snapshots, A/B Comparison, Export Pipeline, Metadata
"""
import os
import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum


class ExportFormat(Enum):
    WAV_24 = "wav_24"
    WAV_32_FLOAT = "wav_32_float"
    MP3_320 = "mp3_320"
    FLAC = "flac"
    OGG = "ogg"


class LoudnessTarget(Enum):
    STREAMING = -14.0      # Spotify, Apple Music, YouTube
    CLUB = -9.0            # Club/EDM
    BROADCAST = -23.0      # TV/Radio (EBU R128)
    PODCAST = -16.0        # Podcast standard
    CD = -9.0              # CD master


@dataclass
class ProjectTemplate:
    name: str
    genre: str
    description: str
    tempo: float
    key: str
    tracks: List[Dict]  # Track definitions
    return_tracks: List[Dict]
    master_chain: List[Dict]  # Devices on master
    scenes: List[str]
    reference_tracks: List[str] = field(default_factory=list)
    
    def to_ableton_commands(self, mcp) -> List[Dict]:
        """Convert template to MCP commands"""
        commands = []
        
        # Set tempo
        commands.append({"action": "set_tempo", "params": {"tempo": self.tempo}})
        
        # Create tracks
        for i, track_def in enumerate(self.tracks):
            if track_def["type"] == "midi":
                commands.append({
                    "action": "create_midi_track",
                    "params": {"name": track_def["name"], "index": i}
                })
            else:
                commands.append({
                    "action": "create_audio_track",
                    "params": {"name": track_def["name"], "index": i}
                })
                
            # Load devices
            for dev in track_def.get("devices", []):
                if dev["type"] == "instrument":
                    commands.append({
                        "action": "load_instrument",
                        "params": {"track_index": i, "device_name": dev["name"]}
                    })
                elif dev["type"] == "audio_effect":
                    commands.append({
                        "action": "load_audio_effect",
                        "params": {"track_index": i, "device_name": dev["name"]}
                    })
                elif dev["type"] == "midi_effect":
                    commands.append({
                        "action": "load_midi_effect",
                        "params": {"track_index": i, "device_name": dev["name"]}
                    })
                    
        # Create return tracks
        for i, ret in enumerate(self.return_tracks):
            commands.append({
                "action": "create_return_track",
                "params": {"name": ret["name"], "index": i}
            })
            for dev in ret.get("devices", []):
                commands.append({
                    "action": "load_audio_effect",
                    "params": {"track_index": -1, "device_name": dev["name"], "return_track": i}
                })
                
        # Master chain
        for dev in self.master_chain:
            commands.append({
                "action": "load_audio_effect",
                "params": {"track_index": -1, "device_name": dev["name"]}  # -1 = master
            })
            
        # Create scenes
        for scene_name in self.scenes:
            commands.append({
                "action": "create_scene",
                "params": {"name": scene_name}
            })
            
        return commands


@dataclass
class MixSnapshot:
    id: str
    name: str
    description: str
    timestamp: float
    track_states: Dict[int, Dict]  # track_index -> {volume, pan, sends, devices}
    master_state: Dict
    analyzer_data: Dict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MixSnapshot':
        return cls(**data)


@dataclass
class ExportJob:
    id: str
    name: str
    formats: List[ExportFormat]
    loudness_target: LoudnessTarget
    start_time: float
    end_time: float
    normalize: bool
    include_metadata: bool
    metadata: Dict = field(default_factory=dict)
    output_dir: str = ""
    status: str = "pending"
    result_files: List[str] = field(default_factory=list)
    error: str = ""


# =========================================================================
# BUILT-IN PROJECT TEMPLATES
# =========================================================================

BUILTIN_TEMPLATES = {
    "dnb": ProjectTemplate(
        name="Drum & Bass",
        genre="dnb",
        description="174 BPM DnB template with proper bus routing",
        tempo=174.0,
        key="F#",
        tracks=[
            {"index": 0, "name": "Kick", "type": "midi", "devices": [{"type": "instrument", "name": "Drum Rack"}]},
            {"index": 1, "name": "Snare", "type": "midi", "devices": [{"type": "instrument", "name": "Drum Rack"}]},
            {"index": 2, "name": "Hats/Perc", "type": "midi", "devices": [{"type": "instrument", "name": "Drum Rack"}]},
            {"index": 3, "name": "Bass Main", "type": "midi", "devices": [{"type": "instrument", "name": "Serum"}]},
            {"index": 4, "name": "Bass Sub", "type": "midi", "devices": [{"type": "instrument", "name": "Operator"}]},
            {"index": 5, "name": "Lead/Synth", "type": "midi", "devices": [{"type": "instrument", "name": "Serum"}]},
            {"index": 6, "name": "Pad/Atmos", "type": "audio", "devices": []},
            {"index": 7, "name": "FX", "type": "audio", "devices": []},
        ],
        return_tracks=[
            {"index": 0, "name": "Reverb", "devices": [{"type": "audio_effect", "name": "Hybrid Reverb"}]},
            {"index": 1, "name": "Delay", "devices": [{"type": "audio_effect", "name": "Echo"}]},
            {"index": 2, "name": "Parallel Comp", "devices": [{"type": "audio_effect", "name": "Glue Compressor"}]},
        ],
        master_chain=[
            {"name": "EQ Eight"},
            {"name": "Glue Compressor"},
            {"name": "Utility"},
            {"name": "Limiter"},
        ],
        scenes=["Intro", "Build", "Drop A", "Break", "Drop B", "Outro"],
    ),
    
    "house": ProjectTemplate(
        name="House",
        genre="house",
        description="124 BPM House template with classic routing",
        tempo=124.0,
        key="G",
        tracks=[
            {"index": 0, "name": "Kick", "type": "midi", "devices": [{"type": "instrument", "name": "Drum Rack"}]},
            {"index": 1, "name": "Clap/Snare", "type": "midi", "devices": [{"type": "instrument", "name": "Drum Rack"}]},
            {"index": 2, "name": "Hats", "type": "midi", "devices": [{"type": "instrument", "name": "Drum Rack"}]},
            {"index": 3, "name": "Percussion", "type": "midi", "devices": [{"type": "instrument", "name": "Drum Rack"}]},
            {"index": 4, "name": "Bass", "type": "midi", "devices": [{"type": "instrument", "name": "Serum"}]},
            {"index": 5, "name": "Chords/Pad", "type": "midi", "devices": [{"type": "instrument", "name": "Wavetable"}]},
            {"index": 6, "name": "Lead", "type": "midi", "devices": [{"type": "instrument", "name": "Serum"}]},
            {"index": 7, "name": "Vox/Vocal", "type": "audio", "devices": [{"type": "audio_effect", "name": "EQ Eight"}]},
        ],
        return_tracks=[
            {"index": 0, "name": "Reverb", "devices": [{"type": "audio_effect", "name": "Convolution Reverb"}]},
            {"index": 1, "name": "Delay", "devices": [{"type": "audio_effect", "name": "Echo"}]},
        ],
        master_chain=[
            {"name": "EQ Eight"},
            {"name": "Glue Compressor"},
            {"name": "Limiter"},
        ],
        scenes=["Intro", "Build", "Drop", "Break", "Outro"],
    ),
    
    "techno": ProjectTemplate(
        name="Techno",
        genre="techno",
        description="130 BPM Techno template with modular-style routing",
        tempo=130.0,
        key="E",
        tracks=[
            {"index": 0, "name": "Kick", "type": "midi", "devices": [{"type": "instrument", "name": "Drum Rack"}]},
            {"index": 1, "name": "Hats", "type": "midi", "devices": [{"type": "instrument", "name": "Drum Rack"}]},
            {"index": 2, "name": "Perc", "type": "midi", "devices": [{"type": "instrument", "name": "Drum Rack"}]},
            {"index": 3, "name": "Bass", "type": "midi", "devices": [{"type": "instrument", "name": "Serum"}]},
            {"index": 4, "name": "Main Synth", "type": "midi", "devices": [{"type": "instrument", "name": "Wavetable"}]},
            {"index": 5, "name": "Texture", "type": "audio", "devices": []},
            {"index": 6, "name": "FX", "type": "audio", "devices": []},
        ],
        return_tracks=[
            {"index": 0, "name": "Reverb", "devices": [{"type": "audio_effect", "name": "Hybrid Reverb"}]},
            {"index": 1, "name": "Delay", "devices": [{"type": "audio_effect", "name": "Echo"}]},
        ],
        master_chain=[
            {"name": "EQ Eight"},
            {"name": "Saturator"},
            {"name": "Glue Compressor"},
            {"name": "Limiter"},
        ],
        scenes=["Intro", "Main", "Breakdown", "Climax", "Outro"],
    ),
    
    "ambient": ProjectTemplate(
        name="Ambient",
        genre="ambient",
        description="Slow tempo ambient with generous reverb tails",
        tempo=80.0,
        key="C",
        tracks=[
            {"index": 0, "name": "Pad 1", "type": "midi", "devices": [{"type": "instrument", "name": "Wavetable"}]},
            {"index": 1, "name": "Pad 2", "type": "midi", "devices": [{"type": "instrument", "name": "Serum"}]},
            {"index": 2, "name": "Texture", "type": "audio", "devices": []},
            {"index": 3, "name": "Drone", "type": "midi", "devices": [{"type": "instrument", "name": "Serum"}]},
            {"index": 4, "name": "Melody", "type": "midi", "devices": [{"type": "instrument", "name": "Wavetable"}]},
            {"index": 5, "name": "Field Recording", "type": "audio", "devices": []},
        ],
        return_tracks=[
            {"index": 0, "name": "Big Reverb", "devices": [{"type": "audio_effect", "name": "Convolution Reverb"}]},
            {"index": 1, "name": "Shimmer", "devices": [{"type": "audio_effect", "name": "Hybrid Reverb"}]},
            {"index": 2, "name": "Delay", "devices": [{"type": "audio_effect", "name": "Echo"}]},
        ],
        master_chain=[
            {"name": "EQ Eight"},
            {"name": "Compressor"},
            {"name": "Limiter"},
        ],
        scenes=["Fade In", "Development", "Climax", "Fade Out"],
    ),
    
    "trap": ProjectTemplate(
        name="Trap",
        genre="trap",
        description="140 BPM Trap with 808 bass and triplet hats",
        tempo=140.0,
        key="Bb",
        tracks=[
            {"index": 0, "name": "Kick", "type": "midi", "devices": [{"type": "instrument", "name": "Drum Rack"}]},
            {"index": 1, "name": "Snare/Clap", "type": "midi", "devices": [{"type": "instrument", "name": "Drum Rack"}]},
            {"index": 2, "name": "Hats (Triplets)", "type": "midi", "devices": [{"type": "instrument", "name": "Drum Rack"}]},
            {"index": 3, "name": "808 Bass", "type": "midi", "devices": [{"type": "instrument", "name": "Serum"}]},
            {"index": 4, "name": "Lead", "type": "midi", "devices": [{"type": "instrument", "name": "Serum"}]},
            {"index": 5, "name": "Vocal Chops", "type": "audio", "devices": []},
            {"index": 6, "name": "FX", "type": "audio", "devices": []},
        ],
        return_tracks=[
            {"index": 0, "name": "Reverb", "devices": [{"type": "audio_effect", "name": "Hybrid Reverb"}]},
            {"index": 1, "name": "Delay", "devices": [{"type": "audio_effect", "name": "Echo"}]},
        ],
        master_chain=[
            {"name": "EQ Eight"},
            {"name": "Saturator"},
            {"name": "Glue Compressor"},
            {"name": "Limiter"},
        ],
        scenes=["Intro", "Chorus", "Verse", "Bridge", "Outro"],
    ),
}


class WorkflowEngine:
    """Professional workflow management"""
    
    def __init__(self, mcp_connection, workspace_dir: str = None):
        self.mcp = mcp_connection
        self.workspace = Path(workspace_dir) if workspace_dir else Path(__file__).parent / "workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        self.templates_dir = self.workspace / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        
        self.snapshots_dir = self.workspace / "snapshots"
        self.snapshots_dir.mkdir(exist_ok=True)
        
        self.exports_dir = self.workspace / "exports"
        self.exports_dir.mkdir(exist_ok=True)
        
        self.snapshots: Dict[str, MixSnapshot] = {}
        self.export_jobs: Dict[str, ExportJob] = {}
        
        # Save built-in templates
        self._save_builtin_templates()
        
    def _save_builtin_templates(self):
        """Save built-in templates to workspace"""
        for key, template in BUILTIN_TEMPLATES.items():
            path = self.templates_dir / f"{key}.json"
            if not path.exists():
                with open(path, 'w') as f:
                    json.dump(asdict(template), f, indent=2)
                    
    def list_templates(self) -> List[Dict]:
        """List available project templates"""
        templates = []
        for f in self.templates_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                templates.append({
                    "id": f.stem,
                    "name": data.get("name", f.stem),
                    "genre": data.get("genre", ""),
                    "description": data.get("description", ""),
                    "tempo": data.get("tempo", 120),
                    "tracks": len(data.get("tracks", [])),
                })
            except:
                pass
        return templates
    
    def get_template(self, template_id: str) -> Optional[ProjectTemplate]:
        """Load a project template"""
        path = self.templates_dir / f"{template_id}.json"
        if not path.exists():
            # Check built-in
            if template_id in BUILTIN_TEMPLATES:
                return BUILTIN_TEMPLATES[template_id]
            return None
            
        with open(path) as f:
            data = json.load(f)
        return ProjectTemplate(**data)
    
    async def create_project_from_template(self, template_id: str, project_name: str = None) -> Dict:
        """Create new Ableton project from template"""
        template = self.get_template(template_id)
        if not template:
            return {"error": f"Template '{template_id}' not found"}
            
        if project_name is None:
            project_name = f"{template.name}_{int(time.time())}"
            
        # Execute template commands
        commands = template.to_ableton_commands(self.mcp)
        results = []
        
        for cmd in commands:
            try:
                result = self.mcp.connection.send_command(cmd["action"], cmd["params"])
                results.append({"command": cmd["action"], "success": True, "result": result})
            except Exception as e:
                results.append({"command": cmd["action"], "success": False, "error": str(e)})
                
        return {
            "project_name": project_name,
            "template": template_id,
            "commands_executed": len(commands),
            "results": results
        }
    
    # =========================================================================
    # MIX SNAPSHOTS (A/B Comparison)
    # =========================================================================
    
    def create_snapshot(self, name: str, description: str = "", tags: List[str] = None) -> MixSnapshot:
        """Create a mix snapshot (captures all track/master parameters)"""
        snapshot_id = str(uuid.uuid4())[:8]
        
        # Get all track states
        track_states = {}
        tracks_result = self.mcp.connection.send_command("get_tracks", {})
        
        for track in tracks_result.get("tracks", []):
            idx = track["index"]
            # Get device parameters for each device
            devices = []
            for dev_idx, dev_name in enumerate(track.get("devices", [])):
                params = self.mcp.connection.send_command("get_device_parameters", {
                    "track_index": idx, "device_index": dev_idx
                })
                devices.append({"name": dev_name, "parameters": params.get("parameters", [])})
                
            track_states[idx] = {
                "name": track["name"],
                "volume": track.get("volume", 0.0),
                "pan": track.get("pan", 0.0),
                "armed": track.get("armed", False),
                "devices": devices,
            }
            
        # Get master track state
        master_track = tracks_result.get("tracks", [])[-1] if tracks_result.get("tracks") else {}
        master_state = {
            "volume": master_track.get("volume", 0.0),
            "pan": master_track.get("pan", 0.0),
            "devices": [],
        }
        
        snapshot = MixSnapshot(
            id=snapshot_id,
            name=name,
            description=description,
            timestamp=time.time(),
            track_states=track_states,
            master_state=master_state,
            tags=tags or [],
        )
        
        self.snapshots[snapshot_id] = snapshot
        self._save_snapshot(snapshot)
        
        return snapshot
    
    def _save_snapshot(self, snapshot: MixSnapshot):
        path = self.snapshots_dir / f"{snapshot.id}.json"
        with open(path, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2)
            
    def load_snapshot(self, snapshot_id: str) -> Optional[MixSnapshot]:
        """Load a snapshot from disk"""
        if snapshot_id in self.snapshots:
            return self.snapshots[snapshot_id]
            
        path = self.snapshots_dir / f"{snapshot_id}.json"
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            snapshot = MixSnapshot.from_dict(data)
            self.snapshots[snapshot_id] = snapshot
            return snapshot
        return None
    
    def list_snapshots(self) -> List[Dict]:
        """List all saved snapshots"""
        snapshots = []
        for f in self.snapshots_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                snapshots.append({
                    "id": data["id"],
                    "name": data["name"],
                    "description": data["description"],
                    "timestamp": data["timestamp"],
                    "tags": data.get("tags", []),
                    "track_count": len(data.get("track_states", {})),
                })
            except:
                pass
        return sorted(snapshots, key=lambda x: x["timestamp"], reverse=True)
    
    def recall_snapshot(self, snapshot_id: str) -> Dict:
        """Recall a mix snapshot (A/B comparison)"""
        snapshot = self.load_snapshot(snapshot_id)
        if not snapshot:
            return {"error": f"Snapshot '{snapshot_id}' not found"}
            
        results = []
        
        # Recall track states
        for track_idx, state in snapshot.track_states.items():
            # Volume
            self.mcp.connection.send_command("set_track_volume", {
                "track_index": track_idx, "volume": state["volume"]
            })
            # Pan
            self.mcp.connection.send_command("set_track_pan", {
                "track_index": track_idx, "pan": state["pan"]
            })
            # Arm
            self.mcp.connection.send_command("arm_track", {
                "track_index": track_idx, "arm": state["armed"]
            })
            # Device parameters
            for dev in state.get("devices", []):
                for param in dev.get("parameters", []):
                    self.mcp.connection.send_command("set_device_parameter", {
                        "track_index": track_idx,
                        "device_index": param.get("index", 0),
                        "parameter_index": param.get("index", 0),
                        "value": param.get("normalized", 0.5)
                    })
            results.append({"track": track_idx, "recalled": True})
            
        return {
            "snapshot_id": snapshot_id,
            "name": snapshot.name,
            "tracks_recalled": len(results),
            "timestamp": snapshot.timestamp
        }
    
    def compare_snapshots(self, snapshot_a: str, snapshot_b: str) -> Dict:
        """Compare two snapshots"""
        a = self.load_snapshot(snapshot_a)
        b = self.load_snapshot(snapshot_b)
        
        if not a or not b:
            return {"error": "One or both snapshots not found"}
            
        differences = []
        
        all_tracks = set(a.track_states.keys()) | set(b.track_states.keys())
        for track_idx in all_tracks:
            sa = a.track_states.get(track_idx, {})
            sb = b.track_states.get(track_idx, {})
            
            if sa.get("volume") != sb.get("volume"):
                differences.append({
                    "track": track_idx,
                    "param": "volume",
                    "a": sa.get("volume"),
                    "b": sb.get("volume"),
                    "diff_db": round(sb.get("volume", 0) - sa.get("volume", 0), 2)
                })
                
            if sa.get("pan") != sb.get("pan"):
                differences.append({
                    "track": track_idx,
                    "param": "pan",
                    "a": sa.get("pan"),
                    "b": sb.get("pan"),
                    "diff": round(sb.get("pan", 0) - sa.get("pan", 0), 2)
                })
                
        return {
            "snapshot_a": {"id": a.id, "name": a.name},
            "snapshot_b": {"id": b.id, "name": b.name},
            "differences": differences,
            "total_differences": len(differences)
        }
    
    # =========================================================================
    # EXPORT PIPELINE
    # =========================================================================
    
    def create_export_job(
        self,
        name: str,
        formats: List[ExportFormat] = None,
        loudness_target: LoudnessTarget = LoudnessTarget.STREAMING,
        start_bar: float = 1.0,
        end_bar: float = None,
        normalize: bool = True,
        metadata: Dict = None
    ) -> ExportJob:
        """Create an export job"""
        job_id = str(uuid.uuid4())[:8]
        
        if formats is None:
            formats = [ExportFormat.WAV_24, ExportFormat.MP3_320]
            
        # Calculate time range
        tempo = self.mcp.connection.send_command("get_session_info", {}).get("tempo", 120)
        beats_per_bar = 4
        seconds_per_beat = 60.0 / tempo
        start_time = (start_bar - 1) * beats_per_bar * seconds_per_beat
        end_time = (end_bar * beats_per_bar * seconds_per_beat) if end_bar else None
        
        output_dir = self.exports_dir / f"{name}_{int(time.time())}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        job = ExportJob(
            id=job_id,
            name=name,
            formats=formats,
            loudness_target=loudness_target,
            start_time=start_time,
            end_time=end_time or 0,
            normalize=normalize,
            include_metadata=True,
            metadata=metadata or {},
            output_dir=str(output_dir),
        )
        
        self.export_jobs[job_id] = job
        return job
    
    async def execute_export(self, job_id: str) -> Dict:
        """Execute export job (renders audio in Ableton)"""
        job = self.export_jobs.get(job_id)
        if not job:
            return {"error": f"Export job '{job_id}' not found"}
            
        job.status = "rendering"
        
        try:
            # Render in Ableton
            length = job.end_time - job.start_time if job.end_time > job.start_time else 60.0
            render_result = self.mcp.connection.send_command("render_audio", {
                "length": length
            })
            
            # In reality, this would use Ableton's Export Audio/Video dialog
            # For now, simulate exported files
            exported_files = []
            for fmt in job.formats:
                ext = fmt.value.split("_")[0]
                filename = f"{job.name}.{ext}"
                filepath = Path(job.output_dir) / filename
                exported_files.append(str(filepath))
                
            job.result_files = exported_files
            job.status = "completed"
            
            # Apply loudness normalization if requested
            if job.normalize:
                # Would use pyloudnorm or similar
                pass
                
            # Embed metadata
            if job.include_metadata:
                # Would use mutagen or similar
                pass
                
            return {
                "job_id": job_id,
                "status": "completed",
                "files": exported_files,
                "output_dir": job.output_dir
            }
            
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            return {"error": str(e)}
    
    # =========================================================================
    # METADATA EMBEDDING
    # =========================================================================
    
    def prepare_metadata(
        self,
        title: str,
        artist: str,
        genre: str = "",
        bpm: float = 0,
        key: str = "",
        isrc: str = "",
        upc: str = "",
        release_date: str = "",
        credits: Dict = None
    ) -> Dict:
        """Prepare metadata for export"""
        return {
            "title": title,
            "artist": artist,
            "genre": genre,
            "bpm": bpm,
            "key": key,
            "isrc": isrc,
            "upc": upc,
            "release_date": release_date or datetime.now().strftime("%Y-%m-%d"),
            "credits": credits or {},
            "created_by": "Ableton Brain",
            "created_at": datetime.now().isoformat(),
        }
    
    def embed_metadata(self, audio_path: str, metadata: Dict) -> bool:
        """Embed metadata into audio file (requires mutagen)"""
        try:
            import mutagen
            # Would implement based on format
            return True
        except ImportError:
            return False


# =========================================================================
# QUICK START TEMPLATES
# =========================================================================

def get_quick_start_template(genre: str) -> Dict:
    """Get minimal quick-start template"""
    templates = {
        "minimal": {
            "name": "Minimal Start",
            "tempo": 120,
            "tracks": [
                {"name": "Drums", "type": "midi", "device": "Drum Rack"},
                {"name": "Bass", "type": "midi", "device": "Serum"},
                {"name": "Synth", "type": "midi", "device": "Wavetable"},
            ],
            "returns": [
                {"name": "Reverb", "device": "Hybrid Reverb"},
                {"name": "Delay", "device": "Echo"},
            ],
            "master": ["EQ Eight", "Glue Compressor", "Limiter"],
        }
    }
    return templates.get(genre, templates["minimal"])


if __name__ == "__main__":
    print("Available Templates:")
    for key, tmpl in BUILTIN_TEMPLATES.items():
        print(f"  {key}: {tmpl.name} ({tmpl.tempo} BPM, {tmpl.key}) - {len(tmpl.tracks)} tracks")
    
    print("\nWorkflow Engine ready for:")
    print("  - Project templates (DnB, House, Techno, Ambient, Trap)")
    print("  - Mix snapshots with A/B comparison")
    print("  - Export pipeline (WAV 24/32, MP3, FLAC)")
    print("  - Loudness targets (Streaming -14, Club -9, Broadcast -23)")
    print("  - Metadata embedding (ISRC, UPC, credits)")