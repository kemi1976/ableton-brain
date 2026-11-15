"""
Ableton Brain - Phase 1: Core Framework
Base DAW Adapter and Universal Interfaces
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import asyncio
import json
from pathlib import Path


class DAWPlatform(Enum):
    ABLETON = "ableton"
    REAPER = "reaper"
    LOGIC = "logic"
    FLSTUDIO = "flstudio"
    CUBASE = "cubase"
    PROTOOLS = "protools"


class TrackType(Enum):
    AUDIO = "audio"
    MIDI = "midi"
    RETURN = "return"
    MASTER = "master"
    GROUP = "group"


@dataclass
class TrackInfo:
    id: str
    name: str
    type: TrackType
    armed: bool = False
    solo: bool = False
    mute: bool = False
    volume: float = 1.0
    pan: float = 0.0
    input_routing: str = ""
    output_routing: str = ""
    devices: List[Dict] = field(default_factory=list)


@dataclass
class DeviceInfo:
    id: str
    name: str
    type: str  # instrument, audio_effect, midi_effect
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class ProjectInfo:
    name: str
    path: str
    tempo: float = 120.0
    time_signature: str = "4/4"
    tracks: List[TrackInfo] = field(default_factory=list)
    markers: List[Dict] = field(default_factory=list)


class BaseDAWAdapter(ABC):
    """Abstract base class for all DAW adapters"""
    
    def __init__(self, daw_name: str):
        self.daw_name = daw_name
        self.platform = DAWPlatform(daw_name.lower())
        self.api = None
        self.version = None
        self.connected = False
        self.project: Optional[ProjectInfo] = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to DAW"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from DAW"""
        pass
    
    @abstractmethod
    async def get_project_info(self) -> Optional[ProjectInfo]:
        """Get current project information"""
        pass
    
    @abstractmethod
    async def create_track(self, name: str, track_type: TrackType = TrackType.MIDI) -> str:
        """Create a new track, return track ID"""
        pass
    
    @abstractmethod
    async def delete_track(self, track_id: str) -> bool:
        """Delete a track"""
        pass
    
    @abstractmethod
    async def rename_track(self, track_id: str, name: str) -> bool:
        """Rename a track"""
        pass
    
    @abstractmethod
    async def arm_track(self, track_id: str, arm: bool = True) -> bool:
        """Arm/disarm track for recording"""
        pass
    
    @abstractmethod
    async def solo_track(self, track_id: str, solo: bool = True) -> bool:
        """Solo/unsolo track"""
        pass
    
    @abstractmethod
    async def mute_track(self, track_id: str, mute: bool = True) -> bool:
        """Mute/unmute track"""
        pass
    
    @abstractmethod
    async def set_track_volume(self, track_id: str, volume: float) -> bool:
        """Set track volume (0.0 - 1.0)"""
        pass
    
    @abstractmethod
    async def set_track_pan(self, track_id: str, pan: float) -> bool:
        """Set track pan (-1.0 to 1.0)"""
        pass
    
    @abstractmethod
    async def load_instrument(self, track_id: str, instrument_name: str, 
                             preset: Optional[str] = None) -> bool:
        """Load instrument on track"""
        pass
    
    @abstractmethod
    async def add_audio_effect(self, track_id: str, effect_name: str, 
                              position: int = -1) -> bool:
        """Add audio effect to track"""
        pass
    
    @abstractmethod
    async def add_midi_effect(self, track_id: str, effect_name: str,
                             position: int = -1) -> bool:
        """Add MIDI effect to track"""
        pass
    
    @abstractmethod
    async def set_device_parameter(self, track_id: str, device_id: str,
                                  param_name: str, value: float) -> bool:
        """Set device parameter"""
        pass
    
    @abstractmethod
    async def get_device_parameters(self, track_id: str, device_id: str) -> Dict:
        """Get all device parameters"""
        pass
    
    @abstractmethod
    async def start_playback(self) -> bool:
        """Start playback"""
        pass
    
    @abstractmethod
    async def stop_playback(self) -> bool:
        """Stop playback"""
        pass
    
    @abstractmethod
    async def set_tempo(self, tempo: float) -> bool:
        """Set project tempo"""
        pass
    
    @abstractmethod
    async def set_time_signature(self, numerator: int, denominator: int) -> bool:
        """Set time signature"""
        pass
    
    @abstractmethod
    async def create_clip(self, track_id: str, start_time: float, 
                         duration: float, notes: List[Dict]) -> str:
        """Create MIDI clip with notes"""
        pass
    
    @abstractmethod
    async def quantize_clip(self, clip_id: str, grid: str = "1/16") -> bool:
        """Quantize MIDI clip"""
        pass
    
    @abstractmethod
    async def export_audio(self, output_path: str, format: str = "wav",
                          sample_rate: int = 44100, bit_depth: int = 24) -> bool:
        """Export project as audio"""
        pass
    
    @abstractmethod
    async def save_project(self, path: Optional[str] = None) -> bool:
        """Save project"""
        pass
    
    @abstractmethod
    async def undo(self) -> bool:
        """Undo last action"""
        pass
    
    @abstractmethod
    async def redo(self) -> bool:
        """Redo last undone action"""
        pass
    
    # Quick actions (one-click operations)
    async def quick_save(self) -> bool:
        """Quick save (Ctrl+S)"""
        return await self.save_project()
    
    async def quick_export_wav(self, output_path: str) -> bool:
        """Quick export to WAV"""
        return await self.export_audio(output_path, "wav")
    
    async def quick_new_midi_track(self, name: str = "New MIDI Track") -> str:
        """Create new MIDI track"""
        return await self.create_track(name, TrackType.MIDI)
    
    async def quick_new_audio_track(self, name: str = "New Audio Track") -> str:
        """Create new audio track"""
        return await self.create_track(name, TrackType.AUDIO)
    
    async def quick_arm_first_track(self) -> bool:
        """Arm first track for recording"""
        if self.project and self.project.tracks:
            return await self.arm_track(self.project.tracks[0].id)
        return False


