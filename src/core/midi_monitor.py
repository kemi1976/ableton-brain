#!/usr/bin/env python3
"""
MIDI Monitor - Real-time MIDI traffic visualization
===============================================
Provides live MIDI monitoring for debugging and creative control
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from collections import deque

PROJECT_ROOT = Path(__file__).parent.parent.parent

class MIDIContentType(Enum):
    """Type of MIDI message content"""
    NOTE_ON = "note_on"
    NOTE_OFF = "note_off"
    CONTROL_CHANGE = "control_change"
    PROGRAM_CHANGE = "program_change"
    PITCH_WHEEL = "pitch_wheel"
    SYSEX = "sysex"
    UNKNOWN = "unknown"

@dataclass
class MIDIEvent:
    """Parsed MIDI event"""
    timestamp: float
    channel: int
    message_type: MIDIContentType
    note: Optional[int] = None
    velocity: Optional[int] = None
    control: Optional[int] = None
    value: Optional[int] = None
    raw_message: Optional[List[int]] = None

class MIDIEventParser:
    """Parse raw MIDI bytes into structured events"""
    
    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    @staticmethod
    def parse_message(message: List[int]) -> Optional[MIDIEvent]:
        """Parse a raw MIDI message"""
        if not message:
            return None
            
        status = message[0]
        channel = status & 0x0F
        message_type = MIDIContentType.UNKNOWN
        
        if len(message) < 2:
            return MIDIEvent(time.time(), channel, message_type, raw_message=message)
        
        # Note On (0x90-0x9F)
        if 0x90 <= status <= 0x9F:
            message_type = MIDIContentType.NOTE_ON
            note = message[1] if len(message) > 1 else 0
            velocity = message[2] if len(message) > 2 else 0
            return MIDIEvent(time.time(), channel, message_type, note=note, velocity=velocity, raw_message=message)
        
        # Note Off (0x80-0x8F)
        if 0x80 <= status <= 0x8F:
            message_type = MIDIContentType.NOTE_OFF
            note = message[1] if len(message) > 1 else 0
            velocity = message[2] if len(message) > 2 else 0
            return MIDIEvent(time.time(), channel, message_type, note=note, velocity=velocity, raw_message=message)
        
        # Control Change (0xB0-0xBF)
        if 0xB0 <= status <= 0xBF:
            message_type = MIDIContentType.CONTROL_CHANGE
            control = message[1] if len(message) > 1 else 0
            value = message[2] if len(message) > 2 else 0
            return MIDIEvent(time.time(), channel, message_type, control=control, value=value, raw_message=message)
        
        # Program Change (0xC0-0xCF)
        if 0xC0 <= status <= 0xCF:
            message_type = MIDIContentType.PROGRAM_CHANGE
            value = message[1] if len(message) > 1 else 0
            return MIDIEvent(time.time(), channel, message_type, value=value, raw_message=message)
        
        # Pitch Wheel (0xE0-0xEF)
        if 0xE0 <= status <= 0xEF:
            message_type = MIDIContentType.PITCH_WHEEL
            if len(message) > 2:
                value = (message[2] << 7) | message[1]
            else:
                value = 0
            return MIDIEvent(time.time(), channel, message_type, value=value, raw_message=message)
        
        return MIDIEvent(time.time(), channel, message_type, raw_message=message)
    
    @staticmethod
    def note_number_to_name(note: int) -> str:
        """Convert MIDI note number to note name"""
        octave = (note // 12) - 1
        name = MIDIEventParser.NOTE_NAMES[note % 12]
        return f"{name}{octave}"

class MIDIConsoleVisualizer:
    """ASCII visualization of MIDI events in console"""
    
    def __init__(self, max_events: int = 50):
        self.max_events = max_events
        self.event_history: deque = deque(maxlen=max_events)
        self.recording = False
        self.output_file: Optional[Path] = None
        self.stats = {
            'total_events': 0,
            'note_ons': 0,
            'note_offs': 0,
            'control_changes': 0,
            'program_changes': 0,
            'pitch_wheels': 0
        }
    
    def add_event(self, event: MIDIEvent) -> None:
        """Add an event to the history"""
        self.event_history.appendleft(event)
        self.stats['total_events'] += 1
        
        # Update specific stats
        if event.message_type == MIDIContentType.NOTE_ON:
            self.stats['note_ons'] += 1
        elif event.message_type == MIDIContentType.NOTE_OFF:
            self.stats['note_offs'] += 1
        elif event.message_type == MIDIContentType.CONTROL_CHANGE:
            self.stats['control_changes'] += 1
        elif event.message_type == MIDIContentType.PROGRAM_CHANGE:
            self.stats['program_changes'] += 1
        elif event.message_type == MIDIContentType.PITCH_WHEEL:
            self.stats['pitch_wheels'] += 1
    
    def format_event(self, event: MIDIEvent) -> str:
        """Format an event for display"""
        time_str = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S.%f")[:-3]
        channel = event.channel
        
        if event.message_type == MIDIContentType.NOTE_ON:
            note_name = MIDIEventParser.note_number_to_name(event.note)
            velocity_bar = '█' * (event.velocity // 8) if event.velocity else ''
            return f"{time_str} | Ch{channel} | NOTE ON  | {note_name:4s} (vel: {event.velocity:3d}) {velocity_bar}"
        
        elif event.message_type == MIDIContentType.NOTE_OFF:
            note_name = MIDIEventParser.note_number_to_name(event.note)
            return f"{time_str} | Ch{channel} | NOTE OFF | {note_name:4s} (vel: {event.velocity:3d})"
        
        elif event.message_type == MIDIContentType.CONTROL_CHANGE:
            control_names = {
                1: "Mod", 7: "Vol", 10: "Pan", 11: "Expr",
                32: "Sustain", 64: "Hold", 12: "Damp"
            }
            ctrl_name = control_names.get(event.control, f"CC{event.control}")
            bar = '█' * (event.value // 16) if event.value else ''
            return f"{time_str} | Ch{channel} | CC       | {ctrl_name:10s} = {event.value:3d} (0-127) {bar}"
        
        elif event.message_type == MIDIContentType.PROGRAM_CHANGE:
            return f"{time_str} | Ch{channel} | PROG     | Program {event.value:2d}"
        
        elif event.message_type == MIDIContentType.PITCH_WHEEL:
            val = event.value - 8192  # Center at 0
            direction = "↑" if val > 0 else "↓" if val < 0 else "="
            bar = '█' * (abs(val) // 200)
            return f"{time_str} | Ch{channel} | PITCH    | {val:+6d} {direction} {bar}"
        
        else:
            return f"{time_str} | Ch{channel} | {event.message_type.value:10s} | {event.raw_message}"
    
    def display(self, clear: bool = True) -> None:
        """Display the event history"""
        if clear:
            # Clear screen (works on Windows, Linux, macOS)
            sys.stdout.write('\033[2J\033[H')
        
        print("╔" + "═" * 70 + "╗")
        print("║ 🎹 MIDI MONITOR - Real-time MIDI Traffic Visualization           ║")
        print("╠" + "═" * 70 + "╣")
        print(f"║ Events: {self.stats['total_events']:5d} | Note On: {self.stats['note_ons']:4d} | " 
              f"Note Off: {self.stats['note_offs']:4d} | CC: {self.stats['control_changes']:4d}           ║")
        print(f"║ Recording: {'YES' if self.recording else 'NO':4s}                              "
              f"| Press [R] to toggle recording           ║")
        print("╠" + "═" * 70 + "╣")
        print("║ " + "─" * 68 + " ║")
        
        for event in list(self.event_history)[:20]:  # Show last 20 events
            line = self.format_event(event)
            if len(line) > 68:
                line = line[:65] + "..."
            print(f"║ {line:<68} ║")
        
        print("║ " + "─" * 68 + " ║")
        print("╚" + "═" * 70 + "╝")
        print("\nControls: [Q]uit, [R]ecord, [C]lear, [S]ave Session")
    
    def save_session(self, filepath: Optional[str] = None) -> Path:
        """Save the current session to a JSON file"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = PROJECT_ROOT / f"midi_session_{timestamp}.json"
        else:
            filepath = Path(filepath)
        
        session_data = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'events': [
                {
                    'timestamp': e.timestamp,
                    'channel': e.channel,
                    'type': e.message_type.value,
                    'note': e.note,
                    'velocity': e.velocity,
                    'control': e.control,
                    'value': e.value,
                    'raw': e.raw_message
                }
                for e in self.event_history
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return filepath

# Global visualizer instance
_visualizer: Optional[MIDIConsoleVisualizer] = None

def get_visualizer() -> MIDIConsoleVisualizer:
    """Get or create the global visualizer instance"""
    global _visualizer
    if _visualizer is None:
        _visualizer = MIDIConsoleVisualizer()
    return _visualizer

def process_midi_message(message: List[int]) -> None:
    """Process a raw MIDI message (entry point for rtmidi/midiin)"""
    event = MIDIEventParser.parse_message(message)
    if event:
        _v = get_visualizer()
        _v.add_event(event)
        _v.display()

def start_monitor() -> None:
    """Start the MIDI monitor interface"""
    print("\n🎵 MIDI Monitor Started")
    print("Use 'process_midi_message([status, data1, data2])' to input messages\n")
    _v = get_visualizer()
    
    # Demo mode - show some example events
    demo_events = [
        [0x90, 60, 100],  # C4 note on
        [0x90, 64, 80],   # E4 note on
        [0xB0, 7, 100],   # Volume CC
        [0xE0, 0x00, 0x40],  # Pitch wheel center
        [0x90, 72, 0],    # G4 note off
    ]
    
    for msg in demo_events:
        process_midi_message(msg)
        time.sleep(0.2)

if __name__ == "__main__":
    start_monitor()