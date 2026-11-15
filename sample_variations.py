#!/usr/bin/env python3
"""
Sample Variations Module
Generates creative variations of audio samples: rhythmic, melodic, timbral.
Competitor parity: Splice Variations, Serato Sample, Output Portal.
Preserves groove/key/tempo using librosa analysis + numpy DSP.
"""

from __future__ import annotations

import os
import json
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

try:
    import numpy as np
except ImportError:
    np = None

try:
    import librosa
    import librosa.effects
    import soundfile as sf
except ImportError:
    librosa = None
    sf = None

VARIATION_TYPES = [
    "reverse",       # reversed sample
    "chop_8",        # 8 chops, reordered
    "chop_16",       # 16 chops, reordered
    "stutter",       # rhythmic stutter gate
    "half_speed",    # time-stretched to half tempo
    "double_speed",  # compressed to double tempo
    "pitch_up_2",    # +2 semitones
    "pitch_down_3",  # -3 semitones
    "filter_sweep",  # lowpass sweep down
    "tape_wobble",   # wow/flutter pitch drift
    "gated",         # rhythmic gate (trance gate)
    "screwed",       # pitched down + slowed (chopped n screwed)
    "reverb_tail",   # inverted reverb-style tail from reversal
    "bitcrush",      # lo-fi bit reduction
    "octave_drop",   # one octave down
]


@dataclass
class Variation:
    """A single generated variation."""
    name: str
    type: str
    path: str
    duration_sec: float
    params: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "path": self.path,
            "duration_sec": round(self.duration_sec, 3),
            "params": self.params,
        }


@dataclass
class VariationSet:
    """All variations generated from one source sample."""
    source_path: str
    tempo: Optional[float]
    estimated_key: Optional[str]
    variations: List[Variation]

    def to_dict(self) -> dict:
        return {
            "source": self.source_path,
            "tempo": self.tempo,
            "key": self.estimated_key,
            "variations": [v.to_dict() for v in self.variations],
            "count": len(self.variations),
        }


