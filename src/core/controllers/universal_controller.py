"""
Ableton Brain - Phase 3: Universal Controller Layer
Abstracts all hardware controllers (Push, Launchpad, Gamepad, etc.)
"""

import asyncio
import json
import hid
import mido
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from pathlib import Path
import threading
import time


class ControllerType(Enum):
    PUSH1 = "push1"
    PUSH2 = "push2"
    PUSH3 = "push3"
    LAUNCHPAD_MINI = "launchpad_mini"
    LAUNCHPAD_MK2 = "launchpad_mk2"
    LAUNCHPAD_PRO = "launchpad_pro"
    LAUNCHPAD_X = "launchpad_x"
    AKAI_MPC = "akai_mpc"
    NOVATION_CIRCUIT = "novation_circuit"
    GAMEPAD_XBOX = "gamepad_xbox"
    GAMEPAD_PS5 = "gamepad_ps5"
    GAMEPAD_SWITCH = "gamepad_switch"
    GAMEPAD_GENERIC = "gamepad_generic"
    BLUETOOTH_MIDI = "bluetooth_midi"
    USB_OTG = "usb_otg"
    CUSTOM = "custom"


class ControlType(Enum):
    KNOB = "knob"
    FADER = "fader"
    BUTTON = "button"
    PAD = "pad"
    ENCODER = "encoder"
    TOUCH_STRIP = "touch_strip"
    JOYSTICK = "joystick"
    TRIGGER = "trigger"


@dataclass
class ControlElement:
    name: str
    control_type: ControlType
    midi_cc: Optional[int] = None
    midi_note: Optional[int] = None
    channel: int = 0
    min_value: float = 0.0
    max_value: float = 127.0
    is_momentary: bool = False
    color: Optional[str] = None  # For RGB pads
    metadata: Dict = field(default_factory=dict)


@dataclass
class ControllerMapping:
    controller_type: ControllerType
    controls: Dict[str, ControlElement] = field(default_factory=dict)
    daw_mappings: Dict[str, Dict] = field(default_factory=dict)  # daw_param -> control_name
    layout: Dict = field(default_factory=dict)  # Visual layout info


class BaseControllerAdapter(ABC):
    """Abstract base for all controller adapters"""
    
    def __init__(self, controller_type: ControllerType):
        self.controller_type = controller_type
        self.connected = False
        self.device = None
        self.mapping = ControllerMapping(controller_type=controller_type)
        self.callbacks: Dict[str, List[Callable]] = {}
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
    
    @abstractmethod
    async def connect(self) -> bool:
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        pass
    
    @abstractmethod
    def _monitor_loop(self):
        """Background thread to read controller input"""
        pass
    
    def register_callback(self, event: str, callback: Callable):
        """Register callback for control events"""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)
    
    def _emit(self, event: str, data: Any):
        """Emit event to callbacks"""
        for cb in self.callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                print(f"Callback error: {e}")
    
    def map_control(self, daw_parameter: str, control_name: str, 
                   curve: str = "linear", min_val: float = 0.0, max_val: float = 1.0):
        """Map a DAW parameter to a physical control"""
        self.mapping.daw_mappings[daw_parameter] = {
            "control": control_name,
            "curve": curve,
            "min": min_val,
            "max": max_val
        }
    
    def get_control_value(self, control_name: str) -> Optional[float]:
        """Get current value of a control (normalized 0-1)"""
        control = self.mapping.controls.get(control_name)
        if not control:
            return None
        # Would read from device in real implementation
        return 0.0
    
    def set_led(self, control_name: str, color: str, brightness: float = 1.0):
        """Set LED color on controller (for RGB pads/buttons)"""
        pass
    
    def set_led_brightness(self, control_name: str, brightness: float):
        """Set LED brightness (0-1)"""
        pass


