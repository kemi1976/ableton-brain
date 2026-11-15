#!/usr/bin/env python3
"""
Preset Browser CLI
==================
Command-line interface for managing controller presets
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent

def list_presets():
    """List all available presets"""
    presets_dir = PROJECT_ROOT / "presets"
    if not presets_dir.exists():
        print("No presets directory found")
        return []
    
    presets = []
    for f in sorted(presets_dir.glob("*.json")):
        try:
            with open(f, 'r') as fp:
                data = json.load(fp)
                presets.append({
                    'name': data.get('name', f.stem),
                    'description': data.get('description', ''),
                    'file': f.name,
                    'mappings': len(data.get('mappings', []))
                })
        except Exception as e:
            print(f"Error reading {f}: {e}")
    
    return presets


def show_preset(preset_file: str):
    """Show details of a specific preset"""
    preset_path = PROJECT_ROOT / "presets" / preset_file
    
    if not preset_path.exists():
        print(f"Preset not found: {preset_file}")
        return None
    
    try:
        with open(preset_path, 'r') as f:
            data = json.load(f)
        
        print(f"\n{'='*60}")
        print(f"PRESET: {data.get('name', 'Unknown')}")
        print(f"{'='*60}")
        print(f"Description: {data.get('description', 'N/A')}")
        print(f"Version: {data.get('version', '1.0')}")
        print(f"Controller Type: {data.get('controller_type', 'Unknown')}")
        print(f"Target DAW: {data.get('daw', 'Universal')}")
        print(f"\nMappings ({len(data.get('mappings', []))}):")
        
        mapping_names = {
            'crossfader': 'Crossfader',
            'volume': 'Volume',
            'filter_cutoff': 'Filter Cutoff',
            'resonance': 'Resonance',
            'attack': 'Attack',
            'release': 'Release',
            'sustain': 'Sustain',
            'decay': 'Decay',
            'pitch_fader': 'Pitch Fader',
            'scratch': 'Scratch',
            'tempo': 'Tempo',
            'pan': 'Pan'
        }
        
        for i, mapping in enumerate(data.get('mappings', []), 1):
            param = mapping.get('daw_parameter', 'Unknown')
            display_name = mapping_names.get(param, param.replace('_', ' ').title())
            print(f"  {i}. {mapping.get('physical_control', 'Unknown'):20s} → {display_name:20s}")
        
        print(f"\n{'='*60}\n")
        return data
    except Exception as e:
        print(f"Error reading preset: {e}")
        return None


def save_preset_cli(name: str, mappings: List[Dict], description: str = "", 
                    controller_type: str = "custom", daw: str = "universal"):
    """Save a new preset via CLI"""
    preset = {
        "name": name,
        "description": description,
        "mappings": mappings,
        "created_at": Path.cwd().isoformat(),
        "version": "1.0",
        "controller_type": controller_type,
        "daw": daw
    }
    
    # Sanitize filename
    filename = name.lower().replace(' ', '_').replace('-', '_') + ".json"
    filepath = PROJECT_ROOT / "presets" / filename
    
    try:
        filepath.parent.mkdir(exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(preset, f, indent=2)
        print(f"✅ Preset saved: {filepath.name}")
        return filepath
    except Exception as e:
        print(f"❌ Error saving preset: {e}")
        return None


def apply_theme_cli(theme_name: str) -> bool:
    """Apply a theme"""
    themes_file = PROJECT_ROOT / "themes.json"
    
    if not themes_file.exists():
        print("No themes.json found")
        return False
    
    try:
        with open(themes_file, 'r') as f:
            themes = json.load(f)
        
        if theme_name in themes.get('themes', {}):
            print(f"🎨 Theme '{theme_name}' is available")
            print(f"   Colors: {list(themes['themes'][theme_name]['colors'].keys())}")
            return True
        else:
            print(f"Theme '{theme_name}' not found")
            print(f"Available themes: {list(themes.get('themes', {}).keys())}")
            return False
    except Exception as e:
        print(f"Error reading themes: {e}")
        return False


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("🎹 Preset Browser CLI")
        print("Usage: preset_browser <command> [args]")
        print("\nCommands:")
        print("  list              List all presets")
        print("  show <name>       Show preset details")
        print("  themes            List available themes")
        print("  theme <name>      Show theme info")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        presets = list_presets()
        if presets:
            print("\n📦 Available Presets:")
            for p in presets:
                print(f"  • {p['name']} ({p['mappings']} mappings)")
        else:
            print("No presets found")
    
    elif command == 'show' and len(sys.argv) > 2:
        show_preset(sys.argv[2])
    
    elif command == 'themes':
        themes_file = PROJECT_ROOT / "themes.json"
        if themes_file.exists():
            with open(themes_file, 'r') as f:
                themes = json.load(f)
            print("\n🎨 Available Themes:")
            for name, data in themes.get('themes', {}).items():
                print(f"  • {name}: {data.get('description', 'A theme')}")
        else:
            print("No themes available")
    
    elif command == 'theme' and len(sys.argv) > 2:
        apply_theme_cli(sys.argv[2])
    
    else:
        print(f"Unknown command: {command}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())