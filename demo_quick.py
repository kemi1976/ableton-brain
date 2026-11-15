#!/usr/bin/env python3
"""
Quick Demo: ABLETON BRAIN Universal MIDI System
Shows the system working in a single, easy-to-run script.
"""

import sys
sys.path.insert(0, 'src')

from pathlib import Path
from core.universal_midi_translator import (
    UniversalMIDITranslator, 
    ControlMapping,
    ControllerType,
    DAWPlatform
)

def main():
    print("🚀 ABLETON BRAIN Quick Demo")
    print("=" * 40)
    
    # Initialize
    translator = UniversalMIDITranslator()
    
    # Show database stats
    artists = translator.get_artist_database()
    genres = translator.get_genres()
    
    print(f"\n📚 Database: {len(artists)} artists, {len(genres)} genres")
    print(f"🎧 Controllers: {len([t.value for t in ControllerType])} types supported")
    print(f"💻 DAWs: {len([t.value for t in DAWPlatform])} platforms supported")
    
    # Demo 1: Create a control mapping
    print("\n🎮 Demo 1: Control Mapping")
    mapping = ControlMapping(
        physical_control="knob_1",
        daw_parameter="filter_cutoff",
        curve_profile="log",
        range_min=0,
        range_max=127
    )
    translator.map_control(mapping)
    print(f"   ✓ Mapped knob_1 → filter_cutoff")
    
    # Demo 2: Look up parameter mapping
    print("\n📍 Demo 2: Parameter Lookup")
    found = translator.get_mapping_for_parameter("filter_cutoff")
    print(f"   ✓ Found {len(found)} mapping(s) for 'filter_cutoff'")
    
    # Demo 3: Export configuration
    print("\n📤 Demo 3: Config Export")
    config = translator.export_config()
    print(f"   ✓ Exported: {config['database_stats']}")
    
    print("\n✅ Demo complete - all systems working!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)