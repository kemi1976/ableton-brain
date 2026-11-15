#!/usr/bin/env python3
"""
ABLETON BRAIN - Intelligent Music Production Assistant
Integrates with Ableton Live via MCP for AI-driven production support
"""

import json
import os
from pathlib import Path
from datetime import datetime
import sys

# ABLETON BRAIN Database paths
BRAIN_DIR = Path(__file__).parent
DATABASE_FILE = BRAIN_DIR / "database.json"
GUI_FILE = BRAIN_DIR / "gui.html"

class AbletonBrain:
    """AI-driven production assistant with comprehensive music knowledge"""
    
    def __init__(self):
        self.database = self.load_database()
        self.artists = self.database.get("artists", {})
        self.engineers = self.database.get("engineers", {})
        self.techniques = self.database.get("techniques", {})
        
    def load_database(self):
        """Load the ABLETON BRAIN database"""
        if DATABASE_FILE.exists():
            with open(DATABASE_FILE, 'r') as f:
                return json.load(f)
        return self.get_default_database()
    
    def get_default_database(self):
        """Return default database structure"""
        return {
            "metadata": {
                "name": "ABLETON BRAIN",
                "version": "3.0.0",
                "created": datetime.now().strftime("%Y-%m-%d")
            },
            "artists": {},
            "engineers": {},
            "techniques": {}
        }
    
    def get_artist(self, artist_id):
        """Get detailed information about an artist"""
        artist_id = artist_id.lower().replace(" ", "_")
        return self.artists.get(artist_id)
    
    def get_technique(self, technique_id):
        """Get technique documentation"""
        return self.techniques.get(technique_id)
    
    def get_engineer(self, engineer_id):
        """Get engineer profile"""
        return self.engineers.get(engineer_id)
    
    def search_artists(self, query):
        """Search artists by name or technique"""
        query = query.lower()
        results = []
        for artist_id, artist in self.artists.items():
            if (query in artist_id.lower() or 
                query in artist.get("genre", "").lower() or
                query in artist.get("origin", "").lower() or
                any(query in t.lower() for t in artist.get("signature_techniques", []))):
                results.append({
                    "id": artist_id,
                    "name": artist_id.replace("_", " ").title(),
                    "genre": artist.get("genre", "Unknown"),
                    "origin": artist.get("origin", "Unknown")
                })
        return results
    
    def get_dnb_pioneers(self):
        """Get all Drum & Bass pioneers"""
        dnb_genres = ["Drum & Bass", "Liquid Drum & Bass", "Techstep", "Jungle"]
        dnb_artists = []
        for artist_id, artist in self.artists.items():
            if any(g in artist.get("genre", "") for g in dnb_genres):
                dnb_artists.append({
                    "id": artist_id,
                    **artist
                })
        return dnb_artists
    
    def get_uk_artists(self):
        """Get all UK artists"""
        uk_artists = []
        for artist_id, artist in self.artists.items():
            if "UK" in artist.get("origin", "") or "London" in artist.get("origin", ""):
                uk_artists.append({
                    "id": artist_id,
                    **artist
                })
        return uk_artists
    
    def get_resource_links(self, artist_id):
        """Get learning resources for an artist"""
        artist = self.get_artist(artist_id)
        if not artist:
            return []
        return artist.get("learning_resources", {})
    
    def generate_ableton_template(self, artist_id, genre="DnB"):
        """Generate Ableton Live template with artist techniques"""
        artist = self.get_artist(artist_id)
        if not artist:
            return None
        
        template = {
            "artist": artist_id,
            "genre": genre,
            "bpm": 174 if "Drum & Bass" in genre else 140,
            "signature_techniques": artist.get("signature_techniques", []),
            "chain_order": [
                {"name": "Drum Bus", "color": "#FF6B35"},
                {"name": "Bass Bus", "color": "#00FF88"},
                {"name": "Lead Bus", "color": "#00BFFF"},
                {"name": "FX Bus", "color": "#FF69B4"}
            ],
            "recommended_vst": ["Serum", "Massive", "Omnisphere"],
            "template_structure": {
                "intro": {"bars": 16, "energy": "Low"},
                "buildup": {"bars": 8, "energy": "Rising"},
                "drop": {"bars": 16, "energy": "High"},
                "breakdown": {"bars": 16, "energy": "Medium"},
                "outro": {"bars": 8, "energy": "Declining"}
            }
        }
        return template
    
    def display_all_artists(self):
        """Display all artists in console-friendly format"""
        print("=" * 60)
        print("ABLETON BRAIN - ARTIST DATABASE")
        print("=" * 60)
        print(f"Total Artists: {len(self.artists)}")
        print(f"Total Engineers: {len(self.engineers)}")
        print(f"Total Techniques: {len(self.techniques)}")
        print("=" * 60)
        
        for artist_id, artist in self.artists.items():
            print(f"\n🎯 {artist_id.replace('_', ' ').title()}")
            print(f"   Genre: {artist.get('genre', 'N/A')}")
            print(f"   Origin: {artist.get('origin', 'N/A')}")
            print(f"   Active: {artist.get('years_active', 'N/A')}")
            print(f"   Techniques: {', '.join(artist.get('signature_techniques', [])[:3])}")
        
        return self.artists
    
    def launch_gui(self):
        """Launch the web-based GUI"""
        if GUI_FILE.exists():
            import webbrowser
            webbrowser.open(f"file://{GUI_FILE.absolute()}")
            print(f"✅ GUI launched: {GUI_FILE}")
        else:
            print("❌ GUI file not found")
    
    def open_resource(self, artist_id):
        """Open primary learning resource"""
        resources = self.get_resource_links(artist_id)
        if resources and resources.get("video_tutorials"):
            import webbrowser
            webbrowser.open(resources["video_tutorials"][0])
            return True
        return False


