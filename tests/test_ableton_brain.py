"""
Test suite for ABLETON BRAIN
Using pytest-style testing with red-green-refactor cycle
"""

import pytest
import json
import sys
from pathlib import Path
from typing import Dict, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.universal_midi_translator import (
    UniversalMIDITranslator,
    ControllerType,
    ControlMapping,
    DAWPlatform
)


class TestDatabaseIntegrity:
    """Tests for the ABLETON BRAIN database"""
    
    @pytest.fixture
    def translator(self):
        return UniversalMIDITranslator()
    
    def test_database_loads_successfully(self, translator):
        """Test that the database loads without errors"""
        assert translator.database is not None
        assert len(translator.database) > 0
    
    def test_artists_count_minimum_23(self, translator):
        """Test we have at least 23 artists"""
        artists = translator.database.get('artists', {})
        assert len(artists) >= 23, f"Expected 23+ artists, got {len(artists)}"
    
    def test_genres_count_exactly_15(self, translator):
        """Test we have exactly 15 genres in metadata"""
        metadata = translator.database.get('metadata', {})
        genres = metadata.get('genres', [])
        assert len(genres) == 15, f"Expected 15 genres, got {len(genres)}"
    
    def test_all_genres_valid(self, translator):
        """Test that all genres are properly formatted"""
        genres = translator.get_genres()
        assert len(genres) > 0
        for genre in genres:
            assert isinstance(genre, str)
            assert len(genre) >= 3  # Minimum reasonable genre name length
            # Accept both single-word genres (Dubstep, Trap) and multi-word (Drum & Bass)
    
    def test_kevin_eubank_profile_exists(self, translator):
        """Test Kevin Eubank is in database"""
        artists = translator.database.get('artists', {})
        assert 'kevin_eubank' in artists, "Kevin Eubank should be in database"
        
        kevin = artists['kevin_eubank']
        assert kevin.get('genre') == 'Jazz Fusion / Smooth Jazz'
        assert kevin.get('origin') == 'Philadelphia, USA'
    
    def test_metadata_complete(self, translator):
        """Test metadata has all required fields"""
        metadata = translator.database.get('metadata', {})
        required_fields = ['name', 'version', 'created', 'description', 'genres']
        
        for field in required_fields:
            assert field in metadata, f"Missing metadata field: {field}"


class TestControllerDiscovery:
    """Tests for controller discovery system"""
    
    @pytest.fixture
    def translator(self):
        return UniversalMIDITranslator()
    
    @pytest.mark.asyncio
    async def test_discover_returns_list(self, translator):
        """Test that discovery returns a list"""
        controllers = await translator.discover_controllers()
        assert isinstance(controllers, list)
    
    @pytest.mark.asyncio
    async def test_discovered_controllers_have_required_fields(self, translator):
        """Test discovered controllers have all required fields"""
        controllers = await translator.discover_controllers()
        
        for ctrl in controllers:
            assert 'name' in ctrl
            assert 'type' in ctrl
            assert 'direction' in ctrl
            assert 'auto_detected' in ctrl


class TestDAWAdapters:
    """Tests for DAW adapter framework"""
    
    @pytest.fixture
    def translator(self):
        return UniversalMIDITranslator()
    
    def test_all_six_daws_supported(self, translator):
        """Test all 6 DAW platforms are supported"""
        adapters = translator.get_daw_adapters()
        
        expected_daws = ['ableton', 'reaper', 'logic', 'flstudio', 'cubase', 'protools']
        
        for daw in expected_daws:
            assert daw in adapters, f"Missing adapter for {daw}"
    
    def test_artist_database_accessible(self, translator):
        """Test artist database is readable"""
        artists = translator.get_artist_database()
        assert isinstance(artists, dict)
        assert len(artists) >= 23


