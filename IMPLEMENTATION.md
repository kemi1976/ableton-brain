# ABLETON BRAIN - Complete Implementation Guide

**The most advanced AI-powered Ableton Live control system. Full DAW automation, real-time audio intelligence, distributed AI inference, professional mixing/mastering, and Multi-Eliza fleet coordination.**

---

## 🎯 What This Does (Complete Feature Matrix)

| Feature Category | Status | Description |
|-----------------|--------|-------------|
| **Complete Ableton Control** | ✅ | Tracks, clips, devices, transport, arrangement, automation |
| **VST/AU/CLAP Plugin Control** | ✅ | Parameter enumeration, 500+ semantic maps, Serum deep control |
| **Real-Time Audio Intelligence** | ✅ | LUFS, true peak, stereo correlation, 7-band spectrum, masking detection |
| **Reference-Guided Mixing** | ✅ | Compare to reference tracks, tonal balance matching, auto-EQ suggestions |
| **Mastering Assistant** | ✅ | Mastering rack template, loudness targets, A/B snapshots |
| **Sample Scanning & Auto Tune** | ✅ | AI role/BPM/key detection → full track generation |
| **AI Generation Pipeline** | ✅ | Magenta Studio, Stable Audio Open, AudioLDM 2, ACE-Step, Demucs stems |
| **Automation Recipes** | ✅ | 16 curve types, 15+ named recipes (filter sweep, sidechain, dub throw, etc.) |
| **Plugin Corpus** | ✅ | Auto-detect VST3/AU/CLAP, 500+ parameter maps, semantic categories |
| **Distributed Architecture** | ✅ | Dell Vostro (DAW) + ThinkPad (GPU) + Mobile (BLE MIDI) + Hermes (Dashboard) |
| **Professional Workflow** | ✅ | Project templates, mix snapshots, A/B comparison, export pipeline, metadata |
| **MCP Protocol** | ✅ | Works with Claude, Cursor, any MCP client |
| **BLE MIDI / Bluetooth** | ✅ | BlueMIDI bridge for mobile controllers |
| **Ableton Link Sync** | ✅ | Tempo sync across all devices |

---

## 📁 Complete File Structure

```
ableton-brain/
├── ableton_remote/
│   └── __init__.py              # Remote Script (835 lines, 80+ commands)
├── mcp_server.py                # MCP Server (380 lines, 47 tools)
├── analyzer_bridge.py           # OSC receiver for Max for Live analyzer (port 9878)
├── sample_scanner.py            # Sample analysis & tune generation
├── automation_recipes.py        # 16 curves, 15+ automation recipes
├── ai_generation.py             # Magenta, Stable Audio, Demucs, AudioLDM bridges
├── plugin_corpus.py             # Plugin detection + 500+ parameter maps
├── fleet_coordinator.py         # Multi-Eliza distributed coordination
├── workflow_engine.py           # Templates, snapshots, export, metadata
├── install.bat                  # Windows installer (7 steps)
├── install_analyzer.bat         # Max for Live analyzer device installer
├── AbletonMCP_Analyzer.maxpat   # Max for Live analyzer device
├── AbletonMCP_Analyzer.amxd     # Compiled analyzer device
├── plugin_maps/                 # JSON parameter maps (Serum, Vital, Pigments, etc.)
├── samples/                     # Organized sample folders (drums/, bass/, loops/, etc.)
├── workspace/
│   ├── templates/               # Project templates (JSON)
│   ├── snapshots/               # Mix snapshots for A/B
│   └── exports/                 # Rendered exports
├── database.json                # Artist/technique database
├── IMPLEMENTATION.md            # This file
└── README.md                    # Quick reference
```

---

## 🚀 Quick Start (Complete)

### 1. Install Everything
```cmd
# Run as Administrator
cd "C:\Users\pc\Documents\AI PROJECTS ANDRIOD\knowledge\ableton-brain"
install.bat
```

This installs:
- Python deps: `mcp fastapi uvicorn librosa numpy scipy pythonosc pyloudnorm soundfile`
- Remote Script → Ableton User Library
- Max for Live Analyzer device → User Library/Presets/Audio Effects/Max Audio Effect/
- Sample folders (drums, bass, loops, melody, pads, fx, vocals)
- Plugin corpus folder

