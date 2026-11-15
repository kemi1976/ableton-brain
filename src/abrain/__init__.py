"""
ABlenET Brain - Cross-DAW AI music production ecosystem

Universal MIDI controller integration, genre-specific intelligence,
and DAW-agnostic architecture.
"""

from .core.universal_midi_translator import (
    UniversalMIDITranslator,
    ControllerType,
    DAWPlatform,
    ControlMapping,
)
from .version import VERSION, AUTHOR

__version__ = VERSION
__author__ = AUTHOR
__all__ = [
    "UniversalMIDITranslator",
    "ControllerType", 
    "DAWPlatform",
    "ControlMapping",
    "VERSION",
    "AUTHOR",
]


def main():
    """Main entry point for the ABLETON BRAIN command-line interface."""
    import asyncio
    
    async def run_async():
        print("=" * 60)
        print("🎵 ABLETON BRAIN: Cross-DAW Controller System")
        print("=" * 60)
        
        translator = UniversalMIDITranslator()
        
        # Load database info
        artists = translator.get_artist_database()
        genres = translator.get_genres()
        
        print(f"\n📊 Database Statistics:")
        print(f"   Artists: {len(artists)}")
        print(f"   Genres: {len(genres)}")
        print(f"   Engine: {translator._rtmidi_available and 'rtmidi (full)' or 'basic MIDI'}")
        
        # Discover controllers
        print(f"\n🔍 Discovering controllers...")
        controllers = await translator.discover_controllers()
        print(f"   Found {len(controllers)} controller(s)")
        
        return {
            "artists": len(artists),
            "genres": len(genres),
            "controllers": len(controllers),
            "supported_daws": list(translator.get_daw_adapters().keys())
        }
    
    result = asyncio.run(run_async())
    print(f"\n✅ Status: Ready for cross-platform music production")
    return result


def discovery():
    """CLI entry point for controller discovery."""
    import asyncio
    import json
    
    async def discover():
        translator = UniversalMIDITranslator()
        controllers = await translator.discover_controllers()
        
        summary = {
            "controllers": controllers,
            "supported_daw_adapters": list(translator.get_daw_adapters().keys()),
            "supported_controller_types": [t.value for t in ControllerType]
        }
        return json.dumps(summary, indent=2, default=str)
    
    result = asyncio.run(discover())
    print(result)
    return result