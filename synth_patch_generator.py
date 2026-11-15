#!/usr/bin/env python3
"""
Synth Patch Generator Module
Audio → synthesizer parameters via spectral analysis.
Exports preset JSON for Ableton Operator / Analog / third-party synths.
Competitor parity: Synplant 2 Genopatch.
"""

from __future__ import annotations

import json
import math
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

try:
    import numpy as np
except ImportError:
    np = None

try:
    import librosa
except ImportError:
    librosa = None


@dataclass
class SynthPatch:
    """Serialized synth patch."""
    name: str
    synth_type: str  # operator, analog, generic
    oscillator: Dict
    filter: Dict
    envelope: Dict
    lfo: Dict
    effects: Dict
    source_audio: str
    match_score: float

    def to_dict(self) -> dict:
        return {
            "name": self.name, "synth_type": self.synth_type,
            "oscillator": self.oscillator, "filter": self.filter,
            "envelope": self.envelope, "lfo": self.lfo, "effects": self.effects,
            "source_audio": self.source_audio, "match_score": round(self.match_score, 3),
        }

    def export_ableton_operator(self) -> Dict:
        """Map to Ableton Operator-style parameters."""
        osc = self.oscillator
        env = self.envelope
        return {
            "osc_wave": osc.get("wave", 0),
            "osc_coarse": osc.get("coarse", 0),
            "osc_fine": osc.get("fine", 0),
            "filter_freq": self.filter.get("cutoff", 1000),
            "filter_res": self.filter.get("resonance", 0),
            "env_attack": env.get("attack", 0.1),
            "env_decay": env.get("decay", 0.3),
            "env_sustain": env.get("sustain", 0.7),
            "env_release": env.get("release", 0.4),
            "lfo_rate": self.lfo.get("rate", 1.0),
            "lfo_depth": self.lfo.get("depth", 0.1),
        }

    def export_generic(self) -> Dict:
        return self.to_dict()