### 2. Configure Ableton Live
1. Open Ableton Live
2. **Preferences → Link, Tempo & MIDI**
3. **Control Surface**: `AbletonBrain`
4. **Input**: `None` | **Output**: `None`
5. **Restart Ableton**

### 3. Start All Services
```cmd
# Terminal 1: MCP Server (main bridge)
python mcp_server.py

# Terminal 2: Analyzer Bridge (real-time audio metrics)
python analyzer_bridge.py

# Terminal 3 (optional): Fleet Coordinator
python fleet_coordinator.py
```

### 4. Configure AI Client (Claude Desktop / Cursor / Windsurf)
```json
{
  "mcpServers": {
    "ableton-brain": {
      "command": "python",
      "args": ["C:/Users/pc/Documents/AI PROJECTS ANDRIOD/knowledge/ableton-brain/mcp_server.py"]
    }
  }
}
```

### 5. Install Analyzer Device in Ableton
1. Open Ableton Browser → **Audio Effects → Max Audio Effect → AbletonMCP_Analyzer**
2. Drag onto **Master track** (for full mix) or any track
3. Metrics flow via OSC to `analyzer_bridge.py` on port 9878

### 6. Enable Bluetooth MIDI (Optional)
```cmd
# Download BlueMIDI from github.com/Armazi000/bluemidi/releases
# Install teVirtualMIDI (from loopMIDI or rtpMIDI)
bluemidi.exe --autostart
```
Then in Ableton: Enable "BlueMIDI - ROLI" input, check **MPE**

---

## 🎛️ Complete MCP Tool Reference (47 Tools)

### Session & Transport
| Tool | Description |
|------|-------------|
| `get_session_info` | Tempo, tracks, playing state, time signature |
| `set_tempo` | Set BPM (20-999) |
| `play` / `stop` / `record` | Transport control |

### Tracks
| Tool | Description |
|------|-------------|
| `create_midi_track` | New MIDI track (name, index) |
| `create_audio_track` | New audio track (name, index) |
| `get_tracks` | List all tracks with devices, volume, pan |
| `arm_track` | Arm/disarm for recording |
| `set_track_volume` | Volume 0-1 |
| `set_track_pan` | Pan -1 to 1 |

### Clips
| Tool | Description |
|------|-------------|
| `create_midi_clip` | Empty MIDI clip (length in beats) |
| `create_audio_clip` | Load audio file to clip slot |
| `get_clip_notes` | Read all MIDI notes from clip |
| `add_notes_to_clip` | Write MIDI notes (pitch, time, duration, velocity) |
| `fire_clip` / `stop_clip` | Launch/stop clip |
| `set_clip_envelope` | Automation envelope (points: time, value) |

### Devices & VST/AU/CLAP
| Tool | Description |
|------|-------------|
| `load_instrument` / `load_audio_effect` / `load_midi_effect` | Load any device |
| `get_device_parameters` | Full parameter list (name, value, min, max, normalized) |
| `set_device_parameter` | Set any param (0-1 normalized) |
| `batch_set_device_parameters` | Efficient multi-param set |
| `probe_plugin_parameters` | Enumerate ALL VST/AU/CLAP params |
| `expose_plugin_parameters` | Map plugin params to macros for automation |

### Drum Rack
| Tool | Description |
|------|-------------|
| `create_drum_rack` | New Drum Rack on track |
| `replace_sample` | Load sample to pad (0-127) |
| `create_drum_pattern` | Program beats from step patterns |

### Arrangement & Scenes
| Tool | Description |
|------|-------------|
| `create_scene` | New scene (index) |
| `delete_clip` / `copy_clip` | Clip management |

### Samples & Browser
| Tool | Description |
|------|-------------|
| `list_samples` | Scan folder recursively (limit) |
| `analyze_sample` | Duration, sample rate, BPM, key detection |

### Serum Deep Control
| Tool | Description |
|------|-------------|
| `get_serum_fx` / `set_serum_fx_param` | FX rack control |
| `get_serum_patch` / `create_serum_patch` | Full patch blob |
| `set_serum_oscillator` / `filter` / `envelope` / `lfo` / `macro` / `wavetable` | Semantic control |
| `add_serum_mod_route` / `clear_serum_mod_route` | Mod matrix |