class Push1Adapter(BaseControllerAdapter):
    """Ableton Push 1 adapter"""
    
    def __init__(self):
        super().__init__(ControllerType.PUSH1)
        self._setup_mapping()
    
    def _setup_mapping(self):
        # 8x8 pad grid (note 36-99)
        for row in range(8):
            for col in range(8):
                note = 36 + row * 8 + col
                self.mapping.controls[f"pad_{row}_{col}"] = ControlElement(
                    name=f"pad_{row}_{col}",
                    control_type=ControlType.PAD,
                    midi_note=note,
                    channel=0,
                    color="#FFFFFF"
                )
        
        # 8 encoders (CC 14-21)
        for i in range(8):
            self.mapping.controls[f"encoder_{i}"] = ControlElement(
                name=f"encoder_{i}",
                control_type=ControlType.ENCODER,
                midi_cc=14 + i,
                channel=0
            )
        
        # 8 buttons above encoders (CC 22-29)
        for i in range(8):
            self.mapping.controls[f"button_enc_{i}"] = ControlElement(
                name=f"button_enc_{i}",
                control_type=ControlType.BUTTON,
                midi_cc=22 + i,
                channel=0,
                is_momentary=True
            )
        
        # Transport buttons
        transport = {
            "play": 118, "stop": 117, "record": 119,
            "loop": 114, "rewind": 115, "forward": 116,
            "tap_tempo": 113, "metronome": 112
        }
        for name, cc in transport.items():
            self.mapping.controls[name] = ControlElement(
                name=name, control_type=ControlType.BUTTON, midi_cc=cc, channel=0, is_momentary=True
            )
        
        # Master encoder
        self.mapping.controls["master_encoder"] = ControlElement(
            name="master_encoder", control_type=ControlType.ENCODER, midi_cc=13, channel=0
        )
    
    async def connect(self) -> bool:
        try:
            # Find Push 1 via MIDI
            for name in mido.get_input_names():
                if "push" in name.lower() and "1" in name:
                    self.device = mido.open_input(name)
                    self.connected = True
                    self._running = True
                    self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                    self._monitor_thread.start()
                    return True
            return False
        except Exception as e:
            print(f"Push 1 connect error: {e}")
            return False
    
    async def disconnect(self) -> bool:
        self._running = False
        if self.device:
            self.device.close()
        self.connected = False
        return True
    
    def _monitor_loop(self):
        while self._running and self.device:
            try:
                msg = self.device.poll()
                if msg:
                    self._handle_midi(msg)
            except:
                pass
            time.sleep(0.001)
    
    def _handle_midi(self, msg):
        # Map MIDI to control events
        if msg.type == "control_change":
            control = next((c for c in self.mapping.controls.values() 
                          if c.midi_cc == msg.control and c.channel == msg.channel), None)
            if control:
                normalized = msg.value / 127.0
                self._emit(f"control_{control.name}", {"value": normalized, "raw": msg.value})
        elif msg.type == "note_on":
            control = next((c for c in self.mapping.controls.values() 
                          if c.midi_note == msg.note and c.channel == msg.channel), None)
            if control:
                self._emit(f"pad_{control.name}", {"pressed": True, "velocity": msg.velocity})
        elif msg.type == "note_off":
            control = next((c for c in self.mapping.controls.values() 
                          if c.midi_note == msg.note and c.channel == msg.channel), None)
            if control:
                self._emit(f"pad_{control.name}", {"pressed": False})


class Push2Adapter(Push1Adapter):
    """Ableton Push 2 adapter (extends Push 1 with display support)"""
    
    def __init__(self):
        super().__init__()
        self.controller_type = ControllerType.PUSH2
        self._setup_display_mapping()
    
    def _setup_display_mapping(self):
        # Additional controls for Push 2
        # Touch strip
        self.mapping.controls["touch_strip"] = ControlElement(
            name="touch_strip", control_type=ControlType.TOUCH_STRIP,
            midi_cc=12, channel=0
        )
        
        # Additional buttons
        extra_buttons = {
            "add_device": 102, "add_track": 103, "device": 104,
            "mixer": 105, "clip": 106, "browse": 107,
            "automate": 108, "duplicate": 109, "double": 110,
            "quantize": 111, "session": 30, "note": 31
        }
        for name, cc in extra_buttons.items():
            self.mapping.controls[name] = ControlElement(
                name=name, control_type=ControlType.BUTTON, midi_cc=cc, channel=0, is_momentary=True
            )


