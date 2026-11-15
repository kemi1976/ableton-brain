# ABLETON BRAIN: Technical Implementation Blueprint

## Cross-Platform MIDI Controller Integration System

### 1. Universal MIDI Bridge Architecture

```python
# ableton_brain/core/midi/universal_bridge.py
import asyncio
import rtmidi
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

class ControllerType(Enum):
    PUSH_1 = "push1"
    PUSH_2 = "push2"
    PUSH_3 = "push3"
    GAMEPAD = "gamepad"
    KEYBOARD = "keyboard"
    CUSTOM = "custom"
    BLUETOOTH = "bluetooth_midi"
    USB_OTG = "usb_otg"

@dataclass
class ControlMapping:
    physical_control: str  # e.g., "knob_1", "pad_5_3"
    daw_parameter: str      # e.g., "filter_cutoff", "volume_1"
    curve_profile: str      # linear, log, exp, step
    range_min: float = 0.0
    range_max: float = 127.0
    hz_output: bool = False

class UniversalMIDITranslator:
    """
    Cross-platform MIDI translation layer
    Supports Windows, macOS, Linux, and Android
    """
    
    def __init__(self):
        self.midi_in = rtmidi.MidiIn()
        self.midi_out = rtmidi.MidiOut()
        self.controller_map: Dict[ControllerType, dict] = {}
        self.active_mappings: List[ControlMapping] = []
        
    async def discover_controllers(self) -> List[dict]:
        """Auto-discover all available MIDI controllers"""
        ports = self.midi_in.get_ports()
        controllers = []
        
        for port in ports:
            controller_info = await self._analyze_midi_device(port)
            controllers.append(controller_info)
            
        return controllers
    
    async def _analyze_midi_device(self, port_name: str) -> dict:
        """Analyze MIDI device capabilities"""
        info = {
            'name': port_name,
            'type': self._detect_type(port_name),
            'inputs': [],
            'outputs': [],
            'capabilities': await self._probe_capabilities(port_name)
        }
        return info
    
    def map_control(self, mapping: ControlMapping):
        """Add a control mapping"""
        self.active_mappings.append(mapping)
        
    async def send_parameter_change(self, param_name: str, value: float):
        """Send parameter change to all mapped controllers"""
        for mapping in self.active_mappings:
            if mapping.daw_parameter == param_name:
                midi_value = self._map_value(value, mapping.range_min, mapping.range_max)
                await self._send_midi_cc(mapping.physical_control, midi_value)

# Android-specific support
class AndroidMIDIBridge:
    """Android USB-OTG MIDI support"""
    
    def __init__(self):
        self.usb_host_active = False
        self.bluetooth_connected = False
        
    async def init_usb_otg(self):
        """Initialize USB-OTG for MIDI devices on Android"""
        # Uses Android's USB Host API via Python wrapper
        import usb.core
        import usb.util
        
        # Find USB MIDI devices
        devices = usb.core.find(find_all=True)
        for device in devices:
            if self._is_midi_device(device):
                await self._configure_midi_device(device)
                
    async def init_bluetooth_midi(self):
        """Initialize Bluetooth MIDI connection"""
        # Uses Android Bluetooth MIDI API
        pass
```

### 2. Game Controller Mapping System

