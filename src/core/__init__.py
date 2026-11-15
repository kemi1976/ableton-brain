"""ABLETON BRAIN Core Module"""
from .universal_midi_translator import (
    UniversalMIDITranslator,
    ControllerType,
    ControlMapping,
    DAWPlatform,
    ControllerCapabilities
)

__version__ = "1.0.0"
__all__ = [
    "UniversalMIDITranslator",
    "ControllerType", 
    "ControlMapping",
    "DAWPlatform",
    "ControllerCapabilities"
]