class LaunchpadAdapter(BaseControllerAdapter):
    """Novation Launchpad family adapter"""
    
    LAUNCHPAD_MODELS = {
        ControllerType.LAUNCHPAD_MINI: {"pads": 64, "size": 8},
        ControllerType.LAUNCHPAD_MK2: {"pads": 64, "size": 8},
        ControllerType.LAUNCHPAD_PRO: {"pads": 64, "size": 8, "rgb": True},
        ControllerType.LAUNCHPAD_X: {"pads": 64, "size": 8, "rgb": True},
    }
    
    def __init__(self, controller_type: ControllerType):
        super().__init__(controller_type)
        self.model_info = self.LAUNCHPAD_MODELS.get(controller_type, {"pads": 64, "size": 8})
        self._setup_mapping()
    
    def _setup_mapping(self):
        size = self.model_info["size"]
        has_rgb = self.model_info.get("rgb", False)
        
        # Pad grid (note 0-63 for most Launchpads)
        for row in range(size):
            for col in range(size):
                note = row * size + col
                self.mapping.controls[f"pad_{row}_{col}"] = ControlElement(
                    name=f"pad_{row}_{col}",
                    control_type=ControlType.PAD,
                    midi_note=note,
                    channel=0,
                    color="#FFFFFF" if has_rgb else "#00FF00"
                )
        
        # Side buttons (CC 104-111 for MK2/Pro)
        for i in range(8):
            self.mapping.controls[f"side_{i}"] = ControlElement(
                name=f"side_{i}",
                control_type=ControlType.BUTTON,
                midi_cc=104 + i,
                channel=0,
                is_momentary=True
            )
        
        # Top buttons (scene launch)
        for i in range(8):
            self.mapping.controls[f"scene_{i}"] = ControlElement(
                name=f"scene_{i}",
                control_type=ControlType.BUTTON,
                midi_cc=89 + i,
                channel=0,
                is_momentary=True
            )
    
    async def connect(self) -> bool:
        try:
            for name in mido.get_input_names():
                if "launchpad" in name.lower():
                    self.device = mido.open_input(name)
                    self.connected = True
                    self._running = True
                    self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                    self._monitor_thread.start()
                    return True
            return False
        except Exception as e:
            print(f"Launchpad connect error: {e}")
            return False
    
    async def disconnect(self) -> bool:
        self._running = False
        if self.device:
            self.device.close()
        self.connected = False
        return True
    
    def _monitor_loop(self):
        while self._running and self.device:
            try:
                msg = self.device.poll()
                if msg:
                    self._handle_midi(msg)
            except:
                pass
            time.sleep(0.001)
    
    def _handle_midi(self, msg):
        if msg.type == "note_on":
            control = next((c for c in self.mapping.controls.values() 
                          if c.midi_note == msg.note and c.channel == msg.channel), None)
            if control:
                self._emit(f"pad_{control.name}", {"pressed": True, "velocity": msg.velocity})
        elif msg.type == "note_off":
            control = next((c for c in self.mapping.controls.values() 
                          if c.midi_note == msg.note and c.channel == msg.channel), None)
            if control:
                self._emit(f"pad_{control.name}", {"pressed": False})
        elif msg.type == "control_change":
            control = next((c for c in self.mapping.controls.values() 
                          if c.midi_cc == msg.control and c.channel == msg.channel), None)
            if control:
                normalized = msg.value / 127.0
                self._emit(f"control_{control.name}", {"value": normalized, "raw": msg.value})


