#!/usr/bin/env python3
"""
Smart Sample Search Module
Context-aware sample library search: key compatibility (Camelot), tempo, spectral similarity.
Competitor parity: Splice Search with Sound, Serato Sample.
"""

from __future__ import annotations

import os
import json
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

# Camelot wheel: key -> camelot number
CAMELOT = {
    "C": 8, "G": 9, "D": 10, "A": 11, "E": 12, "B": 1,
    "F#": 2, "Db": 3, "Ab": 4, "Eb": 5, "Bb": 6, "F": 7,
    "Am": 8, "Em": 9, "Bm": 10, "F#m": 11, "C#m": 12, "G#m": 1,
    "D#m": 2, "A#m": 3, "Fm": 4, "Cm": 5, "Gm": 6, "Dm": 7,
}

CAMELOT_COMPATIBLE = {
    # same number (compatible minor/major) + adjacent numbers
    i: {i - 1 if i > 1 else 12, i, i + 1 if i < 12 else 1}
    for i in range(1, 13)
}

GENRE_BPM_RANGES = {
    "house": (122, 130), "techno": (125, 135), "dubstep": (140, 145),
    "dnb": (160, 180), "hiphop": (85, 100), "trap": (135, 150),
    "electronic": (120, 130), "ambient": (70, 100), "pop": (100, 125),
}


@dataclass
class SampleEntry:
    """Indexed sample with features."""
    path: str
    name: str
    duration_sec: float
    tempo: Optional[float]
    key: Optional[str]
    camelot: Optional[int]
    rms: float
    spectral_centroid: float
    zero_crossing_rate: float
    genre_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "path": self.path, "name": self.name, "duration_sec": round(self.duration_sec, 2),
            "tempo": self.tempo, "key": self.key, "camelot": self.camelot,
            "rms": round(self.rms, 4), "spectral_centroid": round(self.spectral_centroid, 1),
            "zero_crossing_rate": round(self.zero_crossing_rate, 4), "tags": self.genre_tags,
        }


@dataclass
class SearchResult:
    """One search match."""
    entry: SampleEntry
    score: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "sample": self.entry.to_dict(),
            "score": round(self.score, 3),
            "reason": self.reason,
        }


