"""
Ableton Brain - Phase 3: Project Sharing & Education Tools
Cross-DAW project sharing, templates, tutorials, and learning resources
"""

import json
import uuid
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import zipfile
import base64


class SharePermission(Enum):
    VIEW = "view"
    COMMENT = "comment"
    EDIT = "edit"
    ADMIN = "admin"


class ProjectVisibility(Enum):
    PRIVATE = "private"
    LINK = "link"  # Anyone with link
    PUBLIC = "public"


@dataclass
class SharedProject:
    """Shared project metadata"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    owner_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    visibility: ProjectVisibility = ProjectVisibility.PRIVATE
    permissions: Dict[str, SharePermission] = field(default_factory=dict)  # user_id -> permission
    tags: List[str] = field(default_factory=list)
    daw_origin: str = ""  # Original DAW
    daw_compatible: List[str] = field(default_factory=list)  # Compatible DAWs
    thumbnail: Optional[str] = None  # Base64 encoded
    download_count: int = 0
    fork_count: int = 0
    like_count: int = 0
    version: int = 1
    project_data: Optional[Dict] = None  # Universal project format


@dataclass
class ProjectTemplate:
    """Project template for education/quick start"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: str = ""  # genre, technique, template
    difficulty: str = "beginner"  # beginner, intermediate, advanced
    tags: List[str] = field(default_factory=list)
    author: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    project_data: Dict = field(default_factory=dict)  # Universal project
    tutorial_steps: List['TutorialStep'] = field(default_factory=list)
    estimated_time: int = 0  # Minutes
    required_plugins: List[str] = field(default_factory=list)


