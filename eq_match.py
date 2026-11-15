#!/usr/bin/env python3
"""
EQ Match / Reference Track Matching Module
Analyzes spectral difference between a target track and reference track,
generates parametric EQ curve to match tonal balance.
Similar to FabFilter Pro-Q 4 EQ Match / iZotope Ozone Master Assistant.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

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
class EQBand:
    """Single parametric EQ band."""
    frequency: float       # Center frequency in Hz
    gain: float           # Gain in dB (positive or negative)
    q: float              # Quality factor (bandwidth)
    filter_type: str = "bell"  # "bell", "high_shelf", "low_shelf", "high_pass", "low_pass"
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "frequency": self.frequency,
            "gain": self.gain,
            "q": self.q,
            "filter_type": self.filter_type,
            "enabled": self.enabled,
        }


@dataclass
class EQMatchResult:
    """Result of EQ matching analysis."""
    target_path: str
    reference_path: str
    eq_bands: List[EQBand] = field(default_factory=list)
    spectral_difference_db: np.ndarray = field(default_factory=lambda: np.array([]))
    frequencies_hz: np.ndarray = field(default_factory=lambda: np.array([]))
    target_spectrum_db: np.ndarray = field(default_factory=lambda: np.array([]))
    reference_spectrum_db: np.ndarray = field(default_factory=lambda: np.array([]))
    match_quality: float = 0.0  # 0-1, how well EQ matches
    target_lufs: float = -23.0
    reference_lufs: float = -23.0
    gain_match_db: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "target_path": self.target_path,
            "reference_path": self.reference_path,
            "eq_bands": [b.to_dict() for b in self.eq_bands],
            "match_quality": self.match_quality,
            "target_lufs": self.target_lufs,
            "reference_lufs": self.reference_lufs,
            "gain_match_db": self.gain_match_db,
            "error": self.error,
        }


@dataclass
class SpectralAnalysis:
    """Detailed spectral analysis of a track."""
    frequencies_hz: np.ndarray
    magnitude_db: np.ndarray
    lufs: float
    true_peak_db: float
    spectral_centroid: float
    spectral_rolloff: float
    spectral_flatness: float
    zero_crossing_rate: float
    rms_db: float


# ============================================================
# EQ Match Engine
# ============================================================

class EQMatchEngine:
    """
    Match tonal balance of target track to reference track.
    Generates parametric EQ curve using spectral difference analysis.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        fft_size: int = 8192,
        hop_length: int = 2048,
        min_freq: float = 20.0,
        max_freq: float = 20000.0,
        num_bands: int = 12,
        max_gain_db: float = 12.0,
        smoothing_octaves: float = 1/3,
    ):
        """
        Initialize EQ Match engine.

        Args:
            sample_rate: Target sample rate for analysis
            fft_size: FFT window size
            hop_length: Hop length for STFT
            min_freq: Minimum frequency for analysis
            max_freq: Maximum frequency for analysis
            num_bands: Number of EQ bands to generate
            max_gain_db: Maximum gain per band (safety limit)
            smoothing_octaves: Smoothing for spectral comparison
        """
        self.sample_rate = sample_rate
        self.fft_size = fft_size
        self.hop_length = hop_length
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.num_bands = num_bands
        self.max_gain_db = max_gain_db
        self.smoothing_octaves = smoothing_octaves

        # Frequency axis for analysis
        self.freqs = None
        self._build_freq_axis()

    def _build_freq_axis(self):
        """Build logarithmic frequency axis."""
        # Log-spaced frequencies for analysis
        self.freqs = np.logspace(
            np.log10(self.min_freq),
            np.log10(self.max_freq),
            num=2048
        )

    def analyze_track(self, audio_path: str) -> SpectralAnalysis:
        """
        Perform detailed spectral analysis of a track.

        Returns:
            SpectralAnalysis with spectrum, LUFS, and spectral features
        """
        if not LIBROSA_AVAILABLE:
            raise ImportError("librosa required for spectral analysis")

        # Load audio
        y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)

        # Compute STFT
        stft = librosa.stft(y, n_fft=self.fft_size, hop_length=self.hop_length)
        magnitude = np.abs(stft)

        # Average magnitude spectrum (log-frequency)
        # Interpolate to our frequency axis
        freqs_stft = librosa.fft_frequencies(sr=sr, n_fft=self.fft_size)
        magnitude_db = 20 * np.log10(np.mean(magnitude, axis=1) + 1e-10)

        # Interpolate to log-frequency axis
        from scipy.interpolate import interp1d
        interp_func = interp1d(
            freqs_stft, magnitude_db,
            kind='linear', bounds_error=False, fill_value=-120
        )
        magnitude_db_log = interp_func(self.freqs)

        # Apply smoothing (1/3 octave by default)
        magnitude_db_smooth = self._smooth_spectrum(magnitude_db_log)

        # LUFS measurement
        lufs = self._measure_lufs(y, sr)

        # True peak
        true_peak = 20 * np.log10(np.max(np.abs(y)) + 1e-10)

        # Spectral features
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr).mean()
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr).mean()
        flatness = librosa.feature.spectral_flatness(y=y).mean()
        zcr = librosa.feature.zero_crossing_rate(y).mean()
        rms = np.sqrt(np.mean(y**2))
        rms_db = 20 * np.log10(rms + 1e-10)

        return SpectralAnalysis(
            frequencies_hz=self.freqs.copy(),
            magnitude_db=magnitude_db_smooth,
            lufs=lufs,
            true_peak_db=true_peak,
            spectral_centroid=float(centroid),
            spectral_rolloff=float(rolloff),
            spectral_flatness=float(flatness),
            zero_crossing_rate=float(zcr),
            rms_db=rms_db,
        )

    def _smooth_spectrum(self, spectrum_db: np.ndarray) -> np.ndarray:
        """Apply 1/3 octave smoothing to spectrum."""
        if not SCIPY_AVAILABLE:
            return spectrum_db

        # Convert smoothing octaves to frequency-domain window
        # 1/3 octave = factor of 2^(1/3) ≈ 1.26
        # In log-frequency space, this is a constant width
        freq_ratio = 2 ** (1/3)
        log_freqs = np.log2(self.freqs)
        window_width_log = np.log2(freq_ratio)
        window_samples = int(window_width_log / (log_freqs[1] - log_freqs[0]))
        window_samples = max(3, window_samples | 1)  # Odd number

        # Gaussian smoothing in log-frequency domain
        from scipy.ndimage import gaussian_filter1d
        sigma = window_samples / 2.355  # Convert FWHM to sigma
        return gaussian_filter1d(spectrum_db, sigma=sigma)

    def _measure_lufs(self, y: np.ndarray, sr: int) -> float:
        """Measure integrated LUFS (EBU R128 compliant approximation)."""
        try:
            import pyloudnorm as pyln
            meter = pyln.Meter(sr)
            return meter.integrated_loudness(y)
        except ImportError:
            # Fallback: RMS-based approximation
            rms = np.sqrt(np.mean(y**2))
            return 20 * np.log10(rms + 1e-10) - 0.691  # Rough K-weighting offset

    def match_eq(
        self,
        target_path: str,
        reference_path: str,
        num_bands: Optional[int] = None,
        match_gain: bool = True,
    ) -> EQMatchResult:
        """
        Generate EQ curve to match target spectrum to reference spectrum.

        Args:
            target_path: Path to target track (to be EQ'd)
            reference_path: Path to reference track (target tonal balance)
            num_bands: Number of EQ bands (overrides default)
            match_gain: Whether to match overall gain (LUFS)

        Returns:
            EQMatchResult with EQ bands and analysis data
        """
        if not LIBROSA_AVAILABLE:
            return EQMatchResult(
                target_path=target_path,
                reference_path=reference_path,
                error="librosa not available"
            )

        try:
            # Analyze both tracks
            target_analysis = self.analyze_track(target_path)
            reference_analysis = self.analyze_track(reference_path)

            # Compute spectral difference (reference - target)
            # Positive = target needs boost, Negative = target needs cut
            spectral_diff = reference_analysis.magnitude_db - target_analysis.magnitude_db

            # Gain matching
            gain_match_db = 0.0
            if match_gain:
                gain_match_db = reference_analysis.lufs - target_analysis.lufs
                # Apply gain offset to difference
                spectral_diff -= gain_match_db

            # Generate EQ bands from spectral difference
            bands = self._generate_eq_bands(
                self.freqs,
                spectral_diff,
                num_bands or self.num_bands,
            )

            # Calculate match quality (correlation after EQ simulation)
            match_quality = self._calculate_match_quality(
                target_analysis.magnitude_db,
                reference_analysis.magnitude_db,
                bands,
            )

            return EQMatchResult(
                target_path=target_path,
                reference_path=reference_path,
                eq_bands=bands,
                spectral_difference_db=spectral_diff,
                frequencies_hz=self.freqs.copy(),
                target_spectrum_db=target_analysis.magnitude_db.copy(),
                reference_spectrum_db=reference_analysis.magnitude_db.copy(),
                match_quality=match_quality,
                target_lufs=target_analysis.lufs,
                reference_lufs=reference_analysis.lufs,
                gain_match_db=gain_match_db,
            )

        except Exception as e:
            return EQMatchResult(
                target_path=target_path,
                reference_path=reference_path,
                error=str(e)
            )

    def _generate_eq_bands(
        self,
        freqs: np.ndarray,
        spectral_diff: np.ndarray,
        num_bands: int,
    ) -> List[EQBand]:
        """
        Generate parametric EQ bands from spectral difference curve.
        Uses peak detection and band fitting.
        """
        bands = []

        # Find peaks in spectral difference (both positive and negative)
        from scipy.signal import find_peaks

        # Positive peaks (need boost)
        pos_peaks, pos_props = find_peaks(
            spectral_diff,
            height=0.5,  # Minimum 0.5 dB difference
            distance=len(freqs) // (num_bands * 2),
            prominence=0.3,
        )

        # Negative peaks (need cut)
        neg_peaks, neg_props = find_peaks(
            -spectral_diff,
            height=0.5,
            distance=len(freqs) // (num_bands * 2),
            prominence=0.3,
        )

        # Combine and sort by prominence
        all_peaks = []
        for idx, prom in zip(pos_peaks, pos_props.get('prominences', [])):
            all_peaks.append((idx, spectral_diff[idx], prom, 'boost'))
        for idx, prom in zip(neg_peaks, neg_props.get('prominences', [])):
            all_peaks.append((idx, spectral_diff[idx], prom, 'cut'))

        # Sort by prominence (most audible first)
        all_peaks.sort(key=lambda x: -x[2])

        # Take top N peaks
        selected_peaks = all_peaks[:num_bands]

        # Create EQ bands from peaks
        for idx, diff_db, prominence, direction in selected_peaks:
            freq = freqs[idx]
            gain = np.clip(diff_db, -self.max_gain_db, self.max_gain_db)

            # Estimate Q from peak width
            # Find -3dB points around peak
            q = self._estimate_q(freqs, spectral_diff, idx, direction)

            # Determine filter type based on frequency
            if freq < 80:
                filter_type = "low_shelf" if direction == 'boost' else "high_pass"
            elif freq > 10000:
                filter_type = "high_shelf" if direction == 'boost' else "low_pass"
            else:
                filter_type = "bell"

            bands.append(EQBand(
                frequency=freq,
                gain=gain,
                q=q,
                filter_type=filter_type,
            ))

        # Sort bands by frequency
        bands.sort(key=lambda b: b.frequency)

        return bands

    def _estimate_q(
        self,
        freqs: np.ndarray,
        spectrum: np.ndarray,
        peak_idx: int,
        direction: str,
    ) -> float:
        """Estimate Q factor from peak width at -3dB."""
        peak_val = spectrum[peak_idx]
        target_val = peak_val - 3.0 if direction == 'boost' else peak_val + 3.0

        # Find left -3dB point
        left_idx = peak_idx
        while left_idx > 0 and (
            (direction == 'boost' and spectrum[left_idx] > target_val) or
            (direction == 'cut' and spectrum[left_idx] < target_val)
        ):
            left_idx -= 1

        # Find right -3dB point
        right_idx = peak_idx
        while right_idx < len(freqs) - 1 and (
            (direction == 'boost' and spectrum[right_idx] > target_val) or
            (direction == 'cut' and spectrum[right_idx] < target_val)
        ):
            right_idx += 1

        if right_idx <= left_idx:
            return 1.0  # Default Q

        # Bandwidth in octaves
        bw_octaves = np.log2(freqs[right_idx] / freqs[left_idx])
        if bw_octaves <= 0:
            return 1.0

        # Q = sqrt(2^N) / (2^N - 1) where N = bandwidth in octaves
        # Approximation: Q ≈ 1 / (2 * sinh(ln(2) * bw_octaves / 2))
        q = 1.0 / (2 * np.sinh(np.log(2) * bw_octaves / 2))

        return float(np.clip(q, 0.1, 30.0))

    def _calculate_match_quality(
        self,
        target_spectrum: np.ndarray,
        reference_spectrum: np.ndarray,
        bands: List[EQBand],
    ) -> float:
        """Simulate EQ application and calculate match quality."""
        # Simulate EQ curve
        eq_curve = np.zeros_like(target_spectrum)

        for band in bands:
            if not band.enabled:
                continue

            if band.filter_type == "bell":
                # Bell filter response
                response = self._bell_response(
                    self.freqs, band.frequency, band.gain, band.q
                )
            elif band.filter_type == "low_shelf":
                response = self._shelf_response(
                    self.freqs, band.frequency, band.gain, band.q, low=True
                )
            elif band.filter_type == "high_shelf":
                response = self._shelf_response(
                    self.freqs, band.frequency, band.gain, band.q, low=False
                )
            else:
                response = np.zeros_like(self.freqs)

            eq_curve += response

        # Apply EQ to target spectrum
        eqd_spectrum = target_spectrum + eq_curve

        # Correlation with reference
        corr = np.corrcoef(eqd_spectrum, reference_spectrum)[0, 1]

        return float(max(0, corr))  # Clamp to 0-1

    def _bell_response(
        self,
        freqs: np.ndarray,
        fc: float,
        gain_db: float,
        q: float,
    ) -> np.ndarray:
        """Calculate bell filter frequency response."""
        # Analog prototype -> digital via bilinear transform approximation
        w0 = 2 * np.pi * fc / self.sample_rate
        alpha = np.sin(w0) / (2 * q)
        A = 10 ** (gain_db / 40)

        # Biquad coefficients
        b0 = 1 + alpha * A
        b1 = -2 * np.cos(w0)
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * np.cos(w0)
        a2 = 1 - alpha / A

        # Frequency response
        w = 2 * np.pi * freqs / self.sample_rate
        cos_w = np.cos(w)
        cos_2w = np.cos(2 * w)

        num = b0**2 + b1**2 + b2**2 + 2*b0*b1*cos_w + 2*b1*b2*cos_w + 2*b0*b2*cos_2w
        den = a0**2 + a1**2 + a2**2 + 2*a0*a1*cos_w + 2*a1*a2*cos_w + 2*a0*a2*cos_2w

        response_db = 10 * np.log10(num / den + 1e-10)
        return response_db

    def _shelf_response(
        self,
        freqs: np.ndarray,
        fc: float,
        gain_db: float,
        q: float,
        low: bool = True,
    ) -> np.ndarray:
        """Calculate shelf filter frequency response."""
        w0 = 2 * np.pi * fc / self.sample_rate
        A = 10 ** (gain_db / 40)
        sqrt_A = np.sqrt(A)
        alpha = np.sin(w0) / (2 * q)

        if low:
            # Low shelf
            b0 = A * ((A + 1) - (A - 1) * np.cos(w0) + 2 * sqrt_A * alpha)
            b1 = 2 * A * ((A - 1) - (A + 1) * np.cos(w0))
            b2 = A * ((A + 1) - (A - 1) * np.cos(w0) - 2 * sqrt_A * alpha)
            a0 = (A + 1) + (A - 1) * np.cos(w0) + 2 * sqrt_A * alpha
            a1 = -2 * ((A - 1) + (A + 1) * np.cos(w0))
            a2 = (A + 1) - (A - 1) * np.cos(w0) - 2 * sqrt_A * alpha
        else:
            # High shelf
            b0 = A * ((A + 1) + (A - 1) * np.cos(w0) + 2 * sqrt_A * alpha)
            b1 = -2 * A * ((A - 1) + (A + 1) * np.cos(w0))
            b2 = A * ((A + 1) + (A - 1) * np.cos(w0) - 2 * sqrt_A * alpha)
            a0 = (A + 1) - (A - 1) * np.cos(w0) + 2 * sqrt_A * alpha
            a1 = 2 * ((A - 1) - (A + 1) * np.cos(w0))
            a2 = (A + 1) - (A - 1) * np.cos(w0) - 2 * sqrt_A * alpha

        # Normalize
        b0, b1, b2 = b0/a0, b1/a0, b2/a0
        a1, a2 = a1/a0, a2/a0

        # Frequency response
        w = 2 * np.pi * freqs / self.sample_rate
        cos_w = np.cos(w)
        cos_2w = np.cos(2 * w)

        num = b0**2 + b1**2 + b2**2 + 2*b0*b1*cos_w + 2*b1*b2*cos_w + 2*b0*b2*cos_2w
        den = 1 + a1**2 + a2**2 + 2*a1*cos_w + 2*a2*cos_2w + 2*a1*a2*cos_w

        response_db = 10 * np.log10(num / den + 1e-10)
        return response_db

    def export_eq_preset(
        self,
        result: EQMatchResult,
        format: str = "fabfilter",
    ) -> str:
        """
        Export EQ bands as preset for popular EQ plugins.

        Formats: 'fabfilter', 'parametric', 'reaper', 'generic'
        """
        if format == "fabfilter":
            return self._export_fabfilter(result)
        elif format == "reaper":
            return self._export_reaper(result)
        else:
            return self._export_generic(result)

    def _export_fabfilter(self, result: EQMatchResult) -> str:
        """Export as FabFilter Pro-Q XML preset."""
        lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<FabFilterProQ version="4.00">',
                 '  <BandCount>{}</BandCount>'.format(len(result.eq_bands))]

        for i, band in enumerate(result.eq_bands):
            lines.append('  <Band index="{}">'.format(i))
            lines.append('    <Enabled>{}</Enabled>'.format('true' if band.enabled else 'false'))
            lines.append('    <Frequency>{:.3f}</Frequency>'.format(band.frequency))
            lines.append('    <Gain>{:.3f}</Gain>'.format(band.gain))
            lines.append('    <Q>{:.3f}</Q>'.format(band.q))
            lines.append('    <Shape>{}</Shape>'.format(self._map_shape(band.filter_type)))
            lines.append('    <StereoPlacement>0</StereoPlacement>')
            lines.append('    <ChannelMode>0</ChannelMode>')
            lines.append('  </Band>')

        lines.append('</FabFilterProQ>')
        return '\n'.join(lines)

    def _export_reaper(self, result: EQMatchResult) -> str:
        """Export as Reaper ReaEQ preset."""
        lines = ['<REAPER_EQ "ReaEQ"',
                 '  NUM_BANDS {}'.format(len(result.eq_bands))]

        for i, band in enumerate(result.eq_bands):
            shape_map = {"bell": 0, "low_shelf": 1, "high_shelf": 2,
                         "high_pass": 3, "low_pass": 4}
            shape = shape_map.get(band.filter_type, 0)
            lines.append('  BAND {} {} {:.3f} {:.3f} {:.3f}'.format(
                i, shape, band.frequency, band.gain, band.q
            ))

        lines.append('>')
        return '\n'.join(lines)

    def _export_generic(self, result: EQMatchResult) -> str:
        """Export as generic JSON."""
        import json
        return json.dumps({
            "bands": [b.to_dict() for b in result.eq_bands],
            "metadata": {
                "target": result.target_path,
                "reference": result.reference_path,
                "match_quality": result.match_quality,
                "gain_match_db": result.gain_match_db,
            }
        }, indent=2)

    def _map_shape(self, filter_type: str) -> str:
        """Map filter type to FabFilter shape name."""
        mapping = {
            "bell": "Bell",
            "low_shelf": "LowShelf",
            "high_shelf": "HighShelf",
            "high_pass": "HighPass",
            "low_pass": "LowPass",
        }
        return mapping.get(filter_type, "Bell")