class SmartSampleSearch:
    """Index + search samples by musical context."""

    def __init__(self, index_path: Optional[str] = None):
        self.index_path = index_path or os.path.join(os.getcwd(), "sample_index.json")
        self.samples: List[SampleEntry] = []
        self._load()

    # ---------- indexing ----------

    def _load(self) -> None:
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self.samples = [self._entry_from_dict(e) for e in raw]
            except Exception:
                self.samples = []

    def _save(self) -> None:
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self.samples], f, indent=2)

    @staticmethod
    def _entry_from_dict(d: dict) -> SampleEntry:
        return SampleEntry(path=d["path"], name=d["name"], duration_sec=d["duration_sec"],
                           tempo=d.get("tempo"), key=d.get("key"), camelot=d.get("camelot"),
                           rms=d.get("rms", 0), spectral_centroid=d.get("spectral_centroid", 0),
                           zero_crossing_rate=d.get("zero_crossing_rate", 0),
                           genre_tags=d.get("tags", []))

    def index_file(self, path: str) -> SampleEntry:
        """Analyze one file and add to index."""
        info = self._analyze(path)
        entry = SampleEntry(path=path, name=os.path.basename(path), **info)
        self.samples.append(entry)
        self._save()
        return entry

    def index_directory(self, directory: str, extensions: tuple = (".wav", ".aiff", ".aif", ".flac", ".mp3")) -> int:
        """Index all audio files in a folder recursively."""
        count = 0
        for root, _, files in os.walk(directory):
            for fn in files:
                if fn.lower().endswith(extensions):
                    try:
                        self.index_file(os.path.join(root, fn))
                        count += 1
                    except Exception:
                        continue
        return count

    def clear_index(self) -> None:
        self.samples = []
        if os.path.exists(self.index_path):
            os.remove(self.index_path)

    # ---------- analysis ----------

    def _analyze(self, path: str) -> Dict:
        if librosa is None:
            return {
                "duration_sec": 0.0, "tempo": None, "key": None,
                "camelot": None, "rms": 0.0, "spectral_centroid": 0.0,
                "zero_crossing_rate": 0.0,
            }
        y, sr = librosa.load(path, sr=None, mono=True, duration=60)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
        pitch_classes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        key = pitch_classes[int(np.argmax(chroma))]
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0]))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)[0]))
        return {
            "duration_sec": round(len(y) / sr, 3),
            "tempo": round(float(tempo), 1),
            "key": key,
            "camelot": CAMELOT.get(key),
            "rms": round(float(np.sqrt(np.mean(y ** 2))), 4),
            "spectral_centroid": round(centroid, 1),
            "zero_crossing_rate": round(zcr, 4),
        }

    # ---------- search ----------

    def _tempo_ok(self, sample_tempo: Optional[float], target_bpm: Optional[float], tol: float = 15) -> bool:
        if not sample_tempo or not target_bpm:
            return True
        return abs(sample_tempo - target_bpm) <= tol

    def _key_compatible(self, sample_camelot: Optional[int], target_camelot: Optional[int]) -> bool:
        if sample_camelot is None or target_camelot is None:
            return True
        return sample_camelot in CAMELOT_COMPATIBLE.get(target_camelot, set())

    def search_by_context(
        self,
        target_audio_path: Optional[str] = None,
        target_tempo: Optional[float] = None,
        target_key: Optional[str] = None,
        target_genre: Optional[str] = None,
        camelot_strict: bool = False,
        limit: int = 10,
    ) -> List[SearchResult]:
        """Find samples matching the target context."""
        target_camelot = CAMELOT.get(target_key) if target_key else None
        target_info = {}
        if target_audio_path and librosa:
            target_info = self._analyze(target_audio_path)
            if target_tempo is None:
                target_tempo = target_info.get("tempo")
            if target_camelot is None:
                target_camelot = target_info.get("camelot")

        scored: List[SearchResult] = []
        for entry in self.samples:
            score = 0.0
            reasons: List[str] = []

            # tempo match
            if target_tempo:
                diff = abs((entry.tempo or target_tempo) - target_tempo)
                tempo_ok = diff <= 15
                if tempo_ok:
                    score += 3.0
                    reasons.append(f"tempo {entry.tempo} BPM")
                else:
                    continue  # hard filter on tempo

            # key compatibility
            if target_camelot:
                compatible = self._key_compatible(entry.camelot, target_camelot)
                if compatible:
                    score += 3.0
                    reasons.append(f"key compatible ({entry.key})")
                elif camelot_strict:
                    continue
                else:
                    score -= 1.0
                    reasons.append(f"key distant ({entry.key})")

            # genre tags
            if target_genre:
                tags = [t.lower() for t in entry.genre_tags]
                if target_genre.lower() in tags:
                    score += 2.0
                    reasons.append(f"genre {target_genre}")
                elif target_genre.lower() in entry.name.lower():
                    score += 1.0
                    reasons.append("name match")

            # energy (rms) similarity
            if target_info.get("rms"):
                rms_diff = abs(entry.rms - target_info["rms"]) / max(0.01, target_info["rms"])
                score += max(0, 1.0 - rms_diff)

            if score > 0:
                scored.append(SearchResult(entry, score, "; ".join(reasons)))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]

    def find_complementary(
        self,
        source_path: str,
        sample_type: str = "any",
        limit: int = 8,
    ) -> List[SearchResult]:
        """Find samples that complement this one (different type, same key/tempo)."""
        if librosa:
            info = self._analyze(source_path)
        else:
            info = {}
        return self.search_by_context(
            target_audio_path=None,
            target_tempo=info.get("tempo"),
            target_key=info.get("key"),
            limit=limit,
        )

    def camelot_wheel(self, key: Optional[str] = None) -> Dict:
        """Return Camelot wheel info for a key."""
        if key is None:
            return {"camelot": CAMELOT, "compatible_groups": CAMELOT_COMPATIBLE}
        num = CAMELOT.get(key)
        return {
            "key": key, "camelot": num,
            "compatible": CAMELOT_COMPATIBLE.get(num, set()),
            "energy_boost": num + 7 if num <= 5 else num - 5,
        }


def index_library(directory: str) -> int:
    return SmartSampleSearch().index_directory(directory)


def search_samples(target_audio: Optional[str] = None, bpm: Optional[float] = None,
                   key: Optional[str] = None, genre: Optional[str] = None) -> List[Dict]:
    searcher = SmartSampleSearch()
    return [r.to_dict() for r in searcher.search_by_context(target_audio, bpm, key, genre)]


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python smart_sample_search.py <directory>")
        sys.exit(1)
    s = SmartSampleSearch()
    n = s.index_directory(sys.argv[1])
    print(f"Indexed {n} samples")
    print(f"Total: {len(s.samples)}")
    print("Camelot wheel info for C major:", s.camelot_wheel("C"))