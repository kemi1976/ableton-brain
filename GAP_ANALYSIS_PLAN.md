# Ableton Brain — Gap Analysis & Implementation Plan

## Competitive Landscape Summary

| Category | Competitor | Key Features |
|----------|------------|--------------|
| **DAW Control** | LivePilot (474 tools) | Device Atlas, Sample Intelligence, Auto-Composition, Spectral Perception, Technique Memory |
| **AI DAW Assistant** | Splice Create / Rheo | Natural language control, harmonic analysis, stem separation, audio-to-MIDI, sample variations |
| **Mix Assistant** | iZotope Neutron 5 | Mix Assistant, Unmask (frequency masking), Sculptor, Visual Mixer, Density, Clipper, Phase |
| **Mastering** | iZotope Ozone 11 | Master Assistant, EQ Match, Stabilizer, Impact, Maximizer, Reference matching |
| **EQ Matching** | FabFilter Pro-Q 4 | EQ Match (reference spectrum), Spectrum Grab, Collision Detection |
| **Chord/Scale** | Scaler 2, Captain Chords | Audio/MIDI chord detection, genre chord sets, suggestion engine, arpeggiator |
| **Audio-to-MIDI** | Basic Pitch, Samplab, RipX | Polyphonic transcription, pitch bend, stem separation + MIDI |
| **Synth Patch Gen** | Synplant 2 Genopatch | Audio → synth parameters (genetic algorithm) |
| **Arrangement** | Studio One Launcher, Orb Composer | Clip launcher, AI arrangement, section generation |

---

## GAP ANALYSIS — What We're Missing (Priority Order)

### 🔴 TIER 1: High Impact, Achievable with Current Stack

| # | Feature | Competitor Equivalent | Our Gap | Effort |
|---|---------|----------------------|---------|--------|
| 1 | **Audio-to-MIDI Conversion** | Basic Pitch, Ableton native, RipX | No audio → MIDI pipeline | Medium |
| 2 | **Chord/Scale Detection & Suggestion** | Scaler 2, Captain Chords | No harmonic analysis of clips | Medium |
| 3 | **Reference Track EQ Match** | FabFilter Pro-Q 4, Ozone | No tonal matching to reference | Low-Med |
| 4 | **Frequency Masking Detection** | Neutron Unmask | No cross-track masking analysis | Medium |
| 5 | **Natural Language DAW Control** | Splice Rheo | MCP tools exist but no NL interface | Low |
| 6 | **Arrangement Assistant / Launcher** | Studio One, Orb | No section/structure AI | Medium |
| 7 | **Sample Variations (Generate)** | Splice Variations | No variation generation | Medium |

### 🟡 TIER 2: Valuable, Requires More Research/Integration

| # | Feature | Competitor Equivalent | Our Gap | Effort |
|---|---------|----------------------|---------|--------|
| 8 | **Synth Patch from Audio** | Synplant Genopatch | Requires synth-specific models | High |
| 9 | **Visual Mixer / Collision Detection** | Neutron, Pro-Q 4 | No cross-track visual mixing UI | High |
| 10 | **Project Version Control (Git-like)** | — | Snapshots exist, no branching | Medium |
| 11 | **Smart Sample Search (Search with Sound)** | Splice, Studio One | No catalog integration | High |
| 12 | **MIDI Humanization** | Splice Create | No velocity/timing variation | Low |

### 🟢 TIER 3: Nice to Have / Long Term

| # | Feature | Competitor Equivalent | Our Gap |
|---|---------|----------------------|---------|
| 13 | Real-time Collaboration | Splice, Studio One | Requires network sync |
| 14 | Plugin Preset Management | — | No unified preset browser |
| 15 | Workflow Teaching (Point) | Splice Rheo | No interactive tutorials |

---

## IMPLEMENTATION PLAN — PHASED APPROACH

### PHASE 1: Core Intelligence (Weeks 1-2) — **START HERE**
**Goal: Add harmonic intelligence + audio-to-MIDI to existing MCP**