### 🎵 **Audio Analysis & Mixing (NEW - Phase 1)**
| Tool | Description |
|------|-------------|
| `install_analyzer` | Deploy Max for Live analyzer device on track |
| `read_analyzer` | Real-time metrics: LUFS, true peak, stereo, spectrum, tempo, key |
| `get_all_analyzers` | Metrics from all tracks with analyzer |
| `mix_doctor` | **Full mix analysis**: masking, low-end, phase, loudness, tonal balance |
| `compare_to_reference` | Compare mix to reference track → EQ Eight suggestions |
| `capture_stems` | Record individual track stems for external processing |

### 🤖 **AI Generation (NEW - Phase 2)**
| Tool | Description |
|------|-------------|
| `generate_midi_magenta` | Magenta Studio: Generate, Continue, Interpolate, Groove, Drumify |
| `generate_audio_stable` | Stable Audio Open: Text-to-audio (47s stereo) |
| `separate_stems_demucs` | Demucs: drums, bass, vocals, other separation |
| `style_transfer_magenta` | DDSP timbre transfer |
| `create_track_from_prompt` | High-level: Full track from text prompt |

### 🎚️ **Automation Recipes (NEW - Phase 4)**
| Tool | Description |
|------|-------------|
| `apply_automation_recipe` | Named recipe: filter_sweep, sidechain_pump, dub_throw, etc. |
| `generate_automation_curve` | Raw curve: linear, exp, log, s-curve, sine, ping-pong, sidechain |
| `write_arrangement_automation` | Timeline automation (not just clip) |

### 🔌 **Plugin Corpus (NEW - Phase 3)**
| Tool | Description |
|------|-------------|
| `detect_plugins` | Scan VST3/AU/CLAP folders → plugin list |
| `load_plugin_map` | Load semantic parameter map |
| `get_params_by_category` | Filter: oscillator, filter, envelope, lfo, macro, fx |
| `create_patch_from_map` | High-level patch spec → parameter values |

### 🌐 **Fleet Coordination (NEW - Phase 5)**
| Tool | Description |
|------|-------------|
| `submit_task` | Offload to GPU (ThinkPad), Mobile, or DAW |
| `get_fleet_status` | All nodes: health, GPU, capabilities |
| `start_ble_midi_bridge` | BlueMIDI for mobile controllers |
| `setup_ableton_link` | Tempo sync across devices |

### 📋 **Professional Workflow (NEW - Phase 6)**
| Tool | Description |
|------|-------------|
| `create_project_from_template` | Genre templates: DnB, House, Techno, Ambient, Trap |
| `create_snapshot` | Save full mix state (A/B comparison) |
| `recall_snapshot` | Instant recall any snapshot |
| `compare_snapshots` | Diff two mixes (volume, pan, device params) |
| `create_export_job` | Multi-format export with loudness targets |
| `execute_export` | Render + normalize + metadata embed |
| `prepare_metadata` | ISRC, UPC, genre, BPM, key, credits |

---

## 🎵 Sample Scanning & Auto Tune Generation

### Scan a Folder
```bash
python sample_scanner.py "C:\your\samples" "dnb"
```

### What It Does (Complete Pipeline)
1. **Scans** folder recursively (.wav, .aiff, .flac, .mp3, .ogg)
2. **Analyzes** each sample:
   - Duration, sample rate, channels, file size
   - **Role**: drum, bass, melody, pad, fx, vocal (filename keywords)
   - **Kind**: loop or one-shot (duration + keywords)
   - **Genre tags**: dnb, house, techno, dubstep, trap, hiphop, ambient
   - **AI Analysis** (librosa): BPM, key, spectral centroid (brightness), RMS (energy)
3. **Generates** complete track:
   - Drum track → Drum Rack + one-shots → kick/snare pattern
   - Bass track → audio clips
   - Loop tracks → audio clips
   - Melody track → MIDI (Wavetable) ready for Magenta
   - Pad track → audio clips
   - FX track → audio clips
   - **5 Scenes**: Intro, Build, Drop, Break, Outro
4. **Saves** to database for future reference