@dataclass
class TutorialStep:
    """Interactive tutorial step"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    action_type: str = "info"  # info, create_track, add_device, draw_notes, automate, play
    target_track: Optional[str] = None
    target_device: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    validation: Optional[Dict[str, Any]] = None  # How to verify completion
    hint: Optional[str] = None
    order: int = 0


@dataclass
class LearningPath:
    """Structured learning curriculum"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    level: str = "beginner"
    modules: List['LearningModule'] = field(default_factory=list)
    estimated_hours: float = 0
    prerequisites: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class LearningModule:
    """Module within a learning path"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    tutorials: List[str] = field(default_factory=list)  # Tutorial IDs
    order: int = 0
    estimated_minutes: int = 0


class ProjectSharingManager:
    """Manage project sharing, templates, and education content"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.projects_dir = self.storage_path / "projects"
        self.templates_dir = self.storage_path / "templates"
        self.learning_dir = self.storage_path / "learning"
        
        self.projects_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        self.learning_dir.mkdir(exist_ok=True)
        
        # In-memory caches
        self._projects: Dict[str, SharedProject] = {}
        self._templates: Dict[str, ProjectTemplate] = {}
        self._learning_paths: Dict[str, LearningPath] = {}
        
        self._load_all()
    
    def _load_all(self):
        """Load all content from disk"""
        # Projects
        for f in self.projects_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    proj = SharedProject(**data)
                    self._projects[proj.id] = proj
            except Exception as e:
                print(f"Error loading project {f}: {e}")
        
        # Templates
        for f in self.templates_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    # Convert tutorial steps
                    steps = [TutorialStep(**s) for s in data.get('tutorial_steps', [])]
                    data['tutorial_steps'] = steps
                    template = ProjectTemplate(**data)
                    self._templates[template.id] = template
            except Exception as e:
                print(f"Error loading template {f}: {e}")
        
        # Learning paths
        for f in self.learning_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    modules = [LearningModule(**m) for m in data.get('modules', [])]
                    data['modules'] = modules
                    path = LearningPath(**data)
                    self._learning_paths[path.id] = path
            except Exception as e:
                print(f"Error loading learning path {f}: {e}")
    
    # Project sharing
    
    def create_shared_project(self, name: str, owner_id: str, project_data: Dict,
                              description: str = "", tags: List[str] = None,
                              visibility: ProjectVisibility = ProjectVisibility.PRIVATE) -> SharedProject:
        """Create a new shared project"""
        project = SharedProject(
            name=name,
            description=description,
            owner_id=owner_id,
            tags=tags or [],
            visibility=visibility,
            project_data=project_data,
            daw_origin=project_data.get('daw_specific', {}).get('origin', ''),
            daw_compatible=self._detect_compatible_daws(project_data)
        )
        
        self._projects[project.id] = project
        self._save_project(project)
        return project
    
    def _detect_compatible_daws(self, project_data: Dict) -> List[str]:
        """Detect which DAWs can open this project"""
        # Based on features used
        compatible = ['ableton', 'reaper']  # Base support
        
        # Check for features that limit compatibility
        has_advanced_automation = False
        has_complex_routing = False
        
        for track in project_data.get('tracks', []):
            if track.get('automation'):
                has_advanced_automation = True
            if track.get('input_routing') or track.get('output_routing'):
                has_complex_routing = True
        
        if not has_advanced_automation and not has_complex_routing:
            compatible.extend(['logic', 'flstudio', 'cubase', 'protools'])
        
        return list(set(compatible))
    
    def _save_project(self, project: SharedProject):
        """Save project to disk"""
        filepath = self.projects_dir / f"{project.id}.json"
        with open(filepath, 'w') as f:
            json.dump(asdict(project), f, indent=2, default=str)
    
    def get_project(self, project_id: str) -> Optional[SharedProject]:
        return self._projects.get(project_id)
    
    def list_projects(self, owner_id: str = None, visibility: ProjectVisibility = None,
                      tags: List[str] = None, limit: int = 50) -> List[SharedProject]:
        """List projects with filters"""
        projects = list(self._projects.values())
        
        if owner_id:
            projects = [p for p in projects if p.owner_id == owner_id]
        if visibility:
            projects = [p for p in projects if p.visibility == visibility]
        if tags:
            projects = [p for p in projects if any(t in p.tags for t in tags)]
        
        # Sort by updated_at desc
        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects[:limit]
    
    def update_project(self, project_id: str, updates: Dict) -> Optional[SharedProject]:
        """Update project metadata"""
        project = self._projects.get(project_id)
        if not project:
            return None
        
        for key, value in updates.items():
            if hasattr(project, key):
                setattr(project, key, value)
        
        project.updated_at = datetime.now().isoformat()
        project.version += 1
        self._save_project(project)
        return project
    
    def fork_project(self, project_id: str, new_owner_id: str, new_name: str = None) -> Optional[SharedProject]:
        """Create a fork of a project"""
        original = self._projects.get(project_id)
        if not original:
            return None
        
        fork = SharedProject(
            name=new_name or f"{original.name} (fork)",
            description=original.description,
            owner_id=new_owner_id,
            tags=original.tags.copy(),
            visibility=ProjectVisibility.PRIVATE,
            project_data=original.project_data.copy() if original.project_data else None,
            daw_origin=original.daw_origin,
            daw_compatible=original.daw_compatible.copy()
        )
        
        self._projects[fork.id] = fork
        self._save_project(fork)
        
        original.fork_count += 1
        self._save_project(original)
        
        return fork
    
    def export_project_package(self, project_id: str, output_path: Path,
                               include_audio: bool = True) -> bool:
        """Export project as portable package (.abpz)"""
        project = self._projects.get(project_id)
        if not project or not project.project_data:
            return False
        
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Main project file
                zf.writestr('project.abp', json.dumps(project.project_data, indent=2))
                
                # Metadata
                meta = {
                    'name': project.name,
                    'description': project.description,
                    'version': project.version,
                    'exported_at': datetime.now().isoformat(),
                    'daw_origin': project.daw_origin,
                    'daw_compatible': project.daw_compatible
                }
                zf.writestr('meta.json', json.dumps(meta, indent=2))
                
                # TODO: Include audio files if include_audio
                
            return True
        except Exception as e:
            print(f"Export error: {e}")
            return False
    
    def import_project_package(self, package_path: Path, owner_id: str) -> Optional[SharedProject]:
        """Import project from portable package"""
        try:
            with zipfile.ZipFile(package_path, 'r') as zf:
                # Read project data
                project_json = zf.read('project.abp')
                project_data = json.loads(project_json)
                
                # Read metadata
                meta_json = zf.read('meta.json')
                meta = json.loads(meta_json)
                
                # Create project
                project = self.create_shared_project(
                    name=meta.get('name', package_path.stem),
                    owner_id=owner_id,
                    project_data=project_data,
                    description=meta.get('description', ''),
                    tags=[]
                )
                
                return project
        except Exception as e:
            print(f"Import error: {e}")
            return None
    
    # Templates
    
    def create_template(self, name: str, description: str, project_data: Dict,
                        category: str = "", difficulty: str = "beginner",
                        tags: List[str] = None, author: str = "",
                        tutorial_steps: List[TutorialStep] = None,
                        required_plugins: List[str] = None) -> ProjectTemplate:
        """Create a project template"""
        template = ProjectTemplate(
            name=name,
            description=description,
            category=category,
            difficulty=difficulty,
            tags=tags or [],
            author=author,
            project_data=project_data,
            tutorial_steps=tutorial_steps or [],
            required_plugins=required_plugins or []
        )
        
        self._templates[template.id] = template
        self._save_template(template)
        return template
    
    def _save_template(self, template: ProjectTemplate):
        filepath = self.templates_dir / f"{template.id}.json"
        data = asdict(template)
        # Convert tutorial steps to dicts
        data['tutorial_steps'] = [asdict(s) for s in template.tutorial_steps]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def get_template(self, template_id: str) -> Optional[ProjectTemplate]:
        return self._templates.get(template_id)
    
    def list_templates(self, category: str = None, difficulty: str = None,
                       tags: List[str] = None) -> List[ProjectTemplate]:
        templates = list(self._templates.values())
        
        if category:
            templates = [t for t in templates if t.category == category]
        if difficulty:
            templates = [t for t in templates if t.difficulty == difficulty]
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]
        
        return templates
    
    def create_project_from_template(self, template_id: str, owner_id: str,
                                     name: str = None) -> Optional[SharedProject]:
        """Create a new project from template"""
        template = self._templates.get(template_id)
        if not template:
            return None
        
        project = self.create_shared_project(
            name=name or template.name,
            owner_id=owner_id,
            project_data=template.project_data.copy(),
            description=template.description,
            tags=template.tags.copy()
        )
        
        return project
    
    # Learning paths
    
    def create_learning_path(self, name: str, description: str, level: str = "beginner",
                             modules: List[LearningModule] = None,
                             prerequisites: List[str] = None,
                             tags: List[str] = None) -> LearningPath:
        path = LearningPath(
            name=name,
            description=description,
            level=level,
            modules=modules or [],
            prerequisites=prerequisites or [],
            tags=tags or []
        )
        
        # Calculate estimated hours
        total_minutes = sum(m.estimated_minutes for m in path.modules)
        path.estimated_hours = total_minutes / 60
        
        self._learning_paths[path.id] = path
        self._save_learning_path(path)
        return path
    
    def _save_learning_path(self, path: LearningPath):
        filepath = self.learning_dir / f"{path.id}.json"
        data = asdict(path)
        data['modules'] = [asdict(m) for m in path.modules]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def get_learning_path(self, path_id: str) -> Optional[LearningPath]:
        return self._learning_paths.get(path_id)
    
    def list_learning_paths(self, level: str = None, tags: List[str] = None) -> List[LearningPath]:
        paths = list(self._learning_paths.values())
        
        if level:
            paths = [p for p in paths if p.level == level]
        if tags:
            paths = [p for p in paths if any(tag in p.tags for tag in tags)]
        
        return paths


