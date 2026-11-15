"""
Ableton Brain - Phase 4: Plugin System
Enables third-party extensions and integrations
"""

import asyncio
import json
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
import sys


class PluginType(Enum):
    DAW_ADAPTER = "daw_adapter"
    CONTROLLER_ADAPTER = "controller_adapter"
    MIDI_PROCESSOR = "midi_processor"
    AUDIO_PROCESSOR = "audio_processor"
    AI_MODEL = "ai_model"
    UI_EXTENSION = "ui_extension"
    EXPORT_FORMAT = "export_format"
    THEME = "theme"


@dataclass
class PluginMetadata:
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    entry_point: str  # module.ClassName
    dependencies: List[str] = field(default_factory=list)
    min_ableton_brain_version: str = "1.0.0"
    config_schema: Dict = field(default_factory=dict)


@dataclass
class PluginInstance:
    metadata: PluginMetadata
    instance: Any
    enabled: bool = True
    config: Dict = field(default_factory=dict)


class PluginManager:
    """Manages plugin discovery, loading, and lifecycle"""
    
    def __init__(self, plugin_dirs: List[Path] = None):
        self.plugin_dirs = plugin_dirs or [
            Path(__file__).parent.parent.parent / "plugins",
            Path.home() / ".ableton_brain" / "plugins"
        ]
        self.plugins: Dict[str, PluginInstance] = {}
        self.hooks: Dict[str, List[Callable]] = {}
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        for d in self.plugin_dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    def register_hook(self, hook_name: str, callback: Callable):
        """Register a callback for a hook"""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        self.hooks[hook_name].append(callback)
    
    async def trigger_hook(self, hook_name: str, *args, **kwargs):
        """Trigger all callbacks for a hook"""
        if hook_name in self.hooks:
            for callback in self.hooks[hook_name]:
                try:
                    if inspect.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    print(f"Hook {hook_name} error: {e}")
    
    def discover_plugins(self) -> List[PluginMetadata]:
        """Discover all plugins in plugin directories"""
        discovered = []
        
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue
            
            for plugin_path in plugin_dir.iterdir():
                if plugin_path.is_dir():
                    manifest_path = plugin_path / "plugin.json"
                    if manifest_path.exists():
                        try:
                            with open(manifest_path) as f:
                                manifest = json.load(f)
                            metadata = PluginMetadata(**manifest)
                            discovered.append(metadata)
                        except Exception as e:
                            print(f"Failed to load plugin manifest {manifest_path}: {e}")
        
        return discovered
    
    def load_plugin(self, metadata: PluginMetadata, config: Dict = None) -> bool:
        """Load a plugin by its metadata"""
        try:
            # Parse entry point (module.ClassName)
            module_name, class_name = metadata.entry_point.rsplit('.', 1)
            
            # Add plugin directory to path
            plugin_path = None
            for base_dir in self.plugin_dirs:
                candidate = base_dir / metadata.name
                if candidate.exists():
                    plugin_path = candidate
                    break
            
            if plugin_path:
                sys.path.insert(0, str(plugin_path))
            
            # Import module
            module = importlib.import_module(module_name)
            plugin_class = getattr(module, class_name)
            
            # Instantiate
            instance = plugin_class()
            
            # Initialize if method exists
            if hasattr(instance, 'initialize'):
                if inspect.iscoroutinefunction(instance.initialize):
                    asyncio.create_task(instance.initialize(config or {}))
                else:
                    instance.initialize(config or {})
            
            # Store
            self.plugins[metadata.name] = PluginInstance(
                metadata=metadata,
                instance=instance,
                config=config or {}
            )
            
            print(f"✅ Loaded plugin: {metadata.name} v{metadata.version}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load plugin {metadata.name}: {e}")
            return False
    
    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin"""
        if name in self.plugins:
            instance = self.plugins[name].instance
            if hasattr(instance, 'shutdown'):
                if inspect.iscoroutinefunction(instance.shutdown):
                    asyncio.create_task(instance.shutdown())
                else:
                    instance.shutdown()
            del self.plugins[name]
            print(f"🔌 Unloaded plugin: {name}")
            return True
        return False
    
    def get_plugin(self, name: str) -> Optional[PluginInstance]:
        return self.plugins.get(name)
    
    def list_plugins(self, plugin_type: PluginType = None) -> List[PluginMetadata]:
        result = []
        for instance in self.plugins.values():
            if plugin_type is None or instance.metadata.plugin_type == plugin_type:
                result.append(instance.metadata)
        return result
    
    def get_daw_adapters(self) -> Dict[str, Type]:
        """Get all loaded DAW adapter plugins"""
        adapters = {}
        for instance in self.plugins.values():
            if instance.metadata.plugin_type == PluginType.DAW_ADAPTER:
                adapters[instance.metadata.name] = type(instance.instance)
        return adapters
    
    def get_controller_adapters(self) -> Dict[str, Type]:
        """Get all loaded controller adapter plugins"""
        adapters = {}
        for instance in self.plugins.values():
            if instance.metadata.plugin_type == PluginType.CONTROLLER_ADAPTER:
                adapters[instance.metadata.name] = type(instance.instance)
        return adapters


# Built-in plugin base classes
class BasePlugin:
    """Base class for all plugins"""
    
    def __init__(self):
        self.config = {}
    
    def initialize(self, config: Dict):
        self.config = config
    
    def shutdown(self):
        pass


class DAWAdapterPlugin(BasePlugin):
    """Base class for DAW adapter plugins"""
    
    def get_adapter_class(self) -> Type:
        """Return the DAW adapter class"""
        raise NotImplementedError


class ControllerAdapterPlugin(BasePlugin):
    """Base class for controller adapter plugins"""
    
    def get_adapter_class(self) -> Type:
        """Return the controller adapter class"""
        raise NotImplementedError


class MIDIProcessorPlugin(BasePlugin):
    """Base class for MIDI processor plugins"""
    
    async def process_midi(self, message: Dict, context: Dict) -> Dict:
        """Process a MIDI message"""
        return message


class AIModelPlugin(BasePlugin):
    """Base class for AI model plugins"""
    
    async def generate(self, prompt: str, context: Dict) -> Any:
        """Generate content from prompt"""
        raise NotImplementedError


class ExportFormatPlugin(BasePlugin):
    """Base class for export format plugins"""
    
    async def export(self, project_data: Dict, output_path: str, options: Dict) -> bool:
        """Export project to format"""
        raise NotImplementedError


# Global plugin manager
plugin_manager = PluginManager()


def create_plugin_manifest(
    name: str,
    version: str,
    author: str,
    description: str,
    plugin_type: PluginType,
    entry_point: str,
    dependencies: List[str] = None,
    config_schema: Dict = None
) -> Dict:
    """Create a plugin manifest dictionary"""
    return {
        "name": name,
        "version": version,
        "author": author,
        "description": description,
        "plugin_type": plugin_type.value,
        "entry_point": entry_point,
        "dependencies": dependencies or [],
        "config_schema": config_schema or {}
    }


if __name__ == "__main__":
    print("Plugin System - Phase 4")
    print("Enables third-party extensions for Ableton Brain")
    print()
    print("Plugin types:")
    for pt in PluginType:
        print(f"  - {pt.value}")
    print()
    print("To create a plugin:")
    print("1. Create a directory in plugins/")
    print("2. Add plugin.json manifest")
    print("3. Implement plugin class inheriting from base class")
    print("4. Plugin will auto-discover on startup")