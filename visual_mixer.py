#!/usr/bin/env python3
"""
Visual Mixer Module
2D mix-map analysis + cross-track collision detection.
Competitor parity: Neutron Visual Mixer, Ozone Masking Meter.
Output: positions for a visual dashboard (x=frequency centroid, y=level, size=dynamics).
"""

from __future__ import annotations

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
class TrackAnalysis:
    """Analysis of one track for mix placement."""
    name: str
    path: str
    duration_sec: float
    freq_centroid_hz: float       # where it sits in frequency spectrum
    peak_level_db: float          # loudest point
    rms_db: float                 # average loudness
    dynamic_range_db: float       # peak - rms
    stereo_width: float           # 0 mono .. 1 stereo
    pan_position: float           # -1 left .. 1 right
    spectral_band: str            # sub/bass/low-mid/mid/high-mid/high/air

    def to_dict(self) -> dict:
        return {
            "name": self.name, "path": self.path,
            "freq_centroid_hz": round(self.freq_centroid_hz, 1),
            "peak_level_db": round(self.peak_level_db, 1),
            "rms_db": round(self.rms_db, 1),
            "dynamic_range_db": round(self.dynamic_range_db, 1),
            "stereo_width": round(self.stereo_width, 2),
            "pan_position": round(self.pan_position, 2),
            "spectral_band": self.spectral_band,
            "mix_map": {"x": round(self.freq_centroid_hz, 1),
                        "y": round(self.rms_db, 1),
                        "size": round(self.dynamic_range_db, 1)},
        }


@dataclass
class Collision:
    """Frequency collision between two tracks."""
    track_a: str
    track_b: str
    overlap_hz: float            # centroid where they collide
    severity: str                # low/medium/high
    suggestion: str

    def to_dict(self) -> dict:
        return {
            "track_a": self.track_a, "track_b": self.track_b,
            "overlap_hz": round(self.overlap_hz, 1),
            "severity": self.severity, "suggestion": self.suggestion,
        }


@dataclass
class MixAnalysis:
    """Full mix overview."""
    tracks: List[TrackAnalysis]
    collisions: List[Collision]
    recommendations: List[str]

    def to_dict(self) -> dict:
        return {
            "tracks": [t.to_dict() for t in self.tracks],
            "collisions": [c.to_dict() for c in self.collisions],
            "recommendations": self.recommendations,
        }


class VisualMixer:
    """Analyze tracks and produce visual mix-map data + collision warnings."""

    BANDS = [
        ("sub", 20, 60), ("bass", 60, 250), ("low_mid", 250, 500),
        ("mid", 500, 2000), ("high_mid", 2000, 4000), ("high", 4000, 8000), ("air", 8000, 16000),
    ]

    def analyze_track(self, path: str, name: Optional[str] = None) -> TrackAnalysis:
        """Analyze one audio file."""
        if librosa is None:
            return TrackAnalysis(
                name=name or os.path.basename(path), path=path,
                duration_sec=0, freq_centroid_hz=1000, peak_level_db=0,
                rms_db=-20, dynamic_range_db=20, stereo_width=0, pan_position=0,
                spectral_band="mid",
            )
        y, sr = librosa.load(path, sr=None, mono=True, duration=60)
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0]))
        rms = float(np.sqrt(np.mean(y ** 2))) + 1e-10
        peak = float(np.max(np.abs(y))) + 1e-10
        rms_db = 20 * np.log10(rms)
        peak_db = 20 * np.log10(peak)
        dr = peak_db - rms_db

        # spectral band
        band = "mid"
        for bname, lo, hi in self.BANDS:
            if lo <= centroid < hi:
                band = bname
                break

        # simple stereo proxy (mono load => centered)
        pan = 0.0
        width = 0.0
        name_out = name or os.path.basename(path)

        return TrackAnalysis(name_out, path, round(len(y) / sr, 2), centroid,
                             round(peak_db, 1), round(rms_db, 1), round(dr, 1),
                             width, pan, band)

    def analyze_tracks(self, paths: List[str]) -> List[TrackAnalysis]:
        return [self.analyze_track(p) for p in paths]

    def detect_collisions(self, tracks: List[TrackAnalysis], threshold_hz: float = 1500) -> List[Collision]:
        """Flag tracks whose centroids sit in the same band (potential masking)."""
        collisions = []
        for i in range(len(tracks)):
            for j in range(i + 1, len(tracks)):
                a, b = tracks[i], tracks[j]
                if a.spectral_band == b.spectral_band and abs(a.freq_centroid_hz - b.freq_centroid_hz) < threshold_hz:
                    severity = "high" if abs(a.rms_db - b.rms_db) < 6 else "medium"
                    suggestion = (
                        f"EQ carve: notch {a.name} around {b.freq_centroid_hz:.0f}Hz "
                        f"or pan them apart (L/R)."
                    )
                    collisions.append(Collision(a.name, b.name,
                                                (a.freq_centroid_hz + b.freq_centroid_hz) / 2,
                                                severity, suggestion))
        return collisions

    def suggest_resolutions(self, collisions: List[Collision]) -> List[str]:
        tips = []
        for c in collisions:
            tips.append(f"{c.track_a} vs {c.track_b}: {c.suggestion}")
        general = [
            "Keep sub (<60Hz) in mono — one instrument only (usually kick).",
            "High-pass non-bass instruments below 100Hz to clear mud.",
            "Pan similar-frequency instruments left/right instead of competing center.",
            "Use dynamic EQ or sidechain compression for kick/bass collisions.",
        ]
        return tips + general

    def build_mix_map(self, tracks: List[TrackAnalysis]) -> Dict:
        """Compact JSON for a visual 2D mix dashboard."""
        return {
            "tracks": [
                {"name": t.name, "x": t.freq_centroid_hz, "y": t.rms_db,
                 "size": t.dynamic_range_db, "band": t.spectral_band,
                 "pan": t.pan_position}
                for t in tracks
            ],
            "bands": self.BANDS,
        }


def analyze_tracks(paths: List[str]) -> List[Dict]:
    vm = VisualMixer()
    return [t.to_dict() for t in vm.analyze_tracks(paths)]


def detect_collisions(paths: List[str]) -> List[Dict]:
    vm = VisualMixer()
    tracks = vm.analyze_tracks(paths)
    return [c.to_dict() for c in vm.detect_collisions(tracks)]


def build_mix_map(paths: List[str]) -> Dict:
    vm = VisualMixer()
    tracks = vm.analyze_tracks(paths)
    return vm.build_mix_map(tracks)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python visual_mixer.py <file1.wav> [file2.wav ...]")
        sys.exit(1)
    vm = VisualMixer()
    tracks = vm.analyze_tracks(sys.argv[1:])
    collisions = vm.detect_collisions(tracks)
    print(f"Analyzed {len(tracks)} tracks")
    for t in tracks:
        print(f"  {t.name}: centroid={t.freq_centroid_hz:.0f}Hz rms={t.rms_db:.1f}dB band={t.spectral_band}")
    print(f"Collisions: {len(collisions)}")
    for c in collisions:
        print(f"  {c.track_a} <-> {c.track_b} at {c.overlap_hz:.0f}Hz ({c.severity})")
    print(f"Map: {vm.build_mix_map(tracks)}")