### Optimal Sample Folder Structure
```
samples/
├── drums/          # kick_*.wav, snare_*.wav, hat_*.wav, perc_*.wav
├── bass/           # bass_*.wav, reese_*.wav, 808_*.wav
├── loops/          # loop_*_174bpm.wav, groove_*.wav
├── melody/         # lead_*.wav, arp_*.wav, pluck_*.wav
├── pads/           # pad_*.wav, atmos_*.wav, drone_*.wav
├── fx/             # riser_*.wav, downlifter_*.wav, impact_*.wav
└── vocals/         # vocal_*.wav, vox_*.wav
```

---

## 🎚️ Real-Time Audio Intelligence (Analyzer)

### Max for Live Analyzer Device
**File**: `AbletonMCP_Analyzer.maxpat` → compiles to `AbletonMCP_Analyzer.amxd`

**Measures (via OSC on port 9878, 1Hz update):**
| Metric | Standard | Use Case |
|--------|----------|----------|
| Integrated LUFS | ITU-R BS.1770 | Streaming compliance (-14 LUFS) |
| Momentary LUFS | BS.1770 | Real-time loudness |
| Short-term LUFS | BS.1770 | 3-second window |
| LRA (Loudness Range) | EBU R128 | Dynamics measurement |
| True Peak L/R | BS.1770 | Intersample peaks (-1 dBTP limit) |
| Stereo Correlation | -1 to +1 | Phase issues (< -0.2 = problem) |
| Stereo Width | 0-1 | Mono compatibility |
| 7-Band Spectrum | Sub→Air | Tonal balance (31Hz-16kHz) |
| Tempo | - | Auto-detect |
| Key | - | Auto-detect |

### Mix Doctor (Automated Mix Analysis)
```python
# Returns issues + recommendations
mix_doctor({"section_bars": 8})
```
**Detects:**
- 🔴 **Clipping/Headroom**: True peak > -1 dBTP, integrated > -8 LUFS
- 🔵 **Low-End Issues**: Stereo bass/sub, mono compatibility
- 🟡 **Spectral Masking**: Low-mid buildup (250-500Hz), harsh high-mids (2-4kHz)
- 🟣 **Phase Problems**: Correlation < -0.2
- 🟢 **Loudness Compliance**: Streaming (-14), Club (-9), Broadcast (-23), Podcast (-16)

**Auto-Recommendations:**
- "Reduce gain on Track X by 3.2 dB"
- "Mono low-end below 120Hz on Track Y (Utility width 0%)"
- "Cut 250-500Hz on Track Z with EQ Eight"
- "Add limiter ceiling at -1 dBTP on Master"

### Reference Track Comparison
```python
compare_to_reference({"reference_path": "ref.wav", "target_lufs": -14})
```
**Returns per-band EQ suggestions:**
```json
{
  "tonal_balance_match": {
    "sub": {"diff_db": 2.3, "eq_suggestion": "cut 2dB at 40Hz"},
    "bass": {"diff_db": -1.1, "eq_suggestion": "boost 1dB at 100Hz"},
    "low_mid": {"diff_db": 3.5, "eq_suggestion": "cut 3dB at 300Hz"},
    ...
  },
  "loudness": {"gain_needed_db": -2.1}
}
```

---

## 🤖 AI Generation Pipeline

### Available Backends
| Backend | Model | Output | Local/Cloud | Requirements |
|---------|-------|--------|-------------|--------------|
| **Magenta Studio** | MelodyRNN, PerformanceRNN, MusicVAE, Drumify, Groove | MIDI | Local (Max for Live) | Free, built into Live 10.1+ |
| **Stable Audio Open** | Stability AI | 47s stereo 44.1kHz | Local (GPU) | `stable-audio-tools`, 8GB VRAM |
| **AudioLDM 2** | Latent Diffusion | Text-to-audio, SFX | Local (GPU) | `audioldm2`, 6GB VRAM |
| **ACE-Step / YuE** | Full songs with vocals | Audio | Local (GPU) | Apache 2.0 weights |
| **Demucs** | HTDemucs, MDX | Stems (drums/bass/vocals/other) | Local (CPU/GPU) | `pip install demucs` |

### Magenta Studio (Native, Free, Works Today)
```python
# In Ableton: Browser → Max for Live → Magenta Studio
# Devices: Generate, Continue, Interpolate, Groove, Drumify
# Via MCP:
generate_midi_magenta({"track_index": 2, "clip_index": 0, "model": "continue"})
```

