#!/usr/bin/env python3
"""
Natural Language Interface Module
Converts natural language commands to MCP tool calls.
Example: "Add reverb to vocal track at 2.5s" -> MCP call
"""

from __future__ import annotations

import re
import json
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass

try:
    import numpy as np
except ImportError:
    np = None


@dataclass
class ParsedCommand:
    """Parsed natural language command."""
    tool_name: str
    arguments: Dict[str, Any]
    confidence: float
    matched_phrases: List[str]

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "confidence": self.confidence,
            "matched_phrases": self.matched_phrases,
        }


class NaturalLanguageProcessor:
    """
    Natural language to MCP tool mapping.
    Supports verbs like: add, set, create, remove, duplicate, fire, stop, record
    Objects: track, clip, device, parameter, effect, scene, tempo, key
    Values: numbers, booleans, specific names
    """

    def __init__(self):
        # Track name patterns
        self.track_patterns = {
            "kick": ["kick", "kick drum", "808 kick", "kick 808"],
            "snare": ["snare", "snare drum", "rim", "clap", "clapper"],
            "hihat": ["hihat", "hi-hat", "open hat", "closed hat", "hi-hats"],
            "bass": ["bass", "sub bass", "low end", "808", "bass line"],
            "lead": ["lead", "synth lead", "melody", "main melody"],
            "pad": ["pad", "ambient pad", "pad layer", "atmosphere"],
            "vocals": ["vocal", "vocals", "vox", "voice", "singer"],
            "guitar": ["guitar", "guitars", "guitar riff"],
            "piano": ["piano", "keys", "key"],
            "fx": ["fx", "effects", "reverb", "delay", "riser", "fall", "noise"],
            "drums": ["drums", "drum", "percussion"],
        }

        # Device/effect patterns
        self.device_patterns = {
            "reverb": ["reverb", "hall", "plate", "room", "space"],
            "delay": ["delay", "echo", "slapback"],
            "compressor": ["compressor", "comp", "squash"],
            "eq": ["eq", "equalizer", "filter", "tone"],
            "limiter": ["limiter", "ceiling", "maximizer"],
            "chorus": ["chorus", "ensemble"],
            "flanger": ["flanger", "phaser"],
            "distortion": ["distortion", "overdrive", "saturation", "fuzz"],
            "filter": ["filter", "auto filter", "lfo filter"],
            "adder": ["adderr", "saturator", "tape"],
        }

        # Parameter patterns
        self.param_patterns = {
            "volume": ["volume", "level", "gain", "out", "output"],
            "pan": ["pan", "position", "p", "left right"],
            "cutoff": ["cutoff", "freq", "frequency", "filter", "f"],
            "resonance": ["resonance", "q", "sensitivity", "q factor"],
            "attack": ["attack", "a", "hold"],
            "decay": ["decay", "d", "release"],
            "sus": ["sus", "sustain"],
            "release": ["release", "r"],
            "width": ["width", "stereo"],
            "dry_wet": ["wet", "dry", "mix", "blend"],
            "tempo": ["tempo", "bpm", "beats per minute"],
            "transpose": ["transpose", "pitch", "key", "t"],
        }

        # Common verbs
        self.verbs = {
            "add": ["add", "insert", "create", "make", "put", "place"],
            "set": ["set", "change", "adjust", "move to", "to"],
            "remove": ["remove", "delete", "clear", "zero", "off"],
            "activate": ["activate", "enable", "turn on", "start", "run"],
            "deactivate": ["deactivate", "disable", "turn off", "stop", "mute"],
            "duplicate": ["duplicate", "copy", "clone", "dupe"],
            "fire": ["fire", "launch", "trigger", "hit", "play"],
            "stop": ["stop", "end", "kill"],
            "record": ["record", "rec", "capture", "start recording"],
            "group": ["group", "bundle", "folder"],
            "arrange": ["arrange", "organize", "order", "sequence"],
        }

    def parse(self, text: str, context: Optional[Dict] = None) -> ParsedCommand:
        """Parse natural language text to MCP command."""
        text_lower = text.lower().strip()

        # Extract entities
        track_idx = self._extract_track(text_lower, context)
        device_idx = self._extract_device(text_lower, track_idx)
        param_idx = self._extract_parameter(text_lower, device_idx)
        param_name = self._extract_parameter_name(text_lower)
        value = self._extract_value(text_lower)
        verb = self._extract_verb(text_lower)
        tempo = self._extract_number(text_lower, ["tempo", "bpm", "beats per minute"])
        key = self._extract_key(text_lower)
        scene_idx = self._extract_scene(text_lower)

        # Build command based on verb and entities
        matched_phrases = []

        if "clip" in text_lower or "loop" in text_lower or "audio" in text_lower:
            if verb in ["fire", "launch", "trigger"]:
                if track_idx is not None:
                    matched_phrases.append("fire")
                    return ParsedCommand(
                        tool_name="fire_clip",
                        arguments={"track_index": track_idx, "clip_index": 0},
                        confidence=0.9,
                        matched_phrases=matched_phrases,
                    )

            elif verb in ["stop", "kill"]:
                if track_idx is not None:
                    matched_phrases.append("stop clips")
                    return ParsedCommand(
                        tool_name="stop_clip",
                        arguments={"track_index": track_idx},
                        confidence=0.85,
                        matched_phrases=matched_phrases,
                    )

        elif "reverb" in text_lower or "send" in text_lower:
            if verb in ["add", "insert", "place"]:
                if track_idx is not None or device_idx is not None:
                    matched_phrases.append("add reverb")
                    return ParsedCommand(
                        tool_name="load_audio_effect",
                        arguments={
                            "track_index": track_idx if track_idx is not None else 0,
                            "device_name": "Reverb"
                        },
                        confidence=0.8,
                        matched_phrases=matched_phrases,
                    )

        elif "eq" in text_lower or "filter" in text_lower or "tone" in text_lower:
            if param_name:
                matched_phrases.append("set parameter")
                return ParsedCommand(
                    tool_name="set_device_parameter",
                    arguments={
                        "track_index": track_idx if track_idx is not None else 0,
                        "device_index": device_idx if device_idx is not None else 0,
                        "parameter_index": param_idx if param_idx is not None else 0,
                        "value": value if value is not None else 0.5
                    },
                    confidence=0.75,
                    matched_phrases=matched_phrases,
                )

        elif "tempo" in text_lower or "bpm" in text_lower:
            if tempo is not None:
                matched_phrases.append("set tempo")
                return ParsedCommand(
                    tool_name="set_tempo",
                    arguments={"tempo": tempo},
                    confidence=0.9,
                    matched_phrases=matched_phrases,
                )

        elif "key" in text_lower or "tonic" in text_lower:
            if key:
                matched_phrases.append("set key")
                return ParsedCommand(
                    tool_name="set_key",
                    arguments={"key": key},
                    confidence=0.85,
                    matched_phrases=matched_phrases,
                )

        elif "scene" in text_lower:
            if scene_idx is not None:
                matched_phrases.append("create scene")
                return ParsedCommand(
                    tool_name="create_scene",
                    arguments={"index": scene_idx},
                    confidence=0.8,
                    matched_phrases=matched_phrases,
                )

        elif "track" in text_lower or "create" in text_lower:
            if "midi" in text_lower:
                matched_phrases.append("create midi track")
                return ParsedCommand(
                    tool_name="create_midi_track",
                    arguments={"name": "New MIDI Track", "index": -1},
                    confidence=0.7,
                    matched_phrases=matched_phrases,
                )
            elif "audio" in text_lower:
                matched_phrases.append("create audio track")
                return ParsedCommand(
                    tool_name="create_audio_track",
                    arguments={"name": "New Audio Track", "index": -1},
                    confidence=0.7,
                    matched_phrases=matched_phrases,
                )

        # Default: unrecognized command
        return ParsedCommand(
            tool_name="",
            arguments={},
            confidence=0.0,
            matched_phrases=matched_phrases,
        )

    def _extract_track(self, text: str, context: Optional[Dict] = None) -> Optional[int]:
        """Extract track index from text."""
        if context and "tracks" in context:
            for track in context["tracks"]:
                name = track.get("name", "").lower()
                for key, patterns in self.track_patterns.items():
                    if any(p in text for p in patterns):
                        if key.lower() in name or name.startswith(key.lower()[:3]):
                            return track.get("index")

        # Detect position (first = 0, one = 1, two = 2, etc.)
        if "first" in text:
            return 0
        if "one" in text or "1" in text.split():
            return 1

        # Check for numbered track (e.g., "track 3")
        match = re.search(r"track\s+(\d+)", text)
        if match:
            return int(match.group(1)) - 1

        return None

    def _extract_device(self, text: str, track_idx: Optional[int]) -> Optional[int]:
        """Extract device index from text."""
        for dev_idx, (device_name, patterns) in enumerate(self.device_patterns.items()):
            if any(p in text for p in patterns):
                return dev_idx
        return None

    def _extract_parameter(self, text: str, device_idx: Optional[int]) -> Optional[int]:
        """Extract parameter index."""
        for param_idx, (param_name, patterns) in enumerate(self.param_patterns.items()):
            if any(p in text for p in patterns):
                return param_idx
        return None

    def _extract_parameter_name(self, text: str) -> Optional[str]:
        """Extract generic parameter name."""
        return None  # Will be determined by tool

    def _extract_value(self, text: str) -> Optional[float]:
        """Extract numeric value from text."""
        # Extract percentage
        match = re.search(r"(\d+)%", text)
        if match:
            return int(match.group(1)) / 100.0

        # Extract number around context
        match = re.search(r"(\d+\.?\d*)\s*(db|dB|hz|%|level|volume)", text)
        if match:
            val = float(match.group(1))
            unit = match.group(2).lower()
            if unit == "db":
                return max(0, min(1, (val + 24) / 48))  # -24dB to +24dB -> 0-1
            return val

        # Context-based defaults
        if "wet" in text or "reverb" in text:
            return 0.3
        if "dry" in text or "dry" in text:
            return 0.0
        if "on" in text or "enabled" in text:
            return 1.0
        if "off" in text or "disabled" in text:
            return 0.0

        return None

    def _extract_verb(self, text: str) -> str:
        """Extract command verb."""
        for verb, patterns in self.verbs.items():
            if any(p in text for p in patterns):
                return verb
        return "set"

    def _extract_number(self, text: str, keywords: List[str]) -> Optional[int]:
        """Extract a number with context keywords."""
        for keyword in keywords:
            if keyword in text:
                # Look for number after keyword
                match = re.search(rf"{keyword}.*?(\d+)", text)
                if match:
                    return int(match.group(1))
                match = re.search(r"(\d+).*{keyword}", text)
                if match:
                    return int(match.group(1))
        return None

    def _extract_key(self, text: str) -> Optional[str]:
        """Extract musical key."""
        keys = ["c", "c#", "db", "d", "d#", "eb", "e", "f", "f#", "gb", "g", "g#", "ab", "a", "a#", "bb", "b"]
        for key in keys:
            if f" {key}" in text or f"{key} major" in text or f"{key} minor" in text:
                return key.capitalize()
        return "C"

    def _extract_scene(self, text: str) -> Optional[int]:
        """Extract scene index."""
        match = re.search(r"scene\s*(\d+)", text)
        if match:
            return int(match.group(1))
        match = re.search(r"(\d+)", text.replace("scene", ""))
        if match:
            return int(match.group(1))
        return 0


# Convenience function
def parse_command(text: str, context: Optional[Dict] = None) -> ParsedCommand:
    """Quick command parsing."""
    processor = NaturalLanguageProcessor()
    return processor.parse(text, context)


if __name__ == "__main__":
    processor = NaturalLanguageProcessor()

    test_commands = [
        "Add reverb to vocal track",
        "Set tempo to 128 bpm",
        "Fire clip 5 on track 3",
        "Sidechain kick to bass",
        "Create new midi track",
        "Drop reverb on snare",
        "Stop all clips",
        "Record into track 1",
        "Set volume to 80%",
        "What's the tempo?",
    ]

    print("Natural Language Command Parsing Demo")
    print("=" * 50)

    for cmd in test_commands:
        result = processor.parse(cmd)
        print(f"\nInput: {cmd}")
        print(f"Tool: {result.tool_name}")
        print(f"Args: {result.arguments}")
        print(f"Confidence: {result.confidence:.0%}")
        print(f"Matched: {', '.join(result.matched_phrases) or 'none'}")