class GamepadAdapter(BaseControllerAdapter):
    """Generic gamepad adapter (Xbox, PS5, Switch, Generic)"""
    
    def __init__(self, controller_type: ControllerType):
        super().__init__(controller_type)
        self._setup_mapping()
    
    def _setup_mapping(self):
        # Standard gamepad layout
        # Axes (normalized -1 to 1)
        axes = [
            "left_stick_x", "left_stick_y", 
            "right_stick_x", "right_stick_y",
            "left_trigger", "right_trigger"
        ]
        for i, name in enumerate(axes):
            self.mapping.controls[name] = ControlElement(
                name=name, control_type=ControlType.JOYSTICK,
                midi_cc=16 + i, channel=0,
                min_value=-1.0, max_value=1.0
            )
        
        # Buttons (face buttons)
        face_buttons = ["a", "b", "x", "y"]
        for i, name in enumerate(face_buttons):
            self.mapping.controls[name] = ControlElement(
                name=name, control_type=ControlType.BUTTON,
                midi_note=60 + i, channel=0, is_momentary=True
            )
        
        # Shoulder buttons
        shoulder = ["lb", "rb", "lt", "rt"]
        for i, name in enumerate(shoulder):
            self.mapping.controls[name] = ControlElement(
                name=name, control_type=ControlType.TRIGGER,
                midi_cc=20 + i, channel=0, is_momentary=True
            )
        
        # D-pad
        dpad = ["dpad_up", "dpad_down", "dpad_left", "dpad_right"]
        for i, name in enumerate(dpad):
            self.mapping.controls[name] = ControlElement(
                name=name, control_type=ControlType.BUTTON,
                midi_note=64 + i, channel=0, is_momentary=True
            )
        
        # System buttons
        system = ["back", "start", "guide", "left_stick_btn", "right_stick_btn"]
        for i, name in enumerate(system):
            self.mapping.controls[name] = ControlElement(
                name=name, control_type=ControlType.BUTTON,
                midi_note=68 + i, channel=0, is_momentary=True
            )
    
    async def connect(self) -> bool:
        try:
            # Find gamepad via HID
            devices = hid.enumerate()
            for dev in devices:
                if self._is_gamepad(dev):
                    self.device = hid.device()
                    self.device.open(dev['vendor_id'], dev['product_id'])
                    self.device.set_nonblocking(True)
                    self.connected = True
                    self._running = True
                    self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                    self._monitor_thread.start()
                    return True
            return False
        except Exception as e:
            print(f"Gamepad connect error: {e}")
            return False
    
    def _is_gamepad(self, dev: Dict) -> bool:
        # Check if device is a gamepad
        name = (dev.get('product_string', '') + dev.get('manufacturer_string', '')).lower()
        keywords = ['gamepad', 'controller', 'xbox', 'playstation', 'dualsense', 'switch', 'pro controller']
        return any(k in name for k in keywords)
    
    async def disconnect(self) -> bool:
        self._running = False
        if self.device:
            self.device.close()
        self.connected = False
        return True
    
    def _monitor_loop(self):
        while self._running and self.device:
            try:
                data = self.device.read(64)
                if data:
                    self._handle_hid(data)
            except:
                pass
            time.sleep(0.005)  # 200Hz polling
    
    def _handle_hid(self, data: List[int]):
        """Parse HID report based on controller type"""
        if not data or len(data) < 4:
            return
        
        # Xbox controller report format (XInput)
        if self.controller_type in (ControllerType.GAMEPAD_XBOX, ControllerType.GAMEPAD_GENERIC):
            self._parse_xbox_report(data)
        # PS5 DualSense report format
        elif self.controller_type == ControllerType.GAMEPAD_PS5:
            self._parse_dualsense_report(data)
        # Switch Pro Controller report format
        elif self.controller_type == ControllerType.GAMEPAD_SWITCH:
            self._parse_switch_report(data)
    
    def _parse_xbox_report(self, data: List[int]):
        """Parse Xbox/Generic gamepad HID report (XInput layout)"""
        # Typical Xbox HID report: [report_id, buttons_low, buttons_high, lt, rt, lx, ly, rx, ry, ...]
        if len(data) < 10:
            return
        
        # Buttons (bits in bytes 1-2)
        buttons_low = data[1] if len(data) > 1 else 0
        buttons_high = data[2] if len(data) > 2 else 0
        
        # Button mapping (XInput standard)
        btn_map = {
            'a': buttons_low & 0x10,
            'b': buttons_low & 0x20,
            'x': buttons_low & 0x40,
            'y': buttons_low & 0x80,
            'lb': buttons_high & 0x01,
            'rb': buttons_high & 0x02,
            'back': buttons_high & 0x10,
            'start': buttons_high & 0x20,
            'left_stick_btn': buttons_high & 0x40,
            'right_stick_btn': buttons_high & 0x80,
        }
        
        for name, pressed in btn_map.items():
            if name in self.mapping.controls:
                self._emit(f"button_{name}", {"pressed": bool(pressed)})
        
        # D-pad (usually in buttons_low lower nibble)
        dpad = buttons_low & 0x0F
        dpad_map = {0: 'up', 1: 'up_right', 2: 'right', 3: 'down_right', 
                    4: 'down', 5: 'down_left', 6: 'left', 7: 'up_left', 8: 'centered'}
        if dpad in dpad_map and dpad != 8:
            for dir_name in ['up', 'down', 'left', 'right']:
                pressed = dir_name in dpad_map.get(dpad, '')
                if f'dpad_{dir_name}' in self.mapping.controls:
                    self._emit(f"button_dpad_{dir_name}", {"pressed": pressed})
        
        # Triggers (bytes 3-4, 0-255)
        lt = data[3] / 255.0 if len(data) > 3 else 0.0
        rt = data[4] / 255.0 if len(data) > 4 else 0.0
        if 'lt' in self.mapping.controls:
            self._emit("trigger_lt", {"value": lt})
        if 'rt' in self.mapping.controls:
            self._emit("trigger_rt", {"value": rt})
        
        # Sticks (bytes 5-8, signed -128 to 127, centered at 0)
        def normalize_stick(val):
            return (val - 128) / 128.0 if val != 128 else 0.0
        
        lx = normalize_stick(data[5]) if len(data) > 5 else 0.0
        ly = -normalize_stick(data[6]) if len(data) > 6 else 0.0  # Y inverted
        rx = normalize_stick(data[7]) if len(data) > 7 else 0.0
        ry = -normalize_stick(data[8]) if len(data) > 8 else 0.0
        
        # Apply deadzone
        deadzone = 0.1
        for axis, val in [('lx', lx), ('ly', ly), ('rx', rx), ('ry', ry)]:
            if abs(val) < deadzone:
                val = 0.0
            if f'stick_{axis}' in self.mapping.controls:
                self._emit(f"stick_{axis}", {"value": val})
    
    def _parse_dualsense_report(self, data: List[int]):
        """Parse PS5 DualSense HID report"""
        # DualSense report format varies by connection (USB vs BT)
        # USB: 64 bytes, BT: 78 bytes
        # Simplified parsing for common layout
        if len(data) < 16:
            return
        
        # Buttons (typically bytes 5-8)
        # This is simplified - real implementation needs proper DualSense HID spec
        btn_offset = 5 if len(data) > 20 else 2
        
        # For now, emit raw data for debugging
        self._emit("raw_hid", {"data": data[:16]})
    
    def _parse_switch_report(self, data: List[int]):
        """Parse Switch Pro Controller HID report"""
        # Switch Pro Controller uses 64-byte reports
        # Simplified parsing
        if len(data) < 16:
            return
        
        self._emit("raw_hid", {"data": data[:16]})