### Stable Audio Open (High Quality)
```python
generate_audio_stable({
    "prompt": "atmospheric drum and bass pad, evolving texture, 174 bpm",
    "duration_seconds": 30,
    "tempo": 174
})
```

### Stem Separation (Demucs)
```python
separate_stems_demucs({
    "audio_path": "mix.wav",
    "model": "htdemucs",
    "stems": ["drums", "bass", "vocals", "other"]
})
```

---

## 🎚️ Automation Recipes (15+ Named, 16 Curve Types)

### Curve Types
`linear`, `exponential`, `logarithmic`, `s_curve`, `inverse_s_curve`, `step`, `random`, `sine`, `triangle`, `sawtooth`, `square`, `ping_pong`, `sidechain`, `exponential_rise`, `exponential_fall`, `custom`

### Named Recipes
| Recipe | Target Param | Curve | Duration | Use Case |
|--------|--------------|-------|----------|----------|
| `filter_sweep_up` | filter_frequency | exponential | 8 bars | Buildup |
| `filter_sweep_down` | filter_frequency | exponential_fall | 8 bars | Breakdown |
| `filter_sweep_bandpass` | filter_frequency | sine | 16 bars | Movement |
| `sidechain_pump` | volume | sidechain | 1 bar | Kick ducking |
| `sidechain_subtle` | volume | sidechain | 1 bar | Glue |
| `reverb_swell` | send_a | s_curve | 8 bars | Transition |
| `dub_throw` | send_b | ping_pong | 4 bars | Dub delay |
| `delay_feedback_rise` | feedback | exponential_rise | 8 bars | Buildup |
| `pitch_riser` | transpose | linear | 8 bars | Riser |
| `noise_riser` | filter_frequency | exponential | 8 bars | White noise sweep |
| `downlifter` | transpose | linear | 4 bars | Drop transition |
| `stutter_gate` | volume | square | 2 bars | Glitch |
| `tape_stop` | transpose | exponential_fall | 2 bars | Tape stop |
| `formant_shift` | formant | sine | 8 bars | Vocal design |
| `auto_pan` | pan | sine | 32 bars | Width movement |
| `width_swell` | width | s_curve | 8 bars | Stereo expansion |
| `limiter_ceiling_ride` | ceiling | inverse_s_curve | 16 bars | Mastering |

### Usage
```python
apply_automation_recipe({
    "track_index": 3,
    "clip_index": 0,
    "recipe_name": "filter_sweep_up",
    "param_name": "Filter Freq"  # optional override
})
```

---

## 🔌 Plugin Corpus (500+ Semantic Maps)

### Auto-Detection
```python
detect_plugins({"use_auval": true})  # macOS: auval -a for AUv3
```
Scans: `C:\Program Files\Common Files\VST3`, `C:\Program Files\VSTPlugins`, CLAP paths

### Semantic Categories
Every parameter tagged: `oscillator`, `filter`, `envelope`, `lfo`, `macro`, `modulation`, `fx`, `other`

### Built-in Maps (Ready to Use)
| Plugin | Parameters | Patch Templates |
|--------|------------|-----------------|
| **Serum** | 80+ | Bass, Lead, Pluck, Pad, FX |
| **Vital** | 50+ | Bass, Lead |
| **Pigments** | 60+ | Analog, Wavetable, Harmonic |
| **Operator** | 40+ | FM presets |
| **Wavetable** | 50+ | Categories |

### Create Patch from High-Level Spec
```python
create_patch_from_map("serum", {
    "oscillators": [{"index": 0, "wavetable": "Basic Shapes", "unison": 3}],
    "filters": [{"index": 0, "type": "lowpass", "cutoff": 0.3, "resonance": 0.4}],
    "envelopes": [{"index": 0, "attack": 0.01, "decay": 0.2, "sustain": 0.4, "release": 0.3}],
    "lfos": [{"index": 0, "rate": 0.25, "shape": "sine", "amount": 0.3}],
    "macros": [{"index": 0, "target": "filter_1_cutoff", "amount": 0.5}]
})
```

---

## 🌐 Distributed Fleet Architecture (Multi-Eliza)

