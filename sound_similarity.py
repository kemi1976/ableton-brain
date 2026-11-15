"""ABLETON BRAIN - Sound Similarity Search
AI-powered audio fingerprinting and similarity search using FAISS
"""

import os
import json
import pickle
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import asyncio

try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


@dataclass
class AudioFingerprint:
    """Audio fingerprint for similarity matching"""
    path: str
    name: str
    duration: float
    sample_rate: int
    # Spectral features
    mfcc_mean: np.ndarray = None
    mfcc_std: np.ndarray = None
    chroma_mean: np.ndarray = None
    chroma_std: np.ndarray = None
    spectral_centroid_mean: float = 0
    spectral_centroid_std: float = 0
    spectral_rolloff_mean: float = 0
    spectral_bandwidth_mean: float = 0
    zero_crossing_rate_mean: float = 0
    rms_mean: float = 0
    tempo: float = 0
    key: str = "C"
    # Metadata
    file_hash: str = ""
    analyzed_at: float = 0


class SoundSimilaritySearcher:
    """AI-powered sound similarity search using audio fingerprints + FAISS"""

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            cache_dir = Path(__file__).parent / ".sound_similarity_cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.cache_dir / "faiss_index.bin"
        self.metadata_path = self.cache_dir / "metadata.json"
        self.fingerprints_path = self.cache_dir / "fingerprints.pkl"

        self.index = None
        self.metadata: List[Dict] = []
        self.fingerprints: List[AudioFingerprint] = []
        self._load_cache()

    def _load_cache(self):
        """Load FAISS index and metadata from disk"""
        if self.index_path.exists() and FAISS_AVAILABLE:
            try:
                self.index = faiss.read_index(str(self.index_path))
                print(f"[SoundSimilarity] Loaded FAISS index with {self.index.ntotal} vectors")
            except:
                self.index = None

        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, 'r') as f:
                    self.metadata = json.load(f)
            except:
                self.metadata = []

        if self.fingerprints_path.exists():
            try:
                with open(self.fingerprints_path, 'rb') as f:
                    self.fingerprints = pickle.load(f)
            except:
                self.fingerprints = []

    def _save_cache(self):
        """Save FAISS index and metadata to disk"""
        if self.index is not None and FAISS_AVAILABLE:
            try:
                faiss.write_index(self.index, str(self.index_path))
            except:
                pass

        try:
            with open(self.metadata_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except:
            pass

        try:
            with open(self.fingerprints_path, 'wb') as f:
                pickle.dump(self.fingerprints, f)
        except:
            pass

    def _get_file_hash(self, path: str) -> str:
        """Get MD5 hash of file for change detection"""
        hasher = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _extract_features(self, y: np.ndarray, sr: int) -> Dict:
        """Extract comprehensive audio features for fingerprinting"""
        features = {}

        # MFCCs (timbre)
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        features['mfcc_mean'] = mfccs.mean(axis=1).astype(np.float32)
        features['mfcc_std'] = mfccs.std(axis=1).astype(np.float32)

        # Chroma (harmonic content)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        features['chroma_mean'] = chroma.mean(axis=1).astype(np.float32)
        features['chroma_std'] = chroma.std(axis=1).astype(np.float32)

        # Spectral features
        cent = librosa.feature.spectral_centroid(y=y, sr=sr)
        features['spectral_centroid_mean'] = float(cent.mean())
        features['spectral_centroid_std'] = float(cent.std())

        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
        features['spectral_rolloff_mean'] = float(rolloff.mean())

        bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
        features['spectral_bandwidth_mean'] = float(bandwidth.mean())

        zcr = librosa.feature.zero_crossing_rate(y)
        features['zero_crossing_rate_mean'] = float(zcr.mean())

        rms = librosa.feature.rms(y=y)
        features['rms_mean'] = float(rms.mean())

        # Tempo
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        features['tempo'] = float(tempo)

        # Key detection
        chroma_key = librosa.feature.chroma_stft(y=y, sr=sr)
        key_idx = chroma_key.mean(axis=1).argmax()
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        features['key'] = keys[key_idx % 12]

        return features

    def _fingerprint_to_vector(self, fp: AudioFingerprint) -> np.ndarray:
        """Convert fingerprint to fixed-size vector for FAISS"""
        # Concatenate all features into a single vector
        parts = [
            fp.mfcc_mean.flatten() if fp.mfcc_mean is not None else np.zeros(13),
            fp.mfcc_std.flatten() if fp.mfcc_std is not None else np.zeros(13),
            fp.chroma_mean.flatten() if fp.chroma_mean is not None else np.zeros(12),
            fp.chroma_std.flatten() if fp.chroma_std is not None else np.zeros(12),
            np.array([fp.spectral_centroid_mean, fp.spectral_centroid_std], dtype=np.float32),
            np.array([fp.spectral_rolloff_mean], dtype=np.float32),
            np.array([fp.spectral_bandwidth_mean], dtype=np.float32),
            np.array([fp.zero_crossing_rate_mean], dtype=np.float32),
            np.array([fp.rms_mean], dtype=np.float32),
            np.array([fp.tempo / 200.0], dtype=np.float32),  # Normalize tempo
        ]
        return np.concatenate(parts).astype(np.float32)

    def analyze_file(self, file_path: str) -> Optional[AudioFingerprint]:
        """Analyze a single audio file and create fingerprint"""
        if not LIBROSA_AVAILABLE:
            return None

        try:
            # Load audio
            y, sr = librosa.load(file_path, sr=None, duration=30)  # First 30s for speed

            # Extract features
            features = self._extract_features(y, sr)

            # Create fingerprint
            file_hash = self._get_file_hash(file_path)
            fp = AudioFingerprint(
                path=file_path,
                name=Path(file_path).name,
                duration=len(y) / sr,
                sample_rate=sr,
                mfcc_mean=features['mfcc_mean'],
                mfcc_std=features['mfcc_std'],
                chroma_mean=features['chroma_mean'],
                chroma_std=features['chroma_std'],
                spectral_centroid_mean=features['spectral_centroid_mean'],
                spectral_centroid_std=features['spectral_centroid_std'],
                spectral_rolloff_mean=features['spectral_rolloff_mean'],
                spectral_bandwidth_mean=features['spectral_bandwidth_mean'],
                zero_crossing_rate_mean=features['zero_crossing_rate_mean'],
                rms_mean=features['rms_mean'],
                tempo=features['tempo'],
                key=features['key'],
                file_hash=file_hash,
                analyzed_at=os.path.getmtime(file_path),
            )
            return fp
        except Exception as e:
            print(f"[SoundSimilarity] Error analyzing {file_path}: {e}")
            return None

    def index_folder(self, folder: str, extensions: set = None, force_rebuild: bool = False) -> Dict:
        """Index all audio files in a folder for similarity search"""
        if not LIBROSA_AVAILABLE:
            return {"success": False, "error": "librosa not installed"}

        if extensions is None:
            extensions = {'.wav', '.aiff', '.aif', '.flac', '.mp3', '.ogg', '.m4a'}

        folder_path = Path(folder)
        if not folder_path.exists():
            return {"success": False, "error": f"Folder not found: {folder}"}

        # Find all audio files
        audio_files = []
        for ext in extensions:
            audio_files.extend(folder_path.rglob(f"*{ext}"))

        if not audio_files:
            return {"success": False, "error": "No audio files found"}

        print(f"[SoundSimilarity] Indexing {len(audio_files)} files...")

        # Load existing fingerprints to check for changes
        existing_hashes = {fp.path: fp.file_hash for fp in self.fingerprints}

        new_fingerprints = []
        updated_count = 0

        for file_path in audio_files:
            path_str = str(file_path)
            current_hash = self._get_file_hash(path_str)

            # Skip if unchanged and not forcing rebuild
            if not force_rebuild and path_str in existing_hashes and existing_hashes[path_str] == current_hash:
                # Keep existing fingerprint
                for fp in self.fingerprints:
                    if fp.path == path_str:
                        new_fingerprints.append(fp)
                        break
                continue

            # Analyze file
            fp = self.analyze_file(path_str)
            if fp:
                new_fingerprints.append(fp)
                updated_count += 1

        print(f"[SoundSimilarity] Analyzed {updated_count} new/changed files")

        # Build FAISS index
        if new_fingerprints and FAISS_AVAILABLE:
            vectors = np.array([self._fingerprint_to_vector(fp) for fp in new_fingerprints])
            # Normalize for cosine similarity
            faiss.normalize_L2(vectors)

            # Create index (Inner Product = Cosine Similarity for normalized vectors)
            dimension = vectors.shape[1]
            self.index = faiss.IndexFlatIP(dimension)
            self.index.add(vectors)

            print(f"[SoundSimilarity] Built FAISS index: {self.index.ntotal} vectors, {dimension}D")

        self.fingerprints = new_fingerprints
        self.metadata = [
            {
                "path": fp.path,
                "name": fp.name,
                "duration": fp.duration,
                "sample_rate": fp.sample_rate,
                "tempo": fp.tempo,
                "key": fp.key,
            }
            for fp in new_fingerprints
        ]

        self._save_cache()

        return {
            "success": True,
            "indexed": len(new_fingerprints),
            "new_or_updated": updated_count,
            "dimension": dimension if 'dimension' in locals() else 0,
        }

    def find_similar(self, reference_path: str, sample_folder: str = None,
                     limit: int = 10, min_similarity: float = 0.7) -> List[Dict]:
        """Find similar samples to a reference file"""

        if not LIBROSA_AVAILABLE or not FAISS_AVAILABLE:
            return [{"error": "librosa or faiss not installed"}]

        if self.index is None or self.index.ntotal == 0:
            # Try to index the folder first
            if sample_folder:
                self.index_folder(sample_folder)
            if self.index is None or self.index.ntotal == 0:
                return [{"error": "No index available. Run index_folder first."}]

        # Analyze reference file
        ref_fp = self.analyze_file(reference_path)
        if ref_fp is None:
            return [{"error": "Could not analyze reference file"}]

        # Convert to vector and search
        ref_vector = self._fingerprint_to_vector(ref_fp).reshape(1, -1)
        faiss.normalize_L2(ref_vector)

        k = min(limit, self.index.ntotal)
        scores, indices = self.index.search(ref_vector, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= min_similarity and idx < len(self.fingerprints):
                fp = self.fingerprints[idx]
                results.append({
                    "path": fp.path,
                    "name": fp.name,
                    "similarity": float(score),
                    "tempo": fp.tempo,
                    "key": fp.key,
                    "duration": fp.duration,
                })

        return results


# Convenience functions
def create_searcher(cache_dir: str = None) -> SoundSimilaritySearcher:
    return SoundSimilaritySearcher(cache_dir)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python sound_similarity.py <command> <args>")
        print("Commands:")
        print("  index <folder>           - Index all audio files in folder")
        print("  search <reference> <folder> [limit] - Find similar samples")
        sys.exit(1)

    command = sys.argv[1]
    searcher = SoundSimilaritySearcher()

    if command == "index":
        folder = sys.argv[2]
        result = searcher.index_folder(folder)
        print(json.dumps(result, indent=2))

    elif command == "search":
        reference = sys.argv[2]
        folder = sys.argv[3]
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 10
        searcher.index_folder(folder)
        results = searcher.find_similar(reference, limit=limit)
        print(json.dumps(results, indent=2))