# Built-in templates
def create_builtin_templates(sharing: ProjectSharingManager):
    """Create built-in templates for common genres/workflows"""
    
    # Basic EDM Template
    edm_project = {
        "name": "EDM Starter",
        "tempo": 128.0,
        "time_signature_numerator": 4,
        "time_signature_denominator": 4,
        "tracks": [
            {"name": "Kick", "type": "audio", "volume": 0.9},
            {"name": "Snare/Clap", "type": "audio", "volume": 0.7},
            {"name": "Hi-Hats", "type": "audio", "volume": 0.5},
            {"name": "Bass", "type": "midi", "volume": 0.8},
            {"name": "Lead", "type": "midi", "volume": 0.7},
            {"name": "Pad", "type": "midi", "volume": 0.5},
            {"name": "FX", "type": "audio", "volume": 0.4}
        ]
    }
    
    sharing.create_template(
        name="EDM Starter Template",
        description="Complete EDM track structure with kick, bass, lead, and FX tracks",
        category="genre/edm",
        difficulty="beginner",
        tags=["edm", "electronic", "dance", "starter"],
        author="Ableton Brain",
        project_data=edm_project,
        required_plugins=["Serum", "FabFilter Pro-Q"]
    )
    
    # Hip Hop Template
    hiphop_project = {
        "name": "Hip Hop Starter",
        "tempo": 90.0,
        "time_signature_numerator": 4,
        "time_signature_denominator": 4,
        "tracks": [
            {"name": "Kick", "type": "audio", "volume": 1.0},
            {"name": "Snare", "type": "audio", "volume": 0.9},
            {"name": "Hi-Hats", "type": "audio", "volume": 0.6},
            {"name": "808 Bass", "type": "midi", "volume": 0.85},
            {"name": "Sample", "type": "audio", "volume": 0.7},
            {"name": "Vocal", "type": "audio", "volume": 0.8},
            {"name": "Ad-libs", "type": "audio", "volume": 0.5}
        ]
    }
    
    sharing.create_template(
        name="Hip Hop Starter Template",
        description="Classic boom-bap / trap structure with 808 bass and sample tracks",
        category="genre/hiphop",
        difficulty="beginner",
        tags=["hiphop", "trap", "beats", "starter"],
        author="Ableton Brain",
        project_data=hiphop_project,
        required_plugins=["Decimort", "RC-20"]
    )
    
    # Mixing Template
    mixing_project = {
        "name": "Mixing Template",
        "tempo": 120.0,
        "time_signature_numerator": 4,
        "time_signature_denominator": 4,
        "tracks": [
            {"name": "Drums Bus", "type": "group", "volume": 1.0},
            {"name": "├ Kick", "type": "audio", "volume": 0.9},
            {"name": "├ Snare", "type": "audio", "volume": 0.8},
            {"name": "├ Overheads", "type": "audio", "volume": 0.6},
            {"name": "├ Room", "type": "audio", "volume": 0.4},
            {"name": "Bass Bus", "type": "group", "volume": 0.8},
            {"name": "├ Sub Bass", "type": "midi", "volume": 0.7},
            {"name": "├ Mid Bass", "type": "midi", "volume": 0.6},
            {"name": "Instruments Bus", "type": "group", "volume": 0.7},
            {"name": "Vocals Bus", "type": "group", "volume": 0.8},
            {"name": "├ Lead Vocal", "type": "audio", "volume": 0.9},
            {"name": "├ Backing Vox", "type": "audio", "volume": 0.5},
            {"name": "FX Bus", "type": "group", "volume": 0.5},
            {"name": "Master Bus", "type": "master", "volume": 1.0}
        ]
    }
    
    sharing.create_template(
        name="Professional Mixing Template",
        description="Industry-standard bus routing for mixing with groups for drums, bass, instruments, vocals",
        category="workflow/mixing",
        difficulty="intermediate",
        tags=["mixing", "template", "routing", "bus"],
        author="Ableton Brain",
        project_data=mixing_project,
        required_plugins=["FabFilter Pro-Q 3", "FabFilter Pro-C 2", "Saturn 2"]
    )
    
    # Tutorial: Basic Beat Making
    beat_tutorial_steps = [
        TutorialStep(
            title="Create a Drum Rack",
            description="Add a Drum Rack to a MIDI track and load kick, snare, and hi-hat samples",
            action_type="create_track",
            parameters={"track_type": "midi", "device": "Drum Rack"},
            validation={"device_type": "DrumRack", "min_samples": 3},
            hint="Drag samples from browser into Drum Rack pads",
            order=1
        ),
        TutorialStep(
            title="Program a Basic Beat",
            description="Draw a 4-on-the-floor kick pattern and add snare on beats 2 and 4",
            action_type="draw_notes",
            parameters={"pattern": "kick_4_on_floor", "snare_on": [2, 4]},
            validation={"notes_count": 16, "has_kick": True, "has_snare": True},
            hint="Use the pencil tool in the MIDI editor",
            order=2
        ),
        TutorialStep(
            title="Add Hi-Hat Pattern",
            description="Program 8th note hi-hats with velocity variation",
            action_type="draw_notes",
            parameters={"pattern": "hihat_8ths", "velocity_variation": 0.2},
            validation={"notes_count": 16},
            hint="Vary velocity for groove - lower on off-beats",
            order=3
        ),
        TutorialStep(
            title="Add Bass Line",
            description="Create a MIDI track with a bass synth and write a simple bass line",
            action_type="create_track",
            parameters={"track_type": "midi", "device": "Serum"},
            validation={"device_type": "Serum", "notes_count": 8},
            hint="Follow the root notes of your kick pattern",
            order=4
        ),
        TutorialStep(
            title="Arrange Your Beat",
            description="Duplicate the loop and create an 8-bar arrangement with variation",
            action_type="arrange",
            parameters={"bars": 8, "variations": True},
            validation={"arrangement_length": 8},
            hint="Remove elements in intro, add fills every 4 bars",
            order=5
        )
    ]
    
    sharing.create_template(
        name="Beat Making Tutorial",
        description="Step-by-step guide to creating your first beat from scratch",
        category="tutorial/beatmaking",
        difficulty="beginner",
        tags=["tutorial", "beatmaking", "beginner", "drums"],
        author="Ableton Brain",
        project_data={"name": "My First Beat", "tempo": 120.0},
        tutorial_steps=beat_tutorial_steps,
        estimated_time=30,
        required_plugins=[]
    )
    
    print("Built-in templates created")


