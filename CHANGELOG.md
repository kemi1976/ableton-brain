# Changelog for ABLETON BRAIN

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **Firefox HTML Database GUI**: Rebuilt `firefox_edm_database.html` with proper `<script>` tag structure
  - Fixed malformed HTML from missing opening `<script>` tag
  - Integrated all 23 artists and 11 labels
  - Added worldwide_genres section (6 genres)
  - Implemented Firefox compatibility fix for back/forward navigation
  - Added bilingual Arabic-English/English-Hebrew support
  - Inline JavaScript database for offline Firefox compatibility

### Removed
- Obsolete `fix_html.py` and `fix_html_complete.py` repair scripts (superseded by `rebuild_html.py`)

## [3.0.0] - 2026-11-04

### Added
- Universal MIDI controller support (MIDI, USB-OTG, Bluetooth, Gamecontrollers)
- Cross-DAW adapter framework (Ableton, Reaper, Logic, FL Studio, Cubase, Pro Tools)
- 23 artists with genre-specific techniques and equipment data
- 15 genre coverage: Drum & Bass, Grime, UK Garage, Liquid DnB, Neurofunk, Techstep, Hardcore, UK Jungle, Hip Hop, Dubstep, Trap, Jazz Fusion, Smooth Jazz, 4x4 Garage, Ambient Techno
- Python package structure with `src/` layout
- Comprehensive test suite (20 tests)
- Configuration export/import functionality
- Control mapping system with curve profiles
- Package metadata and type hints

### Infrastructure
- pyproject.toml with full build configuration
- requirements.txt for dependency management
- pytest configuration
- Code style configurations (black, ruff, mypy)

### Project Structure
```
ableton-brain/
├── database.json          # Artist/equipment/genre database
├── pyproject.toml         # Build configuration
├── requirements.txt       # Dependencies
├── README.md              # Documentation
├── demo_quick.py          # Quick demo script
├── tests/
│   └── test_ableton_brain.py
└── src/
    ├── abrain/
    │   ├── __init__.py
    │   ├── version.py
    │   └── py.typed
    └── core/
        ├── __init__.py
        ├── universal_midi_translator.py
        └── daws/
            ├── __init__.py
            ├── base_adapter.py
            ├── ableton_adapter.py
            ├── reaper_adapter.py
            ├── logic_adapter.py
            ├── flstudio_adapter.py
            ├── cubase_adapter.py
            └── protools_adapter.py
```

### Installation
```bash
pip install -e .
# or for development
pip install -e ".[dev]"
```

### Usage
```bash
# Run tests
pytest -v

# Quick demo
python demo_quick.py

# Main application
python -m abrain
```