```python
# ableton_brain/core/controllers/game_controller.py
from enum import Enum
import asyncio

class GameControl(Enum):
    DPAD_UP = 0
    DPAD_DOWN = 1
    DPAD_LEFT = 2
    DPAD_RIGHT = 3
    BUTTON_A = 4
    BUTTON_B = 5
    LEFT_STICK_X = 6
    LEFT_STICK_Y = 7
    RIGHT_STICK_X = 8
    RIGHT_STICK_Y = 9
    LEFT_TRIGGER = 10
    RIGHT_TRIGGER = 11
    LEFT_BUMPER = 12
    RIGHT_BUMPER = 13
    POV_HAT = 14

class GameControllerMapper:
    """Maps game controllers to music production controls"""
    
    def __init__(self):
        self.controller_profiles = {
            'xbox_series': self._xbox_profile(),
            'playstation_dualsense': self._playstation_profile(),
            'nintendo_switch_pro': self._nintendo_profile(),
            'generic_gamepad': self._generic_profile()
        }
        
    def _xbox_profile(self) -> Dict[GameControl, str]:
        """Xbox Series X|S controller mapping"""
        return {
            GameControl.LEFT_STICK_X: 'pan_left',
            GameControl.LEFT_STICK_Y: 'volume_left',
            GameControl.RIGHT_STICK_X: 'pan_right',
            GameControl.RIGHT_STICK_Y: 'volume_right',
            GameControl.LEFT_TRIGGER: 'filter_cutoff',
            GameControl.RIGHT_TRIGGER: 'resonance',
            GameControl.BUTTON_A: 'play_selected_clip',
            GameControl.BUTTON_B: 'stop_selected_clip',
            GameControl.BUTTON_X: 'record_enable',
            GameControl.BUTTON_Y: 'mute_track',
            GameControl.DPAD_UP: 'select_next_track',
            GameControl.DPAD_DOWN: 'select_prev_track',
            GameControl.LEFT_BUMPER: 'undo',
            GameControl.RIGHT_BUMPER: 'redo',
            GameControl.POV_HAT: 'navigation_grid'
        }
        
    def _playstation_profile(self) -> Dict[GameControl, str]:
        """PlayStation DualSense controller mapping"""
        return {
            GameControl.LEFT_STICK_X: 'x_position',
            GameControl.LEFT_STICK_Y: 'y_position',
            GameControl.RIGHT_STICK_X: 'x_rotation',
            GameControl.RIGHT_STICK_Y: 'y_rotation',
            GameControl.LEFT_TRIGGER: 'attack',
            GameControl.RIGHT_TRIGGER: 'release',
            GameControl.BUTTON_A: 'a_button',
            GameControl.BUTTON_B: 'circle_button',
            GameControl.BUTTON_X: 'cross_button',
            GameControl.BUTTON_Y: 'square_button',
            GameControl.LEFT_BUMPER: 'l1',
            GameControl.RIGHT_BUMPER: 'r1',
        }
```

### 3. DAW Adapter Framework

```python
# ableton_brain/core/adapters/base_daw.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import asyncio

class BaseDAW(ABC):
    """Abstract base class for DAW adapters"""
    
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.connected = False
        self.api = None
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the DAW"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the DAW"""
        pass
    
    @abstractmethod
    async def create_track(self, name: str, type: str) -> str:
        """Create a new track and return its ID"""
        pass
    
    @abstractmethod
    async def load_instrument(self, track_id: str, instrument: str) -> bool:
        """Load instrument on specified track"""
        pass
    
    @abstractmethod
    async def set_parameter(self, path: str, value: float) -> bool:
        """Set a parameter by path"""
        pass
    
    @abstractmethod
    async def get_parameter(self, path: str) -> float:
        """Get a parameter by path"""
        pass
    
    @abstractmethod
    async def record_midi(self, track_id: str, duration: float) -> bool:
        """Record MIDI input"""
        pass

# reaper_adapter.py
class ReaperAdapter(BaseDAW):
    """Reaper DAW adapter using ReaScript"""
    
    def __init__(self):
        super().__init__("Reaper", "7+")
        self.rea_script_path = None
        
    async def connect(self) -> bool:
        """Connect to Reaper via ReaScript API"""
        try:
            # Check if Reaper is running
            # Establish Python bridge
            # Initialize ReaScript environment
            self.connected = True
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    async def create_track(self, name: str, type: str = "midi") -> str:
        """Create track using RPR_InsertTrackAtIndex"""
        if not self.connected:
            raise ConnectionError("Not connected to Reaper")
            
        # Generate unique track ID
        track_id = f"reaper_{hash(name)}"
        
        # Execute ReaScript to create track
        await self._execute_reascript(f"""
        local track = reaper.InsertTrackAtIndex(0, true)
        reaper.GetSetMediaTrackInfo_String(track, "P_NAME", "{name}", true)
        """)
        
        return track_id
    
    async def load_instrument(self, track_id: str, instrument: str) -> bool:
        """Load VST instrument on track"""
        # Implementation using RPR_AttachMediaItemToTrack or similar
        pass
```

### 4. Android Deployment System

```python
# android_deployment/android_midi_sampler.py
import python_midi as mido
import os
import json
from pathlib import Path

class AndroidMIDISampler:
    """Android MIDI sampler with USB-OTG and Bluetooth support"""
    
    def __init__(self, device_id: str = "SM-A047F"):
        self.device_id = device_id
        self.sample_root = "/sdcard/Music/samples"
        self.midi_in_port = None
        self.midi_out_port = None
        
    def scan_samples(self) -> dict:
        """Scan all samples on device"""
        samples = {
            'kicks': [], 'snare': [], 'hi-hats': [], 
            'percussion': [], 'synths': [], 'bass': []
        }
        
        for category in samples:
            category_path = Path(f"{self.sample_root}/{category}")
            if category_path.exists():
                for file in category_path.glob("*.wav"):
                    samples[category].append(str(file))
                    
        return samples
    
    def create_sample_project(self, name: str) -> str:
        """Create a new sample project"""
        project_path = Path(f"{self.sample_root}/projects/{name}")
        project_path.mkdir(parents=True, exist_ok=True)
        
        project_data = {
            'name': name,
            'created': str(datetime.now()),
            'samples': {},
            'midi_tracks': [],
            'tempo': 120
        }
        
        with open(project_path / 'project.json', 'w') as f:
            json.dump(project_data, f, indent=2)
            
        return str(project_path)
```

