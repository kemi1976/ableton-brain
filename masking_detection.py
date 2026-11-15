#!/usr/bin/env python3
"""
Frequency Masking Detection Module
Analyzes frequency masking between tracks - similar to iZotope Neutron Unmask.
Detects overlapping frequency regions and suggests EQ/panning/level fixes.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any

import numpy as np

warnings.filterwarnings("ignore")

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    librosa = None

try:
    import scipy.signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


# ============================================================
# Data Classes
# ============================================================

@dataclass
class MaskingRegion:
    """A detected frequency masking region between two tracks."""
    freq_low: float        # Lower frequency bound (Hz)
    freq_high: float       # Upper frequency bound (Hz)
    center_freq: float     # Center frequency (Hz)
    track_a_level_db: float    # Track A level in this region
    track_b_level_db: float    # Track B level in this region
    masking_db: float      # How much B masks A (positive = masking)
    severity: str          # "low", "medium", "high", "critical"
    track_a_name: str = "Track A"
    track_b_name: str = "Track B"

    @property
    def bandwidth_hz(self) -> float:
        return self.freq_high - self.freq_low

    @property
    def bandwidth_octaves(self) -> float:
        if self.freq_low <= 0:
            return 0
        return np.log2(self.freq_high / self.freq_low)

    def to_dict(self) -> dict:
        return {
            "freq_low": self.freq_low,
            "freq_high": self.freq_high,
            "center_freq": self.center_freq,
            "track_a_level_db": self.track_a_level_db,
            "track_b_level_db": self.track_b_level_db,
            "masking_db": self.masking_db,
            "severity": self.severity,
            "bandwidth_hz": self.bandwidth_hz,
            "bandwidth_octaves": self.bandwidth_octaves,
            "track_a_name": self.track_a_name,
            "track_b_name": self.track_b_name,
        }


@dataclass
class UnmaskSuggestion:
    """Suggestion to resolve masking."""
    region: MaskingRegion
    action: str            # "cut_a", "cut_b", "pan", "level", "sidechain"
    target_track: str      # "A" or "B"
    frequency: float       # EQ frequency
    gain_db: float         # EQ gain (negative for cut)
    q: float               # EQ Q factor
    pan_change: float = 0.0    # Pan adjustment (-1 to 1)
    level_change_db: float = 0.0  # Level adjustment (dB)
    sidechain_ratio: float = 0.0  # Compression ratio for sidechain
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "region": self.region.to_dict(),
            "action": self.action,
            "target_track": self.target_track,
            "frequency": self.frequency,
            "gain_db": self.gain_db,
            "q": self.q,
            "pan_change": self.pan_change,
            "level_change_db": self.level_change_db,
            "sidechain_ratio": self.sidechain_ratio,
            "description": self.description,
        }


@dataclass
class MaskingAnalysisResult:
    """Complete masking analysis between tracks."""
    track_pairs: List[Tuple[str, str]] = field(default_factory=list)
    masking_regions: List[MaskingRegion] = field(default_factory=list)
    suggestions: List[UnmaskSuggestion] = field(default_factory=list)
    overall_masking_score: float = 0.0  # 0 = clean, 1 = heavily masked
    track_spectra: Dict[str, Dict] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "track_pairs": self.track_pairs,
            "masking_regions": [r.to_dict() for r in self.masking_regions],
            "suggestions": [s.to_dict() for s in self.suggestions],
            "overall_masking_score": self.overall_masking_score,
            "track_spectra": {k: {"freqs": v["freqs"].tolist() if isinstance(v.get("freqs"), np.ndarray) else v.get("freqs", []),
                                  "magnitude_db": v["magnitude_db"].tolist() if isinstance(v.get("magnitude_db"), np.ndarray) else v.get("magnitude_db", [])}
                              for k, v in self.track_spectra.items()},
            "error": self.error,
        }


# ============================================================
# Masking Detector
# ============================================================

class MaskingDetector:
    """
    Detect frequency masking between audio tracks.
    Based on psychoacoustic masking models (Moore-Glasberg, etc.)
    """

    # Critical band rates (ERB scale) - approximate
    CRITICAL_BANDS = [
        (20, 100), (100, 200), (200, 300), (300, 400), (400, 510),
        (510, 630), (630, 770), (770, 920), (920, 1080), (1080, 1270),
        (1270, 1480), (1480, 1720), (1720, 2000), (2000, 2320), (2320, 2700),
        (2700, 3150), (3150, 3700), (3700, 4400), (4400, 5300), (5300, 6400),
        (6400, 7700), (7700, 9500), (9500, 12000), (12000, 15500), (15500, 20000),
    ]

    def __init__(
        self,
        sample_rate: int = 44100,
        fft_size: int = 8192,
        hop_length: int = 2048,
        masking_threshold_db: float = -6.0,  # Masking threshold in dB
        analysis_duration: float = 30.0,     # Seconds to analyze
    ):
        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self.hop_length = hop_length
        self.masking_threshold_db = masking_threshold_db
        self.analysis_duration = analysis_duration

    def analyze_track(self, audio_path: str, track_name: str = "") -> Dict:
        """Analyze single track spectrum."""
        if not LIBROSA_AVAILABLE:
            raise ImportError("librosa required")

        # Load audio (limit duration for speed)
        y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True, duration=self.analysis_duration)

        # STFT
        stft = librosa.stft(y, n_fft=self.fft_size, hop_length=self.hop_length)
        magnitude = np.abs(stft)

        # Average magnitude spectrum
        magnitude_mean = np.mean(magnitude, axis=1)
        magnitude_db = 20 * np.log10(magnitude_mean + 1e-10)

        # Frequency axis
        freqs = librosa.fft_frequencies(sr=sr, n_fft=self.fft_size)

        # Interpolate to critical band centers
        band_centers = [(low + high) / 2 for low, high in self.CRITICAL_BANDS]
        from scipy.interpolate import interp1d
        interp_func = interp1d(freqs, magnitude_db, kind='linear', bounds_error=False, fill_value=-120)
        band_levels = interp_func(band_centers)

        return {
            "name": track_name or Path(audio_path).stem,
            "path": audio_path,
            "freqs": freqs,
            "magnitude_db": magnitude_db,
            "band_centers": np.array(band_centers),
            "band_levels": band_levels,
            "duration": len(y) / sr,
            "rms_db": 20 * np.log10(np.sqrt(np.mean(y**2)) + 1e-10),
        }

    def detect_masking(
        self,
        track_a_path: str,
        track_b_path: str,
        track_a_name: str = "",
        track_b_name: str = "",
    ) -> MaskingAnalysisResult:
        """
        Detect masking between two tracks.
        Track B masks Track A when B's level exceeds A's level + threshold.
        """
        if not LIBROSA_AVAILABLE:
            return MaskingAnalysisResult(error="librosa not available")

        try:
            # Analyze both tracks
            track_a = self.analyze_track(track_a_path, track_a_name)
            track_b = self.analyze_track(track_b_path, track_b_name)

            # Compare in critical bands
            masking_regions = []

            for i, (low, high) in enumerate(self.CRITICAL_BANDS):
                center = (low + high) / 2
                level_a = track_a["band_levels"][i]
                level_b = track_b["band_levels"][i]

                # B masks A if B is louder than A by threshold
                masking_db = level_b - level_a

                if masking_db > -self.masking_threshold_db:  # e.g., B > A - 6dB
                    # Determine severity
                    if masking_db > 12:
                        severity = "critical"
                    elif masking_db > 6:
                        severity = "high"
                    elif masking_db > 0:
                        severity = "medium"
                    else:
                        severity = "low"

                    masking_regions.append(MaskingRegion(
                        freq_low=low,
                        freq_high=high,
                        center_freq=center,
                        track_a_level_db=float(level_a),
                        track_b_level_db=float(level_b),
                        masking_db=float(masking_db),
                        severity=severity,
                        track_a_name=track_a["name"],
                        track_b_name=track_b["name"],
                    ))

            # Merge adjacent regions of same severity
            masking_regions = self._merge_adjacent_regions(masking_regions)

            # Generate suggestions
            suggestions = self._generate_suggestions(masking_regions, track_a, track_b)

            # Overall masking score
            if masking_regions:
                critical_count = sum(1 for r in masking_regions if r.severity == "critical")
                high_count = sum(1 for r in masking_regions if r.severity == "high")
                total_bands = len(self.CRITICAL_BANDS)
                overall_score = (critical_count * 1.0 + high_count * 0.7 +
                                sum(1 for r in masking_regions if r.severity == "medium") * 0.4 +
                                sum(1 for r in masking_regions if r.severity == "low") * 0.1) / total_bands
            else:
                overall_score = 0.0

            return MaskingAnalysisResult(
                track_pairs=[(track_a["name"], track_b["name"])],
                masking_regions=masking_regions,
                suggestions=suggestions,
                overall_masking_score=min(overall_score, 1.0),
                track_spectra={
                    track_a["name"]: {"freqs": track_a["freqs"], "magnitude_db": track_a["magnitude_db"]},
                    track_b["name"]: {"freqs": track_b["freqs"], "magnitude_db": track_b["magnitude_db"]},
                },
            )

        except Exception as e:
            return MaskingAnalysisResult(error=str(e))

    def analyze_project_masking(
        self,
        track_paths: Dict[str, str],  # {track_name: audio_path}
    ) -> MaskingAnalysisResult:
        """Analyze masking across all track pairs in a project."""
        if not LIBROSA_AVAILABLE:
            return MaskingAnalysisResult(error="librosa not available")

        all_regions = []
        all_suggestions = []
        all_spectra = {}
        track_names = list(track_paths.keys())

        # Analyze each track
        tracks_data = {}
        for name, path in track_paths.items():
            tracks_data[name] = self.analyze_track(path, name)
            all_spectra[name] = {
                "freqs": tracks_data[name]["freqs"],
                "magnitude_db": tracks_data[name]["magnitude_db"],
            }

        # Compare all pairs
        for i, name_a in enumerate(track_names):
            for name_b in track_names[i+1:]:
                track_a = tracks_data[name_a]
                track_b = tracks_data[name_b]

                # Check both directions (A masks B, B masks A)
                for (t_a, t_b, n_a, n_b) in [(track_a, track_b, name_a, name_b),
                                              (track_b, track_a, name_b, name_a)]:
                    regions = self._compare_tracks(t_a, t_b, n_a, n_b)
                    all_regions.extend(regions)

        # Merge and deduplicate
        all_regions = self._merge_adjacent_regions(all_regions)

        # Generate suggestions for all regions
        for region in all_regions:
            t_a = tracks_data[region.track_a_name]
            t_b = tracks_data[region.track_b_name]
            suggestions = self._generate_suggestions([region], t_a, t_b)
            all_suggestions.extend(suggestions)

        # Overall score
        if all_regions:
            critical = sum(1 for r in all_regions if r.severity == "critical")
            high = sum(1 for r in all_regions if r.severity == "high")
            med = sum(1 for r in all_regions if r.severity == "medium")
            low = sum(1 for r in all_regions if r.severity == "low")
            total_pairs = len(track_names) * (len(track_names) - 1) / 2
            total_bands = len(self.CRITICAL_BANDS) * total_pairs * 2  # both directions
            overall = (critical * 1.0 + high * 0.7 + med * 0.4 + low * 0.1) / max(total_bands, 1)
        else:
            overall = 0.0

        return MaskingAnalysisResult(
            track_pairs=[(a, b) for i, a in enumerate(track_names) for b in track_names[i+1:]],
            masking_regions=all_regions,
            suggestions=all_suggestions,
            overall_masking_score=min(overall, 1.0),
            track_spectra=all_spectra,
        )

    def _compare_tracks(self, track_a, track_b, name_a, name_b) -> List[MaskingRegion]:
        """Compare two tracks for masking."""
        regions = []

        for i, (low, high) in enumerate(self.CRITICAL_BANDS):
            center = (low + high) / 2
            level_a = track_a["band_levels"][i]
            level_b = track_b["band_levels"][i]

            masking_db = level_b - level_a

            if masking_db > -self.masking_threshold_db:
                if masking_db > 12:
                    severity = "critical"
                elif masking_db > 6:
                    severity = "high"
                elif masking_db > 0:
                    severity = "medium"
                else:
                    severity = "low"

                regions.append(MaskingRegion(
                    freq_low=low,
                    freq_high=high,
                    center_freq=center,
                    track_a_level_db=float(level_a),
                    track_b_level_db=float(level_b),
                    masking_db=float(masking_db),
                    severity=severity,
                    track_a_name=name_a,
                    track_b_name=name_b,
                ))

        return regions

    def _merge_adjacent_regions(self, regions: List[MaskingRegion]) -> List[MaskingRegion]:
        """Merge adjacent regions with same severity and tracks."""
        if not regions:
            return []

        merged = []
        current = regions[0]

        for region in regions[1:]:
            if (region.track_a_name == current.track_a_name and
                region.track_b_name == current.track_b_name and
                region.severity == current.severity and
                region.freq_low <= current.freq_high * 1.05):  # Adjacent or overlapping
                # Merge
                current.freq_high = max(current.freq_high, region.freq_high)
                current.center_freq = (current.freq_low + current.freq_high) / 2
                current.masking_db = max(current.masking_db, region.masking_db)
                current.track_a_level_db = max(current.track_a_level_db, region.track_a_level_db)
                current.track_b_level_db = max(current.track_b_level_db, region.track_b_level_db)
            else:
                merged.append(current)
                current = region

        merged.append(current)
        return merged

    def _generate_suggestions(
        self,
        regions: List[MaskingRegion],
        track_a: Dict,
        track_b: Dict,
    ) -> List[UnmaskSuggestion]:
        """Generate unmasking suggestions for regions."""
        suggestions = []

        for region in regions:
            # Determine best action based on context
            freq = region.center_freq
            masking = region.masking_db

            # Default: cut the masking track (B) at the masking frequency
            # Q based on bandwidth
            bw_octaves = region.bandwidth_octaves
            q = 1.0 / (2 * np.sinh(np.log(2) * bw_octaves / 2)) if bw_octaves > 0 else 1.0
            q = float(np.clip(q, 0.5, 10.0))

            # Gain to reduce masking to threshold
            target_reduction = masking + self.masking_threshold_db  # e.g., if masking=10dB, threshold=-6, reduce by 16dB
            gain = -min(target_reduction, 12.0)  # Cap at -12dB

            # Action selection logic
            if freq < 150:
                # Low frequency: prefer level/pan over EQ
                if masking > 6:
                    action = "level"
                    suggestions.append(UnmaskSuggestion(
                        region=region,
                        action="level",
                        target_track=region.track_b_name,
                        frequency=freq,
                        gain_db=0,
                        q=q,
                        level_change_db=gain,
                        description=f"Reduce {region.track_b_name} level by {abs(gain):.1f}dB to unmask {region.track_a_name} below {freq:.0f}Hz",
                    ))
                else:
                    action = "cut_b"
                    suggestions.append(UnmaskSuggestion(
                        region=region,
                        action="cut_b",
                        target_track=region.track_b_name,
                        frequency=freq,
                        gain_db=gain,
                        q=q,
                        description=f"Cut {region.track_b_name} at {freq:.0f}Hz by {abs(gain):.1f}dB (low freq)",
                    ))
            elif freq > 8000:
                # High frequency: gentle cut
                action = "cut_b"
                suggestions.append(UnmaskSuggestion(
                    region=region,
                    action="cut_b",
                    target_track=region.track_b_name,
                    frequency=freq,
                    gain_db=gain * 0.7,  # Gentler
                    q=q * 1.5,
                    description=f"Gentle cut on {region.track_b_name} at {freq:.0f}Hz",
                ))
            else:
                # Mid frequency: EQ cut on masking track
                action = "cut_b"
                suggestions.append(UnmaskSuggestion(
                    region=region,
                    action="cut_b",
                    target_track=region.track_b_name,
                    frequency=freq,
                    gain_db=gain,
                    q=q,
                    description=f"Cut {region.track_b_name} at {freq:.0f}Hz by {abs(gain):.1f}dB to unmask {region.track_a_name}",
                ))

            # Also suggest panning separation for critical masking
            if region.severity in ("critical", "high"):
                suggestions.append(UnmaskSuggestion(
                    region=region,
                    action="pan",
                    target_track=region.track_b_name,
                    frequency=freq,
                    gain_db=0,
                    q=q,
                    pan_change=0.5 if region.track_b_name == track_b["name"] else -0.5,
                    description=f"Pan {region.track_b_name} away from center to reduce masking at {freq:.0f}Hz",
                ))

                # Sidechain suggestion for rhythmic masking (kick/bass)
                if freq < 200 and "kick" in region.track_a_name.lower() and "bass" in region.track_b_name.lower():
                    suggestions.append(UnmaskSuggestion(
                        region=region,
                        action="sidechain",
                        target_track=region.track_b_name,
                        frequency=freq,
                        gain_db=0,
                        q=q,
                        sidechain_ratio=4.0,
                        description=f"Sidechain {region.track_b_name} to {region.track_a_name} (kick/bass conflict)",
                    ))

        return suggestions

    def export_unmask_preset(self, result: MaskingAnalysisResult, format: str = "fabfilter") -> str:
        """Export unmasking suggestions as EQ preset."""
        if format == "fabfilter":
            lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                     '<FabFilterProQ version="4.00">',
                     f'  <BandCount>{len(result.suggestions)}</BandCount>']

            for i, s in enumerate(result.suggestions):
                if s.action not in ("cut_b", "cut_a"):
                    continue
                lines.append(f'  <Band index="{i}">')
                lines.append('    <Enabled>true</Enabled>')
                lines.append(f'    <Frequency>{s.frequency:.3f}</Frequency>')
                lines.append(f'    <Gain>{s.gain_db:.3f}</Gain>')
                lines.append(f'    <Q>{s.q:.3f}</Q>')
                lines.append('    <Shape>Bell</Shape>')
                lines.append('    <StereoPlacement>0</StereoPlacement>')
                lines.append('    <ChannelMode>0</ChannelMode>')
                lines.append('  </Band>')

            lines.append('</FabFilterProQ>')
            return '\n'.join(lines)
        else:
            import json
            return json.dumps([s.to_dict() for s in result.suggestions], indent=2)


# ============================================================
# Convenience Functions
# ============================================================

def detect_masking(
    track_a_path: str,
    track_b_path: str,
    track_a_name: str = "",
    track_b_name: str = "",
    masking_threshold_db: float = -6.0,
) -> MaskingAnalysisResult:
    """Quick masking detection between two tracks."""
    detector = MaskingDetector(masking_threshold_db=masking_threshold_db)
    return detector.detect_masking(track_a_path, track_b_path, track_a_name, track_b_name)


def analyze_project_masking(
    track_paths: Dict[str, str],
    masking_threshold_db: float = -6.0,
) -> MaskingAnalysisResult:
    """Quick project-wide masking analysis."""
    detector = MaskingDetector(masking_threshold_db=masking_threshold_db)
    return detector.analyze_project_masking(track_paths)


def suggest_unmask(
    track_a_path: str,
    track_b_path: str,
    track_a_name: str = "",
    track_b_name: str = "",
) -> List[UnmaskSuggestion]:
    """Quick unmasking suggestions."""
    result = detect_masking(track_a_path, track_b_path, track_a_name, track_b_name)
    return result.suggestions


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python masking_detection.py <track_a.wav> <track_b.wav> [more_tracks...]")
        sys.exit(1)

    if len(sys.argv) == 3:
        # Two tracks
        result = detect_masking(sys.argv[1], sys.argv[2])
    else:
        # Multiple tracks
        track_paths = {Path(p).stem: p for p in sys.argv[1:]}
        result = analyze_project_masking(track_paths)

    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Overall Masking Score: {result.overall_masking_score:.2%}")
        print(f"Track Pairs: {len(result.track_pairs)}")
        print(f"Masking Regions: {len(result.masking_regions)}")
        print(f"Suggestions: {len(result.suggestions)}")

        for region in result.masking_regions[:10]:
            print(f"  {region.freq_low:.0f}-{region.freq_high:.0f}Hz: "
                  f"{region.track_b_name} masks {region.track_a_name} by {region.masking_db:.1f}dB "
                  f"({region.severity})")

        print("\nTop Suggestions:")
        for s in result.suggestions[:10]:
            print(f"  [{s.action}] {s.description}")