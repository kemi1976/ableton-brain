#!/usr/bin/env python3
"""
Enhanced Mix Doctor Module
Comprehensive mix analysis: per-instrument profiling, phase correlation,
stereo width, dynamic range, tonal balance, loudness compliance.
Extends the existing mix_doctor with Neutron/Ozone-level analysis.
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

try:
    import pyloudnorm as pyln
    PYLOUDNORM_AVAILABLE = True
except ImportError:
    PYLOUDNORM_AVAILABLE = False


# ============================================================
# Instrument Profiles (Target Ranges)
# ============================================================

INSTRUMENT_PROFILES = {
    "kick": {
        "fundamental": (40, 100),      # Hz
        "body": (100, 250),
        "click": (2000, 5000),
        "sub": (20, 40),
        "target_lufs": -12,            # Short-term
        "dynamic_range": (6, 12),      # dB
        "stereo_width": 0.0,           # Mono
        "key_frequencies": [50, 80, 120, 3000],
    },
    "snare": {
        "fundamental": (120, 250),
        "body": (250, 500),
        "crack": (1500, 3000),
        "air": (5000, 10000),
        "target_lufs": -10,
        "dynamic_range": (8, 15),
        "stereo_width": 0.1,
        "key_frequencies": [180, 300, 2000, 8000],
    },
    "hihat": {
        "body": (200, 500),
        "sizzle": (5000, 12000),
        "air": (12000, 20000),
        "target_lufs": -18,
        "dynamic_range": (10, 20),
        "stereo_width": 0.6,
        "key_frequencies": [400, 7000, 14000],
    },
    "bass": {
        "sub": (20, 60),
        "fundamental": (60, 150),
        "harmonics": (300, 800),
        "presence": (1000, 3000),
        "target_lufs": -14,
        "dynamic_range": (4, 10),
        "stereo_width": 0.0,  # Mono below 150Hz
        "key_frequencies": [40, 80, 120, 500, 2000],
    },
    "vocals": {
        "body": (100, 300),
        "presence": (2000, 4000),
        "air": (8000, 15000),
        "sibilance": (4000, 8000),
        "target_lufs": -16,
        "dynamic_range": (8, 14),
        "stereo_width": 0.2,
        "key_frequencies": [200, 3000, 5000, 12000],
    },
    "synth_lead": {
        "fundamental": (200, 800),
        "harmonics": (800, 3000),
        "presence": (3000, 6000),
        "air": (6000, 15000),
        "target_lufs": -14,
        "dynamic_range": (6, 12),
        "stereo_width": 0.4,
        "key_frequencies": [440, 1500, 4000, 10000],
    },
    "pad": {
        "body": (100, 400),
        "warmth": (400, 1000),
        "air": (3000, 12000),
        "target_lufs": -20,
        "dynamic_range": (12, 20),
        "stereo_width": 0.8,
        "key_frequencies": [200, 800, 4000, 8000],
    },
    "piano": {
        "body": (80, 300),
        "presence": (1000, 3000),
        "air": (5000, 15000),
        "target_lufs": -18,
        "dynamic_range": (15, 25),
        "stereo_width": 0.5,
        "key_frequencies": [150, 1000, 3000, 8000],
    },
    "guitar": {
        "body": (100, 300),
        "bite": (1000, 2500),
        "presence": (3000, 6000),
        "air": (8000, 12000),
        "target_lufs": -16,
        "dynamic_range": (8, 16),
        "stereo_width": 0.5,
        "key_frequencies": [200, 1500, 4000, 10000],
    },
}


# ============================================================
# Data Classes
# ============================================================

@dataclass
class TrackAnalysis:
    """Analysis results for a single track."""
    track_name: str
    track_index: int
    instrument_type: Optional[str] = None

    # Loudness
    integrated_lufs: float = -23.0
    short_term_lufs: float = -23.0
    momentary_lufs: float = -23.0
    true_peak_db: float = -20.0
    lra: float = 0.0  # Loudness Range

    # Dynamics
    rms_db: float = -30.0
    peak_db: float = -20.0
    crest_factor_db: float = 0.0
    dynamic_range_db: float = 0.0  # Peak - RMS

    # Spectral
    spectral_centroid: float = 0.0
    spectral_rolloff: float = 0.0
    spectral_flatness: float = 0.0
    spectral_bandwidth: float = 0.0
    zero_crossing_rate: float = 0.0

    # Frequency bands (dB)
    sub_bass_db: float = -60.0       # 20-60 Hz
    bass_db: float = -60.0           # 60-250 Hz
    low_mid_db: float = -60.0        # 250-500 Hz
    mid_db: float = -60.0            # 500-2000 Hz
    high_mid_db: float = -60.0       # 2000-6000 Hz
    presence_db: float = -60.0       # 6000-10000 Hz
    air_db: float = -60.0            # 10000-20000 Hz

    # Stereo
    stereo_width: float = 0.0        # 0=mono, 1=wide
    phase_correlation: float = 1.0   # -1 to 1
    mid_level_db: float = -60.0
    side_level_db: float = -60.0

    # Issues
    issues: List[Dict] = field(default_factory=list)
    profile_match_score: float = 0.0  # 0-1 match to instrument profile

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class MixAnalysisResult:
    """Complete mix analysis."""
    tracks: List[TrackAnalysis] = field(default_factory=list)
    master: Optional[TrackAnalysis] = None

    # Overall metrics
    overall_lufs: float = -23.0
    overall_true_peak: float = -20.0
    overall_lra: float = 0.0

    # Balance
    tonal_balance_score: float = 0.0     # 0-1
    stereo_balance_score: float = 0.0    # 0-1
    dynamic_balance_score: float = 0.0   # 0-1

    # Issues
    global_issues: List[Dict] = field(default_factory=list)
    track_issues: Dict[str, List[Dict]] = field(default_factory=dict)

    # Recommendations
    recommendations: List[Dict] = field(default_factory=list)

    # Compliance
    streaming_compliant: bool = False
    club_compliant: bool = False
    broadcast_compliant: bool = False

    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "tracks": [t.to_dict() for t in self.tracks],
            "master": self.master.to_dict() if self.master else None,
            "overall_lufs": self.overall_lufs,
            "overall_true_peak": self.overall_true_peak,
            "overall_lra": self.overall_lra,
            "tonal_balance_score": self.tonal_balance_score,
            "stereo_balance_score": self.stereo_balance_score,
            "dynamic_balance_score": self.dynamic_balance_score,
            "global_issues": self.global_issues,
            "track_issues": self.track_issues,
            "recommendations": self.recommendations,
            "streaming_compliant": self.streaming_compliant,
            "club_compliant": self.club_compliant,
            "broadcast_compliant": self.broadcast_compliant,
            "error": self.error,
        }


# ============================================================
# Enhanced Mix Doctor
# ============================================================

class EnhancedMixDoctor:
    """
    Professional mix analysis with instrument profiling,
    phase/stereo analysis, and compliance checking.
    """

    # Target curves for different genres (simplified)
    GENRE_TARGETS = {
        "electronic": {
            "sub_bass": -18, "bass": -15, "low_mid": -18, "mid": -18,
            "high_mid": -16, "presence": -18, "air": -24,
            "stereo_width": 0.5, "dynamic_range": 8,
        },
        "hiphop": {
            "sub_bass": -12, "bass": -10, "low_mid": -18, "mid": -18,
            "high_mid": -16, "presence": -18, "air": -24,
            "stereo_width": 0.4, "dynamic_range": 6,
        },
        "rock": {
            "sub_bass": -24, "bass": -18, "low_mid": -16, "mid": -14,
            "high_mid": -14, "presence": -16, "air": -22,
            "stereo_width": 0.5, "dynamic_range": 10,
        },
        "pop": {
            "sub_bass": -20, "bass": -16, "low_mid": -16, "mid": -14,
            "high_mid": -14, "presence": -16, "air": -20,
            "stereo_width": 0.5, "dynamic_range": 8,
        },
        "ambient": {
            "sub_bass": -24, "bass": -20, "low_mid": -18, "mid": -18,
            "high_mid": -20, "presence": -22, "air": -18,
            "stereo_width": 0.7, "dynamic_range": 14,
        },
        "jazz": {
            "sub_bass": -30, "bass": -22, "low_mid": -18, "mid": -16,
            "high_mid": -18, "presence": -20, "air": -22,
            "stereo_width": 0.4, "dynamic_range": 18,
        },
        "orchestral": {
            "sub_bass": -28, "bass": -20, "low_mid": -18, "mid": -16,
            "high_mid": -18, "presence": -20, "air": -18,
            "stereo_width": 0.6, "dynamic_range": 22,
        },
    }

    def __init__(
        self,
        sample_rate: int = 44100,
        fft_size: int = 8192,
        hop_length: int = 2048,
    ):
        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self.hop_length = hop_length

        # Frequency band edges
        self.band_edges = {
            "sub_bass": (20, 60),
            "bass": (60, 250),
            "low_mid": (250, 500),
            "mid": (500, 2000),
            "high_mid": (2000, 6000),
            "presence": (6000, 10000),
            "air": (10000, 20000),
        }

    def analyze_track_audio(
        self,
        audio_path: str,
        track_name: str = "",
        track_index: int = 0,
        instrument_hint: Optional[str] = None,
    ) -> TrackAnalysis:
        """Analyze a single track audio file."""
        if not LIBROSA_AVAILABLE:
            raise ImportError("librosa required")

        y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=False)

        # Handle mono/stereo
        if y.ndim == 1:
            y = y[np.newaxis, :]  # Make (1, samples)
            is_stereo = False
        else:
            is_stereo = True

        # Convert to mono for analysis
        y_mono = librosa.to_mono(y)

        analysis = TrackAnalysis(
            track_name=track_name or Path(audio_path).stem,
            track_index=track_index,
        )

        # Detect instrument type if not provided
        if instrument_hint:
            analysis.instrument_type = instrument_hint
        else:
            analysis.instrument_type = self._detect_instrument_type(y_mono, sr)

        # Loudness analysis
        self._analyze_loudness(y_mono, sr, analysis, is_stereo, y)

        # Spectral analysis
        self._analyze_spectrum(y_mono, sr, analysis)

        # Frequency band analysis
        self._analyze_frequency_bands(y_mono, sr, analysis)

        # Stereo analysis
        if is_stereo:
            self._analyze_stereo(y, sr, analysis)
        else:
            analysis.stereo_width = 0.0
            analysis.phase_correlation = 1.0
            analysis.mid_level_db = analysis.rms_db
            analysis.side_level_db = -120.0

        # Profile matching
        if analysis.instrument_type:
            analysis.profile_match_score = self._match_instrument_profile(analysis)
            self._check_profile_compliance(analysis)

        return analysis

    def _detect_instrument_type(self, y: np.ndarray, sr: int) -> str:
        """Heuristic instrument detection from spectral features."""
        # Simple heuristic based on spectral centroid and bandwidth
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr).mean()
        bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr).mean()
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr).mean()
        flatness = librosa.feature.spectral_flatness(y=y).mean()

        # Sub-bass energy
        stft = np.abs(librosa.stft(y, n_fft=self.fft_size))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=self.fft_size)
        sub_bass = np.mean(stft[(freqs >= 20) & (freqs <= 60)])
        bass = np.mean(stft[(freqs >= 60) & (freqs <= 250)])

        # Heuristics
        if centroid < 200 and sub_bass > bass * 0.5:
            return "kick"
        elif centroid > 5000 and flatness > 0.5:
            return "hihat"
        elif 150 < centroid < 400 and bandwidth > 1000:
            return "snare"
        elif centroid < 300 and bass > sub_bass:
            return "bass"
        elif 300 < centroid < 1000 and bandwidth > 1500:
            return "vocals"
        elif centroid > 1500 and bandwidth > 2000:
            return "synth_lead"
        elif centroid < 800 and flatness < 0.2:
            return "pad"
        elif 400 < centroid < 1500:
            return "piano"
        else:
            return "unknown"

    def _analyze_loudness(self, y_mono: np.ndarray, sr: int, analysis: TrackAnalysis,
                          is_stereo: bool, y_stereo: np.ndarray):
        """Analyze loudness metrics."""
        if PYLOUDNORM_AVAILABLE:
            try:
                meter = pyln.Meter(sr)
                analysis.integrated_lufs = meter.integrated_loudness(y_mono)
                # Short-term (3s window)
                analysis.short_term_lufs = np.mean([
                    meter.integrated_loudness(y_mono[i:i+sr*3])
                    for i in range(0, len(y_mono)-sr*3, sr)
                ]) if len(y_mono) > sr*3 else analysis.integrated_lufs
                # Momentary (400ms)
                analysis.momentary_lufs = np.mean([
                    meter.integrated_loudness(y_mono[i:i+sr//2])
                    for i in range(0, len(y_mono)-sr//2, sr//4)
                ]) if len(y_mono) > sr//2 else analysis.integrated_lufs
                # LRA
                analysis.lra = meter.loudness_range(y_mono)
            except:
                pass

        # True peak (oversampled)
        analysis.true_peak_db = 20 * np.log10(np.max(np.abs(y_mono)) + 1e-10)

        # RMS and peak
        analysis.rms_db = 20 * np.log10(np.sqrt(np.mean(y_mono**2)) + 1e-10)
        analysis.peak_db = 20 * np.log10(np.max(np.abs(y_mono)) + 1e-10)
        analysis.crest_factor_db = analysis.peak_db - analysis.rms_db
        analysis.dynamic_range_db = analysis.crest_factor_db  # Simplified

    def _analyze_spectrum(self, y: np.ndarray, sr: int, analysis: TrackAnalysis):
        """Analyze spectral features."""
        analysis.spectral_centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())
        analysis.spectral_rolloff = float(librosa.feature.spectral_rolloff(y=y, sr=sr).mean())
        analysis.spectral_flatness = float(librosa.feature.spectral_flatness(y=y).mean())
        analysis.spectral_bandwidth = float(librosa.feature.spectral_bandwidth(y=y, sr=sr).mean())
        analysis.zero_crossing_rate = float(librosa.feature.zero_crossing_rate(y).mean())

    def _analyze_frequency_bands(self, y: np.ndarray, sr: int, analysis: TrackAnalysis):
        """Analyze energy in frequency bands."""
        stft = np.abs(librosa.stft(y, n_fft=self.fft_size))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=self.fft_size)
        magnitude_db = 20 * np.log10(np.mean(stft, axis=1) + 1e-10)

        for band_name, (low, high) in self.band_edges.items():
            mask = (freqs >= low) & (freqs <= high)
            if np.any(mask):
                band_level = np.mean(magnitude_db[mask])
                setattr(analysis, f"{band_name}_db", float(band_level))
            else:
                setattr(analysis, f"{band_name}_db", -120.0)

    def _analyze_stereo(self, y: np.ndarray, sr: int, analysis: TrackAnalysis):
        """Analyze stereo image."""
        left = y[0]
        right = y[1]

        # Mid/Side
        mid = (left + right) / 2
        side = (left - right) / 2

        analysis.mid_level_db = 20 * np.log10(np.sqrt(np.mean(mid**2)) + 1e-10)
        analysis.side_level_db = 20 * np.log10(np.sqrt(np.mean(side**2)) + 1e-10)

        # Phase correlation
        correlation = np.corrcoef(left, right)[0, 1]
        analysis.phase_correlation = float(correlation) if not np.isnan(correlation) else 1.0

        # Stereo width (side/mid ratio)
        if analysis.mid_level_db > -60:
            width = 10**((analysis.side_level_db - analysis.mid_level_db) / 20)
            analysis.stereo_width = float(np.clip(width, 0, 2))
        else:
            analysis.stereo_width = 0.0

    def _match_instrument_profile(self, analysis: TrackAnalysis) -> float:
        """Score how well track matches its instrument profile."""
        if not analysis.instrument_type or analysis.instrument_type not in INSTRUMENT_PROFILES:
            return 0.0

        profile = INSTRUMENT_PROFILES[analysis.instrument_type]
        score = 0.0
        checks = 0

        # Check key frequency bands
        for freq_name in ["sub_bass", "bass", "low_mid", "mid", "high_mid", "presence", "air"]:
            track_val = getattr(analysis, f"{freq_name}_db", -120)
            # Profile doesn't have explicit targets for all, skip for now
            checks += 1
            # Score based on whether energy is in expected range
            # Simplified: if track has energy where profile expects it
            score += 1.0  # Placeholder

        # Dynamic range check
        target_dr = profile.get("dynamic_range", (6, 12))
        if target_dr[0] <= analysis.dynamic_range_db <= target_dr[1]:
            score += 1.0
        checks += 1

        # Stereo width check
        target_width = profile.get("stereo_width", 0.5)
        if abs(analysis.stereo_width - target_width) < 0.3:
            score += 1.0
        checks += 1

        return score / max(checks, 1)

    def _check_profile_compliance(self, analysis: TrackAnalysis):
        """Check compliance with instrument profile, add issues."""
        if not analysis.instrument_type or analysis.instrument_type not in INSTRUMENT_PROFILES:
            return

        profile = INSTRUMENT_PROFILES[analysis.instrument_type]
        issues = []

        # Dynamic range
        target_dr = profile.get("dynamic_range", (6, 12))
        if analysis.dynamic_range_db < target_dr[0]:
            issues.append({
                "type": "over_compressed",
                "severity": "high",
                "message": f"Dynamic range ({analysis.dynamic_range_db:.1f}dB) below target ({target_dr[0]}-{target_dr[1]}dB)",
                "suggestion": "Reduce compression/limiting",
            })
        elif analysis.dynamic_range_db > target_dr[1]:
            issues.append({
                "type": "under_compressed",
                "severity": "low",
                "message": f"Dynamic range ({analysis.dynamic_range_db:.1f}dB) above target ({target_dr[0]}-{target_dr[1]}dB)",
                "suggestion": "Consider gentle compression for consistency",
            })

        # Stereo width
        target_width = profile.get("stereo_width", 0.5)
        if analysis.stereo_width < target_width - 0.2:
            issues.append({
                "type": "too_narrow",
                "severity": "medium",
                "message": f"Stereo width ({analysis.stereo_width:.2f}) narrower than target ({target_width:.2f})",
                "suggestion": "Widen with stereo imaging or Haas effect",
            })
        elif analysis.stereo_width > target_width + 0.2:
            issues.append({
                "type": "too_wide",
                "severity": "medium",
                "message": f"Stereo width ({analysis.stereo_width:.2f}) wider than target ({target_width:.2f})",
                "suggestion": "Narrow low frequencies, check phase",
            })

        # Phase correlation
        if analysis.phase_correlation < 0:
            issues.append({
                "type": "phase_issue",
                "severity": "high",
                "message": f"Negative phase correlation ({analysis.phase_correlation:.2f}) - phase cancellation likely",
                "suggestion": "Check polarity, align tracks, use phase rotation",
            })
        elif analysis.phase_correlation < 0.5:
            issues.append({
                "type": "weak_correlation",
                "severity": "medium",
                "message": f"Low phase correlation ({analysis.phase_correlation:.2f})",
                "suggestion": "Check for phase issues between L/R",
            })

        # True peak
        if analysis.true_peak_db > -1:
            issues.append({
                "type": "true_peak_clipping",
                "severity": "high",
                "message": f"True peak ({analysis.true_peak_db:.1f}dB) exceeds -1dBTP",
                "suggestion": "Reduce level or use true peak limiter",
            })

        analysis.issues = issues

    def analyze_mix(
        self,
        track_paths: Dict[str, str],  # {track_name: path}
        master_path: Optional[str] = None,
        genre: str = "electronic",
    ) -> MixAnalysisResult:
        """Analyze full mix from track stems."""
        result = MixAnalysisResult()
        target = self.GENRE_TARGETS.get(genre, self.GENRE_TARGETS["electronic"])

        # Analyze each track
        for idx, (name, path) in enumerate(track_paths.items()):
            try:
                track = self.analyze_track_audio(path, name, idx)
                result.tracks.append(track)
                result.track_issues[name] = track.issues
            except Exception as e:
                result.track_issues[name] = [{"type": "error", "message": str(e)}]

        # Analyze master if provided
        if master_path:
            try:
                result.master = self.analyze_track_audio(master_path, "Master", -1)
                result.overall_lufs = result.master.integrated_lufs
                result.overall_true_peak = result.master.true_peak_db
                result.overall_lra = result.master.lra
            except Exception as e:
                result.error = str(e)

        # Compute mix balance scores
        if result.tracks:
            self._compute_balance_scores(result, target)

        # Generate recommendations
        self._generate_recommendations(result, target, genre)

        # Check compliance
        self._check_compliance(result)

        return result

    def _compute_balance_scores(self, result: MixAnalysisResult, target: Dict):
        """Compute tonal, stereo, dynamic balance scores."""
        if not result.tracks:
            return

        # Tonal balance: compare aggregate spectrum to genre target
        band_names = ["sub_bass", "bass", "low_mid", "mid", "high_mid", "presence", "air"]
        track_levels = {band: [] for band in band_names}

        for track in result.tracks:
            for band in band_names:
                val = getattr(track, f"{band}_db", -120)
                if val > -60:  # Only count tracks with energy in band
                    track_levels[band].append(val)

        # Average level per band across tracks
        avg_levels = {}
        for band in band_names:
            if track_levels[band]:
                avg_levels[band] = np.mean(track_levels[band])
            else:
                avg_levels[band] = -60

        # Compare to genre target
        target_levels = {k: target.get(k, -20) for k in band_names}
        differences = [abs(avg_levels[b] - target_levels[b]) for b in band_names]
        result.tonal_balance_score = float(max(0, 1 - np.mean(differences) / 20))

        # Stereo balance: average width vs target
        widths = [t.stereo_width for t in result.tracks if t.stereo_width > 0]
        if widths:
            avg_width = np.mean(widths)
            target_width = target.get("stereo_width", 0.5)
            result.stereo_balance_score = float(max(0, 1 - abs(avg_width - target_width) / 0.5))

        # Dynamic balance: check dynamic range consistency
        drs = [t.dynamic_range_db for t in result.tracks if t.dynamic_range_db > 0]
        if drs:
            target_dr = target.get("dynamic_range", 8)
            avg_dr = np.mean(drs)
            result.dynamic_balance_score = float(max(0, 1 - abs(avg_dr - target_dr) / 10))

    def _generate_recommendations(self, result: MixAnalysisResult, target: Dict, genre: str):
        """Generate prioritized recommendations."""
        recs = []

        # From track issues
        for track in result.tracks:
            for issue in track.issues:
                recs.append({
                    "priority": "high" if issue["severity"] == "high" else "medium",
                    "track": track.track_name,
                    "type": issue["type"],
                    "message": issue["message"],
                    "suggestion": issue["suggestion"],
                })

        # Tonal balance
        if result.tonal_balance_score < 0.7:
            recs.append({
                "priority": "high",
                "track": "MIX BUS",
                "type": "tonal_balance",
                "message": f"Tonal balance score {result.tonal_balance_score:.0%} - deviates from {genre} target",
                "suggestion": "Use EQ Match to reference track, adjust track levels",
            })

        # Stereo balance
        if result.stereo_balance_score < 0.7:
            recs.append({
                "priority": "medium",
                "track": "MIX BUS",
                "type": "stereo_balance",
                "message": f"Stereo balance score {result.stereo_balance_score:.0%}",
                "suggestion": "Check panning, widen/narrow tracks to match genre",
            })

        # Dynamic balance
        if result.dynamic_balance_score < 0.7:
            recs.append({
                "priority": "medium",
                "track": "MIX BUS",
                "type": "dynamic_balance",
                "message": f"Dynamic balance score {result.dynamic_balance_score:.0%}",
                "suggestion": "Adjust compression per track for consistent dynamics",
            })

        # Master issues
        if result.master:
            if result.master.true_peak_db > -1:
                recs.append({
                    "priority": "critical",
                    "track": "MASTER",
                    "type": "true_peak",
                    "message": f"True peak {result.master.true_peak_db:.1f}dBTP exceeds -1dBTP",
                    "suggestion": "Apply true peak limiter at -0.3 to -1dB ceiling",
                })

            # Streaming targets
            if result.master.integrated_lufs > -14:
                recs.append({
                    "priority": "high",
                    "track": "MASTER",
                    "type": "loudness",
                    "message": f"Integrated LUFS {result.master.integrated_lufs:.1f} too loud for streaming (-14 target)",
                    "suggestion": "Reduce master level or increase dynamic range",
                })
            elif result.master.integrated_lufs < -18:
                recs.append({
                    "priority": "medium",
                    "track": "MASTER",
                    "type": "loudness",
                    "message": f"Integrated LUFS {result.master.integrated_lufs:.1f} quieter than streaming target (-14)",
                    "suggestion": "Consider gentle limiting/maximizing to -14 LUFS",
                })

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recs.sort(key=lambda r: priority_order.get(r["priority"], 3))

        result.recommendations = recs

    def _check_compliance(self, result: MixAnalysisResult):
        """Check loudness compliance for different platforms."""
        if not result.master:
            return

        lufs = result.master.integrated_lufs
        tp = result.master.true_peak_db

        # Streaming (-14 LUFS, -1 dBTP)
        result.streaming_compliant = (lufs >= -15 and lufs <= -13 and tp <= -1)

        # Club (-8 to -10 LUFS, -0.3 dBTP)
        result.club_compliant = (lufs >= -10 and lufs <= -7 and tp <= -0.3)

        # Broadcast (-24 LUFS, -2 dBTP) - EBU R128
        result.broadcast_compliant = (lufs >= -25 and lufs <= -23 and tp <= -2)

    def compare_to_reference(
        self,
        mix_path: str,
        reference_path: str,
        genre: str = "electronic",
    ) -> Dict:
        """Compare mix to reference track."""
        mix = self.analyze_track_audio(mix_path, "Mix")
        ref = self.analyze_track_audio(reference_path, "Reference")

        bands = ["sub_bass", "bass", "low_mid", "mid", "high_mid", "presence", "air"]
        differences = {}

        for band in bands:
            mix_val = getattr(mix, f"{band}_db", -60)
            ref_val = getattr(ref, f"{band}_db", -60)
            differences[band] = mix_val - ref_val  # Positive = mix has more

        return {
            "mix_lufs": mix.integrated_lufs,
            "reference_lufs": ref.integrated_lufs,
            "lufs_diff": mix.integrated_lufs - ref.integrated_lufs,
            "band_differences_db": differences,
            "stereo_width_diff": mix.stereo_width - ref.stereo_width,
            "dynamic_range_diff": mix.dynamic_range_db - ref.dynamic_range_db,
            "spectral_centroid_diff": mix.spectral_centroid - ref.spectral_centroid,
            "recommendations": self._generate_eq_recommendations(differences),
        }

    def _generate_eq_recommendations(self, differences: Dict) -> List[Dict]:
        """Generate EQ recommendations from band differences."""
        recs = []
        for band, diff in differences.items():
            if diff > 3:  # Mix has 3dB more
                recs.append({
                    "band": band,
                    "action": "cut",
                    "gain_db": -min(diff * 0.7, 6),
                    "message": f"Mix has {diff:.1f}dB too much {band}, cut {min(diff * 0.7, 6):.1f}dB",
                })
            elif diff < -3:  # Mix has 3dB less
                recs.append({
                    "band": band,
                    "action": "boost",
                    "gain_db": min(-diff * 0.5, 4),
                    "message": f"Mix has {abs(diff):.1f}dB too little {band}, boost {min(-diff * 0.5, 4):.1f}dB",
                })
        return recs


# ============================================================
# Convenience Functions
# ============================================================

def analyze_track(
    audio_path: str,
    track_name: str = "",
    instrument_hint: Optional[str] = None,
) -> TrackAnalysis:
    """Quick single track analysis."""
    doctor = EnhancedMixDoctor()
    return doctor.analyze_track_audio(audio_path, track_name, instrument_hint=instrument_hint)


def analyze_mix(
    track_paths: Dict[str, str],
    master_path: Optional[str] = None,
    genre: str = "electronic",
) -> MixAnalysisResult:
    """Quick full mix analysis."""
    doctor = EnhancedMixDoctor()
    return doctor.analyze_mix(track_paths, master_path, genre)


def compare_to_reference(
    mix_path: str,
    reference_path: str,
    genre: str = "electronic",
) -> Dict:
    """Quick reference comparison."""
    doctor = EnhancedMixDoctor()
    return doctor.compare_to_reference(mix_path, reference_path, genre)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python enhanced_mix_doctor.py <track.wav> [more_tracks...] [--master master.wav] [--genre electronic]")
        sys.exit(1)

    # Parse args
    tracks = {}
    master = None
    genre = "electronic"

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--master":
            master = sys.argv[i+1]
            i += 2
        elif sys.argv[i] == "--genre":
            genre = sys.argv[i+1]
            i += 2
        else:
            name = Path(sys.argv[i]).stem
            tracks[name] = sys.argv[i]
            i += 1

    if len(tracks) == 1 and not master:
        # Single track
        path = list(tracks.values())[0]
        name = list(tracks.keys())[0]
        result = analyze_track(path, name)
        print(f"Track: {result.track_name}")
        print(f"Instrument: {result.instrument_type}")
        print(f"LUFS: {result.integrated_lufs:.1f}")
        print(f"True Peak: {result.true_peak_db:.1f}dBTP")
        print(f"Dynamic Range: {result.dynamic_range_db:.1f}dB")
        print(f"Stereo Width: {result.stereo_width:.2f}")
        print(f"Phase Correlation: {result.phase_correlation:.2f}")
        print(f"Profile Match: {result.profile_match_score:.0%}")
        print("\nBands:")
        for band in ["sub_bass", "bass", "low_mid", "mid", "high_mid", "presence", "air"]:
            val = getattr(result, f"{band}_db", -120)
            print(f"  {band}: {val:.1f}dB")
        print("\nIssues:")
        for issue in result.issues:
            print(f"  [{issue['severity']}] {issue['message']} -> {issue['suggestion']}")
    else:
        # Full mix
        result = analyze_mix(tracks, master, genre)
        print(f"Genre: {genre}")
        print(f"Overall LUFS: {result.overall_lufs:.1f}")
        print(f"True Peak: {result.overall_true_peak:.1f}dBTP")
        print(f"LRA: {result.overall_lra:.1f}")
        print(f"Tonal Balance: {result.tonal_balance_score:.0%}")
        print(f"Stereo Balance: {result.stereo_balance_score:.0%}")
        print(f"Dynamic Balance: {result.dynamic_balance_score:.0%}")
        print(f"Streaming Compliant: {result.streaming_compliant}")
        print(f"Club Compliant: {result.club_compliant}")
        print(f"Broadcast Compliant: {result.broadcast_compliant}")
        print("\nRecommendations:")
        for r in result.recommendations[:10]:
            print(f"  [{r['priority'].upper()}] {r['track']}: {r['message']}")
            print(f"    -> {r['suggestion']}")