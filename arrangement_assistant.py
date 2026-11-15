#!/usr/bin/env python3
"""
Arrangement Assistant Module
Analyzes project structure, detects sections (intro/verse/chorus/drop/etc.),
suggests arrangement improvements, generates genre-based templates.
Integrates with Ableton's clip launcher for section triggering.
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
    from mido import MidiFile
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False
    MidiFile = None


# ============================================================
# Arrangement Templates by Genre
# ============================================================

ARRANGEMENT_TEMPLATES = {
    "dnb": {
        "name": "Drum & Bass",
        "tempo": 174,
        "structure": [
            ("intro", 32, "atmospheric, drums only last 16"),
            ("build", 16, "rising energy, snare roll"),
            ("drop1", 64, "main drop, full arrangement"),
            ("break", 32, "minimal, melodic focus"),
            ("build2", 16, "second build"),
            ("drop2", 64, "variation, more intensity"),
            ("outro", 16, "drums fade"),
        ],
        "energy_curve": [0.2, 0.4, 0.9, 0.3, 0.5, 1.0, 0.1],
        "track_roles": {
            "drums": ["intro", "build", "drop1", "break", "build2", "drop2", "outro"],
            "bass": ["drop1", "drop2"],
            "lead": ["break", "build2", "drop2"],
            "pad": ["intro", "break", "outro"],
            "fx": ["build", "build2", "drop1", "drop2"],
        }
    },
    "house": {
        "name": "House",
        "tempo": 124,
        "structure": [
            ("intro", 32, "kick + hats, gradual elements"),
            ("verse1", 32, "bass + minimal percussion"),
            ("build", 16, "open hats, snare roll"),
            ("drop", 64, "main groove, vocal chops"),
            ("break", 16, "breakdown, atmospheric"),
            ("build2", 16, "tension build"),
            ("drop2", 64, "peak energy"),
            ("outro", 32, "elements drop out"),
        ],
        "energy_curve": [0.2, 0.4, 0.6, 0.9, 0.3, 0.6, 1.0, 0.1],
        "track_roles": {
            "drums": ["intro", "verse1", "build", "drop", "break", "build2", "drop2", "outro"],
            "bass": ["verse1", "drop", "drop2"],
            "vocals": ["drop", "drop2"],
            "pad": ["intro", "break", "outro"],
            "fx": ["build", "build2"],
        }
    },
    "techno": {
        "name": "Techno",
        "tempo": 130,
        "structure": [
            ("intro", 64, "kick + percussion, hypnotic"),
            ("main", 128, "full groove, evolving textures"),
            ("break", 32, "stripped back, atmospheric"),
            ("main2", 128, "peak intensity, more layers"),
            ("outro", 64, "gradual reduction"),
        ],
        "energy_curve": [0.3, 0.8, 0.4, 1.0, 0.2],
        "track_roles": {
            "drums": ["intro", "main", "break", "main2", "outro"],
            "bass": ["main", "main2"],
            "lead": ["main", "main2"],
            "pad": ["intro", "break", "outro"],
            "fx": ["main", "main2"],
        }
    },
    "trap": {
        "name": "Trap",
        "tempo": 140,
        "structure": [
            ("intro", 16, "melodic, atmospheric"),
            ("verse", 16, "vocal, sparse drums"),
            ("pre_chorus", 8, "building tension"),
            ("chorus", 16, "hard drop, 808s"),
            ("verse2", 16, "variation"),
            ("pre_chorus2", 8, "build"),
            ("chorus2", 16, "peak"),
            ("bridge", 8, "breakdown"),
            ("chorus3", 16, "final"),
            ("outro", 8, "fade"),
        ],
        "energy_curve": [0.2, 0.3, 0.5, 0.9, 0.4, 0.6, 1.0, 0.2, 0.9, 0.1],
        "track_roles": {
            "drums": ["verse", "pre_chorus", "chorus", "verse2", "pre_chorus2", "chorus2", "chorus3"],
            "808": ["chorus", "chorus2", "chorus3"],
            "melody": ["intro", "verse", "bridge", "outro"],
            "vocals": ["verse", "chorus", "verse2", "chorus2", "chorus3"],
            "fx": ["pre_chorus", "pre_chorus2", "bridge"],
        }
    },
    "ambient": {
        "name": "Ambient",
        "tempo": 80,
        "structure": [
            ("intro", 64, "slow fade in, textures"),
            ("development", 128, "evolving layers"),
            ("climax", 64, "peak density"),
            ("release", 64, "gradual fade"),
            ("coda", 32, "final resonance"),
        ],
        "energy_curve": [0.1, 0.4, 0.7, 0.3, 0.1],
        "track_roles": {
            "pad": ["intro", "development", "climax", "release", "coda"],
            "texture": ["intro", "development", "climax", "release"],
            "melody": ["development", "climax", "release"],
            "drone": ["intro", "development", "climax", "release", "coda"],
        }
    },
    "pop": {
        "name": "Pop",
        "tempo": 120,
        "structure": [
            ("intro", 8, "hook teaser"),
            ("verse1", 16, "story setup"),
            ("pre_chorus", 8, "build"),
            ("chorus", 16, "main hook"),
            ("verse2", 16, "development"),
            ("pre_chorus2", 8, "build"),
            ("chorus2", 16, "peak"),
            ("bridge", 8, "contrast"),
            ("chorus3", 16, "final hook"),
            ("outro", 8, "fade"),
        ],
        "energy_curve": [0.3, 0.4, 0.6, 0.9, 0.5, 0.7, 1.0, 0.4, 0.9, 0.2],
        "track_roles": {
            "drums": ["verse1", "pre_chorus", "chorus", "verse2", "pre_chorus2", "chorus2", "bridge", "chorus3"],
            "bass": ["verse1", "pre_chorus", "chorus", "verse2", "pre_chorus2", "chorus2", "chorus3"],
            "vocals": ["verse1", "pre_chorus", "chorus", "verse2", "pre_chorus2", "chorus2", "bridge", "chorus3"],
            "keys": ["intro", "verse1", "chorus", "bridge", "chorus3"],
            "fx": ["pre_chorus", "pre_chorus2", "bridge"],
        }
    },
}


# ============================================================
# Data Classes
# ============================================================

@dataclass
class ArrangementSection:
    """A detected or suggested arrangement section."""
    name: str                    # "intro", "verse", "chorus", "drop", "break", "build", "outro", etc.
    start_bar: float
    end_bar: float
    length_bars: float
    energy: float                # 0-1
    density: float               # 0-1 (number of active tracks)
    key_tracks: List[str] = field(default_factory=list)  # Tracks active in this section
    description: str = ""
    confidence: float = 0.0      # Detection confidence

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start_bar": self.start_bar,
            "end_bar": self.end_bar,
            "length_bars": self.length_bars,
            "energy": self.energy,
            "density": self.density,
            "key_tracks": self.key_tracks,
            "description": self.description,
            "confidence": self.confidence,
        }


@dataclass
class ArrangementAnalysis:
    """Complete arrangement analysis."""
    sections: List[ArrangementSection] = field(default_factory=list)
    total_bars: float = 0
    tempo: float = 120
    time_signature: str = "4/4"
    genre: Optional[str] = None
    energy_curve: List[float] = field(default_factory=list)
    track_activity: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)  # track -> [(start, end), ...]
    issues: List[Dict] = field(default_factory=list)
    suggestions: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sections": [s.to_dict() for s in self.sections],
            "total_bars": self.total_bars,
            "tempo": self.tempo,
            "time_signature": self.time_signature,
            "genre": self.genre,
            "energy_curve": self.energy_curve,
            "track_activity": {k: v for k, v in self.track_activity.items()},
            "issues": self.issues,
            "suggestions": self.suggestions,
        }


@dataclass
class ArrangementTemplate:
    """Generated arrangement template."""
    genre: str
    name: str
    tempo: int
    structure: List[Tuple[str, int, str]]  # (name, bars, description)
    energy_curve: List[float]
    track_roles: Dict[str, List[str]]
    total_bars: int

    def to_dict(self) -> dict:
        return {
            "genre": self.genre,
            "name": self.name,
            "tempo": self.tempo,
            "structure": [{"name": s[0], "bars": s[1], "description": s[2]} for s in self.structure],
            "energy_curve": self.energy_curve,
            "track_roles": self.track_roles,
            "total_bars": self.total_bars,
        }


# ============================================================
# Arrangement Analyzer
# ============================================================

class ArrangementAnalyzer:
    """
    Analyze arrangement from audio stems or Ableton project data.
    Detects sections based on energy, spectral changes, track activity.
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        hop_length: int = 512,
        min_section_bars: int = 4,
    ):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.min_section_bars = min_section_bars

    def analyze_from_stems(
        self,
        stem_paths: Dict[str, str],  # {track_name: audio_path}
        tempo: float = 120,
    ) -> ArrangementAnalysis:
        """Analyze arrangement from rendered stems."""
        if not LIBROSA_AVAILABLE:
            return ArrangementAnalysis(error="librosa not available")

        # Load all stems, compute features per time window
        track_features = {}
        max_duration = 0

        for name, path in stem_paths.items():
            try:
                y, sr = librosa.load(path, sr=self.sample_rate, mono=True)
                max_duration = max(max_duration, len(y) / sr)

                # Compute features in windows
                features = self._compute_track_features(y, sr)
                track_features[name] = features
            except Exception as e:
                print(f"Warning: Failed to load {path}: {e}")

        if not track_features:
            return ArrangementAnalysis(error="No valid stems loaded")

        # Convert duration to bars
        bars_per_second = tempo / 60 * 4  # 4 beats per bar
        total_bars = max_duration * bars_per_second

        # Detect sections from combined energy/density
        sections = self._detect_sections(track_features, total_bars, tempo, bars_per_second)

        # Detect genre from structure
        genre = self._classify_genre(sections, tempo)

        # Track activity
        track_activity = self._compute_track_activity(track_features, bars_per_second)

        # Energy curve
        energy_curve = self._compute_energy_curve(track_features, bars_per_second)

        # Identify issues and suggestions
        issues = self._identify_issues(sections, track_activity, energy_curve)
        suggestions = self._generate_suggestions(sections, issues, genre, tempo)

        return ArrangementAnalysis(
            sections=sections,
            total_bars=total_bars,
            tempo=tempo,
            genre=genre,
            energy_curve=energy_curve,
            track_activity=track_activity,
            issues=issues,
            suggestions=suggestions,
        )

    def _compute_track_features(self, y: np.ndarray, sr: int) -> Dict:
        """Compute per-window features for a track."""
        # Window = 1 bar at tempo 120 = 2 seconds
        # But we'll use fixed time windows and convert later
        window_sec = 2.0  # 2 second windows
        hop_sec = 0.5     # 50% overlap
        window_samples = int(window_sec * sr)
        hop_samples = int(hop_sec * sr)

        n_windows = max(1, (len(y) - window_samples) // hop_samples + 1)

        rms_values = []
        centroid_values = []
        flatness_values = []
        onset_strength = []

        for i in range(n_windows):
            start = i * hop_samples
            end = min(start + window_samples, len(y))
            window = y[start:end]

            if len(window) < sr // 10:  # Too short
                rms_values.append(-60)
                centroid_values.append(0)
                flatness_values.append(0)
                onset_strength.append(0)
                continue

            rms = 20 * np.log10(np.sqrt(np.mean(window**2)) + 1e-10)
            cent = librosa.feature.spectral_centroid(y=window, sr=sr).mean() if len(window) > 512 else 0
            flat = librosa.feature.spectral_flatness(y=window).mean() if len(window) > 512 else 0

            rms_values.append(rms)
            centroid_values.append(float(cent))
            flatness_values.append(float(flat))

            # Onset strength
            if len(window) > 512:
                onset_env = librosa.onset.onset_strength(y=window, sr=sr)
                onset_strength.append(float(np.mean(onset_env)))
            else:
                onset_strength.append(0)

        return {
            "rms": np.array(rms_values),
            "centroid": np.array(centroid_values),
            "flatness": np.array(flatness_values),
            "onset": np.array(onset_strength),
            "n_windows": n_windows,
            "window_sec": window_sec,
            "hop_sec": hop_sec,
        }

    def _detect_sections(
        self,
        track_features: Dict[str, Dict],
        total_bars: float,
        tempo: float,
        bars_per_second: float,
    ) -> List[ArrangementSection]:
        """Detect arrangement sections from track features."""
        # Combine all tracks: sum RMS for energy, count active for density
        n_windows = max(f["n_windows"] for f in track_features.values())
        combined_energy = np.zeros(n_windows)
        combined_density = np.zeros(n_windows)
        track_names = list(track_features.keys())

        for name, feat in track_features.items():
            rms = feat["rms"]
            # Normalize RMS to 0-1 per track
            if rms.max() > rms.min():
                norm_rms = (rms - rms.min()) / (rms.max() - rms.min())
            else:
                norm_rms = np.zeros_like(rms)

            combined_energy += norm_rms
            combined_density += (norm_rms > 0.1).astype(float)

        combined_energy /= len(track_features)
        combined_density /= len(track_features)

        # Smooth
        from scipy.ndimage import gaussian_filter1d
        combined_energy = gaussian_filter1d(combined_energy, sigma=1.5)
        combined_density = gaussian_filter1d(combined_density, sigma=1.5)

        # Find change points (section boundaries)
        # Compute derivative of energy
        energy_diff = np.diff(combined_energy)
        density_diff = np.diff(combined_density)

        # Significant changes
        change_threshold = 0.15
        change_points = np.where(
            (np.abs(energy_diff) > change_threshold) |
            (np.abs(density_diff) > change_threshold)
        )[0]

        # Convert to bar positions
        window_to_bar = lambda w: w * (feat["hop_sec"] * bars_per_second)

        sections = []
        prev_bar = 0

        for cp in change_points:
            bar = window_to_bar(cp)
            if bar - prev_bar >= self.min_section_bars:
                # Classify section
                section_name = self._classify_section(
                    combined_energy[max(0, cp-2):cp+2],
                    combined_density[max(0, cp-2):cp+2],
                    prev_bar, bar,
                )

                sections.append(ArrangementSection(
                    name=section_name,
                    start_bar=prev_bar,
                    end_bar=bar,
                    length_bars=bar - prev_bar,
                    energy=float(np.mean(combined_energy[max(0, cp-2):cp+2])),
                    density=float(np.mean(combined_density[max(0, cp-2):cp+2])),
                    key_tracks=self._get_active_tracks(track_features, cp),
                    confidence=0.7,
                ))
                prev_bar = bar

        # Final section
        if total_bars - prev_bar >= self.min_section_bars:
            sections.append(ArrangementSection(
                name="outro" if len(sections) > 0 else "main",
                start_bar=prev_bar,
                end_bar=total_bars,
                length_bars=total_bars - prev_bar,
                energy=float(np.mean(combined_energy[-4:])),
                density=float(np.mean(combined_density[-4:])),
                key_tracks=self._get_active_tracks(track_features, n_windows - 1),
                confidence=0.6,
            ))

        # If no sections detected, create basic structure
        if not sections:
            sections.append(ArrangementSection(
                name="main",
                start_bar=0,
                end_bar=total_bars,
                length_bars=total_bars,
                energy=float(np.mean(combined_energy)),
                density=float(np.mean(combined_density)),
                key_tracks=track_names,
                confidence=0.3,
            ))

        return sections

    def _classify_section(self, energy_window: np.ndarray, density_window: np.ndarray,
                          start_bar: float, end_bar: float) -> str:
        """Classify section type from energy/density."""
        avg_energy = np.mean(energy_window)
        avg_density = np.mean(density_window)
        energy_trend = energy_window[-1] - energy_window[0] if len(energy_window) > 1 else 0

        # Position-based heuristics
        if start_bar == 0:
            return "intro"
        elif avg_energy < 0.3 and avg_density < 0.3:
            return "break" if energy_trend < 0 else "outro"
        elif energy_trend > 0.2:
            return "build"
        elif energy_trend < -0.2:
            return "drop" if avg_energy > 0.5 else "break"
        elif avg_energy > 0.7:
            return "drop"
        elif avg_energy > 0.4:
            return "verse" if avg_density < 0.5 else "chorus"
        else:
            return "section"

    def _get_active_tracks(self, track_features: Dict, window_idx: int) -> List[str]:
        """Get tracks active at a given window."""
        active = []
        for name, feat in track_features.items():
            if window_idx < len(feat["rms"]):
                rms = feat["rms"][window_idx]
                if rms > -30:  # Arbitrary threshold
                    active.append(name)
        return active

    def _compute_track_activity(
        self,
        track_features: Dict[str, Dict],
        bars_per_second: float,
    ) -> Dict[str, List[Tuple[float, float]]]:
        """Compute activity regions per track."""
        activity = {}
        for name, feat in track_features.items():
            rms = feat["rms"]
            hop_sec = feat["hop_sec"]

            regions = []
            in_region = False
            region_start = 0

            for i, val in enumerate(rms):
                bar = i * hop_sec * bars_per_second
                if val > -30 and not in_region:
                    in_region = True
                    region_start = bar
                elif val <= -30 and in_region:
                    in_region = False
                    regions.append((region_start, bar))

            if in_region:
                regions.append((region_start, len(rms) * hop_sec * bars_per_second))

            activity[name] = regions

        return activity

    def _compute_energy_curve(self, track_features: Dict, bars_per_second: float) -> List[float]:
        """Compute overall energy curve."""
        n_windows = max(f["n_windows"] for f in track_features.values())
        energy = np.zeros(n_windows)

        for feat in track_features.values():
            rms = feat["rms"]
            if rms.max() > rms.min():
                norm = (rms - rms.min()) / (rms.max() - rms.min())
            else:
                norm = np.zeros_like(rms)
            energy[:len(norm)] += norm

        energy /= len(track_features)

        # Downsample to ~1 point per bar
        points_per_bar = max(1, int(1 / (feat["hop_sec"] * bars_per_second)))
        return energy[::points_per_bar].tolist()

    def _classify_genre(self, sections: List[ArrangementSection], tempo: float) -> str:
        """Classify genre from arrangement structure."""
        section_names = [s.name for s in sections]
        structure_str = "-".join(section_names)

        # Heuristics
        if "drop" in section_names and tempo > 160:
            return "dnb"
        elif "drop" in section_names and 135 < tempo < 155:
            return "trap"
        elif "drop" in section_names and tempo > 120:
            return "house"
        elif "main" in section_names and "break" in section_names and tempo > 125:
            return "techno"
        elif "chorus" in structure_str and "verse" in structure_str:
            return "pop"
        elif len(sections) <= 5 and all(s.length_bars > 32 for s in sections):
            return "ambient"
        else:
            return "electronic"

    def _identify_issues(self, sections: List[ArrangementSection],
                         track_activity: Dict, energy_curve: List[float]) -> List[Dict]:
        """Identify arrangement issues."""
        issues = []

        # Too short sections
        for s in sections:
            if s.length_bars < 4 and s.name not in ("build", "pre_chorus", "bridge"):
                issues.append({
                    "type": "short_section",
                    "severity": "medium",
                    "section": s.name,
                    "message": f"Section '{s.name}' is only {s.length_bars:.0f} bars (recommended: 8+)",
                    "suggestion": f"Extend {s.name} or merge with adjacent section",
                })

        # Energy curve issues
        if len(energy_curve) > 2:
            # Check for flat energy (boring)
            energy_std = np.std(energy_curve)
            if energy_std < 0.15:
                issues.append({
                    "type": "flat_energy",
                    "severity": "medium",
                    "message": "Energy curve is flat - arrangement lacks dynamics",
                    "suggestion": "Add builds, breaks, and contrast between sections",
                })

            # Check for no climax
            if max(energy_curve) < 0.6:
                issues.append({
                    "type": "no_climax",
                    "severity": "medium",
                    "message": "No clear energy peak (max energy < 0.6)",
                    "suggestion": "Create a high-energy drop/chorus section",
                })

        # Missing standard sections
        section_types = set(s.name for s in sections)
        if "intro" not in section_types and "outro" not in section_types:
            issues.append({
                "type": "missing_intro_outro",
                "severity": "low",
                "message": "Missing intro/outro sections",
                "suggestion": "Add 8-16 bar intro and outro for DJ-friendly structure",
            })

        return issues

    def _generate_suggestions(self, sections: List[ArrangementSection],
                              issues: List[Dict], genre: str, tempo: float) -> List[Dict]:
        """Generate arrangement improvement suggestions."""
        suggestions = []

        # From issues
        for issue in issues:
            suggestions.append({
                "type": issue["type"],
                "priority": "high" if issue["severity"] == "high" else "medium",
                "message": issue["message"],
                "suggestion": issue["suggestion"],
            })

        # Genre-specific suggestions
        template = ARRANGEMENT_TEMPLATES.get(genre)
        if template:
            expected_sections = [s[0] for s in template["structure"]]
            current_sections = [s.name for s in sections]

            for expected in expected_sections:
                if expected not in current_sections:
                    suggestions.append({
                        "type": "missing_section",
                        "priority": "medium",
                        "message": f"Missing typical {genre} section: {expected}",
                        "suggestion": f"Add {expected} section ({template['structure'][expected_sections.index(expected)][1]} bars)",
                    })

        return suggestions


# ============================================================
# Arrangement Template Generator
# ============================================================

class ArrangementTemplateGenerator:
    """Generate arrangement templates for genres."""

    def get_template(self, genre: str) -> Optional[ArrangementTemplate]:
        """Get arrangement template for genre."""
        if genre not in ARRANGEMENT_TEMPLATES:
            return None

        t = ARRANGEMENT_TEMPLATES[genre]
        total_bars = sum(s[1] for s in t["structure"])

        return ArrangementTemplate(
            genre=genre,
            name=t["name"],
            tempo=t["tempo"],
            structure=t["structure"],
            energy_curve=t["energy_curve"],
            track_roles=t["track_roles"],
            total_bars=total_bars,
        )

    def list_genres(self) -> List[Dict]:
        """List available genre templates."""
        return [
            {
                "genre": g,
                "name": t["name"],
                "tempo": t["tempo"],
                "sections": len(t["structure"]),
                "total_bars": sum(s[1] for s in t["structure"]),
            }
            for g, t in ARRANGEMENT_TEMPLATES.items()
        ]

    def create_custom_template(
        self,
        name: str,
        tempo: int,
        structure: List[Tuple[str, int, str]],
        track_roles: Dict[str, List[str]],
    ) -> ArrangementTemplate:
        """Create custom arrangement template."""
        energy_curve = np.linspace(0.2, 1.0, len(structure)).tolist()
        # Adjust energy for known section types
        for i, (sec_name, _, _) in enumerate(structure):
            if sec_name in ("intro", "outro"):
                energy_curve[i] = 0.2
            elif sec_name in ("break", "bridge"):
                energy_curve[i] = 0.3
            elif sec_name in ("build", "pre_chorus"):
                energy_curve[i] = 0.6
            elif sec_name in ("drop", "chorus"):
                energy_curve[i] = 0.9

        total_bars = sum(s[1] for s in structure)

        return ArrangementTemplate(
            genre="custom",
            name=name,
            tempo=tempo,
            structure=structure,
            energy_curve=energy_curve,
            track_roles=track_roles,
            total_bars=total_bars,
        )


# ============================================================
# Clip Launcher Integration (for Ableton)
# ============================================================

class ClipLauncherArranger:
    """
    Map arrangement sections to Ableton clip launcher scenes.
    Enables live triggering of arrangement sections.
    """

    def __init__(self, mcp_connection):
        self.connection = mcp_connection

    def create_scenes_from_analysis(self, analysis: ArrangementAnalysis) -> List[Dict]:
        """Create Ableton scenes for each detected section."""
        scenes = []
        for i, section in enumerate(analysis.sections):
            scene = {
                "index": i,
                "name": f"{section.name.title()} ({section.start_bar:.0f}-{section.end_bar:.0f})",
                "section": section.name,
                "start_bar": section.start_bar,
                "end_bar": section.end_bar,
                "tracks_to_fire": section.key_tracks,
            }
            scenes.append(scene)
        return scenes

    def apply_to_ableton(self, scenes: List[Dict]) -> Dict:
        """Create scenes in Ableton and assign clips."""
        results = []
        for scene in scenes:
            try:
                # Create scene
                self.connection.send_command("create_scene", {"index": scene["index"]})
                # Fire clips for this section
                for track_name in scene["tracks_to_fire"]:
                    # Find track index by name
                    tracks_result = self.connection.send_command("get_tracks", {})
                    track_idx = None
                    for t in tracks_result.get("tracks", []):
                        if t["name"].lower() == track_name.lower():
                            track_idx = t["index"]
                            break
                    if track_idx is not None:
                        # Find clip for this section (simplified)
                        self.connection.send_command("fire_clip", {
                            "track_index": track_idx,
                            "clip_index": scene["index"]
                        })
                results.append({"scene": scene["name"], "success": True})
            except Exception as e:
                results.append({"scene": scene["name"], "success": False, "error": str(e)})
        return {"scenes_created": results}


# ============================================================
# Convenience Functions
# ============================================================

def analyze_arrangement(
    stem_paths: Dict[str, str],
    tempo: float = 120,
) -> ArrangementAnalysis:
    """Quick arrangement analysis from stems."""
    analyzer = ArrangementAnalyzer()
    return analyzer.analyze_from_stems(stem_paths, tempo)


def suggest_arrangement(
    stem_paths: Dict[str, str],
    tempo: float = 120,
) -> List[Dict]:
    """Quick arrangement suggestions."""
    result = analyze_arrangement(stem_paths, tempo)
    return result.suggestions


def generate_arrangement_template(
    genre: str,
    length_bars: int = 64,
    include_tracks: bool = True,
) -> Dict:
    """Quick template generation."""
    generator = ArrangementTemplateGenerator()
    template = generator.get_template(genre)
    if not template:
        return {"error": f"Unknown genre: {genre}"}

    # Scale to requested length
    if template.total_bars != length_bars:
        scale = length_bars / template.total_bars
        scaled_structure = []
        for s in template.structure:
            scaled_bars = max(4, int(s[1] * scale))
            scaled_structure.append((s[0], scaled_bars, s[2]))
        # Adjust last to match exactly
        if sum(s[1] for s in scaled_structure) != length_bars:
            scaled_structure[-1] = (scaled_structure[-1][0], 
                scaled_structure[-1][1] + length_bars - sum(s[1] for s in scaled_structure),
                scaled_structure[-1][2])
        template.structure = scaled_structure
        template.total_bars = length_bars

    return template.to_dict()


def generate_structure(
    genre: str,
    bpm: int = 120,
    key: str = "C",
    length_bars: int = 64,
) -> Dict:
    """Generate full arrangement structure."""
    template = generate_arrangement_template(genre, length_bars)

    if "error" in template:
        return template

    return {
        "genre": genre,
        "bpm": bpm,
        "key": key,
        "total_bars": length_bars,
        "sections": template["structure"],
        "energy_curve": template["energy_curve"],
        "track_roles": template["track_roles"],
        "clip_launcher_plan": {
            "scenes": [s["name"] for s in template["structure"]],
            "bars_per_scene": [s["bars"] for s in template["structure"]],
        },
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python arrangement_assistant.py <genre> | <stem1.wav> <stem2.wav> ...")
        sys.exit(1)

    if sys.argv[1] in ARRANGEMENT_TEMPLATES:
        # Show template
        template = get_arrangement_template(sys.argv[1])
        print(f"Genre: {template.name} ({template.genre})")
        print(f"Tempo: {template.tempo} BPM")
        print(f"Total Bars: {template.total_bars}")
        print(f"Energy Curve: {[f'{e:.1f}' for e in template.energy_curve]}")
        print("\nStructure:")
        for s in template.structure:
            print(f"  {s[0]:12s} {s[1]:3d} bars - {s[2]}")
        print("\nTrack Roles:")
        for track, sections in template.track_roles.items():
            print(f"  {track}: {', '.join(sections)}")
    else:
        # Analyze stems
        stem_paths = {Path(p).stem: p for p in sys.argv[1:]}
        result = analyze_arrangement(stem_paths)
        print(f"Total Bars: {result.total_bars:.0f}")
        print(f"Tempo: {result.tempo}")
        print(f"Genre: {result.genre}")
        print(f"\nSections ({len(result.sections)}):")
        for s in result.sections:
            print(f"  {s.start_bar:5.0f}-{s.end_bar:5.0f} ({s.length_bars:4.0f} bars) "
                  f"{s.name:10s} energy={s.energy:.2f} density={s.density:.2f} "
                  f"tracks={', '.join(s.key_tracks)}")
        print(f"\nIssues ({len(result.issues)}):")
        for issue in result.issues:
            print(f"  [{issue['severity']}] {issue['message']}")
        print(f"\nSuggestions ({len(result.suggestions)}):")
        for s in result.suggestions:
            print(f"  [{s['priority']}] {s['message']} -> {s['suggestion']}")