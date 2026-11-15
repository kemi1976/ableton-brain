"""
ABLETON BRAIN - Sample Scanner & Tune Generator
Scans sample folders, analyzes content, generates complete Ableton tracks
Based on ok2ju/ableton-mcp make-track-from-samples + Magenta AI
"""
import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import time

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    from mcp_server import AbletonBrainMCP, AbletonBrainComposer
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


@dataclass
class SampleInfo:
    """Analyzed sample metadata"""
    path: str
    name: str
    duration_s: float
    sample_rate: int
    channels: int
    size_bytes: int
    # AI-analyzed
    bpm: Optional[float] = None
    key: Optional[str] = None
    role: str = "unknown"  # drum, bass, melody, pad, fx, loop, one_shot
    kind: str = "unknown"  # loop, one_shot
    genre_tags: List[str] = field(default_factory=list)
    energy: float = 0.5
    brightness: float = 0.5


class SampleScanner:
    """Scans and analyzes sample folders"""

    EXTENSIONS = {'.wav', '.aiff', '.aif', '.flac', '.mp3', '.ogg', '.m4a'}

    ROLE_KEYWORDS = {
        'drum': ['kick', 'snare', 'clap', 'hat', 'hihat', 'cymbal', 'tom', 'perc', 'drum', 'rim', 'shaker', 'conga', 'bongo'],
        'bass': ['bass', 'sub', '808', 'reese', 'low'],
        'melody': ['lead', 'melody', 'synth', 'arp', 'arpeggio', 'pluck', 'bell', 'keys', 'piano', 'organ'],
        'pad': ['pad', 'atmos', 'ambient', 'drone', 'texture', 'wash', 'string', 'choir'],
        'fx': ['fx', 'effect', 'riser', 'downlifter', 'impact', 'whoosh', 'sweep', 'noise', 'glitch'],
        'vocal': ['vocal', 'vox', 'voice', 'chant', 'adlib', 'phrase'],
    }

    KIND_KEYWORDS = {
        'loop': ['loop', 'phrase', 'pattern', 'groove', 'beat', 'measure', 'bar'],
        'one_shot': ['hit', 'shot', 'stab', 'click', 'tap', 'single'],
    }

    GENRE_KEYWORDS = {
        'dnb': ['dnb', 'drumandbass', 'drum_and_bass', 'jungle', 'liquid', 'neuro', 'techstep'],
        'house': ['house', 'deep_house', 'tech_house', 'progressive'],
        'techno': ['techno', 'minimal', 'industrial'],
        'dubstep': ['dubstep', 'riddim', 'brostep'],
        'trap': ['trap', '808'],
        'hiphop': ['hiphop', 'boombap', 'lofi'],
        'ambient': ['ambient', 'drone', 'cinematic'],
    }

    def __init__(self, sample_folder: str):
        self.sample_folder = Path(sample_folder)
        self.samples: List[SampleInfo] = []

    def scan(self, limit: int = 500) -> List[SampleInfo]:
        """Scan folder for audio files"""
        self.samples = []

        for root, dirs, files in os.walk(self.sample_folder):
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in self.EXTENSIONS:
                    path = Path(root) / f
                    info = self._basic_info(path, f)
                    self.samples.append(info)
                    if len(self.samples) >= limit:
                        break
            if len(self.samples) >= limit:
                break

        return self.samples

    def _basic_info(self, path: Path, name: str) -> SampleInfo:
        """Get basic file info"""
        try:
            stat = path.stat()
            # Try to get audio info
            duration = 0
            sr = 0
            channels = 0
            try:
                import wave
                with wave.open(str(path), 'rb') as w:
                    frames = w.getnframes()
                    rate = w.getframerate()
                    duration = frames / float(rate)
                    sr = rate
                    channels = w.getnchannels()
            except:
                pass

            return SampleInfo(
                path=str(path),
                name=name,
                duration_s=duration,
                sample_rate=sr,
                channels=channels,
                size_bytes=stat.st_size,
            )
        except:
            return SampleInfo(
                path=str(path),
                name=name,
                duration_s=0,
                sample_rate=0,
                channels=0,
                size_bytes=0,
            )

    def analyze_all(self) -> List[SampleInfo]:
        """Analyze all samples for role, kind, genre, BPM, key"""
        for sample in self.samples:
            self._classify_role(sample)
            self._classify_kind(sample)
            self._classify_genre(sample)

            # Try AI analysis if librosa available
            if LIBROSA_AVAILABLE and sample.duration_s > 0:
                try:
                    self._ai_analyze(sample)
                except:
                    pass

        return self.samples

    def _classify_role(self, sample: SampleInfo):
        """Classify sample role from filename"""
        name_lower = sample.name.lower()
        for role, keywords in self.ROLE_KEYWORDS.items():
            if any(kw in name_lower for kw in keywords):
                sample.role = role
                return
        # Default based on duration
        if sample.duration_s > 4:
            sample.role = "loop"
        else:
            sample.role = "one_shot"

    def _classify_kind(self, sample: SampleInfo):
        """Classify as loop or one-shot"""
        name_lower = sample.name.lower()
        for kind, keywords in self.KIND_KEYWORDS.items():
            if any(kw in name_lower for kw in keywords):
                sample.kind = kind
                return
        # Default by duration
        sample.kind = "loop" if sample.duration_s > 4 else "one_shot"

    def _classify_genre(self, sample: SampleInfo):
        """Guess genre from folder structure and filename"""
        path_lower = str(sample.path).lower()
        for genre, keywords in self.GENRE_KEYWORDS.items():
            if any(kw in path_lower for kw in keywords):
                sample.genre_tags.append(genre)

    def _ai_analyze(self, sample: SampleInfo):
        """AI analysis using librosa"""
        y, sr = librosa.load(sample.path, sr=None)
        sample.duration_s = len(y) / sr
        sample.sample_rate = sr

        # BPM detection
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        sample.bpm = float(tempo)

        # Key detection (simplified)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        key_idx = chroma.mean(axis=1).argmax()
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        sample.key = keys[key_idx]

        # Spectral features
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr).mean()
        sample.brightness = min(1.0, spectral_centroid / 4000.0)

        rms = librosa.feature.rms(y=y).mean()
        sample.energy = min(1.0, rms * 10)

    def get_by_role(self, role: str) -> List[SampleInfo]:
        return [s for s in self.samples if s.role == role]

    def get_by_kind(self, kind: str) -> List[SampleInfo]:
        return [s for s in self.samples if s.kind == kind]

    def summary(self) -> Dict:
        roles = defaultdict(int)
        kinds = defaultdict(int)
        genres = defaultdict(int)
        for s in self.samples:
            roles[s.role] += 1
            kinds[s.kind] += 1
            for g in s.genre_tags:
                genres[g] += 1
        return {
            'total': len(self.samples),
            'roles': dict(roles),
            'kinds': dict(kinds),
            'genres': dict(genres),
            'total_duration': sum(s.duration_s for s in self.samples),
        }


