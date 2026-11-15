#!/usr/bin/env python3
"""
MIDI Humanization Module
Adds human feel to MIDI: velocity curves, timing variation, groove templates.
Competitor parity: Splice Create, Logic humanize, MPC groove templates.
"""

from __future__ import annotations

import json
import math
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    import numpy as np
except ImportError:
    np = None


# Note format: {"pitch": int, "start_time": float (beats), "duration": float (beats), "velocity": int 0-127}

VELOCITY_CURVES = {
    "linear": lambda x: x,
    "exponential": lambda x: x ** 2,
    "logarithmic": lambda x: math.sqrt(x),
    "s_curve": lambda x: 0.5 - 0.5 * math.cos(math.pi * x),
    "accent_first": lambda x: 1.0 if x < 0.2 else 0.6 + 0.4 * x,
    "human": lambda x: 0.7 + 0.3 * x + random.uniform(-0.08, 0.08),
}

GROOVES = {
    "straight": {"swing": 0.0, "shuffle_8": 0.0, "shuffle_16": 0.0},
    "mpc_54": {"swing": 0.54, "shuffle_16": 0.54},        # classic MPC 54%
    "mpc_58": {"swing": 0.58, "shuffle_16": 0.58},
    "mpc_62": {"swing": 0.62, "shuffle_16": 0.62},        # heavy hip-hop
    "shuffle": {"swing": 0.66, "shuffle_8": 0.66},        # jazz shuffle
    "laid_back": {"push": -0.04},                          # behind the beat
    "pushed": {"push": 0.03},                              # ahead of the beat
    "house": {"swing": 0.56, "push": 0.01},
    "dnb": {"push": 0.02, "ghost_accent": True},
    "latin": {"swing": 0.60, "shuffle_16": 0.60},
}

STYLES = {
    "robot": {"timing_var": 0.0, "vel_var": 0.0, "curve": "linear", "push": 0.0},
    "tight": {"timing_var": 0.005, "vel_var": 3, "curve": "linear", "push": 0.0},
    "human": {"timing_var": 0.015, "vel_var": 8, "curve": "human", "push": -0.008},
    "loose": {"timing_var": 0.035, "vel_var": 14, "curve": "human", "push": -0.02},
    "drunk": {"timing_var": 0.06, "vel_var": 22, "curve": "logarithmic", "push": -0.04},
    "gentle": {"timing_var": 0.008, "vel_var": 5, "curve": "s_curve", "push": 0.0},
}


@dataclass
class HumanizeResult:
    """Result of humanization."""
    original_notes: List[Dict]
    humanized_notes: List[Dict]
    style: str
    changes_made: int
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "style": self.style,
            "changes_made": self.changes_made,
            "stats": self.stats,
            "humanized_notes": self.humanized_notes,
        }