class BluetoothMIDIAdapter(BaseControllerAdapter):
    """Bluetooth MIDI controller adapter with platform-specific support"""
    
    def __init__(self):
        super().__init__(ControllerType.BLUETOOTH_MIDI)
        self._setup_mapping()
        self.platform = self._get_platform()
    
    def _get_platform(self):
        import platform
        return platform.system().lower()
    
    def _setup_mapping(self):
        # Generic MIDI controls - will be populated on connect
        pass
    
    async def connect(self) -> bool:
        try:
            # Platform-specific Bluetooth MIDI discovery
            if self.platform == "windows":
                return await self._connect_windows()
            elif self.platform == "darwin":
                return await self._connect_macos()
            elif self.platform == "linux":
                return await self._connect_linux()
            else:
                return await self._connect_generic()
        except Exception as e:
            print(f"Bluetooth MIDI connect error: {e}")
            return False
    
    async def _connect_windows(self) -> bool:
        """Windows 10+ has built-in Bluetooth MIDI support via UWP MIDI API"""
        try:
            # On Windows, Bluetooth MIDI devices appear as regular MIDI ports
            # when paired via Settings > Bluetooth > MIDI devices
            for name in mido.get_input_names():
                name_lower = name.lower()
                if any(kw in name_lower for kw in ["bluetooth", "bt-", "bt_", "midi", "ble"]):
                    # Skip virtual ports
                    if not any(skip in name_lower for skip in ["virtual", "microsoft gs", "loopback", "rtpmidi"]):
                        self.device = mido.open_input(name)
                        self.connected = True
                        self._running = True
                        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                        self._monitor_thread.start()
                        print(f"Connected to Bluetooth MIDI (Windows): {name}")
                        return True
            return False
        except Exception as e:
            print(f"Windows Bluetooth MIDI error: {e}")
            return False
    
    async def _connect_macos(self) -> bool:
        """macOS has native Bluetooth MIDI via Audio MIDI Setup"""
        try:
            for name in mido.get_input_names():
                name_lower = name.lower()
                # macOS Bluetooth MIDI typically shows as "Bluetooth MIDI" or device name
                if not any(skip in name_lower for skip in ["virtual", "iacc", "network", "loopback"]):
                    if "bluetooth" in name_lower or "bt" in name_lower or True:  # On macOS, most external MIDI is BT
                        self.device = mido.open_input(name)
                        self.connected = True
                        self._running = True
                        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                        self._monitor_thread.start()
                        print(f"Connected to MIDI (macOS): {name}")
                        return True
            return False
        except Exception as e:
            print(f"macOS Bluetooth MIDI error: {e}")
            return False
    
    async def _connect_linux(self) -> bool:
        """Linux uses BlueZ for Bluetooth MIDI"""
        try:
            for name in mido.get_input_names():
                name_lower = name.lower()
                if not any(skip in name_lower for skip in ["virtual", "through", "loopback", "network"]):
                    self.device = mido.open_input(name)
                    self.connected = True
                    self._running = True
                    self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                    self._monitor_thread.start()
                    print(f"Connected to MIDI (Linux): {name}")
                    return True
            return False
        except Exception as e:
            print(f"Linux Bluetooth MIDI error: {e}")
            return False
    
    async def _connect_generic(self) -> bool:
        """Generic fallback"""
        try:
            for name in mido.get_input_names():
                name_lower = name.lower()
                if any(kw in name_lower for kw in ["bluetooth", "bt", "ble"]):
                    if not any(skip in name_lower for skip in ["virtual", "loopback", "network"]):
                        self.device = mido.open_input(name)
                        self.connected = True
                        self._running = True
                        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                        self._monitor_thread.start()
                        return True
            return False
        except Exception as e:
            print(f"Generic Bluetooth MIDI error: {e}")
            return False
    
    async def disconnect(self) -> bool:
        self._running = False
        if self.device:
            self.device.close()
        self.connected = False
        return True
    
    def _monitor_loop(self):
        while self._running and self.device:
            try:
                msg = self.device.poll()
                if msg:
                    self._handle_midi(msg)
            except:
                pass
            time.sleep(0.001)
    
    def _handle_midi(self, msg):
        # Generic MIDI handling with full message detail
        if msg.type in ("control_change", "note_on", "note_off", "pitchwheel", "program_change", "aftertouch", "polytouch"):
            key = f"{msg.type}_{msg.control if msg.type == 'control_change' else msg.note if hasattr(msg, 'note') else msg.program if hasattr(msg, 'program') else msg.value if hasattr(msg, 'value') else 0}"
            self._emit(key, {
                "type": msg.type,
                "channel": msg.channel,
                "control": getattr(msg, 'control', None),
                "note": getattr(msg, 'note', None),
                "velocity": getattr(msg, 'velocity', None),
                "value": getattr(msg, 'value', None),
                "program": getattr(msg, 'program', None),
                "pitch": getattr(msg, 'pitch', None),
                "time": time.time()
            })