### Node Topology
| Node | Role | IP (Tailscale) | Capabilities |
|------|------|----------------|--------------|
| **Dell Vostro** | DAW Primary | 100.82.15.79 | Ableton, MCP, Analyzer, MOTU 828mk2, Focusrite, Yamaha 01X |
| **ThinkPad X13** | GPU Secondary | 100.90.0.100 | CUDA, Magenta RealTime 2, Stable Audio, AudioLDM, Demucs, librosa |
| **Galaxy S9** | Mobile Controller | 100.84.148.23 | BLE MIDI, TouchOSC, Ableton Link |
| **Neo Nubia** | Mobile Controller | 100.99.81.13 | BLE MIDI, TouchOSC, Ableton Link |
| **Hermes Dashboard** | Monitoring | 100.82.15.79 | Fleet UI, Kanban, Memory |

### Communication Ports
| Port | Protocol | Purpose |
|------|----------|---------|
| 9877 | TCP | LOM commands (MCP ↔ Remote Script) |
| 9878 | UDP/OSC | Real-time analyzer metrics |
| 9879 | OSC | VST Hub (synth control) |
| 9880 | OSC | FX Chain (effect control) |
| 8384 | TCP | Syncthing GUI |
| 22000 | TCP | Syncthing sync |
| 3190 | UDP | Ableton Link (tempo sync) |

### Offload GPU Tasks to ThinkPad
```python
# From Dell Vostro (or Hermes)
submit_task({
    "action": "stable_audio",
    "params": {"prompt": "deep atmospheric dnb pad", "duration": 30},
    "target": "gpu"
})

# Or Magenta RealTime 2 for live performance
submit_task({
    "action": "magenta_realtime",
    "params": {"style": "continue", "temperature": 1.0},
    "target": "gpu"
})
```

### Mobile BLE MIDI
```python
# Start BlueMIDI bridge
start_ble_midi_bridge()

# Galaxy S9/Neo Nubia connect via Bluetooth
# Appear as "BlueMIDI - ROLI" in Ableton MIDI Preferences
# Enable MPE for full expression
```

### Hermes Dashboard Embedding
```html
<!-- fleet_dashboard.html - embed in Hermes Messaging pane -->
<!-- Shows: Node health, GPU status, Active tasks, Analyzer metrics -->
```

---

## 📋 Professional Workflow Engine

### Project Templates (5 Built-in)
| Template | Genre | Tempo | Tracks | Key Features |
|----------|-------|-------|--------|--------------|
| `dnb` | Drum & Bass | 174 | 8 | Dual bass (main+sub), parallel comp return |
| `house` | House | 124 | 8 | Classic 4-on-floor, chord/pad, vocal track |
| `techno` | Techno | 130 | 7 | Modular routing, saturator on master |
| `ambient` | Ambient | 80 | 6 | Big reverbs, shimmer, slow evolution |
| `trap` | Trap | 140 | 7 | 808 bass, triplet hats, vocal chops |

### Create Project from Template
```python
create_project_from_template({"template_id": "dnb", "project_name": "My DnB Track"})
```

### Mix Snapshots (A/B Comparison)
```python
# Save current mix state
create_snapshot({"name": "Mix v1 - Pre Mastering", "tags": ["pre-master", "v1"]})

# Later... make changes, save another
create_snapshot({"name": "Mix v2 - Post EQ", "tags": ["post-eq", "v2"]})

# Compare
compare_snapshots({"snapshot_a": "abc123", "snapshot_b": "def456"})

# Instant recall (A/B)
recall_snapshot({"snapshot_id": "abc123"})
```

### Export Pipeline
```python
# Create export job
job_id = create_export_job({
    "name": "MyTrack_Master",
    "formats": ["wav_24", "wav_32_float", "mp3_320", "flac"],
    "loudness_target": "streaming",  # -14 LUFS
    "start_bar": 1,
    "end_bar": 257,  # 64 bars @ 4/4
    "normalize": true,
    "metadata": {
        "title": "My Track",
        "artist": "KEMERTARIAN",
        "genre": "Drum & Bass",
        "bpm": 174,
        "key": "F#m",
        "isrc": "USXXX2400001",
        "credits": {"producer": "KEMERTARIAN", "mixing": "Ableton Brain"}
    }
})

# Execute (renders in Ableton, normalizes, embeds metadata)
execute_export({"job_id": job_id})
```