class MidiHumanizer:
    """Applies human-like variations to MIDI notes."""

    def humanize_notes(
        self,
        notes: List[Dict],
        style: str = "human",
        amount: float = 1.0,
        seed: Optional[int] = None,
    ) -> HumanizeResult:
        """Humanize a list of MIDI notes.

        amount: 0.0 (no change) to 1.0 (full style strength).
        """
        if seed is not None:
            random.seed(seed)

        if style not in STYLES:
            raise ValueError(f"Unknown style: {style}. Available: {list(STYLES.keys())}")

        cfg = STYLES[style]
        result = []

        for note in notes:
            n = dict(note)

            # Timing variation (in beats)
            timing_var = cfg["timing_var"] * amount * random.gauss(0, 1)
            n["start_time"] = max(0.0, note["start_time"] + timing_var + cfg["push"] * amount)

            # Velocity variation
            vel_var = cfg["vel_var"] * amount * random.gauss(0, 1)
            curve = VELOCITY_CURVES[cfg["curve"]]
            v = note["velocity"] / 127.0
            v_curved = curve(max(0.0, min(1.0, v)))
            n["velocity"] = int(max(1, min(127, 127 * v_curved + vel_var)))

            # Slight duration variation (legato feel)
            dur_var = cfg["timing_var"] * 0.5 * amount * random.gauss(0, 1)
            n["duration"] = max(0.02, note["duration"] + dur_var)

            result.append(n)

        changes = sum(
            1 for a, b in zip(notes, result)
            if abs(a["start_time"] - b["start_time"]) > 1e-4
            or a["velocity"] != b["velocity"]
        )

        stats = {
            "note_count": len(notes),
            "avg_velocity_before": round(sum(n["velocity"] for n in notes) / max(1, len(notes)), 1),
            "avg_velocity_after": round(sum(n["velocity"] for n in result) / max(1, len(result)), 1),
            "avg_timing_shift_beats": round(
                sum(abs(b["start_time"] - a["start_time"]) for a, b in zip(notes, result)) / max(1, len(notes)), 4
            ),
        }

        return HumanizeResult(notes, result, style, changes, stats)

    def apply_groove(
        self,
        notes: List[Dict],
        groove: str = "mpc_54",
        amount: float = 1.0,
    ) -> HumanizeResult:
        """Apply a groove template (swing, push) to notes."""
        if groove not in GROOVES:
            raise ValueError(f"Unknown groove: {groove}. Available: {list(GROOVES.keys())}")

        g = GROOVES[groove]
        result = []
        swing = g.get("swing", 0.0) * amount
        push = g.get("push", 0.0) * amount
        shuffle_16 = g.get("shuffle_16", 0.0) * amount

        for note in notes:
            n = dict(note)
            start = note["start_time"]

            # 8th-note shuffle: offbeat 8ths delayed
            pos_in_8th = (start % 0.5) / 0.5  # 0..1 within 8th
            if shuffle_8_swing := g.get("shuffle_8", 0.0):
                if 0.9 < pos_in_8th or abs(pos_in_8th) < 0.1:
                    if (start / 0.5) % 2 >= 1:  # offbeat 8th
                        start += (shuffle_8_swing - 0.5) * 0.5 * 2 * 0.5

            # 16th-note swing: offbeat 16ths delayed
            pos_in_16th = (start % 0.25) / 0.25
            if abs(pos_in_16th - 0.5) < 0.01 and shuffle_16 > 0:
                # offbeat 16th: delay from 50% position to swing amount
                start += (shuffle_16 - 0.5) * 0.25

            # Global push/pull
            start += push

            n["start_time"] = max(0.0, start)
            result.append(n)

        shifts = [abs(b["start_time"] - a["start_time"]) for a, b in zip(notes, result)]
        stats = {
            "note_count": len(notes),
            "groove": groove,
            "notes_shifted": sum(1 for s in shifts if s > 1e-4),
            "max_shift_beats": round(max(shifts), 4) if shifts else 0.0,
        }
        return HumanizeResult(notes, result, groove, stats["notes_shifted"], stats)

    def apply_velocity_curve(
        self,
        notes: List[Dict],
        curve: str = "exponential",
        intensity: float = 1.0,
    ) -> List[Dict]:
        """Reshape velocities with a curve (accent shaping)."""
        if curve not in VELOCITY_CURVES:
            raise ValueError(f"Unknown curve: {curve}")
        fn = VELOCITY_CURVES[curve]
        result = []
        for note in notes:
            n = dict(note)
            v = note["velocity"] / 127.0
            shaped = fn(max(0.0, min(1.0, v)))
            blended = v + (shaped - v) * intensity
            n["velocity"] = int(max(1, min(127, 127 * blended)))
            result.append(n)
        return result

    def add_ghost_notes(
        self,
        notes: List[Dict],
        density: float = 0.15,
        pitch_options: Optional[List[int]] = None,
        velocity_range: tuple = (15, 35),
    ) -> List[Dict]:
        """Add quiet ghost notes between existing hits (drum fills feel)."""
        pitches = pitch_options or [n["pitch"] for n in notes]
        result = list(notes)
        starts = sorted(set(n["start_time"] for n in notes))
        for i in range(len(starts) - 1):
            gap = starts[i + 1] - starts[i]
            if gap > 0.25 and random.random() < density * 2:
                ghost = {
                    "pitch": random.choice(pitches),
                    "start_time": round(starts[i] + gap * random.uniform(0.4, 0.6), 4),
                    "duration": min(0.1, gap * 0.3),
                    "velocity": random.randint(*velocity_range),
                }
                result.append(ghost)
        result.sort(key=lambda n: n["start_time"])
        return result

    def extract_groove(self, notes: List[Dict]) -> Dict[str, Any]:
        """Reverse-engineer timing feel from played notes (for groove capture)."""
        if not notes:
            return {"error": "no notes"}
        offsets = []
        for n in notes:
            grid = round(n["start_time"] * 4) / 4  # nearest 16th
            offsets.append(round(n["start_time"] - grid, 4))
        avg_offset = sum(offsets) / len(offsets)
        vel_velocities = [n["velocity"] for n in notes]
        return {
            "avg_timing_offset_beats": round(avg_offset, 4),
            "feel": "laid_back" if avg_offset < -0.01 else ("pushed" if avg_offset > 0.01 else "centered"),
            "velocity_range": [min(vel_velocities), max(vel_velocities)],
            "velocity_std": round(
                (sum((v - sum(vel_velocities) / len(vel_velocities)) ** 2 for v in vel_velocities) / len(vel_velocities)) ** 0.5, 1
            ),
            "suggested_groove": "laid_back" if avg_offset < -0.01 else ("pushed" if avg_offset > 0.01 else "straight"),
        }


def humanize_midi(notes: List[Dict], style: str = "human", amount: float = 1.0) -> Dict:
    """Quick humanize."""
    return MidiHumanizer().humanize_notes(notes, style, amount).to_dict()


def apply_groove_template(notes: List[Dict], groove: str = "mpc_54") -> Dict:
    """Quick groove apply."""
    return MidiHumanizer().apply_groove(notes, groove).to_dict()


def list_styles() -> List[str]:
    return list(STYLES.keys())


def list_grooves() -> List[str]:
    return list(GROOVES.keys())


if __name__ == "__main__":
    notes = [
        {"pitch": 36, "start_time": 0.0, "duration": 0.25, "velocity": 100},
        {"pitch": 36, "start_time": 0.5, "duration": 0.25, "velocity": 100},
        {"pitch": 36, "start_time": 1.0, "duration": 0.25, "velocity": 100},
        {"pitch": 36, "start_time": 1.5, "duration": 0.25, "velocity": 100},
    ]
    h = MidiHumanizer()
    res = h.humanize_notes(notes, "human", 1.0)
    print(f"Humanized {res.changes_made}/{len(notes)} notes")
    for n in res.humanized_notes[:2]:
        print(f"  pitch={n['pitch']} t={n['start_time']:.3f} v={n['velocity']}")
    res2 = h.apply_groove(notes, "mpc_58")
    print(f"Groove shifted {res2.changes_made}/{len(notes)} notes")
    print(f"Extracted: {h.extract_groove(res2.humanized_notes)}")