# Demo
if __name__ == "__main__":
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Path(tmpdir) / "sharing"
        sharing = ProjectSharingManager(storage)
        
        # Create built-in templates
        create_builtin_templates(sharing)
        
        # List templates
        print("\n=== Templates ===")
        for t in sharing.list_templates():
            print(f"  {t.name} ({t.category}) - {t.difficulty}")
        
        # Create project from template
        templates = sharing.list_templates(category="genre/edm")
        if templates:
            project = sharing.create_project_from_template(templates[0].id, "user-1", "My EDM Track")
            print(f"\nCreated project: {project.name} (ID: {project.id})")
        
        # Create learning path
        module1 = LearningModule(
            name="Beat Fundamentals",
            description="Learn basic drum programming",
            tutorials=[t.id for t in sharing.list_templates(category="tutorial/beatmaking")],
            order=1,
            estimated_minutes=30
        )
        
        path = sharing.create_learning_path(
            name="Electronic Music Production 101",
            description="Complete beginner course for electronic music",
            level="beginner",
            modules=[module1],
            tags=["course", "beginner", "electronic"]
        )
        print(f"\nCreated learning path: {path.name} ({path.estimated_hours:.1f} hours)")
        
        # Export/import test
        export_path = Path(tmpdir) / "test_project.abpz"
        if project:
            sharing.export_project_package(project.id, export_path)
            print(f"Exported to {export_path}")
            
            imported = sharing.import_project_package(export_path, "user-2")
            print(f"Imported: {imported.name} (ID: {imported.id})")