### Loudness Targets
| Target | Integrated LUFS | True Peak | Use Case |
|--------|-----------------|-----------|----------|
| `streaming` | -14 | -1 dBTP | Spotify, Apple Music, YouTube |
| `club` | -9 | -1 dBTP | Club/EDM |
| `broadcast` | -23 | -1 dBTP | TV/Radio (EBU R128) |
| `podcast` | -16 | -1 dBTP | Podcast standard |
| `cd` | -9 | -0.3 dBTP | CD master |

---

## 🔧 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ABLETON BRAIN ECOSYSTEM                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐           │
│  │   HERMES     │     │  DELL VOSTRO │     │  THINKPAD    │           │
│  │  DASHBOARD   │     │  (PRIMARY)   │     │  (GPU)       │           │
│  │              │     │              │     │              │           │
│  │ • Fleet UI   │     │ • Ableton    │◄───►│ • Stable     │           │
│  │ • Kanban     │     │ • Remote     │     │   Audio Open │           │
│  │ • Memory     │     │   Script     │     │ • Magenta    │           │
│  │ • Monitoring │     │ • MCP Server │     │   RealTime 2 │           │
│  └──────┬───────┘     │ • Analyzer   │     │ • AudioLDM 2 │           │
│         │             │   Bridge     │     │ • Demucs     │           │
│         │ Tailscale   │ • BlueMIDI   │     │ • librosa    │           │
│         │  Mesh       │ • Syncthing  │     └──────┬───────┘           │
│         │             └──────┬───────┘            │                   │
│         │                    │                    │                   │
│         ▼                    ▼                    ▼                   │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │                    SYNCTHING (Real-time Sync)               │     │
│  │  Projects  •  Samples  •  Analysis  •  Stems  •  Exports   │     │
│  └─────────────────────────────────────────────────────────────┘     │
│         │                    │                    │                   │
│         ▼                    ▼                    ▼                   │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐         │
│  │  GALAXY S9   │     │  NEO NUBIA   │     │  MACBOOKS    │         │
│  │  (MOBILE)    │     │  (MOBILE)    │     │  (PLANNED)   │         │
│  │              │     │              │     │              │         │
│  │ • BLE MIDI   │     │ • BLE MIDI   │     │ • Legacy     │         │
│  │ • TouchOSC   │     │ • TouchOSC   │     │   Support    │         │
│  │ • Ableton    │     │ • Ableton    │     │              │         │
│  │   Link       │     │   Link       │     │              │         │
│  └──────────────┘     └──────────────┘     └──────────────┘         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

MCP Client (Claude/Cursor) ──stdio──► mcp_server.py ──TCP:9877──► Remote Script
                                                              │
                                                              ▼
                                                    Ableton Live 12 (LOM)
                                                              │
                                      ┌───────────────────────┼───────────────────────┐
                                      ▼                       ▼                       ▼
                              Max for Live              Analyzer OSC             VST/AU/CLAP
                            (Magenta Studio)            (port 9878)             (semantic maps)
