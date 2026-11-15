#!/usr/bin/env python3
"""
Preset Manager Module
Unified preset browser across plugins: save, rate, search, tag, export/import.
Storage: SQLite database (stdlib).
Competitor parity: None — unified preset browser is unique.
"""

from __future__ import annotations

import json
import os
import sqlite3
import shutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Preset:
    """One preset entry."""
    id: str
    name: str
    plugin: str
    plugin_type: str  # vst3, au, clap, vst2, aax, lv2, ableton, generic
    category: str  # bass, lead, pad, drums, fx, etc.
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    rating: int = 0  # -5 .. 5
    created_at: str = ""
    file_path: Optional[str] = None  # original preset file if imported

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "plugin": self.plugin,
            "plugin_type": self.plugin_type, "category": self.category,
            "tags": self.tags, "parameters": self.parameters,
            "rating": self.rating, "created_at": self.created_at,
            "file_path": self.file_path,
        }


class PresetManager:
    """SQLite-backed preset library."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(os.getcwd(), "presets.db")
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS presets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            plugin TEXT NOT NULL,
            plugin_type TEXT NOT NULL,
            category TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '[]',
            parameters TEXT NOT NULL DEFAULT '{}',
            rating INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            file_path TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_presets_plugin ON presets(plugin);
        CREATE INDEX IF NOT EXISTS idx_presets_category ON presets(category);
        CREATE INDEX IF NOT EXISTS idx_presets_rating ON presets(rating);
        """)
        self.conn.commit()

    def save_preset(self, name: str, plugin: str, plugin_type: str, category: str,
                    parameters: Dict, tags: Optional[List[str]] = None,
                    file_path: Optional[str] = None) -> Preset:
        import uuid
        from datetime import datetime
        pid = str(uuid.uuid4())[:8]
        preset = Preset(
            id=pid, name=name, plugin=plugin, plugin_type=plugin_type,
            category=category, tags=tags or [], parameters=parameters,
            rating=0, created_at=datetime.now().isoformat(), file_path=file_path,
        )
        self.conn.execute(
            "INSERT INTO presets VALUES (?,?,?,?,?,?,?,?,?,?)",
            (pid, name, plugin, plugin_type, category, json.dumps(tags or []),
             json.dumps(parameters), 0, preset.created_at, file_path),
        )
        self.conn.commit()
        return preset

    def load_preset(self, preset_id: str) -> Optional[Preset]:
        row = self.conn.execute("SELECT * FROM presets WHERE id=?", (preset_id,)).fetchone()
        if not row:
            return None
        return self._row_to_preset(row)

    def browse(
        self,
        plugin: Optional[str] = None,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        min_rating: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 50,
    ) -> List[Preset]:
        q = "SELECT * FROM presets WHERE 1=1"
        params: List = []
        if plugin:
            q += " AND plugin LIKE ?"; params.append(f"%{plugin}%")
        if category:
            q += " AND category=?"; params.append(category)
        if min_rating is not None:
            q += " AND rating>=?"; params.append(min_rating)
        if search:
            q += " AND (name LIKE ? OR tags LIKE ?)"; params.append(f"%{search}%"); params.append(f"%{search}%")
        q += " ORDER BY rating DESC, created_at DESC LIMIT ?"; params.append(limit)
        rows = self.conn.execute(q, params).fetchall()
        result = []
        for row in rows:
            p = self._row_to_preset(row)
            if tag and tag.lower() not in [t.lower() for t in p.tags]:
                continue
            result.append(p)
        return result

    def rate_preset(self, preset_id: str, rating: int) -> bool:
        rating = max(-5, min(5, rating))
        cur = self.conn.execute("UPDATE presets SET rating=? WHERE id=?", (rating, preset_id))
        self.conn.commit()
        return cur.rowcount > 0

    def delete_preset(self, preset_id: str) -> bool:
        cur = self.conn.execute("DELETE FROM presets WHERE id=?", (preset_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def categories(self) -> List[str]:
        rows = self.conn.execute("SELECT DISTINCT category FROM presets").fetchall()
        return [r[0] for r in rows]

    def plugins(self) -> List[str]:
        rows = self.conn.execute("SELECT DISTINCT plugin FROM presets").fetchall()
        return [r[0] for r in rows]

    def export_presets(self, path: str) -> int:
        rows = self.conn.execute("SELECT * FROM presets").fetchall()
        data = [self._row_to_preset(r).to_dict() for r in rows]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return len(data)

    def import_presets(self, path: str) -> int:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        count = 0
        for item in data:
            self.save_preset(
                name=item["name"], plugin=item["plugin"], plugin_type=item["plugin_type"],
                category=item["category"], parameters=item["parameters"],
                tags=item.get("tags", []), file_path=item.get("file_path"),
            )
            count += 1
        return count

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM presets").fetchone()[0]

    # ---------- helpers ----------

    @staticmethod
    def _row_to_preset(row: sqlite3.Row) -> Preset:
        return Preset(
            id=row["id"], name=row["name"], plugin=row["plugin"],
            plugin_type=row["plugin_type"], category=row["category"],
            tags=json.loads(row["tags"] or "[]"),
            parameters=json.loads(row["parameters"] or "{}"),
            rating=row["rating"] or 0, created_at=row["created_at"] or "",
            file_path=row["file_path"],
        )

    def close(self) -> None:
        self.conn.close()


def save_preset(name: str, plugin: str, plugin_type: str, category: str,
                parameters: Dict, tags: Optional[List[str]] = None) -> Dict:
    mgr = PresetManager()
    return mgr.save_preset(name, plugin, plugin_type, category, parameters, tags).to_dict()


def browse_presets(plugin: Optional[str] = None, category: Optional[str] = None,
                   tag: Optional[str] = None, min_rating: Optional[int] = None,
                   search: Optional[str] = None) -> List[Dict]:
    mgr = PresetManager()
    return [p.to_dict() for p in mgr.browse(plugin, category, tag, min_rating, search)]


def rate_preset(preset_id: str, rating: int) -> bool:
    mgr = PresetManager()
    return mgr.rate_preset(preset_id, rating)


def list_categories() -> List[str]:
    mgr = PresetManager()
    return mgr.categories()


if __name__ == "__main__":
    mgr = PresetManager()
    p = mgr.save_preset("Sub Bass", "Operator", "ableton", "bass",
                        {"osc": "sine", "cutoff": 120}, tags=["sub", "808"])
    print(f"Saved: {p.id} {p.name}")
    print(f"Browse: {len(mgr.browse(category='bass'))} bass presets")
    print(f"Rate: {mgr.rate_preset(p.id, 5)}")
    print(f"Categories: {mgr.categories()}")
    mgr.close()