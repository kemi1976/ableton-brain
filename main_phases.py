#!/usr/bin/env python3
"""
Main entry point for ABLETON BRAIN - Updated with Phases 1-3
"""

import asyncio
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent / 'src'))
# Add Services path (at vault root - 3 levels up from ableton-brain)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'Services'))

from core.universal_midi_translator import UniversalMIDITranslator
from core.universal_midi_translator import ControlMapping, ControllerType

from core.adapters import (
    BaseDAWAdapter, DAWAdapterRegistry, DAWPlatform, TrackType,
    TrackInfo, DeviceInfo, ProjectInfo, daw_registry, connect_daw, quick_action,
    ReaperAdapter
)
from core.controllers import (
    UniversalController, BaseControllerAdapter, Push1Adapter, Push2Adapter,
    LaunchpadAdapter, GamepadAdapter, BluetoothMIDIAdapter, USBMIDIAdapter,
    ControllerType as CtrlType, ControlType, ControlElement, ControllerMapping,
    DEFAULT_MAPPINGS, apply_mapping
)

def load_themes() -> Dict:
    theme_path = Path(__file__).parent / "themes.json"
    if theme_path.exists():
        with open(theme_path, 'r') as f:
            return json.load(f)
    return {"themes": {}, "presets": {}}

def create_preset(name: str, mappings: List[Dict], description: str = "") -> Dict:
    return {"name": name, "description": description, "mappings": mappings,
            "created_at": str(Path(__file__).parent.stat().st_mtime), "version": "1.0"}

def save_preset(preset: Dict, filepath: Optional[str] = None) -> Path:
    if not filepath:
        filepath = Path(__file__).parent / "presets" / f"{preset['name'].lower().replace(' ', '_')}.json"
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(preset, f, indent=2)
    return filepath

def load_preset(filepath: str) -> Dict:
    with open(filepath, 'r') as f:
        return json.load(f)

def list_presets() -> List[Dict]:
    presets_dir = Path(__file__).parent / "presets"
    if not presets_dir.exists():
        return []
    presets = []
    for preset_file in presets_dir.glob("*.json"):
        try:
            preset = load_preset(str(preset_file))
            preset['path'] = str(preset_file)
            presets.append(preset)
        except Exception:
            pass
    return presets

class DAWQuickActions:
    def __init__(self, translator: UniversalMIDITranslator):
        self.translator = translator
        self.active_daw = None
        self.daw_adapter = None
    def set_active_daw(self, daw_name: str):
        if daw_name in self.translator.get_daw_adapters():
            self.active_daw = daw_name
            self.daw_adapter = daw_registry.get(daw_name)
        else:
            raise ValueError(f"Unsupported DAW: {daw_name}")
    async def _execute(self, action: str, **kwargs) -> bool:
        if not self.daw_adapter:
            print(f"⚠️  No DAW adapter for {self.active_daw}")
            return False
        if not self.daw_adapter.connected:
            print(f"🔌 Connecting to {self.active_daw}...")
            await self.daw_adapter.connect()
        action_map = {
            "save": self.daw_adapter.save_project,
            "export_wav": lambda: self.daw_adapter.export_audio(kwargs.get("path", "export.wav")),
            "new_midi_track": lambda: self.daw_adapter.create_track(kwargs.get("name", "New Track"), TrackType.MIDI),
            "new_audio_track": lambda: self.daw_adapter.create_track(kwargs.get("name", "New Track"), TrackType.AUDIO),
            "arm_first": self.daw_adapter.arm_track,
            "play": self.daw_adapter.start_playback,
            "stop": self.daw_adapter.stop_playback,
            "undo": self.daw_adapter.undo,
            "redo": self.daw_adapter.redo,
            "set_tempo": lambda: self.daw_adapter.set_tempo(kwargs.get("tempo", 120)),
        }
        if action in action_map:
            try:
                result = await action_map[action]()
                print(f"✅ {action} completed on {self.active_daw}")
                return result
            except Exception as e:
                print(f"❌ {action} failed: {e}")
                return False
        print(f"⚠️  Unknown action: {action}")
        return False
    def save_project(self) -> bool: return asyncio.run(self._execute("save"))
    def bounce_to_wav(self) -> bool: return asyncio.run(self._execute("export_wav"))
    def undo(self) -> bool: return asyncio.run(self._execute("undo"))
    def redo(self) -> bool: return asyncio.run(self._execute("redo"))
    def create_new_track(self, name: str = "New Track") -> bool: return asyncio.run(self._execute("new_midi_track", name=name))
    def arm_track_for_recording(self, track_number: int = 1) -> bool: return asyncio.run(self._execute("arm_first"))

class ThemeManager:
    def __init__(self):
        self.themes = load_themes()
        self.current_theme = "dark"
    def get_theme(self, name: str) -> Optional[Dict]:
        return self.themes.get('themes', {}).get(name)
    def apply_theme(self, name: str) -> bool:
        if name in self.themes.get('themes', {}):
            self.current_theme = name
            print(f"🎨 Theme applied: {name}")
            return True
        return False
    def list_themes(self) -> List[str]:
        return list(self.themes.get('themes', {}).keys())

def start_midi_monitor():
    try:
        from core.midi_monitor import MIDIConsoleVisualizer, process_midi_message
        print("\n" + "="*60)
        print("🎵 MIDI MONITOR - Real-time Traffic Visualization")
        print("="*60 + "\n")
        print("This monitor will display incoming MIDI messages in real-time.")
        print("Press Ctrl+C to stop monitoring.\n")
        viz = MIDIConsoleVisualizer(max_events=30)
        viz.display()
        return viz
    except ImportError:
        print("⚠️  MIDI Monitor not available - module not found")
        return None