#### 1.1 Audio-to-MIDI Module (`audio_to_midi.py`)
- Integrate **Basic Pitch** (Spotify, open-source, ONNX/TensorFlow Lite)
- Support: melody, harmony, drums → MIDI clips
- MCP tools: `convert_audio_to_midi`, `convert_drums_to_midi`
- Output: MIDI clip inserted into selected track

#### 1.2 Chord/Scale Detection (`harmonic_analysis.py`)
- Integrate **Basic Pitch** chord detection + **librosa** chroma/tonnetz
- Detect: key, scale, chord progression from audio/MIDI clips
- Suggestion engine: next chords (Markov chain from theory database)
- MCP tools: `detect_chords`, `suggest_chords`, `analyze_harmony`

#### 1.3 Reference Track EQ Match (`eq_match.py`)
- Use existing `analyzer_bridge.py` spectrum data
- Compare track spectrum → reference spectrum → generate EQ curve
- Match: LUFS, spectral tilt, resonant peaks
- MCP tools: `match_eq_to_reference`, `analyze_spectral_difference`

---

### PHASE 2: Mix Intelligence (Weeks 2-3)
**Goal: Neutron-level mix assistance**

#### 2.1 Frequency Masking Detection (`masking_detection.py`)
- Cross-track spectral analysis via Max for Live
- Detect overlapping frequency regions between any 2 tracks
- Suggest: EQ cuts, panning, level adjustments
- MCP tools: `detect_masking`, `suggest_unmask`, `analyze_track_conflicts`

#### 2.2 Mix Doctor Enhancement (extend existing `mix_doctor`)
- Add: gain staging check, phase correlation, stereo width analysis
- Per-instrument profiling (kick, snare, bass, vocal, etc.)
- Reference track comparison (tonal balance, dynamics)
- MCP tools: `full_mix_analysis`, `compare_to_reference`

---

### PHASE 3: Creative Assistance (Weeks 3-4)
**Goal: Composition & arrangement AI**

#### 3.1 Arrangement Assistant (`arrangement_assistant.py`)
- Analyze project structure → suggest sections (intro, verse, chorus, etc.)
- Generate arrangement templates by genre
- Clip launcher integration: trigger/record arrangement sections
- MCP tools: `analyze_arrangement`, `suggest_arrangement`, `generate_structure`

#### 3.2 Sample Variation Generator (`sample_variations.py`)
- Use existing `ai_generation.py` (Stable Audio, Magenta)
- Input: audio clip → output: rhythmic/melodic/timbral variations
- Preserve groove, key, tempo
- MCP tools: `generate_variations`, `create_fill`, `extend_loop`

#### 3.3 Natural Language Interface (`nl_interface.py`)
- LLM (local or API) → MCP tool calls
- "Add reverb to vocal track" → `set_device_parameter`
- "Sidechain bass to kick" → `add_compressor` + `set_sidechain`
- MCP tool: `natural_language_command`

---

### PHASE 4: Advanced Features (Weeks 4-6)
**Goal: Professional workflow features**

#### 4.1 Project Version Control (`version_control.py`)
- Git-like snapshots with metadata (what changed, why)
- Branch/merge for A/B comparisons
- Diff view: parameter changes, clip additions/removals
- MCP tools: `create_branch`, `merge_branch`, `diff_snapshots`

#### 4.2 MIDI Humanization (`midi_humanization.py`)
- Apply: timing variation, velocity curves, note length variation
- Style presets: "human", "swing", "tight", "loose"
- Per-track or per-clip
- MCP tools: `humanize_midi`, `apply_groove`

#### 4.3 Smart Sample Search (`smart_sample_search.py`)
- Index user sample library with: key, tempo, genre, timbre (from `sound_similarity.py`)
- Query: "find kick that matches this track"
- Integration: drag-to-track from dashboard
- MCP tools: `search_samples_by_context`, `find_complementary_samples`

---

## TECHNICAL ARCHITECTURE FOR NEW MODULES

