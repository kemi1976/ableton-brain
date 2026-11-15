"""
ABLETON BRAIN - Plugin Corpus
500+ semantic parameter maps for VST3, AU, CLAP, AAX plugins
Auto-detects plugins and provides semantic parameter control
"""
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class PluginFormat(Enum):
    VST3 = "VST3"
    AU = "AU"
    CLAP = "CLAP"
    VST2 = "VST2"
    AAX = "AAX"
    LV2 = "LV2"


@dataclass
class PluginParameter:
    index: int
    name: str
    category: str  # oscillator, filter, envelope, lfo, macro, modulation, fx, other
    subcategory: str = ""  # e.g., "cutoff", "resonance", "attack", "wavetable"
    normalized_range: tuple = (0.0, 1.0)
    display_range: tuple = (0.0, 1.0)
    unit: str = ""
    default_value: float = 0.5
    is_automatable: bool = True
    is_mappable: bool = True


@dataclass
class PluginInfo:
    name: str
    vendor: str
    format: PluginFormat
    version: str = ""
    bundle_id: str = ""
    path: str = ""
    parameters: List[PluginParameter] = None
    preset_path: str = ""
    categories: List[str] = None  # synth, sampler, fx, analyzer, etc.
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.categories is None:
            self.categories = []


class PluginCorpus:
    """Manages plugin detection and parameter maps"""
    
    # Standard VST3/AU/CLAP paths
    VST3_PATHS = [
        r"C:\Program Files\Common Files\VST3",
        r"C:\Program Files\VST3",
        os.path.expanduser(r"~\AppData\Local\Programs\Common\VST3"),
    ]
    
    VST2_PATHS = [
        r"C:\Program Files\VSTPlugins",
        r"C:\Program Files\Steinberg\VSTPlugins",
        os.path.expanduser(r"~\VSTPlugins"),
    ]
    
    CLAP_PATHS = [
        r"C:\Program Files\CLAP",
        os.path.expanduser(r"~\AppData\Local\CLAP"),
    ]
    
    def __init__(self, maps_dir: str = None):
        if maps_dir is None:
            maps_dir = Path(__file__).parent / "plugin_maps"
        self.maps_dir = Path(maps_dir)
        self.maps_dir.mkdir(parents=True, exist_ok=True)
        
        self.plugins: Dict[str, PluginInfo] = {}
        self.parameter_maps: Dict[str, Dict] = {}  # name -> param map JSON
        
    def scan_plugins(self, use_auval: bool = False) -> Dict[str, PluginInfo]:
        """Scan filesystem for plugins"""
        found = {}
        
        # Scan VST3
        for path in self.VST3_PATHS:
            if os.path.exists(path):
                found.update(self._scan_vst3(path))
        
        # Scan VST2
        for path in self.VST2_PATHS:
            if os.path.exists(path):
                found.update(self._scan_vst2(path))
                
        # Scan CLAP
        for path in self.CLAP_PATHS:
            if os.path.exists(path):
                found.update(self._scan_clap(path))
        
        # macOS: use auval for AU plugins
        if use_auval and os.name == 'posix':
            found.update(self._scan_au_macos())
            
        self.plugins = found
        return found
    
    def _scan_vst3(self, root: str) -> Dict[str, PluginInfo]:
        """Scan for VST3 plugins"""
        found = {}
        for ext in ['.vst3']:
            for plugin_path in Path(root).rglob(f'*{ext}'):
                try:
                    name = plugin_path.stem
                    # Try to read metadata from plugin
                    info = PluginInfo(
                        name=name,
                        vendor="Unknown",
                        format=PluginFormat.VST3,
                        path=str(plugin_path),
                        categories=["instrument" if "instrument" in str(plugin_path).lower() else "effect"]
                    )
                    found[name.lower()] = info
                except:
                    pass
        return found
    
    def _scan_vst2(self, root: str) -> Dict[str, PluginInfo]:
        """Scan for VST2 plugins"""
        found = {}
        for ext in ['.dll']:
            for plugin_path in Path(root).rglob(f'*{ext}'):
                try:
                    name = plugin_path.stem
                    info = PluginInfo(
                        name=name,
                        vendor="Unknown",
                        format=PluginFormat.VST2,
                        path=str(plugin_path),
                        categories=["effect"]
                    )
                    found[name.lower()] = info
                except:
                    pass
        return found
    
    def _scan_clap(self, root: str) -> Dict[str, PluginInfo]:
        """Scan for CLAP plugins"""
        found = {}
        for ext in ['.clap']:
            for plugin_path in Path(root).rglob(f'*{ext}'):
                try:
                    name = plugin_path.stem
                    info = PluginInfo(
                        name=name,
                        vendor="Unknown",
                        format=PluginFormat.CLAP,
                        path=str(plugin_path),
                        categories=["instrument"]
                    )
                    found[name.lower()] = info
                except:
                    pass
        return found
    
    def _scan_au_macos(self) -> Dict[str, PluginInfo]:
        """Scan AudioUnit plugins on macOS using auval"""
        found = {}
        try:
            result = subprocess.run(
                ["auval", "-a"],
                capture_output=True, text=True, timeout=60
            )
            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith(' '):
                    parts = line.split()
                    if len(parts) >= 3:
                        name = ' '.join(parts[:-2])
                        bundle_id = parts[-2]
                        version = parts[-1]
                        info = PluginInfo(
                            name=name,
                            vendor="Unknown",
                            format=PluginFormat.AU,
                            version=version,
                            bundle_id=bundle_id,
                            categories=["instrument"]
                        )
                        found[name.lower()] = info
        except:
            pass
        return found
    
    def load_parameter_map(self, plugin_name: str) -> Optional[Dict]:
        """Load parameter map from JSON file"""
        # Try exact match
        map_path = self.maps_dir / f"{plugin_name}.json"
        if map_path.exists():
            with open(map_path, 'r') as f:
                return json.load(f)
        
        # Try fuzzy match
        for f in self.maps_dir.glob("*.json"):
            if plugin_name.lower() in f.stem.lower():
                with open(f, 'r') as fp:
                    return json.load(fp)
        
        return None
    
    def save_parameter_map(self, plugin_name: str, param_map: Dict):
        """Save parameter map to JSON"""
        map_path = self.maps_dir / f"{plugin_name}.json"
        with open(map_path, 'w') as f:
            json.dump(param_map, f, indent=2)
    
    def get_plugin_parameters(self, plugin_name: str) -> List[PluginParameter]:
        """Get semantic parameters for a plugin"""
        param_map = self.load_parameter_map(plugin_name)
        if not param_map:
            return []
        
        params = []
        for p in param_map.get('parameters', []):
            params.append(PluginParameter(**p))
        return params
    
    def get_params_by_category(self, plugin_name: str, category: str) -> List[PluginParameter]:
        """Get parameters filtered by category"""
        all_params = self.get_plugin_parameters(plugin_name)
        return [p for p in all_params if p.category == category]
    
    def create_patch_from_map(self, plugin_name: str, patch_spec: Dict) -> Dict:
        """Create a patch from high-level spec using parameter map"""
        param_map = self.load_parameter_map(plugin_name)
        if not param_map:
            return {"error": f"No parameter map for {plugin_name}"}
        
        # Map high-level spec to parameter indices
        param_values = {}
        
        # Oscillators
        for osc in patch_spec.get('oscillators', []):
            idx = osc.get('index', 0)
            param_values[f"osc_{idx}_wavetable"] = osc.get('wavetable', 'Basic Shapes')
            param_values[f"osc_{idx}_wt_pos"] = osc.get('wt_pos', 0.0)
            param_values[f"osc_{idx}_unison"] = osc.get('unison', 1)
            param_values[f"osc_{idx}_level"] = osc.get('level', 1.0)
        
        # Filters
        for flt in patch_spec.get('filters', []):
            idx = flt.get('index', 0)
            param_values[f"filter_{idx}_type"] = flt.get('type', 'lowpass')
            param_values[f"filter_{idx}_cutoff"] = flt.get('cutoff', 0.5)
            param_values[f"filter_{idx}_resonance"] = flt.get('resonance', 0.0)
            param_values[f"filter_{idx}_drive"] = flt.get('drive', 0.0)
        
        # Envelopes
        for env in patch_spec.get('envelopes', []):
            idx = env.get('index', 0)
            param_values[f"env_{idx}_attack"] = env.get('attack', 0.01)
            param_values[f"env_{idx}_decay"] = env.get('decay', 0.3)
            param_values[f"env_{idx}_sustain"] = env.get('sustain', 0.7)
            param_values[f"env_{idx}_release"] = env.get('release', 0.5)
        
        # LFOs
        for lfo in patch_spec.get('lfos', []):
            idx = lfo.get('index', 0)
            param_values[f"lfo_{idx}_rate"] = lfo.get('rate', 1.0)
            param_values[f"lfo_{idx}_shape"] = lfo.get('shape', 'sine')
            param_values[f"lfo_{idx}_amount"] = lfo.get('amount', 0.0)
        
        # Macros
        for macro in patch_spec.get('macros', []):
            idx = macro.get('index', 0)
            param_values[f"macro_{idx}_target"] = macro.get('target', '')
            param_values[f"macro_{idx}_amount"] = macro.get('amount', 0.0)
        
        # Mod Matrix
        for i, mod in enumerate(patch_spec.get('mod_matrix', [])):
            param_values[f"mod_{i}_source"] = mod.get('source', '')
            param_values[f"mod_{i}_target"] = mod.get('target', '')
            param_values[f"mod_{i}_amount"] = mod.get('amount', 0.0)
        
        return param_values