class TuneGenerator:
    """Generates complete Ableton tracks from scanned samples"""

    def __init__(self, scanner: SampleScanner, mcp: Optional[AbletonBrainMCP] = None):
        self.scanner = scanner
        self.mcp = mcp
        self.composer = AbletonBrainComposer(mcp) if mcp and MCP_AVAILABLE else None

    async def generate_track(self, genre: str = "electronic", style: str = "full") -> Dict:
        """Generate complete track structure"""
        # Analyze samples
        self.scanner.analyze_all()

        # Categorize
        drums = self.scanner.get_by_role('drum')
        bass = self.scanner.get_by_role('bass')
        melody = self.scanner.get_by_role('melody')
        pads = self.scanner.get_by_role('pad')
        fx = self.scanner.get_by_role('fx')
        vocals = self.scanner.get_by_role('vocal')

        loops = self.scanner.get_by_kind('loop')
        one_shots = self.scanner.get_by_kind('one_shot')

        # Determine tempo from longest loop with BPM
        tempo = 120
        key = 'C'
        for loop in loops:
            if loop.bpm and 60 < loop.bpm < 200:
                tempo = loop.bpm
                key = loop.key or 'C'
                break

        # Build track plan
        plan = {
            'tempo': tempo,
            'key': key,
            'genre': genre,
            'tracks': [],
            'scenes': ['Intro', 'Build', 'Drop', 'Break', 'Outro'],
        }

        track_idx = 0

        # Track 0: Drums
        if drums or one_shots:
            plan['tracks'].append({
                'index': track_idx,
                'name': 'Drums',
                'type': 'midi',
                'device': 'Drum Rack',
                'samples': [s.path for s in one_shots[:16]],
                'pattern': 'auto',
            })
            track_idx += 1

        # Track 1: Bass
        if bass:
            plan['tracks'].append({
                'index': track_idx,
                'name': 'Bass',
                'type': 'audio',
                'samples': [s.path for s in bass[:4]],
            })
            track_idx += 1

        # Track 2+: Loops
        for i, loop in enumerate(loops[:6]):
            plan['tracks'].append({
                'index': track_idx,
                'name': f'Loop {i+1}',
                'type': 'audio',
                'samples': [loop.path],
            })
            track_idx += 1

        # Melody track
        if melody:
            plan['tracks'].append({
                'index': track_idx,
                'name': 'Melody',
                'type': 'midi',
                'device': 'Wavetable',
                'notes': 'generated',
            })
            track_idx += 1

        # Pad track
        if pads:
            plan['tracks'].append({
                'index': track_idx,
                'name': 'Pad',
                'type': 'audio',
                'samples': [s.path for s in pads[:2]],
            })
            track_idx += 1

        # FX track
        if fx:
            plan['tracks'].append({
                'index': track_idx,
                'name': 'FX',
                'type': 'audio',
                'samples': [s.path for s in fx[:4]],
            })

        # Execute in Ableton if MCP available
        if self.composer:
            result = await self.composer.make_track_from_samples(
                str(self.scanner.sample_folder), genre
            )
            plan['execution'] = result

        return plan

    async def generate_melody_for_chords(self, chord_progression: List[str], key: str = 'C', scale: str = 'major') -> List[Dict]:
        """Generate melody notes for a chord progression"""
        # Simplified melody generation - would use Magenta AI in production
        melody_notes = []
        chords = {
            'major': [0, 4, 7],
            'minor': [0, 3, 7],
        }
        intervals = chords.get(scale, chords['major'])

        for i, chord_root in enumerate(chord_progression):
            root_note = self._note_to_midi(chord_root)
            for interval in intervals:
                note = root_note + interval + 12  # Up an octave
                melody_notes.append({
                    'pitch': note,
                    'start_time': i * 4.0,
                    'duration': 2.0,
                    'velocity': 80,
                })

        return melody_notes

    def _note_to_midi(self, note: str) -> int:
        """Convert note name to MIDI number"""
        notes = {'C': 60, 'C#': 61, 'D': 62, 'D#': 63, 'E': 64, 'F': 65,
                 'F#': 66, 'G': 67, 'G#': 68, 'A': 69, 'A#': 70, 'B': 71}
        base = notes.get(note[0].upper(), 60)
        if len(note) > 1:
            if note[1] == '#':
                base += 1
            elif note[1] == 'b':
                base -= 1
        return base


