#!/usr/bin/env python3
"""
Project Version Control Module
Git-like snapshots for Ableton projects: create branches, diff changes, merge.
Competitor parity: None unique to Ableton Brain.
Storage: JSON snapshots under .ableton-brain/versions/
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class Snapshot:
    """One captured project state."""
    id: str
    name: str
    created_at: str
    parent: Optional[str]
    data: Dict  # project state dict from Remote Script
    track_count: int
    clip_count: int
    param_count: int

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "created_at": self.created_at,
            "parent": self.parent, "track_count": self.track_count,
            "clip_count": self.clip_count, "param_count": self.param_count,
        }


@dataclass
class DiffEntry:
    """One difference between snapshots."""
    field: str
    old: Any
    new: Any
    change_type: str  # added, removed, changed


class VersionControl:
    """Snapshot-based version control for Ableton projects."""

    def __init__(self, project_dir: str = "."):
        self.project_dir = os.path.abspath(project_dir)
        self.versions_dir = os.path.join(project_dir, ".ableton-brain", "versions")
        os.makedirs(self.versions_dir, exist_ok=True)
        self.index_file = os.path.join(self.versions_dir, "index.json")
        self.index = self._load_index()

    # ---------- core ----------

    def _load_index(self) -> Dict:
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_index(self) -> None:
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2)

    def _snapshot_path(self, snap_id: str) -> str:
        return os.path.join(self.versions_dir, f"{snap_id}.json")

    # ---------- public API ----------

    def create_snapshot(self, project_state: Dict, name: Optional[str] = None) -> Snapshot:
        """Capture current project state as a snapshot."""
        snap_id = str(uuid.uuid4())[:8]
        ts = datetime.now().isoformat()
        tracks = project_state.get("tracks", [])
        clips = sum(len(t.get("clips", [])) for t in tracks)
        params = sum(len(d.get("parameters", [])) for t in tracks for d in t.get("devices", []))

        snap = Snapshot(
            id=snap_id,
            name=name or f"Snapshot {len(self.index) + 1}",
            created_at=ts,
            parent=self.index.get("head"),
            data=project_state,
            track_count=len(tracks),
            clip_count=clips,
            param_count=params,
        )

        with open(self._snapshot_path(snap_id), "w", encoding="utf-8") as f:
            json.dump(snap.to_dict(), f, indent=2)

        self.index[snap_id] = snap.to_dict()
        self.index["head"] = snap_id
        self._save_index()
        return snap

    def create_branch(self, branch_name: str, from_snapshot: Optional[str] = None) -> str:
        """Create a named branch pointer at a snapshot."""
        snap_id = from_snapshot or self.index.get("head")
        if not snap_id:
            raise ValueError("no snapshot to branch from")
        self.index[f"branch:{branch_name}"] = snap_id
        self._save_index()
        return snap_id

    def switch_branch(self, branch_name: str) -> None:
        key = f"branch:{branch_name}"
        if key not in self.index:
            raise ValueError(f"branch not found: {branch_name}")
        self.index["head"] = self.index[key]
        self._save_index()

    def list_snapshots(self) -> List[Dict]:
        """List all snapshots newest first."""
        items = [v for k, v in self.index.items() if not k.startswith("branch:") and k != "head"]
        items.sort(key=lambda s: s["created_at"], reverse=True)
        return items

    def list_branches(self) -> List[str]:
        return [k[len("branch:"):] for k in self.index if k.startswith("branch:")]

    def get_snapshot(self, snap_id: str) -> Optional[Snapshot]:
        raw = self.index.get(snap_id)
        if not raw:
            return None
        path = self._snapshot_path(snap_id)
        data = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        return Snapshot(id=snap_id, name=raw["name"], created_at=raw["created_at"],
                        parent=raw["parent"], data=data, track_count=raw["track_count"],
                        clip_count=raw["clip_count"], param_count=raw["param_count"])

    def restore_snapshot(self, snap_id: str) -> Dict:
        """Return project state data for restoring into Ableton."""
        snap = self.get_snapshot(snap_id)
        if not snap:
            raise ValueError(f"snapshot not found: {snap_id}")
        return snap.data

    def delete_snapshot(self, snap_id: str) -> None:
        path = self._snapshot_path(snap_id)
        if os.path.exists(path):
            os.remove(path)
        self.index.pop(snap_id, None)
        if self.index.get("head") == snap_id:
            self.index["head"] = None
        self._save_index()

    # ---------- diff ----------

    def diff_snapshots(self, id_a: str, id_b: str) -> List[DiffEntry]:
        """Diff two snapshots by structure (tracks/devices/params)."""
        a = self.get_snapshot(id_a)
        b = self.get_snapshot(id_b)
        if not a or not b:
            raise ValueError("one or both snapshots missing")
        return self._diff_structures(a.data, b.data)

    def _diff_structures(self, a: Dict, b: Dict, prefix: str = "") -> List[DiffEntry]:
        diffs: List[DiffEntry] = []
        keys_a = set(a.keys())
        keys_b = set(b.keys())
        for k in keys_a | keys_b:
            f = f"{prefix}{k}"
            va, vb = a.get(k), b.get(k)
            if k not in keys_b:
                diffs.append(DiffEntry(f, va, None, "removed"))
            elif k not in keys_a:
                diffs.append(DiffEntry(f, None, vb, "added"))
            elif isinstance(va, dict) and isinstance(vb, dict):
                diffs.extend(self._diff_structures(va, vb, f + "."))
            elif va != vb:
                diffs.append(DiffEntry(f, va, vb, "changed"))
        return diffs

    def summary(self) -> Dict:
        return {
            "snapshot_count": len(self.list_snapshots()),
            "branches": self.list_branches(),
            "head": self.index.get("head"),
        }


def create_snapshot(project_state: Dict, name: Optional[str] = None) -> Dict:
    return VersionControl().create_snapshot(project_state, name).to_dict()


def diff_snapshots(id_a: str, id_b: str) -> List[Dict]:
    return [d.__dict__ for d in VersionControl().diff_snapshots(id_a, id_b)]


def list_snapshots() -> List[Dict]:
    return VersionControl().list_snapshots()


if __name__ == "__main__":
    vc = VersionControl()
    state = {"tracks": [{"name": "Kick", "devices": [{"parameters": {}}], "clips": [1]}]}
    s1 = vc.create_snapshot(state, "First idea")
    state2 = {"tracks": [{"name": "Kick", "devices": [{"parameters": {}}], "clips": [1, 2]}]}
    s2 = vc.create_snapshot(state2, "Added clip")
    print(f"Snapshots: {len(vc.list_snapshots())}")
    print(f"Branches: {vc.list_branches()}")
    vc.create_branch("verse", s1.id)
    print(f"Branches: {vc.list_branches()}")
    d = vc.diff_snapshots(s1.id, s2.id)
    print(f"Diff entries: {len(d)}")
    for dd in d[:3]:
        print(f"  {dd.change_type}: {dd.field}")