# Initialize the brain
brain = AbletonBrain()

# Main interactive interface
def main():
    print("\n" + "="*60)
    print("🧠 ABLETON BRAIN - Music Production Intelligence Hub")
    print("="*60)
    print("\n📚 Available Commands:")
    print("  artists     - List all artists")
    print("  dnb         - Show DnB pioneers") 
    print("  uk          - Show UK artists")
    print("  search <term> - Search artists")
    print("  gui         - Launch web GUI")
    print("  help        - Show this help")
    print("  quit        - Exit")
    
    while True:
        try:
            cmd = input("\nAIA> ").strip().split()
            if not cmd:
                continue
            
            command = cmd[0].lower()
            
            if command in ['quit', 'exit', 'q']:
                print("\n🎵 Happy producing!")
                break
            
            elif command == 'help':
                main()
            
            elif command == 'artists':
                brain.display_all_artists()
            
            elif command == 'dnb':
                dnb = brain.get_dnb_pioneers()
                print(f"\n🎧 Drum & Bass Pioneers ({len(dnb)} artists):")
                for artist in dnb:
                    print(f"  • {artist['id'].replace('_', ' ').title()} - {artist['origin']}")
            
            elif command == 'uk':
                uk = brain.get_uk_artists()
                print(f"\n🇬🇧 UK Artists ({len(uk)} artists):")
                for artist in uk:
                    print(f"  • {artist['id'].replace('_', ' ').title()} - {artist['genre']}")
            
            elif command == 'search':
                if len(cmd) > 1:
                    results = brain.search_artists(cmd[1])
                    print(f"\n🔍 Search results for '{cmd[1]}':")
                    for r in results:
                        print(f"  • {r['name']} - {r['genre']} ({r['origin']})")
                else:
                    print("Usage: search <term>")
            
            elif command == 'gui':
                brain.launch_gui()
            
            else:
                print(f"❓ Unknown command: {command}")
                print("Type 'help' for available commands")
        
        except KeyboardInterrupt:
            print("\n\n🎵 Happy producing!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()