# ============================================================
# Convenience Functions
# ============================================================

def match_eq(
    target_path: str,
    reference_path: str,
    num_bands: int = 12,
    max_gain_db: float = 12.0,
) -> EQMatchResult:
    """Quick EQ match."""
    engine = EQMatchEngine(num_bands=num_bands, max_gain_db=max_gain_db)
    return engine.match_eq(target_path, reference_path, num_bands=num_bands)


def analyze_spectrum(audio_path: str) -> SpectralAnalysis:
    """Quick spectral analysis."""
    engine = EQMatchEngine()
    return engine.analyze_track(audio_path)


def export_eq_preset(
    result: EQMatchResult,
    format: str = "fabfilter",
) -> str:
    """Quick preset export."""
    engine = EQMatchEngine()
    return engine.export_eq_preset(result, format)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python eq_match.py <target_audio> <reference_audio> [output_preset]")
        sys.exit(1)

    target = sys.argv[1]
    reference = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) > 3 else None

    print(f"Matching EQ: {target} -> {reference}")
    result = match_eq(target, reference)

    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Match Quality: {result.match_quality:.2%}")
        print(f"Gain Match: {result.gain_match_db:.1f} dB")
        print(f"Target LUFS: {result.target_lufs:.1f}")
        print(f"Reference LUFS: {result.reference_lufs:.1f}")
        print(f"\nEQ Bands ({len(result.eq_bands)}):")
        for b in result.eq_bands:
            print(f"  {b.frequency:.1f} Hz: {b.gain:+.1f} dB, Q={b.q:.2f}, {b.filter_type}")

        if output:
            preset = export_eq_preset(result, "fabfilter")
            with open(output, 'w') as f:
                f.write(preset)
            print(f"\nPreset saved to: {output}")