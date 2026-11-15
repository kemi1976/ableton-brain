#!/usr/bin/env python3
"""
Audio-to-MIDI Conversion Module
Integrates Spotify's Basic Pitch (ONNX) for polyphonic audio transcription.
Supports melody, harmony, and drum conversion to MIDI clips.
"""

from __future__ import annotations

import os
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple

import numpy as np

# Suppress ONNX/TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore", category=UserWarning)

try:
    from basic_pitch.inference import predict
    from basic_pitch import ICASSP_2022_MODEL_PATH
    BASIC_PITCH_AVAILABLE = True
except ImportError:
    BASIC_PITCH_AVAILABLE = False
    predict = None
    ICASSP_2022_MODEL_PATH = None

try:
    import pretty_midi
    PRETTY_MIDI_AVAILABLE = True
except ImportError:
    PRETTY_MIDI_AVAILABLE = False
    pretty_midi = None

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    librosa = None


@dataclass
class MidiConversionResult:
    """Result of audio-to-MIDI conversion."""
    midi_path: str
    notes: List[dict]  # [{pitch, start, end, velocity, instrument}]
    tempo: float
    key: Optional[str] = None
    scale: Optional[str] = None
    error: Optional[str] = None


class AudioToMidiConverter:
    """
    Wrapper around Spotify's Basic Pitch for audio-to-MIDI conversion.
    Supports polyphonic transcription with pitch bend detection.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        onset_threshold: float = 0.5,
        frame_threshold: float = 0.3,
        minimum_note_length: float = 0.058,
        minimum_frequency: float = 27.5,
        maximum_frequency: float = 4186.0,
        multiple_pitch_bends: bool = False,
        melodia_trick: bool = True,
    ):
        """
        Initialize the converter.

        Args:
            model_path: Path to Basic Pitch ONNX model (uses default if None)
            onset_threshold: Threshold for note onset detection (0-1)
            frame_threshold: Threshold for frame detection (0-1)
            minimum_note_length: Minimum note length in seconds
            minimum_frequency: Minimum frequency in Hz
            maximum_frequency: Maximum frequency in Hz
            multiple_pitch_bends: Enable multiple pitch bends per note
            melodia_trick: Use Melodia trick for better pitch estimation
        """
        self.model_path = model_path or ICASSP_2022_MODEL_PATH
        self.onset_threshold = onset_threshold
        self.frame_threshold = frame_threshold
        self.minimum_note_length = minimum_note_length
        self.minimum_frequency = minimum_frequency
        self.maximum_frequency = maximum_frequency
        self.multiple_pitch_bends = multiple_pitch_bends
        self.melodia_trick = melodia_trick

        if not BASIC_PITCH_AVAILABLE:
            raise ImportError(
                "basic-pitch not installed. Install with: "
                "pip install basic-pitch @ git+https://github.com/spotify/basic-pitch"
            )
        if not PRETTY_MIDI_AVAILABLE:
            raise ImportError("pretty_midi not installed. Install with: pip install pretty_midi")

    def convert_audio_file(
        self,
        audio_path: str,
        output_midi_path: Optional[str] = None,
        instrument_program: int = 0,
    ) -> MidiConversionResult:
        """
        Convert an audio file to MIDI.

        Args:
            audio_path: Path to input audio file (WAV, MP3, etc.)
            output_midi_path: Output MIDI file path (auto-generated if None)
            instrument_program: MIDI program number (0=Acoustic Grand Piano)

        Returns:
            MidiConversionResult with MIDI path and note data
        """
        if not os.path.exists(audio_path):
            return MidiConversionResult(
                midi_path="",
                notes=[],
                tempo=120.0,
                error=f"Audio file not found: {audio_path}"
            )

        # Generate output path if not provided
        if output_midi_path is None:
            audio_stem = Path(audio_path).stem
            output_midi_path = str(Path(audio_path).parent / f"{audio_stem}_basic_pitch.mid")

        try:
            # Run Basic Pitch inference
            model_output, midi_data, note_events = predict(
                audio_path,
                model_path=self.model_path,
                onset_threshold=self.onset_threshold,
                frame_threshold=self.frame_threshold,
                minimum_note_length=self.minimum_note_length,
                minimum_frequency=self.minimum_frequency,
                maximum_frequency=self.maximum_frequency,
                multiple_pitch_bends=self.multiple_pitch_bends,
                melodia_trick=self.melodia_trick,
            )

            # Set instrument program
            for instrument in midi_data.instruments:
                instrument.program = instrument_program

            # Save MIDI
            midi_data.write(output_midi_path)

            # Extract note data for return
            notes = []
            for instrument in midi_data.instruments:
                for note in instrument.notes:
                    notes.append({
                        "pitch": note.pitch,
                        "start": note.start,
                        "end": note.end,
                        "velocity": note.velocity,
                        "instrument": instrument.program,
                    })

            # Estimate tempo from MIDI
            tempo = self._estimate_tempo(midi_data)

            # Detect key/scale if librosa available
            key = None
            scale = None
            if LIBROSA_AVAILABLE and notes:
                key, scale = self._detect_key_from_notes(notes)

            return MidiConversionResult(
                midi_path=output_midi_path,
                notes=notes,
                tempo=tempo,
                key=key,
                scale=scale,
            )

        except Exception as e:
            return MidiConversionResult(
                midi_path="",
                notes=[],
                tempo=120.0,
                error=str(e)
            )

    def convert_audio_array(
        self,
        audio: np.ndarray,
        sample_rate: int,
        output_midi_path: Optional[str] = None,
        instrument_program: int = 0,
    ) -> MidiConversionResult:
        """
        Convert audio array to MIDI via temporary file.

        Args:
            audio: Audio signal as numpy array
            sample_rate: Sample rate in Hz
            output_midi_path: Output MIDI path
            instrument_program: MIDI program number

        Returns:
            MidiConversionResult
        """
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            import soundfile as sf
            sf.write(tmp.name, audio, sample_rate)
            try:
                return self.convert_audio_file(tmp.name, output_midi_path, instrument_program)
            finally:
                os.unlink(tmp.name)

    def convert_drums(
        self,
        audio_path: str,
        output_midi_path: Optional[str] = None,
    ) -> MidiConversionResult:
        """
        Convert drums audio to MIDI with standard drum mapping.

        Drum mapping (GM standard):
        36 = Kick, 38 = Snare, 42 = Closed HH, 46 = Open HH,
        39 = Clap, 49 = Crash, 51 = Ride, 45 = Tom
        """
        # Use lower thresholds for percussion
        result = self.convert_audio_file(
            audio_path,
            output_midi_path,
            instrument_program=0,  # Piano program, but we'll remap
        )

        if result.error:
            return result

        # Remap pitches to GM drum map
        drum_map = {
            # Basic Pitch often detects these as low notes for kick
            24: 36, 25: 36, 26: 36, 27: 36, 28: 36, 29: 36, 30: 36, 31: 36,
            32: 36, 33: 36, 34: 36, 35: 36,  # C1-B1 -> Kick
            36: 36,  # C2 -> Kick
            37: 38, 38: 38, 39: 38,  # C#2-D#2 -> Snare
            40: 38, 41: 38, 42: 42,  # E2-F#2 -> Snare/CHH
            43: 46, 44: 46,  # G2-G#2 -> OHH
            45: 45, 46: 45, 47: 45, 48: 45,  # A2-C3 -> Toms
        }

        # Apply remapping to notes
        for note in result.notes:
            original_pitch = note["pitch"]
            note["pitch"] = drum_map.get(original_pitch, 36)  # Default to kick
            note["instrument"] = 128  # Drum channel (channel 10 in 0-indexed)

        # Rewrite MIDI with remapped notes
        if PRETTY_MIDI_AVAILABLE:
            midi_data = pretty_midi.PrettyMIDI(result.midi_path)
            for instrument in midi_data.instruments:
                instrument.program = 0  # Standard kit
                instrument.is_drum = True
                for note in instrument.notes:
                    original_pitch = note.pitch
                    note.pitch = drum_map.get(original_pitch, 36)
            midi_data.write(result.midi_path)

        return result

    def _estimate_tempo(self, midi_data) -> float:
        """Estimate tempo from MIDI note onsets."""
        if not midi_data.instruments:
            return 120.0

        onsets = []
        for instrument in midi_data.instruments:
            for note in instrument.notes:
                onsets.append(note.start)

        if len(onsets) < 2:
            return 120.0

        onsets = np.array(sorted(onsets))
        intervals = np.diff(onsets)

        # Filter reasonable intervals (50ms - 2s)
        intervals = intervals[(intervals > 0.05) & (intervals < 2.0)]

        if len(intervals) == 0:
            return 120.0

        # Find most common interval (beat)
        hist, bins = np.histogram(intervals, bins=50)
        beat_interval = bins[np.argmax(hist)]
        tempo = 60.0 / beat_interval

        # Clamp to reasonable range
        return float(np.clip(tempo, 60, 200))

    def _detect_key_from_notes(self, notes: List[dict]) -> Tuple[Optional[str], Optional[str]]:
        """Detect key and scale from note pitches using chroma."""
        if not LIBROSA_AVAILABLE or not notes:
            return None, None

        try:
            # Create chroma from note pitches
            pitches = [n["pitch"] for n in notes]
            if not pitches:
                return None, None

            # Weight by duration and velocity
            chroma = np.zeros(12)
            for note in notes:
                pitch_class = note["pitch"] % 12
                duration = note["end"] - note["start"]
                weight = duration * (note["velocity"] / 127.0)
                chroma[pitch_class] += weight

            # Normalize
            if chroma.sum() > 0:
                chroma = chroma / chroma.sum()

            # Key profiles (Krumhansl-Schmuckler)
            major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                                      2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
            minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                                      2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

            key_names = ["C", "C#", "D", "D#", "E", "F",
                         "F#", "G", "G#", "A", "A#", "B"]

            best_correlation = -1
            best_key = None
            best_mode = None

            for i in range(12):
                # Rotate profiles
                major_rotated = np.roll(major_profile, i)
                minor_rotated = np.roll(minor_profile, i)

                major_corr = np.corrcoef(chroma, major_rotated)[0, 1]
                minor_corr = np.corrcoef(chroma, minor_rotated)[0, 1]

                if major_corr > best_correlation:
                    best_correlation = major_corr
                    best_key = key_names[i]
                    best_mode = "major"

                if minor_corr > best_correlation:
                    best_correlation = minor_corr
                    best_key = key_names[i]
                    best_mode = "minor"

            return best_key, best_mode

        except Exception:
            return None, None


# Convenience function for quick conversion
def convert_audio_to_midi(
    audio_path: str,
    output_midi_path: Optional[str] = None,
    **kwargs
) -> MidiConversionResult:
    """Quick conversion function."""
    converter = AudioToMidiConverter(**kwargs)
    return converter.convert_audio_file(audio_path, output_midi_path)


def convert_drums_to_midi(
    audio_path: str,
    output_midi_path: Optional[str] = None,
    **kwargs
) -> MidiConversionResult:
    """Quick drum conversion function."""
    converter = AudioToMidiConverter(**kwargs)
    return converter.convert_drums(audio_path, output_midi_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python audio_to_midi.py <audio_file> [output_midi]")
        sys.exit(1)

    audio_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Converting {audio_file} to MIDI...")
    result = convert_audio_to_midi(audio_file, output_file)

    if result.error:
        print(f"Error: {result.error}")
    else:
        print(f"Success! MIDI saved to: {result.midi_path}")
        print(f"Notes: {len(result.notes)}")
        print(f"Tempo: {result.tempo:.1f} BPM")
        print(f"Key: {result.key} {result.scale}")