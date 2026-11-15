"""
Ableton Brain - Phase 3: Universal Project Format
Cross-DAW project interchange format (JSON-based)
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import base64


class ProjectVersion(Enum):
    V1 = "1.0"


@dataclass
class UniversalProject:
    """Universal project format - DAW agnostic"""
    name: str
    version: str = "1.0"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tempo: float = 120.0
    time_signature_numerator: int = 4
    time_signature_denominator: int = 4
    sample_rate: int = 44100
    bit_depth: int = 24
    tracks: List['UniversalTrack'] = field(default_factory=list)
    markers: List['UniversalMarker'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    daw_specific: Dict[str, Any] = field(default_factory=dict)  # DAW-specific extensions


@dataclass
class UniversalTrack:
    """Universal track format"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Track"
    type: str = "midi"  # midi, audio, return, master, group
    color: Optional[str] = None
    volume: float = 1.0
    pan: float = 0.0
    mute: bool = False
    solo: bool = False
    armed: bool = False
    input_routing: str = ""
    output_routing: str = ""
    devices: List['UniversalDevice'] = field(default_factory=list)
    clips: List['UniversalClip'] = field(default_factory=list)
    automation: List['UniversalAutomation'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UniversalDevice:
    """Universal device/plugin format"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    type: str = "instrument"  # instrument, audio_effect, midi_effect
    plugin_format: str = "vst3"  # vst3, vst, au, aax, lv2, clap
    plugin_id: str = ""  # Plugin unique identifier
    version: str = ""
    enabled: bool = True
    parameters: Dict[str, float] = field(default_factory=dict)
    preset_name: Optional[str] = None
    preset_data: Optional[str] = None  # Base64 encoded preset
    position: int = -1  # Position in device chain


@dataclass
class UniversalClip:
    """Universal clip format"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Clip"
    track_id: str = ""
    start_time: float = 0.0  # In beats
    duration: float = 4.0  # In beats
    loop_start: float = 0.0
    loop_end: float = 4.0
    is_looping: bool = False
    notes: List['UniversalNote'] = field(default_factory=list)
    audio_file: Optional[str] = None  # Path or base64 for audio clips
    warp_markers: List['WarpMarker'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UniversalNote:
    """Universal MIDI note"""
    pitch: int = 60  # MIDI note number (0-127)
    velocity: int = 100  # 0-127
    start_time: float = 0.0  # In beats from clip start
    duration: float = 1.0  # In beats
    channel: int = 0  # 0-15
    muted: bool = False


@dataclass
class WarpMarker:
    """Audio warp marker"""
    beat_time: float = 0.0
    sample_time: float = 0.0


@dataclass
class UniversalMarker:
    """Project marker/locator"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    time: float = 0.0  # In beats
    type: str = "marker"  # marker, loop_start, loop_end, section
    color: Optional[str] = None


@dataclass
class UniversalAutomation:
    """Automation envelope"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parameter_path: str = ""  # e.g., "track_1/device_0/mixer/volume"
    points: List['AutomationPoint'] = field(default_factory=list)


@dataclass
class AutomationPoint:
    """Automation breakpoint"""
    time: float = 0.0  # In beats
    value: float = 0.0
    shape: str = "linear"  # linear, curve, step


class UniversalProjectSerializer:
    """Serialize/deserialize universal project format"""
    
    @staticmethod
    def to_json(project: UniversalProject, indent: int = 2) -> str:
        """Convert project to JSON string"""
        return json.dumps(asdict(project), indent=indent)
    
    @staticmethod
    def from_json(json_str: str) -> UniversalProject:
        """Create project from JSON string"""
        data = json.loads(json_str)
        return UniversalProjectSerializer._deserialize_project(data)
    
    @staticmethod
    def save(project: UniversalProject, filepath: Path) -> bool:
        """Save project to file"""
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(UniversalProjectSerializer.to_json(project))
            return True
        except Exception as e:
            print(f"Save error: {e}")
            return False
    
    @staticmethod
    def load(filepath: Path) -> Optional[UniversalProject]:
        """Load project from file"""
        try:
            with open(filepath, 'r') as f:
                return UniversalProjectSerializer.from_json(f.read())
        except Exception as e:
            print(f"Load error: {e}")
            return None
    
    @staticmethod
    def _deserialize_project(data: Dict) -> UniversalProject:
        """Deserialize project from dict"""
        project = UniversalProject(
            name=data.get('name', 'Untitled'),
            version=data.get('version', '1.0'),
            id=data.get('id', str(uuid.uuid4())),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            tempo=data.get('tempo', 120.0),
            time_signature_numerator=data.get('time_signature_numerator', 4),
            time_signature_denominator=data.get('time_signature_denominator', 4),
            sample_rate=data.get('sample_rate', 44100),
            bit_depth=data.get('bit_depth', 24),
            metadata=data.get('metadata', {}),
            daw_specific=data.get('daw_specific', {})
        )
        
        # Tracks
        for track_data in data.get('tracks', []):
            project.tracks.append(UniversalProjectSerializer._deserialize_track(track_data))
        
        # Markers
        for marker_data in data.get('markers', []):
            project.markers.append(UniversalMarker(**marker_data))
        
        return project
    
    @staticmethod
    def _deserialize_track(data: Dict) -> UniversalTrack:
        track = UniversalTrack(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', 'New Track'),
            type=data.get('type', 'midi'),
            color=data.get('color'),
            volume=data.get('volume', 1.0),
            pan=data.get('pan', 0.0),
            mute=data.get('mute', False),
            solo=data.get('solo', False),
            armed=data.get('armed', False),
            input_routing=data.get('input_routing', ''),
            output_routing=data.get('output_routing', ''),
            metadata=data.get('metadata', {})
        )
        
        # Devices
        for device_data in data.get('devices', []):
            track.devices.append(UniversalProjectSerializer._deserialize_device(device_data))
        
        # Clips
        for clip_data in data.get('clips', []):
            track.clips.append(UniversalProjectSerializer._deserialize_clip(clip_data))
        
        # Automation
        for auto_data in data.get('automation', []):
            track.automation.append(UniversalProjectSerializer._deserialize_automation(auto_data))
        
        return track
    
    @staticmethod
    def _deserialize_device(data: Dict) -> UniversalDevice:
        return UniversalDevice(**data)
    
    @staticmethod
    def _deserialize_clip(data: Dict) -> UniversalClip:
        clip = UniversalClip(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', 'Clip'),
            track_id=data.get('track_id', ''),
            start_time=data.get('start_time', 0.0),
            duration=data.get('duration', 4.0),
            loop_start=data.get('loop_start', 0.0),
            loop_end=data.get('loop_end', 4.0),
            is_looping=data.get('is_looping', False),
            audio_file=data.get('audio_file'),
            metadata=data.get('metadata', {})
        )
        
        for note_data in data.get('notes', []):
            clip.notes.append(UniversalNote(**note_data))
        
        for warp_data in data.get('warp_markers', []):
            clip.warp_markers.append(WarpMarker(**warp_data))
        
        return clip
    
    @staticmethod
    def _deserialize_automation(data: Dict) -> UniversalAutomation:
        auto = UniversalAutomation(
            id=data.get('id', str(uuid.uuid4())),
            parameter_path=data.get('parameter_path', '')
        )
        for point_data in data.get('points', []):
            auto.points.append(AutomationPoint(**point_data))
        return auto


# DAW-specific exporters/importers
class DAWProjectConverter:
    """Base class for DAW-specific converters"""
    
    def export_to_universal(self, daw_project_path: Path) -> UniversalProject:
        """Import from DAW format to universal"""
        raise NotImplementedError
    
    def import_from_universal(self, project: UniversalProject, output_path: Path) -> bool:
        """Export from universal to DAW format"""
        raise NotImplementedError


class AbletonProjectConverter(DAWProjectConverter):
    """Ableton Live (.als) converter"""
    
    def export_to_universal(self, daw_project_path: Path) -> UniversalProject:
        # .als files are gzipped XML
        import gzip
        import xml.etree.ElementTree as ET
        
        with gzip.open(daw_project_path, 'rb') as f:
            xml_content = f.read()
        
        root = ET.fromstring(xml_content)
        project = UniversalProject(name=daw_project_path.stem)
        
        # Parse tempo
        tempo_elem = root.find('.//Tempo')
        if tempo_elem is not None:
            project.tempo = float(tempo_elem.get('Value', '120'))
        
        # Parse time signature
        ts_elem = root.find('.//TimeSignature')
        if ts_elem is not None:
            project.time_signature_numerator = int(ts_elem.get('Numerator', '4'))
            project.time_signature_denominator = int(ts_elem.get('Denominator', '4'))
        
        # Parse tracks
        tracks_elem = root.find('.//Tracks')
        if tracks_elem is not None:
            for i, track_elem in enumerate(tracks_elem):
                track = self._parse_ableton_track(track_elem, i)
                if track:
                    project.tracks.append(track)
        
        return project
    
    def _parse_ableton_track(self, track_elem, index: int) -> Optional[UniversalTrack]:
        # Simplified parsing - real implementation would be more complete
        track = UniversalTrack(
            id=str(uuid.uuid4()),
            name=track_elem.get('Name', f'Track {index + 1}'),
            type='midi' if 'MidiTrack' in track_elem.tag else 'audio'
        )
        return track
    
    def import_from_universal(self, project: UniversalProject, output_path: Path) -> bool:
        # Generate .als XML structure
        # This is complex - would need full Live Object Model mapping
        return False


class ReaperProjectConverter(DAWProjectConverter):
    """Reaper (.rpp) converter"""
    
    def export_to_universal(self, daw_project_path: Path) -> UniversalProject:
        # .rpp files are text-based
        project = UniversalProject(name=daw_project_path.stem)
        
        with open(daw_project_path, 'r') as f:
            content = f.read()
        
        # Parse tempo
        import re
        tempo_match = re.search(r'TEMPO\s+([\d.]+)', content)
        if tempo_match:
            project.tempo = float(tempo_match.group(1))
        
        # Parse tracks
        track_sections = re.findall(r'<TRACK\s+(.*?)\n>', content, re.DOTALL)
        for i, track_data in enumerate(track_sections):
            track = self._parse_reaper_track(track_data, i)
            if track:
                project.tracks.append(track)
        
        return project
    
    def _parse_reaper_track(self, track_data: str, index: int) -> Optional[UniversalTrack]:
        import re
        track = UniversalTrack(
            id=str(uuid.uuid4()),
            name=f'Track {index + 1}'
        )
        
        name_match = re.search(r'NAME\s+"([^"]*)"', track_data)
        if name_match:
            track.name = name_match.group(1)
        
        # Parse volume
        vol_match = re.search(r'VOLPAN\s+([\d.]+)', track_data)
        if vol_match:
            track.volume = float(vol_match.group(1))
        
        # Parse pan
        pan_match = re.search(r'VOLPAN\s+[\d.]+\s+([\d.-]+)', track_data)
        if pan_match:
            track.pan = float(pan_match.group(1))
        
        # Parse mute/solo
        track.mute = 'MUTE 1' in track_data
        track.solo = 'SOLO 1' in track_data
        
        return track
    
    def import_from_universal(self, project: UniversalProject, output_path: Path) -> bool:
        # Generate .rpp format
        lines = [
            f'REAPER_PROJECT 0.1 "{project.name}"',
            f'TEMPO {project.tempo}',
            f'SIGNATURE {project.time_signature_numerator} {project.time_signature_denominator}',
            ''
        ]
        
        for track in project.tracks:
            lines.append(f'<TRACK')
            lines.append(f'  NAME "{track.name}"')
            lines.append(f'  VOLPAN {track.volume} {track.pan}')
            if track.mute:
                lines.append('  MUTE 1')
            if track.solo:
                lines.append('  SOLO 1')
            lines.append('>')
            
            # Devices
            for device in track.devices:
                lines.append(f'  <FX_DEVICE')
                lines.append(f'    NAME "{device.name}"')
                lines.append(f'    PLUGIN_ID "{device.plugin_id}"')
                lines.append('  >')
            
            # Clips (as items)
            for clip in track.clips:
                lines.append(f'  <ITEM')
                lines.append(f'    NAME "{clip.name}"')
                lines.append(f'    POSITION {clip.start_time * 60 / project.tempo}')  # Convert beats to seconds
                lines.append(f'    LENGTH {clip.duration * 60 / project.tempo}')
                if clip.notes:
                    lines.append('    <SOURCE MIDI>')
                    for note in clip.notes:
                        lines.append(f'      <NOTE {note.pitch} {note.velocity} {note.start_time} {note.duration}>')
                    lines.append('    >')
                lines.append('  >')
            
            lines.append('')
        
        output_path.write_text('\n'.join(lines))
        return True


# Converter registry
CONVERTERS = {
    'ableton': AbletonProjectConverter,
    'reaper': ReaperProjectConverter,
    # 'logic': LogicProjectConverter,
    # 'flstudio': FLStudioProjectConverter,
    # 'cubase': CubaseProjectConverter,
    # 'protools': ProToolsProjectConverter,
}


def get_converter(daw_name: str) -> Optional[DAWProjectConverter]:
    """Get converter for DAW"""
    converter_class = CONVERTERS.get(daw_name.lower())
    if converter_class:
        return converter_class()
    return None


def convert_project(input_path: Path, output_path: Path, target_daw: str = None) -> bool:
    """Convert project between formats"""
    source_ext = input_path.suffix.lower()
    
    # Determine source DAW from extension
    source_daw = None
    if source_ext == '.als':
        source_daw = 'ableton'
    elif source_ext == '.rpp':
        source_daw = 'reaper'
    # Add more mappings
    
    if not source_daw:
        print(f"Unknown source format: {source_ext}")
        return False
    
    # Load universal project
    converter = get_converter(source_daw)
    if not converter:
        print(f"No converter for {source_daw}")
        return False
    
    universal = converter.export_to_universal(input_path)
    if not universal:
        return False
    
    # Export to target DAW
    if target_daw:
        target_converter = get_converter(target_daw)
        if target_converter:
            return target_converter.import_from_universal(universal, output_path)
    
    # Save as universal format
    return UniversalProjectSerializer.save(universal, output_path)


if __name__ == "__main__":
    # Demo
    project = UniversalProject(
        name="Demo Project",
        tempo=140.0,
        time_signature_numerator=4,
        time_signature_denominator=4
    )
    
    # Add a track
    track = UniversalTrack(
        name="Lead Synth",
        type="midi",
        volume=0.8,
        pan=-0.2
    )
    
    # Add device
    device = UniversalDevice(
        name="Serum",
        type="instrument",
        plugin_format="vst3",
        plugin_id="com.xfer.serum",
        parameters={"osc_a_wavetable": 0.5, "filter_cutoff": 0.7}
    )
    track.devices.append(device)
    
    # Add clip with notes
    clip = UniversalClip(
        name="Main Riff",
        track_id=track.id,
        start_time=0.0,
        duration=8.0,
        notes=[
            UniversalNote(pitch=60, velocity=100, start_time=0.0, duration=1.0),
            UniversalNote(pitch=62, velocity=90, start_time=1.0, duration=1.0),
            UniversalNote(pitch=64, velocity=100, start_time=2.0, duration=1.0),
            UniversalNote(pitch=65, velocity=90, start_time=3.0, duration=1.0),
        ]
    )
    track.clips.append(clip)
    
    project.tracks.append(track)
    
    # Save
    UniversalProjectSerializer.save(project, Path("demo_project.abp"))
    print("Saved demo_project.abp")
    
    # Load and verify
    loaded = UniversalProjectSerializer.load(Path("demo_project.abp"))
    print(f"Loaded: {loaded.name}, {len(loaded.tracks)} tracks, {loaded.tempo} BPM")