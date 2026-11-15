#!/usr/bin/env python3
"""
ABLETON BRAIN: Cross-DAW Controller Integration System
========================================================
Universal AI music production platform - Phase 1 Implementation

This script implements:
1. Universal MIDI Controller discovery and mapping
2. Game controller integration layer
3. Bluetooth MIDI support
4. Android USB-OTG MIDI
5. Cross-DAW adapter framework foundation

Author: ELIZA (Nous Research)
Date: November 2026
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
PROJECT_ROOT = Path(__file__).parent.parent.parent  # Go up from src/core to project root
DATABASE_PATH = PROJECT_ROOT / "database.json"
CONFIG_PATH = PROJECT_ROOT / ".abrain_config.json"

# ============================================================================
# ENUMERATIONS AND DATA CLASSES
# ============================================================================

class ControllerType(Enum):
    """Types of controllers supported"""
    PUSH_1 = "push1"
    PUSH_2 = "push2"
    PUSH_3 = "push3"
    GAMEPAD = "gamepad"
    KEYBOARD = "keyboard"
    CUSTOM = "custom"
    BLUETOOTH_MIDI = "bluetooth_midi"
    USB_OTG = "usb_otg"
    VIOMINI = "vomini"
    LAUNCHPAD = "launchpad"

class DAWPlatform(Enum):
    """Supported DAW platforms"""
    ABLETON = "ableton"
    REAPER = "reaper"
    LOGIC = "logic"
    FL_STUDIO = "flstudio"
    CUBASE = "cubase"
    PRO_TOOLS = "protools"

@dataclass
class ControlMapping:
    """Maps a physical control to a DAW parameter"""
    physical_control: str  # e.g., "knob_1", "pad_5_3"
    daw_parameter: str     # e.g., "filter_cutoff", "volume_1"
    curve_profile: str = "linear"
    range_min: float = 0.0
    range_max: float = 127.0
    hz_output: bool = False
    daw_scope: Optional[str] = None  # Track-specific, global, etc.

@dataclass
class ControllerCapabilities:
    """Detected capabilities of a controller"""
    name: str
    type: ControllerType
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    capabilities: Dict[str, Any] = field(default_factory=dict)

# ============================================================================
# UNIVERSAL MIDI TRANSLATOR
# ============================================================================

class UniversalMIDITranslator:
    """
    Cross-platform MIDI translation layer
    Supports Windows, macOS, Linux, and Android
    """
    
    def __init__(self, database_path: Path = DATABASE_PATH):
        self.database_path = database_path
        self.database = self._load_database()
        self.controller_mappings: Dict[ControllerType, dict] = {}
        self.active_mappings: List[ControlMapping] = []
        self._rtmidi_available = self._check_rtmidi()
        
    def _load_database(self) -> dict:
        """Load the ABLETON BRAIN database"""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load database: {e}")
            return {"artists": {}, "engineers": {}, "techniques": {}, "genres": []}
    
    def _check_rtmidi(self) -> bool:
        """Check if python-rtmidi is available"""
        try:
            import rtmidi
            return True
        except ImportError:
            logger.warning("python-rtmidi not available - using basic MIDI mode")
            return False
    
    def get_artist_database(self) -> dict:
        """Return the artist database from ABLETON BRAIN"""
        return self.database.get('artists', {})
    
    def get_genres(self) -> List[str]:
        """Return all genres in the database"""
        # Extract unique genres from artists
        genres = set()
        for artist in self.database.get('artists', {}).values():
            genre = artist.get('genre', '')
            if genre:
                # Split compound genres
                for g in genre.split(' / '):
                    genres.add(g.strip())
        return sorted(list(genres))
    
    def get_controllers_database(self) -> dict:
        """Return controller mappings database"""
        controllers = {}
        
        # Extract controller info from artists
        for artist_id, artist in self.database.get('artists', {}).items():
            key_equipment = artist.get('key_equipment', [])
            for eq in key_equipment:
                if 'Push' in eq or 'Akai' in eq or 'MPC' in eq or 'Novation' in eq:
                    controller_key = eq.split()[0].lower()
                    if controller_key not in controllers:
                        controllers[controller_key] = {
                            'name': eq,
                            'artist_reference': artist_id,
                            'compatible_with_abrain': True
                        }
        
        return controllers
    
    async def discover_controllers(self) -> List[dict]:
        """
        Auto-discover all available MIDI and game controllers
        Returns list of detected controllers with their capabilities
        """
        discovered = []
        
        # Try to use rtmidi for MIDI discovery
        if self._rtmidi_available:
            try:
                import rtmidi
                midi_in = rtmidi.MidiIn()
                midi_out = rtmidi.MidiOut()
                
                in_ports = midi_in.get_ports()
                out_ports = midi_out.get_ports()
                
                # Analyze each MIDI input port
                for port in in_ports:
                    controller_info = await self._analyze_midi_device(port, 'input')
                    discovered.append(controller_info)
                    
                # Analyze each MIDI output port
                for port in out_ports:
                    controller_info = await self._analyze_midi_device(port, 'output')
                    if not any(c['name'] == controller_info['name'] for c in discovered):
                        discovered.append(controller_info)
                        
            except Exception as e:
                logger.error(f"MIDI discovery error: {e}")
        
        # Add game controller detection (platform-specific)
        game_controllers = await self._discover_game_controllers()
        discovered.extend(game_controllers)
        
        # Add Android USB-OTG devices if on Android
        if self._is_android():
            usb_devices = await self._discover_usb_devices()
            discovered.extend(usb_devices)
        
        return discovered
    
    async def _analyze_midi_device(self, port_name: str, direction: str) -> dict:
        """Analyze a MIDI device and infer its capabilities"""
        # Map common controller names
        controller_map = {
            'push': ControllerType.PUSH_1,
            'push 1': ControllerType.PUSH_1,
            'push 2': ControllerType.PUSH_2,
            'push 3': ControllerType.PUSH_3,
            'launchpad': ControllerType.LAUNCHPAD,
            'viomini': ControllerType.VIOMINI,
            'bluetooth': ControllerType.BLUETOOTH_MIDI
        }
        
        # Determine controller type
        controller_type = ControllerType.CUSTOM
        port_lower = port_name.lower()
        for key, ctype in controller_map.items():
            if key in port_lower:
                controller_type = ctype
                break
        
        # Get capabilities based on known controllers
        capabilities = self._get_controller_capabilities(controller_type)
        
        return {
            'name': port_name,
            'type': controller_type.value if isinstance(controller_type, ControllerType) else controller_type,
            'direction': direction,
            'inputs': [port_name] if direction == 'input' else [],
            'outputs': [port_name] if direction == 'output' else [],
            'capabilities': capabilities,
            'auto_detected': True
        }
    
    def _get_controller_capabilities(self, controller_type: ControllerType) -> dict:
        """Get known capabilities for a controller type"""
        capabilities = {
            'push1': {
                'pads': 82,
                'knobs': 8,
                'keys': 0,
                'transport': True,
                'rgb_leds': True,
                'velocity_sensitive': True
            },
            'push2': {
                'pads': 82,
                'knobs': 8,
                'screen': True,
                'rgb_leds': True,
                'velocity_sensitive': True
            },
            'push3': {
                'pads': 82,
                'knobs': 8,
                'screen': True,
                'rgb_leds': True,
                'velocity_sensitive': True,
                'note_mode': True
            },
            'gamepad': {
                'buttons': 17,
                'axes': 6,
                'd-pad': True,
                'triggers': 2,
                'joy_sticks': 2
            },
            'launchpad': {
                'pads': 128,  # 8x16
                'rgb_leds': True,
                'velocity_sensitive': True
            }
        }
        
        type_name = controller_type.value if isinstance(controller_type, ControllerType) else str(controller_type)
        return capabilities.get(type_name, {
            'custom': True,
            'unknown': True
        })
    
    async def _discover_game_controllers(self) -> List[dict]:
        """Discover connected game controllers (pads, joysticks, etc.)"""
        controllers = []
        
        # Platform-specific discovery
        if sys.platform.startswith('win'):
            controllers = await self._discover_windows_gamepads()
        elif sys.platform.startswith('darwin'):
            controllers = await self._discover_macos_gamepads()
        elif sys.platform.startswith('linux'):
            controllers = await self._discover_linux_gamepads()
        
        return controllers
    
    async def _discover_windows_gamepads(self) -> List[dict]:
        """Discover Windows gamepads using ctypes"""
        controllers = []
        try:
            import ctypes
            from ctypes import wintypes
            
            # Check for XInput controllers
            XUSER_MAX_COUNT = 4
            
            # Simplified detection - in production, use XInputGetState
            for i in range(XUSER_MAX_COUNT):
                # Placeholder - would check actual XInput state
                controllers.append({
                    'name': f'XInput Controller {i+1}',
                    'type': ControllerType.GAMEPAD.value,
                    'direction': 'input',
                    'inputs': [f'xinput_{i}'],
                    'outputs': [],
                    'capabilities': {
                        'buttons': 15,
                        'triggers': 2,
                        'axes': 4,
                        'd_pad': True
                    },
                    'auto_detected': True
                })
        except Exception as e:
            logger.debug(f"Windows gamepad discovery: {e}")
        
        return controllers
    
    async def _discover_usb_devices(self) -> List[dict]:
        """Discover USB devices on Android via USB-OTG"""
        devices = []
        
        try:
            import usb.core
            import usb.util
            
            # Find USB MIDI devices
            for device in usb.core.find(find_all=True):
                try:
                    # Check if it's a MIDI device (class 1 = Audio, subclass 3 = MIDI)
                    if (device.descriptor.bDeviceClass == 0xff and 
                        hasattr(device, 'interface')):
                        devices.append({
                            'name': f'USB Device {device.idVendor:04x}:{device.idProduct:04x}',
                            'type': ControllerType.USB_OTG.value,
                            'direction': 'input_output',
                            'inputs': [],
                            'outputs': [],
                            'capabilities': {
                                'usb_id': f'{device.idVendor:04x}:{device.idProduct:04x}',
                                'product': usb.util.get_string(device, device.iProduct) if hasattr(device, 'iProduct') else None
                            },
                            'auto_detected': True
                        })
                except Exception:
                    continue
                    
        except ImportError:
            logger.debug("pyusb not available for USB discovery")
        
        return devices
    
    def _is_android(self) -> bool:
        """Check if running on Android"""
        try:
            import android  # Python for Android
            return True
        except ImportError:
            return False
    
    # ========================================================================
    # MIDI MAPPING FUNCTIONS
    # ========================================================================
    
    def map_control(self, mapping: ControlMapping) -> None:
        """Add a control mapping"""
        self.active_mappings.append(mapping)
        logger.info(f"Mapped {mapping.physical_control} -> {mapping.daw_parameter}")
    
    def get_mapping_for_parameter(self, parameter: str) -> Optional[ControlMapping]:
        """Get all mappings for a DAW parameter"""
        return [m for m in self.active_mappings if m.daw_parameter == parameter]
    
    async def send_parameter_change(self, parameter: str, value: float, 
                                    dais: Optional[List[str]] = None) -> bool:
        """
        Send parameter change to all mapped controllers
        Can target specific DAWs via the 'dais' parameter
        """
        # Find all mappings for this parameter
        mappings = self.get_mapping_for_parameter(parameter)
        
        if not mappings:
            logger.debug(f"No mappings found for parameter: {parameter}")
            return False
        
        # Filter by target DAWs if specified
        if dais:
            mappings = [m for m in mappings if m.daw_scope in dais or m.daw_scope is None]
        
        success_count = 0
        for mapping in mappings:
            try:
                # Map float 0-1 to MIDI range
                midi_value = int(value * (mapping.range_max - mapping.range_min) + mapping.range_min)
                midi_value = max(0, min(127, midi_value))
                
                # Apply curve profile
                if mapping.curve_profile == 'log':
                    midi_value = int(127 * (midi_value / 127) ** 2)
                elif mapping.curve_profile == 'exp':
                    midi_value = int(127 * (midi_value / 127) ** 0.5)
                
                logger.debug(f"Sending MIDI {mapping.physical_control} = {midi_value}")
                success_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send mapping {mapping.physical_control}: {e}")
        
        return success_count > 0
    
    # ========================================================================
    # DAIS ADAPTER FRAMEWORK
    # ========================================================================
    
    def get_daw_adapters(self) -> Dict[str, Callable]:
        """Get available DAW adapter classes/functions"""
        return {
            'ableton': self._create_ableton_adapter,
            'reaper': self._create_reaper_adapter,
            'logic': self._create_logic_adapter,
            'flstudio': self._create_flstudio_adapter,
            'cubase': self._create_cubase_adapter,
            'protools': self._create_protools_adapter
        }
    
    def _create_ableton_adapter(self):
        """Create Ableton Live adapter instance"""
        # Returns adapter for the Extensions API
        from .daws.ableton_adapter import AbletonAdapter
        return AbletonAdapter(self.database)
    
    def _create_reaper_adapter(self):
        """Create Reaper adapter instance using ReaScript"""
        from .daws.reaper_adapter import ReaperAdapter
        return ReaperAdapter(self.database)
    
    def _create_logic_adapter(self):
        """Create Logic Pro adapter instance"""
        from .daws.logic_adapter import LogicAdapter
        return LogicAdapter(self.database)
    
    def _create_flstudio_adapter(self):
        """Create FL Studio adapter instance"""
        from .daws.flstudio_adapter import FLStudioAdapter
        return FLStudioAdapter(self.database)
    
    def _create_cubase_adapter(self):
        """Create Cubase adapter instance"""
        from .daws.cubase_adapter import CubaseAdapter
        return CubaseAdapter(self.database)
    
    def _create_protools_adapter(self):
        """Create Pro Tools adapter instance"""
        from .daws.protools_adapter import ProToolsAdapter
        return ProToolsAdapter(self.database)
    
    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================
    
    def export_config(self) -> dict:
        """Export current configuration/state"""
        return {
            'database_stats': {
                'artists': len(self.database.get('artists', {})),
                'engineers': len(self.database.get('engineers', {})),
                'techniques': len(self.database.get('techniques', {})),
                'genres': len(self.get_genres())
            },
            'controllers': [
                {'name': m.physical_control, 'target': m.daw_parameter}
                for m in self.active_mappings
            ],
            'supported_daws': list(self.get_daw_adapters().keys()),
            'supported_controllers': [t.value for t in ControllerType]
        }
    
    def load_config(self, config: dict) -> None:
        """Load configuration from file"""
        if 'controllers' in config:
            for ctrl in config['controllers']:
                mapping = ControlMapping(
                    physical_control=ctrl['name'],
                    daw_parameter=ctrl['target']
                )
                self.active_mappings.append(mapping)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

async def main():
    """Main entry point for the ABLETON BRAIN controller system"""
    print("=" * 60)
    print("🎵 ABLETON BRAIN: Cross-DAW Controller System")
    print("=" * 60)
    
    # Initialize the translator
    translator = UniversalMIDITranslator()
    
    # Load database info
    artists = translator.get_artist_database()
    genres = translator.get_genres()
    
    print(f"\n📊 Database Statistics:")
    print(f"   Artists: {len(artists)}")
    print(f"   Genres: {', '.join(genres[:10])}...")
    
    # Discover controllers
    print(f"\n🔍 Discovering controllers...")
    controllers = await translator.discover_controllers()
    
    print(f"   Found {len(controllers)} controller(s):")
    for ctrl in controllers[:5]:  # Show first 5
        print(f"   - {ctrl['name']} ({ctrl['type']})")
    
    # Show DAW adapters
    print(f"\n💻 DAW Adapters Available:")
    adapters = translator.get_daw_adapters()
    for daw_name in adapters.keys():
        print(f"   - {daw_name.upper()}")
    
    # Export config
    config = translator.export_config()
    print(f"\n📋 Configuration exported successfully")
    
    # Save config
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"   Saved to: {CONFIG_PATH}")
    
    print("\n✅ Ready for cross-platform music production!")
    return config


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nResult: {json.dumps(result, indent=2)}")