class USBMIDIAdapter(BaseControllerAdapter):
    """Generic USB MIDI controller adapter"""
    
    def __init__(self):
        super().__init__(ControllerType.USB_OTG)
        self._setup_mapping()
    
    def _setup_mapping(self):
        pass
    
    async def connect(self) -> bool:
        try:
            # Auto-detect USB MIDI devices
            inputs = mido.get_input_names()
            for name in inputs:
                # Skip known virtual ports
                if not any(skip in name.lower() for skip in ["virtual", "microsoft", "loopback"]):
                    self.device = mido.open_input(name)
                    self.connected = True
                    self._running = True
                    self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                    self._monitor_thread.start()
                    print(f"Connected to USB MIDI: {name}")
                    return True
            return False
        except Exception as e:
            print(f"USB MIDI connect error: {e}")
            return False
    
    async def disconnect(self) -> bool:
        self._running = False
        if self.device:
            self.device.close()
        self.connected = False
        return True
    
    def _monitor_loop(self):
        while self._running and self.device:
            try:
                msg = self.device.poll()
                if msg:
                    self._handle_midi(msg)
            except:
                pass
            time.sleep(0.001)
    
    def _handle_midi(self, msg):
        if msg.type in ("control_change", "note_on", "note_off", "pitchwheel"):
            self._emit(f"midi_{msg.type}", msg.__dict__)