class SampleVariationEngine:
    """Generates DSP-based variations that preserve groove and key."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.join(os.getcwd(), "variations")
        os.makedirs(self.output_dir, exist_ok=True)
        self._rng = random.Random()

    def analyze_source(self, path: str) -> Dict:
        """Detect tempo and key of the source sample."""
        if librosa is None:
            return {"error": "librosa not installed"}
        y, sr = librosa.load(path, sr=None, mono=True)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
        pitch_classes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        key = pitch_classes[int(np.argmax(chroma))]
        return {
            "duration_sec": round(len(y) / sr, 3),
            "sample_rate": sr,
            "tempo": round(float(tempo), 1),
            "estimated_key": key,
            "rms": round(float(np.sqrt(np.mean(y ** 2))), 4),
        }

    def generate_variations(
        self,
        source_path: str,
        count: int = 6,
        types: Optional[List[str]] = None,
        seed: Optional[int] = None,
    ) -> VariationSet:
        """Generate `count` variations from one source sample."""
        if librosa is None or np is None:
            raise RuntimeError("librosa and numpy required for variation generation")

        if seed is not None:
            self._rng = random.Random(seed)

        y, sr = librosa.load(source_path, sr=None, mono=True)
        info = self.analyze_source(source_path)

        chosen = types or self._rng.sample(VARIATION_TYPES, min(count, len(VARIATION_TYPES)))
        variations: List[Variation] = []
        base = os.path.splitext(os.path.basename(source_path))[0]

        for i, vtype in enumerate(chosen[:count]):
            try:
                vy, params = self._apply_variation(y, sr, vtype)
                out_name = f"{base}_var{i+1:02d}_{vtype}.wav"
                out_path = os.path.join(self.output_dir, out_name)
                sf.write(out_path, vy, sr)
                variations.append(Variation(
                    name=out_name, type=vtype, path=out_path,
                    duration_sec=len(vy) / sr, params=params,
                ))
            except Exception as e:
                variations.append(Variation(
                    name=f"failed_{vtype}", type=vtype, path="", duration_sec=0.0,
                    params={"error": str(e)},
                ))

        return VariationSet(source_path, info.get("tempo"), info.get("estimated_key"), variations)

    # ---------- variation DSP ----------

    def _apply_variation(self, y: "np.ndarray", sr: int, vtype: str) -> Tuple["np.ndarray", Dict]:
        if vtype == "reverse":
            return y[::-1].copy(), {}

        if vtype in ("chop_8", "chop_16"):
            n = 8 if vtype == "chop_8" else 16
            chops = np.array_split(y, n)
            order = list(range(n))
            self._rng.shuffle(order)
            # keep first chop first for musicality
            order[0] = 0
            out = np.concatenate([chops[i] for i in order])
            return out, {"chop_order": order}

        if vtype == "stutter":
            # repeat short segments rhythmically
            seg = len(y) // 16
            pattern = [1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1]
            parts = []
            for i, p in enumerate(pattern):
                chunk = y[i * seg:(i + 1) * seg]
                if p and len(chunk):
                    reps = self._rng.choice([1, 1, 2, 2, 3])
                    parts.extend([chunk] * reps)
            return np.concatenate(parts) if parts else y, {"gate_pattern": pattern}

        if vtype == "half_speed":
            return librosa.effects.time_stretch(y, rate=0.5), {"rate": 0.5}

        if vtype == "double_speed":
            return librosa.effects.time_stretch(y, rate=2.0), {"rate": 2.0}

        if vtype.startswith("pitch_"):
            steps = {"pitch_up_2": 2, "pitch_down_3": -3, "octave_drop": -12}[vtype]
            return librosa.effects.pitch_shift(y, sr=sr, n_steps=steps), {"semitones": steps}

        if vtype == "filter_sweep":
            # simple one-pole lowpass sweep via STFT band limit
            out = np.copy(y)
            n_frames = 8
            seg = len(y) // n_frames
            cutoffs = np.linspace(8000, 400, n_frames)
            for i in range(n_frames):
                lo, hi = i * seg, (i + 1) * seg
                out[lo:hi] = self._lowpass(y[lo:hi], sr, cutoffs[i])
            return out, {"cutoff_start_hz": 8000, "cutoff_end_hz": 400}

        if vtype == "tape_wobble":
            t = np.arange(len(y)) / sr
            drift = np.sin(2 * np.pi * 0.7 * t) * 0.0015 + np.sin(2 * np.pi * 4.1 * t) * 0.0004
            idx = np.clip(np.arange(len(y)) + drift * sr, 0, len(y) - 1).astype(int)
            return y[idx], {"wow_hz": 0.7, "flutter_hz": 4.1}

        if vtype == "gated":
            bpm = 120.0
            gate_len = int(sr * 60.0 / bpm / 4)  # 16th
            out = np.zeros_like(y)
            for i in range(0, len(y) - gate_len, gate_len * 2):
                out[i:i + gate_len] = y[i:i + gate_len]
            return out, {"gate_division": "1/16"}

        if vtype == "screwed":
            slow = librosa.effects.time_stretch(y, rate=0.76)
            pitched = librosa.effects.pitch_shift(slow, sr=sr, n_steps=-3)
            return pitched, {"rate": 0.76, "semitones": -3}

        if vtype == "reverb_tail":
            rev = y[::-1].copy()
            decay = np.exp(-np.linspace(0, 6, len(rev)))
            return rev * decay, {"decay_exp": 6.0}

        if vtype == "bitcrush":
            levels = 32
            quantized = np.round(y * levels) / levels
            return quantized.astype(y.dtype), {"bit_depth": 5}

        raise ValueError(f"unknown variation type: {vtype}")

    @staticmethod
    def _lowpass(y: "np.ndarray", sr: int, cutoff_hz: float) -> "np.ndarray":
        """Cheap FFT lowpass."""
        if len(y) < 4:
            return y
        spec = np.fft.rfft(y)
        freqs = np.fft.rfftfreq(len(y), 1 / sr)
        spec[freqs > cutoff_hz] = 0
        return np.fft.irfft(spec, len(y))

    def create_fill(self, source_path: str, target_bars: int = 1, beats_per_bar: int = 4) -> Variation:
        """Build a drum fill from a sample: chops get denser toward the end."""
        y, sr = librosa.load(source_path, sr=None, mono=True)
        target_len = int(sr * 60 / 120 * beats_per_bar * target_bars)  # at 120bpm
        n = 16
        chops = np.array_split(y, n)
        # density ramp: later chops repeat more
        parts = []
        for i in range(n):
            reps = 1 + int(3 * (i / n) ** 2)
            parts.extend([chops[i % n]] * reps)
        out = np.concatenate(parts)[:target_len]
        if len(out) < target_len:
            out = np.pad(out, (0, target_len - len(out)))
        out_name = os.path.splitext(os.path.basename(source_path))[0] + "_fill.wav"
        out_path = os.path.join(self.output_dir, out_name)
        sf.write(out_path, out, sr)
        return Variation(out_name, "fill", out_path, len(out) / sr, {"bars": target_bars})

    def extend_loop(self, source_path: str, target_bars: int = 8, beats_per_bar: int = 4) -> Variation:
        """Seamlessly loop-extend a sample to N bars with varied repeats."""
        y, sr = librosa.load(source_path, sr=None, mono=True)
        info = self.analyze_source(source_path)
        bpm = info.get("tempo") or 120.0
        loop_len = int(sr * 60 / bpm * beats_per_bar)
        reps_needed = max(1, int(np.ceil(len(y) / max(1, loop_len))))
        target_reps = target_bars
        parts = []
        for r in range(target_reps):
            seg = y[(r % reps_needed) * 0 + 0:]  # full source each time
            if r % 4 == 3:
                seg = seg[::-1]  # every 4th repeat reversed for interest
            parts.append(seg)
        out = np.concatenate(parts)
        out_name = os.path.splitext(os.path.basename(source_path))[0] + f"_ext{target_bars}bars.wav"
        out_path = os.path.join(self.output_dir, out_name)
        sf.write(out_path, out, sr)
        return Variation(out_name, "loop_extend", out_path, len(out) / sr,
                         {"bars": target_bars, "bpm": round(bpm, 1)})


def generate_variations(source_path: str, count: int = 6, types: Optional[List[str]] = None) -> Dict:
    """Quick variation generation."""
    engine = SampleVariationEngine()
    return engine.generate_variations(source_path, count, types).to_dict()


def list_variation_types() -> List[str]:
    return VARIATION_TYPES


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python sample_variations.py <sample.wav> [count]")
        print(f"Types: {', '.join(VARIATION_TYPES)}")
        sys.exit(1)
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    engine = SampleVariationEngine()
    info = engine.analyze_source(sys.argv[1])
    print(f"Source: {info}")
    result = engine.generate_variations(sys.argv[1], count)
    for v in result.variations:
        print(f"  {v.name:40s} {v.duration_sec:.2f}s {v.params}")