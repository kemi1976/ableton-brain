#!/usr/bin/env python3
"""
Workflow Tutorial Module
Interactive in-DAW tours: step-by-step guided lessons with progress tracking.
Competitor parity: Splice Rheo Point, Ableton Learn.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TutorialStep:
    """One step in a tour."""
    id: str
    title: str
    instruction: str            # plain-language text shown to user
    tool_suggested: Optional[str] = None   # MCP tool to run next
    checkpoint: Optional[str] = None       # condition to auto-advance
    hint: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "instruction": self.instruction,
            "tool_suggested": self.tool_suggested, "checkpoint": self.checkpoint,
            "hint": self.hint,
        }


@dataclass
class Tour:
    """A guided tutorial."""
    id: str
    title: str
    description: str
    steps: List[TutorialStep]
    estimated_minutes: int

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "estimated_minutes": self.estimated_minutes,
        }


@dataclass
class Session:
    """User's progress through a tour."""
    tour_id: str
    step_index: int
    completed_steps: List[str] = field(default_factory=list)
    started_at: str = ""
    last_activity: str = ""

    def to_dict(self) -> dict:
        return {
            "tour_id": self.tour_id, "step_index": self.step_index,
            "completed_steps": self.completed_steps,
            "started_at": self.started_at, "last_activity": self.last_activity,
        }


class WorkflowTutorials:
    """Registry of tours + user sessions."""

    def __init__(self):
        self.tours: Dict[str, Tour] = {}
        self.sessions: Dict[str, Session] = {}
        self._register_default_tours()

    def _register_default_tours(self) -> None:
        # Tour 1: First project
        self.tours["first_project"] = Tour(
            id="first_project",
            title="Your First Project",
            description="Make a beat from scratch: kick, bass, melody, arrangement.",
            estimated_minutes=20,
            steps=[
                TutorialStep("s1", "Create a MIDI track",
                             "Add a new MIDI track for your drum kit.",
                             tool_suggested="create_midi_track",
                             checkpoint="track_created"),
                TutorialStep("s2", "Load a drum rack",
                             "Drag a drum rack onto the track.",
                             tool_suggested="load_device",
                             checkpoint="device_loaded"),
                TutorialStep("s3", "Program a kick pattern",
                             "Draw kick hits on beats 1, 1.5, 2, 2.5, 3, 3.5, 4.",
                             tool_suggested="add_notes_to_clip",
                             checkpoint="notes_added"),
                TutorialStep("s4", "Add a bassline",
                             "Create a second MIDI track and draw a simple bass pattern.",
                             tool_suggested="create_midi_track",
                             checkpoint="bass_added"),
                TutorialStep("s5", "Arrange into scenes",
                             "Turn your loop into scenes in the clip launcher.",
                             tool_suggested="create_scene",
                             checkpoint="scenes_created"),
            ],
        )
        # Tour 2: Mixing basics
        self.tours["mixing_basics"] = Tour(
            id="mixing_basics",
            description="Balance levels, EQ, and compress your mix.",
            estimated_minutes=25,
            steps=[
                TutorialStep("s1", "Set starting levels",
                             "Bring all faders down, then raise the most important track first.",
                             tool_suggested="set_device_parameter",
                             checkpoint="levels_set"),
                TutorialStep("s2", "High-pass non-bass tracks",
                             "Cut everything below 100Hz on non-bass instruments.",
                             tool_suggested="set_device_parameter",
                             checkpoint="eq_applied"),
                TutorialStep("s3", "Check for clashes",
                             "Run collision detection on your tracks.",
                             tool_suggested="detect_collisions",
                             checkpoint="collisions_checked"),
                TutorialStep("s4", "Add bus compression",
                             "Glue your drum bus with a gentle compressor.",
                             tool_suggested="load_device",
                             checkpoint="compressor_added"),
            ],
        )
        # Tour 3: Arrangement
        self.tours["arranging"] = Tour(
            id="arranging",
            title="Arranging a Song",
            description="Turn an 8-bar loop into a full song structure.",
            estimated_minutes=30,
            steps=[
                TutorialStep("s1", "Analyze your loop",
                             "Run arrangement analysis on your stems.",
                             tool_suggested="analyze_arrangement",
                             checkpoint="analysis_done"),
                TutorialStep("s2", "Pick a template",
                             "Choose a genre arrangement template.",
                             tool_suggested="generate_arrangement_template",
                             checkpoint="template_picked"),
                TutorialStep("s3", "Build scenes",
                             "Create clip launcher scenes for each section.",
                             tool_suggested="create_scene",
                             checkpoint="scenes_built"),
                TutorialStep("s4", "Record arrangement",
                             "Fire scenes in order to record the arrangement view.",
                             tool_suggested="fire_clip",
                             checkpoint="arrangement_recorded"),
            ],
        )

    def list_tours(self) -> List[Dict]:
        return [t.to_dict() for t in self.tours.values()]

    def get_tour(self, tour_id: str) -> Optional[Tour]:
        return self.tours.get(tour_id)

    def start_tour(self, tour_id: str, user_id: str = "default") -> Session:
        tour = self.get_tour(tour_id)
        if not tour:
            raise ValueError(f"tour not found: {tour_id}")
        now = datetime.now().isoformat()
        sess = Session(tour_id=tour_id, step_index=0, started_at=now, last_activity=now)
        self.sessions[user_id] = sess
        return sess

    def get_session(self, user_id: str = "default") -> Optional[Session]:
        return self.sessions.get(user_id)

    def current_step(self, user_id: str = "default") -> Optional[Dict]:
        sess = self.get_session(user_id)
        if not sess:
            return None
        tour = self.get_tour(sess.tour_id)
        if not tour or sess.step_index >= len(tour.steps):
            return {"done": True, "message": "Tour complete!"}
        step = tour.steps[sess.step_index]
        return {
            "done": False,
            "step_number": sess.step_index + 1,
            "total_steps": len(tour.steps),
            "step": step.to_dict(),
            "progress": round(sess.step_index / len(tour.steps) * 100),
        }

    def next_step(self, user_id: str = "default") -> Optional[Dict]:
        sess = self.get_session(user_id)
        if not sess:
            return None
        tour = self.get_tour(sess.tour_id)
        if not tour or sess.step_index >= len(tour.steps):
            return {"done": True}
        sess.step_index += 1
        sess.completed_steps.append(tour.steps[sess.step_index - 1].id)
        sess.last_activity = datetime.now().isoformat()
        return self.current_step(user_id)

    def hint_for(self, user_id: str = "default") -> Optional[str]:
        step = self.current_step(user_id)
        if step and not step.get("done"):
            return step["step"].get("hint")
        return None


def start_tour(tour_id: str, user_id: str = "default") -> Dict:
    mgr = WorkflowTutorials()
    return mgr.start_tour(tour_id, user_id).to_dict()


def current_step(user_id: str = "default") -> Optional[Dict]:
    mgr = WorkflowTutorials()
    return mgr.current_step(user_id)


def list_tours() -> List[Dict]:
    mgr = WorkflowTutorials()
    return mgr.list_tours()


if __name__ == "__main__":
    mgr = WorkflowTutorials()
    print(f"Tours: {[t['id'] for t in mgr.list_tours()]}")
    sess = mgr.start_tour("first_project")
    print(f"Started: {sess.tour_id}")
    step = mgr.current_step()
    print(f"Step 1: {step['step']['title']} -> {step['step']['instruction']}")
    mgr.next_step()
    step2 = mgr.current_step()
    print(f"Step 2: {step2['step']['title']}")