# =========================================================================
# SYNC WITH ABLETON BRAIN DATABASE
# =========================================================================

class AbletonBrainSync:
    """Sync sample analysis with Ableton Brain database"""

    def __init__(self, brain_db_path: str = None):
        if brain_db_path is None:
            brain_db_path = Path(__file__).parent / "database.json"
        self.db_path = Path(brain_db_path)
        self.db = self._load_db()

    def _load_db(self) -> Dict:
        if self.db_path.exists():
            with open(self.db_path, 'r') as f:
                return json.load(f)
        return {"artists": {}, "techniques": {}, "presets": {}}

    def save_sample_analysis(self, scanner: SampleScanner):
        """Save sample analysis to database"""
        if "samples" not in self.db:
            self.db["samples"] = {}

        for sample in scanner.samples:
            self.db["samples"][sample.name] = {
                "path": sample.path,
                "duration": sample.duration_s,
                "bpm": sample.bpm,
                "key": sample.key,
                "role": sample.role,
                "kind": sample.kind,
                "genre_tags": sample.genre_tags,
                "energy": sample.energy,
                "brightness": sample.brightness,
                "analyzed_at": time.time(),
            }

        with open(self.db_path, 'w') as f:
            json.dump(self.db, f, indent=2)

    def get_samples_for_genre(self, genre: str) -> List[Dict]:
        """Get samples matching genre from database"""
        results = []
        for name, info in self.db.get("samples", {}).items():
            if genre in info.get("genre_tags", []):
                results.append({"name": name, **info})
        return results


# =========================================================================
# MAIN WORKFLOW
# =========================================================================

async def scan_and_generate(sample_folder: str, genre: str = "dnb", mcp: Optional[AbletonBrainMCP] = None) -> Dict:
    """Complete workflow: scan → analyze → generate → execute"""
    print(f"[Brain] Scanning: {sample_folder}")
    scanner = SampleScanner(sample_folder)
    scanner.scan()
    scanner.analyze_all()

    print(f"[Brain] Found {len(scanner.samples)} samples")
    print(f"[Brain] Summary: {scanner.summary()}")

    # Save to database
    sync = AbletonBrainSync()
    sync.save_sample_analysis(scanner)

    # Generate track
    generator = TuneGenerator(scanner, mcp)
    plan = await generator.generate_track(genre)

    print(f"[Brain] Generated track plan: {len(plan['tracks'])} tracks")
    return {
        'scanner': scanner,
        'plan': plan,
        'summary': scanner.summary(),
    }


if __name__ == '__main__':
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else "C:/Users/pc/Documents/AI PROJECTS ANDRIOD/knowledge/ableton-brain/samples"
    genre = sys.argv[2] if len(sys.argv) > 2 else "dnb"

    result = asyncio.run(scan_and_generate(folder, genre))
    print(json.dumps(result['plan'], indent=2))