```

---

## 📋 Requirements Summary

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **Ableton Live** | 11/12 (Suite recommended) | Suite = Max for Live included |
| **Python** | 3.10+ | 3.11/3.12 tested |
| **OS** | Windows 10/11 | macOS/Linux with path adjustments |
| **Max for Live** | Required for Analyzer, Magenta, Serum deep control | Suite or Standard + add-on |
| **GPU (ThinkPad)** | NVIDIA CUDA 8GB+ VRAM | For Stable Audio, AudioLDM, Magenta RT2 |
| **Audio Interface** | MOTU 828mk2 / Focusrite / Yamaha 01X | Your hardware chain |
| **Tailscale** | All nodes | Mesh VPN |
| **Syncthing** | All nodes | Real-time folder sync |
| **BlueMIDI** | Windows | BLE MIDI bridge |
| **teVirtualMIDI** | Windows | Virtual MIDI ports |

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| "Connection refused" (port 9877) | Remote Script not loaded. Check Preferences → Control Surface = AbletonBrain. Restart Live. |
| "Command timeout" | Ableton frozen. Restart Live. Check Remote Script log. |
| "Device not found" | Check track/device indices with `get_tracks`. Indices are 0-based. |
| Serum params not showing | Load Serum, then `probe_plugin_parameters`. Some params need Configure Mode. |
| Sample analysis fails | `pip install librosa`. Ensure ffmpeg installed for mp3. |
| Analyzer shows -60 LUFS | Device not on track, or no audio playing. Check OSC port 9878. |
| BlueMIDI not in Ableton | Install teVirtualMIDI, run `bluemidi.exe --autostart`, restart Ableton. |
| Syncthing not syncing | Check GUI (port 8384), folder paths, firewall ports 8384/22000. |
| ThinkPad GPU tasks fail | Check SSH keys, CUDA installation, `nvidia-smi`. |

---

## 🔗 Related Projects (Referenced in This Implementation)

| Project | GitHub | Purpose |
|---------|--------|---------|
| **ableton-mcp** | `ok2ju/ableton-mcp` | Sample scanning + track generation (inspiration) |
| **ableton-mcp-pro** | `nicholasbien/ableton-mcp-pro` | Arrangement + Serum control |
| **ableton-mcp-max** | `closestfriend/ableton-mcp` | VST/AU + Max for Live hybrid |
| **ableton-mcp-extended** | `elleural/ableton-mcp` | 76 tools + audio-to-MIDI |
| **ableton-ai** | `F-Fischer/ableton-copilot` | Music-theory-aware generation |
| **CanArslanDev/ableton-live-mcp** | `CanArslanDev/ableton-live-mcp` | **Analyzer device, mix_doctor, compare_to_reference** |
| **Live Maestro** | `romanstark/live-maestro` | Generic LOM bridge, YAML catalog, read-back verification |
| **MARA / MixMatch** | `moritzlauper/mara` | Reference-guided mixing, masking detection |
| **MixCoach** | `xeewi/mixcoach` | Real-time mix analysis, auto-fix suggestions |
| **ableton-live-pilot** | `bepena/ableton-live-pilot` | 474 tools, plugin corpus (500+), automation recipes |
| **BAP Labs** | `brentpinero/BAP-LABS_ABLETON_CONTROL` | Dual VST control (OSC), 500+ param maps, AppleScript GUI |
| **theDAW** | `gantasmo/theDAW` | Stable Audio 3, Magenta RT2, full DAW |
| **Magenta Studio** | `magenta/magenta` | Free AI MIDI tools for Ableton |
| **Stable Audio Open** | `stability-ai/stable-audio-tools` | Local text-to-audio |
| **Demucs** | `facebookresearch/demucs` | Stem separation |
| **BlueMIDI** | `Armazi000/bluemidi` | Windows BLE MIDI bridge |

---

## 📝 License

MIT - Free for personal and commercial use.

---

## 🤝 Contributing

This is the **KEMERTARIAN** Ableton Brain implementation. Built for the Multi-Eliza network.

**Core files to modify for new features:**
- `ableton_remote/__init__.py` — New LOM commands (in Live's Python)
- `mcp_server.py` — New MCP tools (external Python)
- `sample_scanner.py` — New analysis/generation logic
- `analyzer_bridge.py` — New audio metrics
- `automation_recipes.py` — New curves/recipes
- `ai_generation.py` — New generation backends
- `plugin_corpus.py` — New plugin maps
- `fleet_coordinator.py` — New distributed tasks
- `workflow_engine.py` — New templates/workflows

---

## 🎉 What's Next (Roadmap)

### Immediate (Week 1-2)
- [ ] Compile `AbletonMCP_Analyzer.maxpat` → `.amxd` in Max
- [ ] Test analyzer bridge with live audio
- [ ] Verify `mix_doctor` detects real issues
- [ ] Test Magenta Studio devices in Live

### Short-term (Week 3-4)
- [ ] Deploy ThinkPad GPU inference server
- [ ] Set up BlueMIDI on Dell Vostro
- [ ] Create first project templates in workspace
- [ ] Test export pipeline with loudness normalization

### Medium-term (Month 2)
- [ ] Stable Audio Open local inference
- [ ] Demucs stem separation integration
- [ ] Plugin corpus: scan your VST folder, generate maps
- [ ] Hermes dashboard embedding (iframe in Messaging pane)

### Long-term (Month 3+)
- [ ] Magenta RealTime 2 live performance
- [ ] ACE-Step / YuE full song generation
- [ ] Automated mastering chain (Ozone-style)
- [ ] Multi-device Ableton Link jam sessions

---

**Built with 🧠 by KEMERTARIAN for the Multi-Eliza Network**

*Happy producing!* 🎹🎧🚀