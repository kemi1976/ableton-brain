#!/usr/bin/env python3
"""
Harmonic Analysis Module
Chord/key/scale detection from audio/MIDI + chord suggestion engine.
Uses librosa for audio analysis, music21 for music theory, Basic Pitch for MIDI extraction.
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
    import music21
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False
    music21 = None

try:
    import pretty_midi
    PRETTY_MIDI_AVAILABLE = True
except ImportError:
    PRETTY_MIDI_AVAILABLE = False
    pretty_midi = None

try:
    from basic_pitch.inference import predict
    from basic_pitch import ICASSP_2022_MODEL_PATH
    BASIC_PITCH_AVAILABLE = True
except ImportError:
    BASIC_PITCH_AVAILABLE = False


# ============================================================
# Data Classes
# ============================================================

@dataclass
class Chord:
    """Represents a detected chord."""
    root: str              # e.g., "C", "F#", "Bb"
    quality: str           # e.g., "major", "minor", "diminished", "augmented", "7", "maj7", "m7"
    bass: Optional[str] = None  # For slash chords
    start_time: float = 0.0
    end_time: float = 0.0
    confidence: float = 0.0
    roman_numeral: Optional[str] = None  # Relative to key

    @property
    def symbol(self) -> str:
        """Chord symbol (e.g., 'Cmaj7', 'F#m7', 'G/B')."""
        qual_map = {
            "major": "", "minor": "m", "diminished": "dim", "augmented": "aug",
            "7": "7", "maj7": "maj7", "m7": "m7", "m7b5": "m7b5", "dim7": "dim7",
        }
        qual = qual_map.get(self.quality, self.quality)
        symbol = f"{self.root}{qual}"
        if self.bass:
            symbol += f"/{self.bass}"
        return symbol

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "quality": self.quality,
            "bass": self.bass,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "confidence": self.confidence,
            "symbol": self.symbol,
            "roman_numeral": self.roman_numeral,
        }


@dataclass
class HarmonicAnalysisResult:
    """Complete harmonic analysis of audio/MIDI."""
    key: Optional[str] = None          # e.g., "C", "F#"
    scale: Optional[str] = None        # e.g., "major", "minor", "dorian"
    chords: List[Chord] = field(default_factory=list)
    tempo: float = 120.0
    time_signature: str = "4/4"
    chord_changes_per_bar: float = 1.0
    overall_confidence: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "scale": self.scale,
            "chords": [c.to_dict() for c in self.chords],
            "tempo": self.tempo,
            "time_signature": self.time_signature,
            "chord_changes_per_bar": self.chord_changes_per_bar,
            "overall_confidence": self.overall_confidence,
            "error": self.error,
        }


@dataclass
class ChordSuggestion:
    """A suggested next chord with reasoning."""
    chord: Chord
    probability: float
    reason: str
    voice_leading_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "chord": self.chord.to_dict(),
            "probability": self.probability,
            "reason": self.reason,
            "voice_leading_score": self.voice_leading_score,
        }


# ============================================================
# Chord Suggestion Engine
# ============================================================

class ChordSuggestionEngine:
    """
    Suggests next chords based on:
    - Music theory (circle of fifths, functional harmony)
    - Statistical patterns from common practice
    - Voice leading principles
    """

    # Common chord progressions by genre (simplified)
    GENRE_PROGRESSIONS = {
        "pop": [
            ["I", "V", "vi", "IV"],      # Axis of Awesome
            ["I", "IV", "V", "IV"],      # Classic pop
            ["vi", "IV", "I", "V"],      # Pop punk
            ["I", "V", "IV", "V"],       # Simple
        ],
        "jazz": [
            ["ii", "V", "I", "I"],       # ii-V-I
            ["iii", "vi", "ii", "V"],    # Circle of fifths
            ["I", "vi", "ii", "V"],      # Turnaround
            ["IV", "iv", "I", "V"],      # Backdoor
        ],
        "edm": [
            ["i", "VI", "III", "VII"],   # Minor plum
            ["i", "iv", "V", "i"],       # Minor with major V
            ["VI", "VII", "i", "i"],     # Epic
        ],
        "rock": [
            ["I", "bVII", "IV", "I"],    # Mixolydian
            ["I", "IV", "V", "V"],       # Blues rock
            ["i", "bVI", "bVII", "i"],   # Minor rock
        ],
        "lofi": [
            ["I", "iii", "vi", "IV"],    # Nostalgic
            ["ii", "V", "I", "vi"],      # Jazzy
        ],
    }

    # Chord transition probabilities (simplified Markov chain)
    TRANSITION_WEIGHTS = {
        "I":   {"IV": 0.3, "V": 0.25, "vi": 0.2, "ii": 0.1, "iii": 0.05, "I": 0.1},
        "ii":  {"V": 0.4, "IV": 0.2, "vi": 0.15, "I": 0.1, "iii": 0.1, "vii": 0.05},
        "iii": {"vi": 0.35, "IV": 0.2, "ii": 0.15, "I": 0.1, "V": 0.1, "vii": 0.1},
        "IV":  {"V": 0.3, "I": 0.25, "vi": 0.15, "ii": 0.1, "IV": 0.1, "iii": 0.1},
        "V":   {"I": 0.4, "vi": 0.2, "IV": 0.15, "V": 0.1, "ii": 0.1, "iii": 0.05},
        "vi":  {"IV": 0.25, "ii": 0.2, "V": 0.2, "I": 0.15, "iii": 0.1, "vi": 0.1},
        "vii": {"I": 0.5, "iii": 0.2, "vi": 0.15, "V": 0.15},
    }

    # Quality mappings for roman numerals
    MAJOR_QUALITIES = {
        "I": "major", "ii": "minor", "iii": "minor", "IV": "major",
        "V": "major", "vi": "minor", "vii": "diminished"
    }
    MINOR_QUALITIES = {
        "i": "minor", "ii": "diminished", "III": "major", "iv": "minor",
        "v": "minor", "VI": "major", "VII": "major"
    }

    def __init__(self, key: str = "C", scale: str = "major"):
        self.set_key(key, scale)

    def set_key(self, key: str, scale: str = "major"):
        """Set the current key and scale."""
        self.key = key
        self.scale = scale.lower()
        self.is_minor = self.scale in ("minor", "aeolian", "harmonic_minor", "melodic_minor")
        self._build_chord_map()

    def _build_chord_map(self):
        """Build chord map for current key."""
        if MUSIC21_AVAILABLE:
            try:
                if self.is_minor:
                    ks = music21.key.Key(self.key, music21.key.Key.MINOR)
                else:
                    ks = music21.key.Key(self.key, music21.key.Key.MAJOR)
                self.key_obj = ks
            except Exception:
                self.key_obj = None
        else:
            self.key_obj = None

    def _roman_to_chord(self, roman: str) -> Chord:
        """Convert roman numeral to Chord object."""
        # Simplified - in practice use music21
        root_map = {
            "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
            "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
            "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
        }

        # This is simplified - real implementation uses music21
        # For now return a basic chord
        return Chord(root=self.key, quality="major")

    def suggest_next_chords(
        self,
        current_progression: List[str],
        num_suggestions: int = 5,
        genre: Optional[str] = None,
    ) -> List[ChordSuggestion]:
        """
        Suggest next chords based on current progression.

        Args:
            current_progression: List of roman numerals (e.g., ["I", "V", "vi"])
            num_suggestions: Number of suggestions to return
            genre: Genre hint for style-appropriate suggestions

        Returns:
            List of ChordSuggestion objects
        """
        if not current_progression:
            # No context - suggest common starting chords
            starters = ["I", "vi", "IV", "ii"]
            return [self._make_suggestion(r, 0.25, "Common starting chord") for r in starters]

        last_chord = current_progression[-1].upper()

        # Get transition weights
        weights = self.TRANSITION_WEIGHTS.get(last_chord, {"I": 1.0})

        # Boost genre-specific progressions
        if genre and genre in self.GENRE_PROGRESSIONS:
            for prog in self.GENRE_PROGRESSIONS[genre]:
                # Find where current progression matches
                for i in range(len(prog) - 1):
                    if prog[:i+1] == [c.upper() for c in current_progression[-(i+1):]]:
                        next_chord = prog[i+1]
                        weights[next_chord] = weights.get(next_chord, 0) + 0.3

        # Normalize and create suggestions
        total = sum(weights.values())
        suggestions = []

        for roman, weight in sorted(weights.items(), key=lambda x: -x[1])[:num_suggestions]:
            prob = weight / total
            chord = self._roman_to_pitch_class(roman)
            reason = self._get_reason(last_chord, roman, genre)
            vl_score = self._voice_leading_score(last_chord, roman)

            suggestions.append(ChordSuggestion(
                chord=chord,
                probability=prob,
                reason=reason,
                voice_leading_score=vl_score,
            ))

        return suggestions

    def _roman_to_pitch_class(self, roman: str) -> Chord:
        """Convert roman numeral to actual chord in current key."""
        # Simplified - uses music21 if available
        if self.key_obj and MUSIC21_AVAILABLE:
            try:
                rn = music21.roman.RomanNumeral(roman, self.key_obj)
                chord_obj = rn.chord
                root = chord_obj.root().name
                quality = self._chord_quality_to_string(chord_obj)
                return Chord(root=root, quality=quality)
            except Exception:
                pass

        # Fallback: manual calculation
        scale_degrees = self._get_scale_degrees()
        roman_clean = roman.replace("♭", "b").replace("♯", "#")
        degree = self._roman_to_degree(roman_clean)

        if degree and degree in scale_degrees:
            root_pc = scale_degrees[degree]
            root_name = self._pc_to_name(root_pc)
            quality = self.MAJOR_QUALITIES.get(roman_clean, "major") if not self.is_minor \
                      else self.MINOR_QUALITIES.get(roman_clean, "minor")
            return Chord(root=root_name, quality=quality)

        return Chord(root=self.key, quality="major")

    def _get_scale_degrees(self) -> Dict[int, int]:
        """Get pitch classes for scale degrees 1-7."""
        # Major scale intervals
        major_intervals = [0, 2, 4, 5, 7, 9, 11]
        # Natural minor
        minor_intervals = [0, 2, 3, 5, 7, 8, 10]

        intervals = minor_intervals if self.is_minor else major_intervals
        key_pc = self._name_to_pc(self.key)

        return {i+1: (key_pc + intervals[i]) % 12 for i in range(7)}

    def _roman_to_degree(self, roman: str) -> Optional[int]:
        """Convert roman numeral to scale degree (1-7)."""
        roman = roman.upper()
        base = roman[0] if roman else ""
        degree_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}
        return degree_map.get(base)

    def _name_to_pc(self, name: str) -> int:
        """Note name to pitch class."""
        map_ = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
                "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
                "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
        return map_.get(name, 0)

    def _pc_to_name(self, pc: int) -> str:
        """Pitch class to note name (sharps)."""
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return names[pc % 12]

    def _chord_quality_to_string(self, chord) -> str:
        """Music21 chord quality to our string."""
        q = str(chord.quality).lower()
        if "major" in q and "minor" not in q:
            return "major"
        elif "minor" in q:
            return "minor"
        elif "diminished" in q:
            return "diminished"
        elif "augmented" in q:
            return "augmented"
        return q

    def _get_reason(self, from_chord: str, to_chord: str, genre: Optional[str]) -> str:
        """Generate human-readable reason."""
        reasons = {
            ("I", "V"): "Dominant pulls to tonic",
            ("V", "I"): "Authentic cadence",
            ("IV", "V"): "Predominant to dominant",
            ("ii", "V"): "ii-V progression",
            ("vi", "IV"): "Deceptive motion",
            ("I", "vi"): "Relative minor",
            ("IV", "iv"): "Modal mixture (backdoor)",
        }
        key = (from_chord, to_chord)
        if key in reasons:
            return reasons[key]
        if genre and genre in self.GENRE_PROGRESSIONS:
            return f"Common in {genre}"
        return "Theory-based suggestion"

    def _voice_leading_score(self, from_chord: str, to_chord: str) -> float:
        """Score voice leading smoothness (0-1)."""
        # Simplified: prefer chords with common tones
        from_deg = self._roman_to_degree(from_chord)
        to_deg = self._roman_to_degree(to_chord)

        if not from_deg or not to_deg:
            return 0.5

        # Circle of fifths distance
        diff = abs(from_deg - to_deg)
        diff = min(diff, 7 - diff)

        # Closer on circle = better voice leading
        return 1.0 - (diff / 3.5)


# ============================================================
# Harmonic Analyzer
# ============================================================

class HarmonicAnalyzer:
    """
    Analyze harmony from audio or MIDI.
    Combines librosa chroma, Basic Pitch MIDI extraction, and music21 theory.
    """

    def __init__(self):
        self.suggestion_engine = ChordSuggestionEngine()

    def analyze_audio_file(self, audio_path: str) -> HarmonicAnalysisResult:
        """Analyze harmony from audio file."""
        if not LIBROSA_AVAILABLE:
            return HarmonicAnalysisResult(error="librosa not available")

        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=None)

            # Tempo
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            tempo = float(tempo)

            # Chroma for key detection
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)

            # Key detection using Krumhansl-Schmuckler
            key, scale = self._detect_key_from_chroma(chroma_mean)

            # Chord segmentation
            chords = self._segment_chords(y, sr, beats, chroma, key, scale)

            # Set suggestion engine key
            if key:
                self.suggestion_engine.set_key(key, scale)

            return HarmonicAnalysisResult(
                key=key,
                scale=scale,
                chords=chords,
                tempo=tempo,
                time_signature="4/4",
                chord_changes_per_bar=len(chords) / max(1, len(beats) / 4),
                overall_confidence=np.mean([c.confidence for c in chords]) if chords else 0,
            )

        except Exception as e:
            return HarmonicAnalysisResult(error=str(e))

    def analyze_midi_file(self, midi_path: str) -> HarmonicAnalysisResult:
        """Analyze harmony from MIDI file."""
        if not PRETTY_MIDI_AVAILABLE:
            return HarmonicAnalysisResult(error="pretty_midi not available")

        try:
            midi = pretty_midi.PrettyMIDI(midi_path)

            # Tempo
            tempo = midi.estimate_tempo()

            # Extract all notes
            all_notes = []
            for instrument in midi.instruments:
                if not instrument.is_drum:
                    for note in instrument.notes:
                        all_notes.append({
                            "pitch": note.pitch,
                            "start": note.start,
                            "end": note.end,
                            "velocity": note.velocity,
                        })

            if not all_notes:
                return HarmonicAnalysisResult(error="No melodic notes found")

            # Sort by time
            all_notes.sort(key=lambda n: n["start"])

            # Segment into time windows and detect chords
            chords = self._detect_chords_from_notes(all_notes)

            # Detect key from chord progression
            key, scale = self._detect_key_from_chords(chords)

            if key:
                self.suggestion_engine.set_key(key, scale)

            return HarmonicAnalysisResult(
                key=key,
                scale=scale,
                chords=chords,
                tempo=tempo,
                time_signature="4/4",
                chord_changes_per_bar=len(chords) / max(1, tempo / 60 * 4),
                overall_confidence=np.mean([c.confidence for c in chords]) if chords else 0,
            )

        except Exception as e:
            return HarmonicAnalysisResult(error=str(e))

    def analyze_audio_with_basic_pitch(self, audio_path: str) -> HarmonicAnalysisResult:
        """Analyze using Basic Pitch for MIDI extraction then harmonic analysis."""
        if not BASIC_PITCH_AVAILABLE:
            return HarmonicAnalysisResult(error="basic-pitch not available")

        try:
            # Extract MIDI using Basic Pitch
            model_output, midi_data, note_events = predict(
                audio_path,
                model_path=ICASSP_2022_MODEL_PATH,
            )

            # Convert to notes format
            all_notes = []
            for instrument in midi_data.instruments:
                if not instrument.is_drum:
                    for note in instrument.notes:
                        all_notes.append({
                            "pitch": note.pitch,
                            "start": note.start,
                            "end": note.end,
                            "velocity": note.velocity,
                        })

            all_notes.sort(key=lambda n: n["start"])

            # Detect chords
            chords = self._detect_chords_from_notes(all_notes)

            # Detect key
            key, scale = self._detect_key_from_chords(chords)

            # Tempo from MIDI
            tempo = midi_data.estimate_tempo()

            if key:
                self.suggestion_engine.set_key(key, scale)

            return HarmonicAnalysisResult(
                key=key,
                scale=scale,
                chords=chords,
                tempo=tempo,
                time_signature="4/4",
                chord_changes_per_bar=len(chords) / max(1, tempo / 60 * 4),
                overall_confidence=np.mean([c.confidence for c in chords]) if chords else 0,
            )

        except Exception as e:
            return HarmonicAnalysisResult(error=str(e))

    def suggest_chords(
        self,
        current_progression: List[str],
        num_suggestions: int = 5,
        genre: Optional[str] = None,
    ) -> List[ChordSuggestion]:
        """Suggest next chords for a progression."""
        return self.suggestion_engine.suggest_next_chords(
            current_progression, num_suggestions, genre
        )

    def generate_progression(
        self,
        key: str,
        scale: str,
        length: int = 8,
        genre: Optional[str] = None,
    ) -> List[Chord]:
        """Generate a full chord progression."""
        self.suggestion_engine.set_key(key, scale)

        # Start with I or i
        start = "i" if scale.lower() in ("minor", "aeolian") else "I"
        progression = [start]

        for _ in range(length - 1):
            suggestions = self.suggestion_engine.suggest_next_chords(
                progression, num_suggestions=3, genre=genre
            )
            if suggestions:
                # Pick highest probability
                next_roman = self._chord_to_roman(suggestions[0].chord)
                progression.append(next_roman)
            else:
                break

        # Convert to Chord objects
        return [self.suggestion_engine._roman_to_pitch_class(r) for r in progression]

    def _chord_to_roman(self, chord: Chord) -> str:
        """Convert Chord back to roman numeral (simplified)."""
        # This is simplified - real implementation would use music21
        return "I"  # Placeholder

    # --- Internal Analysis Methods ---

    def _detect_key_from_chroma(self, chroma: np.ndarray) -> Tuple[Optional[str], Optional[str]]:
        """Detect key from chroma vector using Krumhansl-Schmuckler."""
        key_names = ["C", "C#", "D", "D#", "E", "F",
                     "F#", "G", "G#", "A", "A#", "B"]

        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                                  2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                                  2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

        best_corr = -1
        best_key = None
        best_mode = None

        for i in range(12):
            major_rot = np.roll(major_profile, i)
            minor_rot = np.roll(minor_profile, i)

            major_corr = np.corrcoef(chroma, major_rot)[0, 1]
            minor_corr = np.corrcoef(chroma, minor_rot)[0, 1]

            if major_corr > best_corr:
                best_corr = major_corr
                best_key = key_names[i]
                best_mode = "major"

            if minor_corr > best_corr:
                best_corr = minor_corr
                best_key = key_names[i]
                best_mode = "minor"

        return best_key, best_mode

    def _detect_key_from_chords(self, chords: List[Chord]) -> Tuple[Optional[str], Optional[str]]:
        """Detect key from chord progression."""
        if not chords:
            return None, None

        # Count root occurrences weighted by duration/confidence
        root_counts = {}
        for chord in chords:
            weight = chord.confidence * (chord.end_time - chord.start_time)
            root = chord.root
            root_counts[root] = root_counts.get(root, 0) + weight

        if not root_counts:
            return None, None

        # Most common root is likely tonic
        tonic = max(root_counts, key=root_counts.get)

        # Check if major or minor by chord qualities
        major_count = sum(1 for c in chords if c.root == tonic and c.quality == "major")
        minor_count = sum(1 for c in chords if c.root == tonic and c.quality == "minor")

        scale = "major" if major_count >= minor_count else "minor"
        return tonic, scale

    def _segment_chords(
        self,
        y: np.ndarray,
        sr: int,
        beats: np.ndarray,
        chroma: np.ndarray,
        key: Optional[str],
        scale: Optional[str],
    ) -> List[Chord]:
        """Segment audio into chords based on beat boundaries."""
        chords = []

        # Use beat positions as chord boundaries
        beat_times = librosa.frames_to_time(beats, sr=sr)

        for i in range(len(beat_times) - 1):
            start = beat_times[i]
            end = beat_times[i + 1]

            # Get chroma for this segment
            start_frame = int(start * sr / 512)  # Approximate hop length
            end_frame = int(end * sr / 512)
            end_frame = min(end_frame, chroma.shape[1])

            if end_frame <= start_frame:
                continue

            seg_chroma = np.mean(chroma[:, start_frame:end_frame], axis=1)

            # Detect chord from chroma
            chord = self._chord_from_chroma(seg_chroma, key, scale, start, end)
            if chord:
                chords.append(chord)

        return chords

    def _detect_chords_from_notes(self, notes: List[dict]) -> List[Chord]:
        """Detect chords from note list (MIDI)."""
        if not notes:
            return []

        # Group notes by time windows (e.g., 0.5s windows)
        window_size = 0.5
        chords = []

        current_window = []
        window_start = notes[0]["start"]

        for note in notes:
            if note["start"] >= window_start + window_size:
                # Process current window
                if current_window:
                    chord = self._chord_from_notes(current_window, window_start, window_start + window_size)
                    if chord:
                        chords.append(chord)

                # Start new window
                window_start = note["start"]
                current_window = [note]
            else:
                current_window.append(note)

        # Process last window
        if current_window:
            chord = self._chord_from_notes(current_window, window_start, window_start + window_size)
            if chord:
                chords.append(chord)

        return chords

    def _chord_from_notes(
        self,
        notes: List[dict],
        start_time: float,
        end_time: float,
    ) -> Optional[Chord]:
        """Identify chord from a set of notes."""
        if not notes:
            return None

        # Get pitch classes
        pitch_classes = [n["pitch"] % 12 for n in notes]
        velocities = [n["velocity"] for n in notes]

        # Weight by velocity
        pc_weights = np.zeros(12)
        for pc, vel in zip(pitch_classes, velocities):
            pc_weights[pc] += vel / 127.0

        # Find best matching chord template
        chord_templates = self._get_chord_templates()
        best_chord = None
        best_score = 0

        for root in range(12):
            for quality, template in chord_templates.items():
                # Rotate template to root
                rotated = np.roll(template, root)
                score = np.dot(pc_weights, rotated) / (np.sum(pc_weights) + 1e-6)

                if score > best_score:
                    best_score = score
                    root_name = self._pc_to_name(root)
                    best_chord = Chord(
                        root=root_name,
                        quality=quality,
                        start_time=start_time,
                        end_time=end_time,
                        confidence=min(score, 1.0),
                    )

        return best_chord

    def _chord_from_chroma(
        self,
        chroma: np.ndarray,
        key: Optional[str],
        scale: Optional[str],
        start_time: float,
        end_time: float,
    ) -> Optional[Chord]:
        """Identify chord from chroma vector."""
        chord_templates = self._get_chord_templates()
        best_chord = None
        best_score = 0

        for root in range(12):
            for quality, template in chord_templates.items():
                rotated = np.roll(template, root)
                score = np.dot(chroma, rotated) / (np.sum(chroma) + 1e-6)

                if score > best_score:
                    best_score = score
                    root_name = self._pc_to_name(root)
                    best_chord = Chord(
                        root=root_name,
                        quality=quality,
                        start_time=start_time,
                        end_time=end_time,
                        confidence=min(score, 1.0),
                    )

        return best_chord

    def _get_chord_templates(self) -> Dict[str, np.ndarray]:
        """Chord templates as pitch class vectors."""
        return {
            "major":        np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0]),
            "minor":        np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0]),
            "diminished":   np.array([1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0]),
            "augmented":    np.array([1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]),
            "7":            np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0]),
            "maj7":         np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1]),
            "m7":           np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0]),
            "m7b5":         np.array([1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0]),
            "dim7":         np.array([1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0]),
        }

    def _pc_to_name(self, pc: int) -> str:
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return names[pc % 12]


# ============================================================
# Convenience Functions
# ============================================================

def analyze_harmony_audio(audio_path: str) -> HarmonicAnalysisResult:
    """Quick audio harmonic analysis."""
    analyzer = HarmonicAnalyzer()
    return analyzer.analyze_audio_file(audio_path)


def analyze_harmony_midi(midi_path: str) -> HarmonicAnalysisResult:
    """Quick MIDI harmonic analysis."""
    analyzer = HarmonicAnalyzer()
    return analyzer.analyze_midi_file(midi_path)


def analyze_harmony_basic_pitch(audio_path: str) -> HarmonicAnalysisResult:
    """Quick analysis using Basic Pitch."""
    analyzer = HarmonicAnalyzer()
    return analyzer.analyze_audio_with_basic_pitch(audio_path)


def suggest_next_chords(
    progression: List[str],
    key: str = "C",
    scale: str = "major",
    genre: Optional[str] = None,
    num_suggestions: int = 5,
) -> List[ChordSuggestion]:
    """Quick chord suggestion."""
    engine = ChordSuggestionEngine(key, scale)
    return engine.suggest_next_chords(progression, num_suggestions, genre)


def generate_chord_progression(
    key: str,
    scale: str,
    length: int = 8,
    genre: Optional[str] = None,
) -> List[Chord]:
    """Quick progression generation."""
    analyzer = HarmonicAnalyzer()
    return analyzer.generate_progression(key, scale, length, genre)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python harmonic_analysis.py <audio_or_midi_file>")
        sys.exit(1)

    file_path = sys.argv[1]

    print(f"Analyzing {file_path}...")
    analyzer = HarmonicAnalyzer()

    if file_path.lower().endswith((".mid", ".midi")):
        result = analyzer.analyze_midi_file(file_path)
    else:
        result = analyzer.analyze_audio_with_basic_pitch(file_path)

    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Key: {result.key} {result.scale}")
        print(f"Tempo: {result.tempo:.1f} BPM")
        print(f"Chords ({len(result.chords)}):")
        for c in result.chords:
            print(f"  {c.start_time:.2f}-{c.end_time:.2f}: {c.symbol} (conf: {c.confidence:.2f})")

        # Suggest next chords
        progression = [c.symbol for c in result.chords[-4:]]
        suggestions = analyzer.suggest_chords(progression)
        print("\nNext chord suggestions:")
        for s in suggestions[:5]:
            print(f"  {s.chord.symbol} ({s.probability:.0%}) - {s.reason}")