async def demo_daw_adapters():
    print("\n" + "="*60)
    print("🔧 PHASE 1: Core Framework - DAW Adapters")
    print("="*60)
    print(f"\nRegistered DAW adapters: {daw_registry.list_available()}")
    print("\nBaseDAWAdapter defines interface:")
    for method in dir(BaseDAWAdapter):
        if not method.startswith('_') and callable(getattr(BaseDAWAdapter, method)):
            print(f"  - {method}")
    reaper = ReaperAdapter()
    print(f"\nReaper adapter: {reaper.reaper_path or 'Not found'}")
    if reaper.reaper_path:
        connected = await reaper.connect()
        print(f"Reaper connection: {'✅' if connected else '❌'}")

async def demo_universal_controller():
    print("\n" + "="*60)
    print("🔧 PHASE 3: Universal Controller Layer")
    print("="*60)
    uc = UniversalController()
    print("\nSupported controller types:")
    for ctrl in CtrlType:
        print(f"  - {ctrl.value}")
    print("\nAuto-detecting controllers...")
    detected = await uc.auto_detect()
    connected = [k for k, v in detected.items() if v]
    print(f"\nConnected: {connected if connected else 'None'}")
    if uc.active_controller:
        print(f"Active: {uc.active_controller.controller_type.value}")
        if apply_mapping(uc.active_controller, "ableton_mixer"):
            print("Applied 'ableton_mixer' preset mapping")
        print(f"Mapped parameters: {len(uc.active_controller.mapping.daw_mappings)}")

async def demo_task_orchestrator():
    print("\n" + "="*60)
    print("🔧 MULTI-MACHINE: Task Orchestrator")
    print("="*60)
    try:
        import sys
        from pathlib import Path
        # Import individual modules directly from Services
        services_path = str(Path(__file__).resolve().parent.parent.parent / 'Services')
        sys.path.insert(0, services_path)
        import task_orchestrator
        from task_orchestrator import TaskOrchestrator, create_task_from_template
        orchestrator = TaskOrchestrator()
        status = orchestrator.get_status()
        print(f"\nMachines configured: {len(status['machines'])}")
        for ip, m in status['machines'].items():
            print(f"  - {m['name']} ({ip}) - {m['role']} - Load: {m['current_tasks']}/{m['max_concurrent']}")
        task = create_task_from_template("drum_bass_variants")
        print(f"\nCreated task: {task.name} ({task.id})")
        print(f"Steps: {len(task.steps)}")
        for i, step in enumerate(task.steps):
            print(f"  {i+1}. {step.get('cmd', 'unknown')} on {step.get('machine', 'auto')}")
    except ImportError as e:
        print(f"Task orchestrator not available: {e}")

async def async_main():
    print("🎵 ABLETON BRAIN - Cross-DAW Music Production System")
    print("=" * 60)
    print("Phases 1-3: Core Framework | Reaper Adapter | Universal Controllers")
    print("Multi-Machine: Task Orchestration | MIDI Bridge | File Sync")
    
    translator = UniversalMIDITranslator()
    database = translator.database
    artists = database.get('artists', {})
    engineers = database.get('engineers', {})
    techniques = database.get('techniques', {})
    genres = translator.get_genres()
    
    print(f"\n📊 Database Statistics:")
    print(f"   Artists:    {len(artists)}")
    print(f"   Genres:     {len(genres)}")
    print(f"   Engineers:  {len(engineers)}")
    print(f"   Techniques: {len(techniques)}")
    
    print(f"\n🎧 Legacy Controllers:")
    for ct in ControllerType:
        print(f"   - {ct.value}")
    
    print(f"\n💻 Legacy DAWs:")
    daw_adapters = translator.get_daw_adapters()
    for daw_name in daw_adapters.keys():
        print(f"   - {daw_name.title()}")
    
    print(f"\n🔧 Phase 1-3 DAW Adapters: {daw_registry.list_available()}")
    
    theme_manager = ThemeManager()
    print(f"\n🎨 Available Themes:")
    for theme_name in theme_manager.list_themes():
        print(f"   - {theme_name}")
    
    print(f"\n💾 Available Presets:")
    presets = list_presets()
    if presets:
        for preset in presets:
            print(f"   - {preset['name']}: {preset.get('description', 'No description')}")
    else:
        print("   (No custom presets yet)")
    
    print(f"\n🖥️  System Tray Controller:")
    try:
        from tray_controller import create_system_tray
        tray = create_system_tray()
        if tray.start():
            print("   ✅ System tray running")
    except Exception as e:
        print(f"   ⚠️  System tray unavailable: {e}")
    
    await demo_daw_adapters()
    await demo_universal_controller()
    await demo_task_orchestrator()
    
    print(f"\n✅ System Ready!")
    print(f"\n🔧 Quick Commands Available:")
    print(f"   - midi_monitor()       : Start real-time MIDI visualization")
    print(f"   - daw_quick_actions    : Access one-click DAW operations")
    print(f"   - theme_manager        : Switch between {len(theme_manager.list_themes())} themes")
    print(f"   - list_presets()       : Browse controller mappings")
    print(f"   - save_preset()        : Save your current mapping")
    print(f"   - demo_daw_adapters()  : Show Phase 1 DAW framework")
    print(f"   - demo_universal_controller() : Show Phase 3 controllers")
    print(f"   - demo_task_orchestrator()    : Show multi-machine tasks")
    
    return {"artists": len(artists), "genres": len(genres), "controllers": len(ControllerType),
            "daws": len(daw_adapters), "phase_daws": len(daw_registry.list_available()),
            "themes": len(theme_manager.list_themes()), "presets": len(presets)}

def main():
    return asyncio.run(async_main())

if __name__ == "__main__":
    result = main()
    print(f"\n📋 Result: {json.dumps(result, indent=2)}")
    sys.exit(0)