class TestControlMapping:
    """Tests for MIDI control mapping"""
    
    @pytest.fixture
    def translator(self):
        return UniversalMIDITranslator()
    
    def test_control_mapping_creation(self, translator):
        """Test creating a control mapping"""
        mapping = ControlMapping(
            physical_control="knob_1",
            daw_parameter="filter_cutoff",
            curve_profile="log"
        )
        
        assert mapping.physical_control == "knob_1"
        assert mapping.daw_parameter == "filter_cutoff"
        assert mapping.curve_profile == "log"
    
    def test_mapping_registration(self, translator):
        """Test registering mappings"""
        initial_count = len(translator.active_mappings)
        
        mapping = ControlMapping(
            physical_control="button_a",
            daw_parameter="play_button"
        )
        
        translator.map_control(mapping)
        
        assert len(translator.active_mappings) == initial_count + 1
    
    def test_parameter_mapping_lookup(self, translator):
        """Test finding mappings by parameter"""
        translator.map_control(ControlMapping(
            physical_control="knob_1",
            daw_parameter="volume_1"
        ))
        
        translator.map_control(ControlMapping(
            physical_control="knob_2",
            daw_parameter="filter_cutoff"
        ))
        
        mappings = translator.get_mapping_for_parameter("volume_1")
        assert len(mappings) == 1
        assert mappings[0].physical_control == "knob_1"


class TestGenreCoverage:
    """Tests for genre completeness"""
    
    @pytest.fixture
    def translator(self):
        return UniversalMIDITranslator()
    
    def test_all_15_genres_present(self, translator):
        """Test all 15 genres are represented"""
        expected_genres = [
            "Drum & Bass",
            "Grime", 
            "UK Garage",
            "Liquid DnB",
            "Neurofunk",
            "Techstep",
            "Hardcore",
            "UK Jungle",
            "Hip Hop",
            "Dubstep",
            "Trap",
            "Jazz Fusion",
            "Smooth Jazz",
            "4x4 Garage",
            "Ambient Techno"
        ]
        
        genres = translator.database.get('metadata', {}).get('genres', [])
        
        for genre in expected_genres:
            assert genre in genres, f"Missing genre: {genre}"
    
    def test_artists_span_multiple_genres(self, translator):
        """Test that artists are distributed across genres"""
        artists = translator.get_artist_database()
        
        # At least some artists should have Grime or DnB
        grime_artists = [a for a, d in artists.items() 
                        if 'grime' in d.get('genre', '').lower() or 
                           'drum' in d.get('genre', '').lower()]
        
        assert len(grime_artists) >= 3, "Should have multiple grime/drum artists"


class TestExportImport:
    """Tests for configuration export/import"""
    
    @pytest.fixture
    def translator(self):
        return UniversalMIDITranslator()
    
    def test_export_config_structure(self, translator):
        """Test export config has correct structure"""
        config = translator.export_config()
        
        assert 'database_stats' in config
        assert 'controllers' in config
        assert 'supported_daws' in config
        assert 'supported_controllers' in config
        
        assert config['database_stats']['artists'] >= 23
        assert len(config['supported_daws']) == 6
        assert len(config['supported_controllers']) >= 5
    
    def test_config_roundtrip(self, translator):
        """Test config can be exported and re-imported"""
        # Add a test mapping
        translator.map_control(ControlMapping(
            physical_control="test_knob",
            daw_parameter="test_param"
        ))
        
        # Export
        config = translator.export_config()
        
        # Create new instance and import
        new_translator = UniversalMIDITranslator()
        new_translator.load_config(config)
        
        # Verify
        assert len(new_translator.active_mappings) >= 1
        assert new_translator.active_mappings[0].physical_control == "test_knob"
    
    def test_control_mapping_with_range(self, translator):
        """Test control mapping with range parameters"""
        mapping = ControlMapping(
            physical_control="filter_knob",
            daw_parameter="lfo_rate",
            curve_profile="exp",
            range_min=0.0,
            range_max=127.0
        )
        assert mapping.range_min == 0.0
        assert mapping.range_max == 127.0
        assert mapping.hz_output == False
    
    def test_rtmidi_detection(self, translator):
        """Test rtmidi availability check"""
        # Should have the method and return a boolean
        assert hasattr(translator, '_rtmidi_available')
        assert isinstance(translator._rtmidi_available, bool)
    
    def test_get_controllers_database(self, translator):
        """Test controller database extraction"""
        controllers = translator.get_controllers_database()
        assert isinstance(controllers, dict)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])