### 5. Cross-DAW Project Format

```json
// ableton_brain/core/project/cross_daw_format.json
{
  "project": {
    "name": "Universal_Project",
    "version": "1.0",
    "created": "2026-11-04T00:00:00Z",
    "daws": ["ableton", "reaper", "logic", "flstudio"],
    "tracks": [
      {
        "id": "track_001",
        "name": "Drums",
        "type": "drum_machine",
        "genre_context": "uk_dnb",
        "instruments": [
          {
            "name": "TR-808 Kick",
            "source": "ftp://samples.archive/drums/808/kick.wav",
            "vst": "DrumNation 808",
            "au": "808Kick AU",
            "plugin_id": "drumnation_808_kick"
          }
        ],
        "midi_data": {
          "notes": [
            {"pitch": 36, "velocity": 100, "start": 0.0, "duration": 0.5}
          ]
        }
      }
    ],
    "mappings": {
      "cross_platform": {
        "filter_cutoff": {
          "ableton": "Device["Filter"].Cutoff",
          "reaper": "Track[1].FX[1]Param[1]",
          "logic": "Track[1].Plugin[1].Parameter[1]",
          "flstudio": "MixerTrack[1].FX[1].Control[1]"
        }
      }
    }
  }
}
```

### 6. Installation & Setup Script

```bash
#!/bin/bash
# setup_universal_controller.sh

echo "🎵 ABLETON BRAIN Universal Controller Setup"
echo "==========================================="

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
fi

# Install dependencies
case $OS in
    linux)
        sudo apt-get update
        sudo apt-get install -y python3-rtmidi python3-usb python3-pip
        pip3 install python-rtmidi pyusb mido
        ;;
    macos)
        brew install python3-rtmidi
        pip3 install python-rtmidi mido
        ;;
    windows)
        pip install python-rtmidi pywinusb mido
        ;;
esac

# Configure MIDI settings
python3 << EOF
from ableton_brain.core.midi.universal_bridge import UniversalMIDITranslator
import asyncio

async def setup():
    translator = UniversalMIDITranslator()
    controllers = await translator.discover_controllers()
    print(f"Found {len(controllers)} MIDI controllers:")
    for c in controllers:
        print(f"  - {c['name']} ({c['type']})")

asyncio.run(setup())
EOF

echo "✅ Setup complete!"
echo "Run 'abrain-controller' to start the universal controller."
```

### 7. API Endpoints for Cross-Platform Control

```python
# ableton_brain/api/server.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="ABLETON BRAIN API", version="1.0.0")

class ParameterUpdate(BaseModel):
    parameter: str
    value: float
    scope: str = "global"
    dais: Optional[List[str]] = None  # Target DAW

class ControllerMapping(BaseModel):
    controller: str
    physical_control: str
    daw_parameter: str
    curve: str = "linear"

@app.post("/api/v1/connect")
async def connect_to_daw(daw_name: str):
    """Connect to specified DAW"""
    pass

@app.post("/api/v1/controller/map")
async def map_controller(mapping: ControllerMapping):
    """Map physical control to DAW parameter"""
    pass

@app.post("/api/v1/parameter/update")
async def update_parameter(update: ParameterUpdate):
    """Update parameter across DAWs"""
    pass

@app.get("/api/v1/controllers/discover")
async def discover_controllers():
    """Discover all connected controllers"""
    pass

@app.get("/api/v1/status")
async def get_status():
    """Get current system status"""
    return {
        "connected_da_ws": [],
        "controllers": [],
        "version": "1.0.0",
        "platform": "auto_detected"
    }
```

---

## Implementation Priority Order

1. **Week 1-2**: Universal MIDI Bridge Core
2. **Week 3**: Reaper Adapter Implementation
3. **Week 4**: Logic Adapter Implementation
4. **Week 5**: Game Controller Support
5. **Week 6**: Bluetooth MIDI Integration
6. **Week 7**: Android USB-OTG Support
7. **Week 8**: Cross-DAW Project Format
8. **Week 9**: API Development
9. **Week 10**: Testing & Documentation

---

*All code to be placed in: `knowledge/ableton-brain/src/core/`*
*Documentation updated: `knowledge/ableton-brain/IMPLEMENTATION_GUIDE.md`*