class UniversalController:
    """Main universal controller manager"""
    
    def __init__(self):
        self.controllers: Dict[str, BaseControllerAdapter] = {}
        self.active_controller: Optional[BaseControllerAdapter] = None
        self.daw_adapter = None
        self._register_default_controllers()
    
    def _register_default_controllers(self):
        """Register all supported controller types"""
        self.controller_classes = {
            ControllerType.PUSH1: Push1Adapter,
            ControllerType.PUSH2: Push2Adapter,
            ControllerType.LAUNCHPAD_MINI: lambda: LaunchpadAdapter(ControllerType.LAUNCHPAD_MINI),
            ControllerType.LAUNCHPAD_MK2: lambda: LaunchpadAdapter(ControllerType.LAUNCHPAD_MK2),
            ControllerType.LAUNCHPAD_PRO: lambda: LaunchpadAdapter(ControllerType.LAUNCHPAD_PRO),
            ControllerType.LAUNCHPAD_X: lambda: LaunchpadAdapter(ControllerType.LAUNCHPAD_X),
            ControllerType.GAMEPAD_XBOX: lambda: GamepadAdapter(ControllerType.GAMEPAD_XBOX),
            ControllerType.GAMEPAD_PS5: lambda: GamepadAdapter(ControllerType.GAMEPAD_PS5),
            ControllerType.GAMEPAD_SWITCH: lambda: GamepadAdapter(ControllerType.GAMEPAD_SWITCH),
            ControllerType.GAMEPAD_GENERIC: lambda: GamepadAdapter(ControllerType.GAMEPAD_GENERIC),
            ControllerType.BLUETOOTH_MIDI: BluetoothMIDIAdapter,
            ControllerType.USB_OTG: USBMIDIAdapter,
        }
    
    async def auto_detect(self) -> Dict[str, bool]:
        """Auto-detect and connect all available controllers"""
        results = {}
        
        for ctrl_type, factory in self.controller_classes.items():
            try:
                adapter = factory()
                connected = await adapter.connect()
                if connected:
                    self.controllers[ctrl_type.value] = adapter
                    if not self.active_controller:
                        self.active_controller = adapter
                results[ctrl_type.value] = connected
            except Exception as e:
                print(f"Error detecting {ctrl_type.value}: {e}")
                results[ctrl_type.value] = False
        
        return results
    
    async def connect_controller(self, controller_type: ControllerType) -> bool:
        """Manually connect a specific controller"""
        if controller_type.value in self.controllers:
            return True  # Already connected
        
        factory = self.controller_classes.get(controller_type)
        if not factory:
            return False
        
        try:
            adapter = factory()
            connected = await adapter.connect()
            if connected:
                self.controllers[controller_type.value] = adapter
                if not self.active_controller:
                    self.active_controller = adapter
            return connected
        except Exception as e:
            print(f"Error connecting {controller_type.value}: {e}")
            return False
    
    def set_daw_adapter(self, daw_adapter):
        """Set the DAW adapter for control mapping"""
        self.daw_adapter = daw_adapter
        
        # Forward control events to DAW
        for adapter in self.controllers.values():
            adapter.register_callback("control_*", self._forward_to_daw)
            adapter.register_callback("pad_*", self._forward_to_daw)
    
    def _forward_to_daw(self, data: Dict):
        """Forward controller events to DAW adapter"""
        if self.daw_adapter and self.active_controller:
            # Map controller event to DAW parameter
            for daw_param, mapping in self.active_controller.mapping.daw_mappings.items():
                # In real implementation, would match event to mapping
                pass
    
    def get_active(self) -> Optional[BaseControllerAdapter]:
        return self.active_controller
    
    def set_active(self, controller_type: ControllerType) -> bool:
        if controller_type.value in self.controllers:
            self.active_controller = self.controllers[controller_type.value]
            return True
        return False
    
    def list_connected(self) -> List[str]:
        return list(self.controllers.keys())
    
    async def disconnect_all(self):
        for adapter in self.controllers.values():
            await adapter.disconnect()
        self.controllers.clear()
        self.active_controller = None