class SynthPatchGenerator:
    """Reverse-engineer synth settings from an audio sample."""

    WAVEFORMS = ["sine", "triangle", "sawtooth", "square"]

    def __init__(self):
        pass

    def analyze_target(self, path: str) -> Dict:
        """Extract spectral envelope, pitch, envelope shape from audio."""
        if librosa is None:
            return {
                "pitch_hz": 220.0, "brightness": 0.5,
                "attack_ms": 100, "decay_ms": 300, "sustain": 0.7, "release_ms": 400,
                "has_vibrato": False, "noise": 0.1,
            }
        y, sr = librosa.load(path, sr=None, mono=True, duration=10)
        # fundamental pitch via autocorrelation (librosa pyin)
        f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=50, fmax=2000, sr=sr)
        f0_clean = [f for f, v in zip(f0, voiced_flag) if v]
        pitch_hz = float(np.median(f0_clean)) if f0_clean else 220.0

        # brightness = spectral centroid relative to nyquist
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0]))
        brightness = min(1.0, centroid / (sr / 2))

        # envelope from RMS
        rms = librosa.feature.rms(y=y)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr)
        max_rms = float(np.max(rms)) + 1e-10
        attack_idx = int(np.argmax(rms >= max_rms * 0.9))
        # decay: time to drop to 50% of peak after attack
        half = max_rms * 0.5
        decay_idx = len(rms) - 1
        for i in range(attack_idx, len(rms)):
            if rms[i] <= half:
                decay_idx = i
                break
        attack_s = times[attack_idx] if attack_idx < len(times) else 0.05
        decay_s = times[decay_idx] - attack_s if decay_idx > attack_idx else 0.3
        sustain = float(np.percentile(rms[decay_idx:], 50)) / max_rms if decay_idx < len(rms) else 0.7

        # noise ratio (high-freq content / total)
        spec = np.abs(np.fft.rfft(y))
        freqs = np.fft.rfftfreq(len(y), 1 / sr)
        noise_band = (freqs > 4000)
        noise_ratio = float(np.sum(spec[noise_band]) / (np.sum(spec) + 1e-10))

        return {
            "pitch_hz": round(pitch_hz, 2),
            "brightness": round(brightness, 3),
            "attack_ms": round(attack_s * 1000, 1),
            "decay_ms": round(decay_s * 1000, 1),
            "sustain": round(sustain, 3),
            "release_ms": 400.0,
            "has_vibrato": False,
            "noise": round(noise_ratio, 3),
        }

    def generate_patch(self, audio_path: str, synth_type: str = "operator",
                       name: Optional[str] = None) -> SynthPatch:
        """Create a synth patch approximating the audio source."""
        target = self.analyze_target(audio_path)
        base = os.path.splitext(os.path.basename(audio_path))[0]
        patch_name = name or f"{base}_patch"

        pitch_hz = target["pitch_hz"]
        # midi note from pitch
        midi = 69 + 12 * math.log2(pitch_hz / 440.0) if pitch_hz > 0 else 69
        coarse = int(round(midi)) - 69  # semitone offset from A4
        fine = (midi - round(midi)) * 100  # cents

        # waveform from brightness
        brightness = target["brightness"]
        if brightness < 0.25:
            wave = "sine"
        elif brightness < 0.45:
            wave = "triangle"
        elif brightness < 0.65:
            wave = "sawtooth"
        else:
            wave = "square"

        # filter cutoff from brightness
        cutoff = 400 + brightness * 7600  # 400Hz .. 8kHz
        resonance = 0.2 + (1.0 - brightness) * 0.4  # duller = more resonance emphasis

        # envelope
        env = {
            "attack": max(0.01, target["attack_ms"] / 1000),
            "decay": max(0.05, target["decay_ms"] / 1000),
            "sustain": target["sustain"],
            "release": target["release_ms"] / 1000,
        }

        # lfo: slight vibrato if noise/pitch suggests
        lfo = {"rate": 5.0, "depth": 0.05 if target["has_vibrato"] else 0.0}

        # effects
        fx = {"reverb": min(1.0, target["noise"] * 2), "delay": 0.0, "drive": 0.2 if wave == "square" else 0.0}

        match_score = 0.7 + min(0.3, brightness * 0.3)  # rough heuristic

        return SynthPatch(
            name=patch_name, synth_type=synth_type,
            oscillator={"wave": wave, "coarse": coarse, "fine": fine, "detune": 0.0},
            filter={"type": "lowpass", "cutoff": round(cutoff, 1), "resonance": round(resonance, 2)},
            envelope=env, lfo=lfo, effects=fx,
            source_audio=audio_path, match_score=match_score,
        )

    def render_preview(self, patch: SynthPatch, duration_sec: float = 2.0,
                       sr: int = 44100) -> "np.ndarray":
        """Additive synth preview of the patch (for A/B listening)."""
        if np is None:
            raise RuntimeError("numpy required for preview rendering")
        t = np.arange(int(duration_sec * sr)) / sr
        freq = 440.0 * (2 ** (patch.oscillator["coarse"] / 12.0)) * (1 + patch.oscillator["fine"] / 1200.0)
        wave = patch.oscillator["wave"]

        if wave == "sine":
            sig = np.sin(2 * np.pi * freq * t)
        elif wave == "triangle":
            sig = 2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1
        elif wave == "sawtooth":
            sig = 2 * (t * freq - np.floor(t * freq + 0.5))
        else:  # square
            sig = np.sign(np.sin(2 * np.pi * freq * t))

        # envelope
        env = patch.envelope
        a = int(env["attack"] * sr)
        d = int(env["decay"] * sr)
        s = env["sustain"]
        r = int(env["release"] * sr)
        env_shape = np.ones_like(t)
        env_shape[:a] = np.linspace(0, 1, a)
        if a + d < len(t):
            env_shape[a:a + d] = np.linspace(1, s, d)
        env_shape[a + d:] = s
        r_start = len(t) - r
        if r_start > a + d:
            env_shape[r_start:] = np.linspace(s, 0, r)

        sig = sig * env_shape

        # simple lowpass via one-pole
        fc = patch.filter["cutoff"]
        rc = 1.0 / (2 * np.pi * fc)
        dt = 1.0 / sr
        alpha = dt / (rc + dt)
        out = np.zeros_like(sig)
        out[0] = sig[0]
        for i in range(1, len(sig)):
            out[i] = out[i - 1] + alpha * (sig[i] - out[i - 1])

        # normalize
        peak = np.max(np.abs(out)) + 1e-10
        return (out / peak * 0.7).astype(np.float32)

    def export_preset(self, patch: SynthPatch, path: str, fmt: str = "json") -> str:
        """Save patch as JSON (generic) or Ableton Operator preset dict."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        data = patch.export_ableton_operator() if fmt == "ableton" else patch.to_dict()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path


def audio_to_synth_patch(audio_path: str, synth_type: str = "operator") -> Dict:
    """Quick patch generation."""
    gen = SynthPatchGenerator()
    return gen.generate_patch(audio_path, synth_type).to_dict()


def list_synth_types() -> List[str]:
    return ["operator", "analog", "generic"]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python synth_patch_generator.py <audio.wav>")
        sys.exit(1)
    gen = SynthPatchGenerator()
    info = gen.analyze_target(sys.argv[1])
    print(f"Analysis: {info}")
    patch = gen.generate_patch(sys.argv[1])
    print(f"Patch: {patch.name} wave={patch.oscillator['wave']} cutoff={patch.filter['cutoff']}Hz")
    print(f"Operator map: {patch.export_ableton_operator()}")