class DAWAdapterRegistry:
    """Registry for DAW adapters"""
    
    def __init__(self):
        self.adapters: Dict[str, BaseDAWAdapter] = {}
        self.active_adapter: Optional[BaseDAWAdapter] = None
    
    def register(self, adapter: BaseDAWAdapter):
        self.adapters[adapter.daw_name.lower()] = adapter
    
    def get(self, daw_name: str) -> Optional[BaseDAWAdapter]:
        return self.adapters.get(daw_name.lower())
    
    def set_active(self, daw_name: str) -> bool:
        adapter = self.get(daw_name)
        if adapter:
            self.active_adapter = adapter
            return True
        return False
    
    def get_active(self) -> Optional[BaseDAWAdapter]:
        return self.active_adapter
    
    def list_available(self) -> List[str]:
        return list(self.adapters.keys())
    
    async def connect_active(self) -> bool:
        if self.active_adapter:
            return await self.active_adapter.connect()
        return False
    
    async def disconnect_all(self):
        for adapter in self.adapters.values():
            if adapter.connected:
                await adapter.disconnect()


# Global registry instance
daw_registry = DAWAdapterRegistry()


# Convenience functions
async def connect_daw(daw_name: str) -> bool:
    adapter = daw_registry.get(daw_name)
    if adapter:
        daw_registry.set_active(daw_name)
        return await adapter.connect()
    return False


async def quick_action(action: str, **kwargs) -> Any:
    """Execute quick action on active DAW"""
    adapter = daw_registry.get_active()
    if not adapter:
        return False
    
    action_map = {
        "save": adapter.quick_save,
        "export_wav": lambda: adapter.quick_export_wav(kwargs.get("path", "export.wav")),
        "new_midi_track": lambda: adapter.quick_new_midi_track(kwargs.get("name", "New Track")),
        "new_audio_track": lambda: adapter.quick_new_audio_track(kwargs.get("name", "New Track")),
        "arm_first": adapter.quick_arm_first_track,
        "play": adapter.start_playback,
        "stop": adapter.stop_playback,
        "undo": adapter.undo,
        "redo": adapter.redo,
        "set_tempo": lambda: adapter.set_tempo(kwargs.get("tempo", 120)),
    }
    
    if action in action_map:
        return await action_map[action]()
    return False


if __name__ == "__main__":
    print("Ableton Brain - Core Framework")
    print("Available DAW adapters:", daw_registry.list_available())
    print("BaseDAWAdapter defines interface for:")
    for method in dir(BaseDAWAdapter):
        if not method.startswith('_') and callable(getattr(BaseDAWAdapter, method)):
            print(f"  - {method}")