# Preset mappings for common setups
DEFAULT_MAPPINGS = {
    "ableton_mixer": {
        "description": "Standard Ableton mixer layout",
        "mappings": {
            "track_1_volume": "encoder_0",
            "track_2_volume": "encoder_1",
            "track_3_volume": "encoder_2",
            "track_4_volume": "encoder_3",
            "track_5_volume": "encoder_4",
            "track_6_volume": "encoder_5",
            "track_7_volume": "encoder_6",
            "track_8_volume": "encoder_7",
            "master_volume": "master_encoder",
            "track_1_pan": "encoder_0",  # With shift
            "track_1_send_a": "encoder_1",  # With shift
            "play": "play",
            "stop": "stop",
            "record": "record",
            "loop": "loop",
        }
    },
    "ableton_device": {
        "description": "Device parameter control",
        "mappings": {
            "device_param_1": "encoder_0",
            "device_param_2": "encoder_1",
            "device_param_3": "encoder_2",
            "device_param_4": "encoder_3",
            "device_param_5": "encoder_4",
            "device_param_6": "encoder_5",
            "device_param_7": "encoder_6",
            "device_param_8": "encoder_7",
            "prev_device": "button_enc_0",
            "next_device": "button_enc_1",
            "device_on": "button_enc_2",
        }
    },
    "launchpad_session": {
        "description": "Launchpad session view control",
        "mappings": {
            "clip_1_1": "pad_0_0", "clip_1_2": "pad_0_1", "clip_1_3": "pad_0_2", "clip_1_4": "pad_0_3",
            "clip_2_1": "pad_1_0", "clip_2_2": "pad_1_1", "clip_2_3": "pad_1_2", "clip_2_4": "pad_1_3",
            "clip_3_1": "pad_2_0", "clip_3_2": "pad_2_1", "clip_3_3": "pad_2_2", "clip_3_4": "pad_2_3",
            "clip_4_1": "pad_3_0", "clip_4_2": "pad_3_1", "clip_4_3": "pad_3_2", "clip_4_4": "pad_3_3",
            "scene_1": "scene_0", "scene_2": "scene_1", "scene_3": "scene_2", "scene_4": "scene_3",
        }
    }
}


def apply_mapping(controller: BaseControllerAdapter, mapping_name: str):
    """Apply a preset mapping to a controller"""
    mapping = DEFAULT_MAPPINGS.get(mapping_name)
    if not mapping:
        return False
    
    for daw_param, control_name in mapping["mappings"].items():
        controller.map_control(daw_param, control_name)
    
    return True


if __name__ == "__main__":
    print("Universal Controller Layer - Phase 3")
    print("Supported controllers:")
    for ctrl in ControllerType:
        print(f"  - {ctrl.value}")
    print("\nPreset mappings:")
    for name, info in DEFAULT_MAPPINGS.items():
        print(f"  - {name}: {info['description']}")