```
ableton-brain/
├── audio_to_midi.py          # Basic Pitch integration
├── harmonic_analysis.py      # Chord/scale detection + suggestion
├── eq_match.py              # Reference track EQ matching
├── masking_detection.py     # Frequency masking analysis
├── arrangement_assistant.py # Structure analysis + generation
├── sample_variations.py     # AI variation generation
├── nl_interface.py          # Natural language → MCP
├── version_control.py       # Git-like session versioning
├── midi_humanization.py     # Humanization engine
├── smart_sample_search.py   # Context-aware sample search
├── mcp_server.py            # ← Register new tools here
└── requirements.txt         # ← Add new deps
```

### New Dependencies
```
# Audio-to-MIDI
basic-pitch @ git+https://github.com/spotify/basic-pitch
onnxruntime

# Harmonic analysis
music21              # Music theory (chords, scales, roman numerals)
madmom               # Beat/downbeat detection

# Existing (already in requirements.txt)
librosa, numpy, scipy, faiss-cpu, torch, mido
```

---

## MCP TOOLS TO ADD (Total: +25 tools)

### Audio-to-MIDI (3)
- `convert_audio_to_midi` — full polyphonic conversion
- `convert_drums_to_midi` — drum-specific (kick/snare/hihat mapping)
- `convert_harmony_to_midi` — chord/harmony extraction

### Harmonic Analysis (5)
- `detect_chords` — from audio or MIDI clip
- `detect_key_scale` — key + scale detection
- `suggest_chords` — next chord suggestions
- `analyze_harmony` — full harmonic analysis report
- `generate_chord_progression` — by genre/mood/key

### EQ Match (3)
- `match_eq_to_reference` — generate EQ curve to match reference
- `analyze_spectral_difference` — detailed spectrum comparison
- `save_reference_spectrum` — store reference for later matching

### Masking Detection (4)
- `detect_masking` — between two tracks
- `suggest_unmask` — EQ/panning/level suggestions
- `analyze_track_conflicts` — full project conflict report
- `auto_unmask` — apply suggested fixes

### Arrangement (4)
- `analyze_arrangement` — detect sections, energy curve
- `suggest_arrangement` — improvements for flow
- `generate_structure` — create arrangement template
- `launch_arrangement_section` — trigger section in clip launcher

### Variations (3)
- `generate_variations` — rhythmic/melodic/timbral
- `create_fill` — drum fill generation
- `extend_loop` — extend clip naturally

### Natural Language (1)
- `natural_language_command` — parse and execute

### Version Control (3)
- `create_snapshot_branch` — named branch
- `merge_snapshot_branch` — merge with conflict resolution
- `diff_snapshots` — parameter/clip diff

### Humanization (2)
- `humanize_midi` — apply humanization
- `apply_groove` — apply groove template

### Smart Search (2)
- `search_samples_by_context` — key/tempo/genre/timbre
- `find_complementary_samples` — for current track

---

## ACCEPTANCE CRITERIA PER PHASE

### Phase 1 Complete When:
- [ ] Drop audio clip → get MIDI clip in Ableton (melody + drums)
- [ ] Select clip → see detected chords + key + suggested next chords
- [ ] Select reference track → auto-generate EQ on target track

### Phase 2 Complete When:
- [ ] "Analyze mix" → report shows masking pairs with specific freq ranges
- [ ] "Fix masking" → applies EQ cuts that resolve conflicts
- [ ] Mix Doctor shows per-instrument profile compliance

### Phase 3 Complete When:
- [ ] "Suggest arrangement" → shows section labels + energy curve
- [ ] "Generate variations" → creates 4 usable variations of selected clip
- [ ] "Add reverb to vocal" → works via natural language

### Phase 4 Complete When:
- [ ] Can branch session, experiment, merge back
- [ ] MIDI sounds "human" not robotic
- [ ] "Find kick for this track" → returns ranked matches

---

## START NEXT: Phase 1 Implementation

**First 3 files to create:**
1. `audio_to_midi.py` — Basic Pitch wrapper
2. `harmonic_analysis.py` — Chord/key detection + suggestion
3. `eq_match.py` — Spectrum matching

**Then register 11 new MCP tools in `mcp_server.py`**

Ready to start Phase 1?