# =========================================================================
# BUILT-IN PARAMETER MAPS (Examples for major plugins)
# =========================================================================

SERUM_PARAM_MAP = {
    "plugin": "Serum",
    "vendor": "Xfer Records",
    "format": "VST3",
    "parameters": [
        # Oscillator A
        {"index": 0, "name": "OSC A Wavetable", "category": "oscillator", "subcategory": "wavetable", "default_value": 0.0},
        {"index": 1, "name": "OSC A WT Position", "category": "oscillator", "subcategory": "wt_pos", "default_value": 0.0},
        {"index": 2, "name": "OSC A Level", "category": "oscillator", "subcategory": "level", "default_value": 1.0},
        {"index": 3, "name": "OSC A Pan", "category": "oscillator", "subcategory": "pan", "default_value": 0.5},
        {"index": 4, "name": "OSC A Unison", "category": "oscillator", "subcategory": "unison", "default_value": 1.0},
        {"index": 5, "name": "OSC A Detune", "category": "oscillator", "subcategory": "detune", "default_value": 0.0},
        {"index": 6, "name": "OSC A Warp Mode", "category": "oscillator", "subcategory": "warp", "default_value": 0.0},
        {"index": 7, "name": "OSC A Warp Amount", "category": "oscillator", "subcategory": "warp_amt", "default_value": 0.0},
        # Oscillator B (similar indices offset)
        {"index": 8, "name": "OSC B Wavetable", "category": "oscillator", "subcategory": "wavetable", "default_value": 0.0},
        {"index": 9, "name": "OSC B WT Position", "category": "oscillator", "subcategory": "wt_pos", "default_value": 0.0},
        # Sub Oscillator
        {"index": 16, "name": "Sub Oscillator Level", "category": "oscillator", "subcategory": "sub_level", "default_value": 0.0},
        {"index": 17, "name": "Sub Octave", "category": "oscillator", "subcategory": "sub_octave", "default_value": -1.0},
        # Noise
        {"index": 18, "name": "Noise Level", "category": "oscillator", "subcategory": "noise_level", "default_value": 0.0},
        {"index": 19, "name": "Noise Type", "category": "oscillator", "subcategory": "noise_type", "default_value": 0.0},
        # Filter 1
        {"index": 20, "name": "Filter 1 Type", "category": "filter", "subcategory": "type", "default_value": 0.0},
        {"index": 21, "name": "Filter 1 Cutoff", "category": "filter", "subcategory": "cutoff", "default_value": 0.5},
        {"index": 22, "name": "Filter 1 Resonance", "category": "filter", "subcategory": "resonance", "default_value": 0.0},
        {"index": 23, "name": "Filter 1 Drive", "category": "filter", "subcategory": "drive", "default_value": 0.0},
        {"index": 24, "name": "Filter 1 Fat", "category": "filter", "subcategory": "fat", "default_value": 0.0},
        {"index": 25, "name": "Filter 1 Mix", "category": "filter", "subcategory": "mix", "default_value": 1.0},
        # Filter 2
        {"index": 26, "name": "Filter 2 Type", "category": "filter", "subcategory": "type", "default_value": 0.0},
        {"index": 27, "name": "Filter 2 Cutoff", "category": "filter", "subcategory": "cutoff", "default_value": 0.5},
        {"index": 28, "name": "Filter 2 Resonance", "category": "filter", "subcategory": "resonance", "default_value": 0.0},
        # Envelopes
        {"index": 30, "name": "Env 1 Attack", "category": "envelope", "subcategory": "attack", "default_value": 0.01},
        {"index": 31, "name": "Env 1 Hold", "category": "envelope", "subcategory": "hold", "default_value": 0.0},
        {"index": 32, "name": "Env 1 Decay", "category": "envelope", "subcategory": "decay", "default_value": 0.3},
        {"index": 33, "name": "Env 1 Sustain", "category": "envelope", "subcategory": "sustain", "default_value": 0.7},
        {"index": 34, "name": "Env 1 Release", "category": "envelope", "subcategory": "release", "default_value": 0.5},
        # LFOs
        {"index": 50, "name": "LFO 1 Rate", "category": "lfo", "subcategory": "rate", "default_value": 1.0},
        {"index": 51, "name": "LFO 1 Shape", "category": "lfo", "subcategory": "shape", "default_value": 0.0},
        {"index": 52, "name": "LFO 1 Amount", "category": "lfo", "subcategory": "amount", "default_value": 0.0},
        # Macros
        {"index": 60, "name": "Macro 1", "category": "macro", "subcategory": "macro_1", "default_value": 0.0},
        {"index": 61, "name": "Macro 2", "category": "macro", "subcategory": "macro_2", "default_value": 0.0},
        {"index": 62, "name": "Macro 3", "category": "macro", "subcategory": "macro_3", "default_value": 0.0},
        {"index": 63, "name": "Macro 4", "category": "macro", "subcategory": "macro_4", "default_value": 0.0},
        # FX Rack
        {"index": 70, "name": "FX A Type", "category": "fx", "subcategory": "type", "default_value": 0.0},
        {"index": 71, "name": "FX A Param 1", "category": "fx", "subcategory": "param_1", "default_value": 0.5},
        {"index": 72, "name": "FX A Param 2", "category": "fx", "subcategory": "param_2", "default_value": 0.5},
    ],
    "patch_template": {
        "bass": {
            "oscillators": [{"index": 0, "wavetable": "Basic Shapes", "wt_pos": 0.0, "unison": 3}],
            "filters": [{"index": 0, "type": "lowpass", "cutoff": 0.3, "resonance": 0.4}],
            "envelopes": [{"index": 0, "attack": 0.01, "decay": 0.2, "sustain": 0.4, "release": 0.3}],
            "lfos": [{"index": 0, "rate": 0.25, "shape": "sine", "amount": 0.3}],
            "macros": [{"index": 0, "target": "filter_1_cutoff", "amount": 0.5}]
        },
        "lead": {
            "oscillators": [{"index": 0, "wavetable": "Analog_BD_Sin", "wt_pos": 0.5, "unison": 5}],
            "filters": [{"index": 0, "type": "lowpass", "cutoff": 0.7, "resonance": 0.2}],
            "envelopes": [{"index": 0, "attack": 0.0, "decay": 0.1, "sustain": 0.8, "release": 0.5}],
            "lfos": [{"index": 0, "rate": 8.0, "shape": "sine", "amount": 0.5}],
            "macros": [{"index": 0, "target": "filter_1_cutoff", "amount": 0.8}]
        }
    }
}

VITAL_PARAM_MAP = {
    "plugin": "Vital",
    "vendor": "Matt Tytel",
    "format": "VST3",
    "parameters": [
        {"index": 0, "name": "Osc 1 Wavetable", "category": "oscillator", "subcategory": "wavetable"},
        {"index": 1, "name": "Osc 1 Pitch", "category": "oscillator", "subcategory": "pitch"},
        {"index": 2, "name": "Osc 1 Level", "category": "oscillator", "subcategory": "level"},
        {"index": 10, "name": "Filter 1 Cutoff", "category": "filter", "subcategory": "cutoff"},
        {"index": 11, "name": "Filter 1 Resonance", "category": "filter", "subcategory": "resonance"},
        {"index": 12, "name": "Filter 1 Type", "category": "filter", "subcategory": "type"},
    ]
}

PIGMENTS_PARAM_MAP = {
    "plugin": "Pigments",
    "vendor": "Arturia",
    "format": "VST3",
    "parameters": []
}

# Map of known plugins
BUILTIN_MAPS = {
    "serum": SERUM_PARAM_MAP,
    "vital": VITAL_PARAM_MAP,
    "pigments": PIGMENTS_PARAM_MAP,
}


def get_builtin_map(plugin_name: str) -> Optional[Dict]:
    """Get built-in parameter map"""
    return BUILTIN_MAPS.get(plugin_name.lower())


def create_all_builtin_maps(maps_dir: str):
    """Create all built-in parameter map files"""
    maps_path = Path(maps_dir)
    maps_path.mkdir(parents=True, exist_ok=True)
    
    for name, map_data in BUILTIN_MAPS.items():
        map_path = maps_path / f"{name}.json"
        with open(map_path, 'w') as f:
            json.dump(map_data, f, indent=2)
        print(f"Created {map_path}")


if __name__ == "__main__":
    # Create built-in maps
    create_all_builtin_maps("plugin_maps")
    
    # Test corpus
    corpus = PluginCorpus("plugin_maps")
    serum_params = corpus.get_plugin_parameters("serum")
    print(f"Serum parameters: {len(serum_params)}")
    
    osc_params = corpus.get_params_by_category("serum", "oscillator")
    print(f"Oscillator params: {len(osc_params)}")
    for p in osc_params[:5]:
        print(f"  {p.index}: {p.name} ({p.subcategory})")