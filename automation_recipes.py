"""
ABLETON BRAIN - Automation Recipes
16 curve types, 15+ named recipes for common automation patterns
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import math


class CurveType(Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    S_CURVE = "s_curve"
    INVERSE_S_CURVE = "inverse_s_curve"
    STEP = "step"
    RANDOM = "random"
    SINE = "sine"
    TRIANGLE = "triangle"
    SAWTOOTH = "sawtooth"
    SQUARE = "square"
    PING_PONG = "ping_pong"
    SIDECHAIN = "sidechain"
    EXPONENTIAL_RISE = "exponential_rise"
    EXPONENTIAL_FALL = "exponential_fall"
    CUSTOM = "custom"


@dataclass
class AutomationPoint:
    time: float  # in beats
    value: float  # 0.0 - 1.0
    shape: Optional[str] = None  # curve shape to next point


@dataclass
class AutomationRecipe:
    name: str
    description: str
    target_param: str  # e.g., "filter_frequency", "volume", "send_a"
    curve_type: CurveType
    duration_bars: float
    params: Dict[str, Any]  # recipe-specific parameters
    points: List[AutomationPoint] = None
    
    def generate_points(self, start_beat: float = 0.0) -> List[AutomationPoint]:
        """Generate automation points for this recipe"""
        if self.points:
            return self.points
        return self._generate_from_curve(start_beat)
    
    def _generate_from_curve(self, start_beat: float) -> List[AutomationPoint]:
        points = []
        duration_beats = self.duration_bars * 4.0  # assuming 4/4
        num_points = 32
        
        for i in range(num_points + 1):
            t = i / num_points
            beat = start_beat + t * duration_beats
            value = self._curve_value(t)
            points.append(AutomationPoint(time=beat, value=value))
        return points
    
    def _curve_value(self, t: float) -> float:
        """Calculate curve value at normalized time t (0-1)"""
        ct = self.curve_type
        p = self.params
        
        if ct == CurveType.LINEAR:
            return t
        elif ct == CurveType.EXPONENTIAL:
            exp = p.get('exponent', 3.0)
            return t ** exp
        elif ct == CurveType.LOGARITHMIC:
            return math.log1p(t * (math.e - 1))
        elif ct == CurveType.S_CURVE:
            return 3 * t * t - 2 * t * t * t  # smoothstep
        elif ct == CurveType.INVERSE_S_CURVE:
            return 1 - (3 * (1-t) * (1-t) - 2 * (1-t) * (1-t) * (1-t))
        elif ct == CurveType.STEP:
            steps = p.get('steps', 4)
            return math.floor(t * steps) / steps
        elif ct == CurveType.RANDOM:
            import random
            seed = p.get('seed', 42)
            random.seed(seed)
            return random.random()
        elif ct == CurveType.SINE:
            freq = p.get('frequency', 1.0)
            phase = p.get('phase', 0.0)
            return 0.5 + 0.5 * math.sin(2 * math.pi * freq * t + phase)
        elif ct == CurveType.TRIANGLE:
            freq = p.get('frequency', 1.0)
            return 1 - abs((t * freq * 2) % 2 - 1)
        elif ct == CurveType.SAWTOOTH:
            freq = p.get('frequency', 1.0)
            return (t * freq) % 1.0
        elif ct == CurveType.SQUARE:
            freq = p.get('frequency', 1.0)
            return 1.0 if (t * freq) % 1.0 < 0.5 else 0.0
        elif ct == CurveType.PING_PONG:
            return 1 - abs((t * 2) % 2 - 1)
        elif ct == CurveType.SIDECHAIN:
            # Ducking envelope: fast attack, adjustable release
            attack = p.get('attack', 0.01)
            release = p.get('release', 0.3)
            if t < attack:
                return t / attack
            else:
                return max(0.0, 1.0 - (t - attack) / release)
        elif ct == CurveType.EXPONENTIAL_RISE:
            return 1 - (1 - t) ** p.get('exponent', 3.0)
        elif ct == CurveType.EXPONENTIAL_FALL:
            return (1 - t) ** p.get('exponent', 3.0)
        else:
            return t


# =========================================================================
# PREDEFINED AUTOMATION RECIPES (15+)
# =========================================================================

AUTOMATION_RECIPES: Dict[str, AutomationRecipe] = {
    # Filter Sweeps
    "filter_sweep_up": AutomationRecipe(
        name="filter_sweep_up",
        description="Classic filter opening sweep - great for buildups",
        target_param="filter_frequency",
        curve_type=CurveType.EXPONENTIAL,
        duration_bars=8,
        params={"exponent": 2.5, "start_freq": 200, "end_freq": 18000}
    ),
    
    "filter_sweep_down": AutomationRecipe(
        name="filter_sweep_down",
        description="Filter closing sweep - great for breakdowns",
        target_param="filter_frequency",
        curve_type=CurveType.EXPONENTIAL_FALL,
        duration_bars=8,
        params={"exponent": 2.5, "start_freq": 18000, "end_freq": 200}
    ),
    
    "filter_sweep_bandpass": AutomationRecipe(
        name="filter_sweep_bandpass",
        description="Bandpass sweep for movement",
        target_param="filter_frequency",
        curve_type=CurveType.SINE,
        duration_bars=16,
        params={"frequency": 0.25, "phase": 0.0}
    ),
    
    # Sidechain / Ducking
    "sidechain_pump": AutomationRecipe(
        name="sidechain_pump",
        description="Classic sidechain ducking on kick",
        target_param="volume",
        curve_type=CurveType.SIDECHAIN,
        duration_bars=1,
        params={"attack": 0.005, "release": 0.15, "depth": 0.6}
    ),
    
    "sidechain_subtle": AutomationRecipe(
        name="sidechain_subtle",
        description="Gentle sidechain for glue",
        target_param="volume",
        curve_type=CurveType.SIDECHAIN,
        duration_bars=1,
        params={"attack": 0.01, "release": 0.3, "depth": 0.2}
    ),
    
    # Reverb/Delay Throws
    "reverb_swell": AutomationRecipe(
        name="reverb_swell",
        description="Long reverb swell - send goes up then down",
        target_param="send_a",  # assuming send A = reverb
        curve_type=CurveType.S_CURVE,
        duration_bars=8,
        params={}
    ),
    
    "dub_throw": AutomationRecipe(
        name="dub_throw",
        description="Ping-pong delay throw on last beat",
        target_param="send_b",  # assuming send B = delay
        curve_type=CurveType.PING_PONG,
        duration_bars=4,
        params={"feedback": 0.7}
    ),
    
    "delay_feedback_rise": AutomationRecipe(
        name="delay_feedback_rise",
        description="Delay feedback increasing to self-oscillation",
        target_param="feedback",
        curve_type=CurveType.EXPONENTIAL_RISE,
        duration_bars=8,
        params={"exponent": 3.0}
    ),
    
    # Risers / Transitions
    "pitch_riser": AutomationRecipe(
        name="pitch_riser",
        description="Pitch rising 1-2 octaves",
        target_param="transpose",
        curve_type=CurveType.LINEAR,
        duration_bars=8,
        params={"start": 0, "end": 12}
    ),
    
    "noise_riser": AutomationRecipe(
        name="noise_riser",
        description="White noise filter sweep + volume swell",
        target_param="filter_frequency",
        curve_type=CurveType.EXPONENTIAL,
        duration_bars=8,
        params={"exponent": 2.0}
    ),
    
    "downlifter": AutomationRecipe(
        name="downlifter",
        description="Reverse riser - pitch down + filter down",
        target_param="transpose",
        curve_type=CurveType.LINEAR,
        duration_bars=4,
        params={"start": 0, "end": -12}
    ),
    
    # Creative/Glitch
    "stutter_gate": AutomationRecipe(
        name="stutter_gate",
        description="Rhythmic volume gating (16th notes)",
        target_param="volume",
        curve_type=CurveType.SQUARE,
        duration_bars=2,
        params={"frequency": 4.0}
    ),
    
    "tape_stop": AutomationRecipe(
        name="tape_stop",
        description="Pitch down + time stretch simulation",
        target_param="transpose",
        curve_type=CurveType.EXPONENTIAL_FALL,
        duration_bars=2,
        params={"exponent": 4.0, "start": 0, "end": -24}
    ),
    
    "formant_shift": AutomationRecipe(
        name="formant_shift",
        description="Vocal formant shifting up/down",
        target_param="formant",
        curve_type=CurveType.SINE,
        duration_bars=8,
        params={"frequency": 0.125, "phase": 0.0}
    ),
    
    # Mixing
    "auto_pan": AutomationRecipe(
        name="auto_pan",
        description="Slow stereo panning movement",
        target_param="pan",
        curve_type=CurveType.SINE,
        duration_bars=32,
        params={"frequency": 0.0625}
    ),
    
    "width_swell": AutomationRecipe(
        name="width_swell",
        description="Stereo width automation (Utility width)",
        target_param="width",
        curve_type=CurveType.S_CURVE,
        duration_bars=8,
        params={}
    ),
    
    # Mastering-style
    "limiter_ceiling_ride": AutomationRecipe(
        name="limiter_ceiling_ride",
        description="Ride limiter ceiling for dynamics",
        target_param="ceiling",
        curve_type=CurveType.INVERSE_S_CURVE,
        duration_bars=16,
        params={}
    ),
}


def get_recipe(name: str) -> Optional[AutomationRecipe]:
    """Get a recipe by name"""
    return AUTOMATION_RECIPES.get(name)


def list_recipes() -> List[Dict[str, str]]:
    """List all available recipes"""
    return [
        {"name": k, "description": v.description, "target": v.target_param, "bars": v.duration_bars}
        for k, v in AUTOMATION_RECIPES.items()
    ]


def generate_automation_curve(
    curve_type: str,
    duration_bars: float,
    num_points: int = 32,
    **params
) -> List[Dict[str, float]]:
    """Generate raw automation curve points"""
    try:
        ct = CurveType(curve_type)
    except ValueError:
        ct = CurveType.LINEAR
    
    recipe = AutomationRecipe(
        name="custom",
        description="Custom curve",
        target_param="param",
        curve_type=ct,
        duration_bars=duration_bars,
        params=params
    )
    
    points = recipe.generate_points()
    return [{"time": p.time, "value": p.value} for p in points]


def apply_automation_recipe_to_clip(
    mcp_connection,
    track_index: int,
    clip_index: int,
    recipe_name: str,
    param_name: str = None,
    start_beat: float = 0.0
) -> Dict:
    """Apply a named automation recipe to a session clip via MCP"""
    recipe = get_recipe(recipe_name)
    if not recipe:
        return {"error": f"Recipe '{recipe_name}' not found"}
    
    target = param_name or recipe.target_param
    points = recipe.generate_points(start_beat)
    
    # Convert to clip envelope format
    envelope_points = [{"time": p.time, "value": p.value} for p in points]
    
    result = mcp_connection.send_command('set_clip_envelope', {
        'track_index': track_index,
        'clip_index': clip_index,
        'parameter': target,
        'points': envelope_points
    })
    
    return {
        "recipe": recipe_name,
        "target_param": target,
        "points": len(points),
        "duration_bars": recipe.duration_bars,
        "result": result
    }


# =========================================================================
# CURVE SHAPES FOR MANUAL USE
# =========================================================================

CURVE_SHAPES = {
    "linear": lambda t: t,
    "ease_in": lambda t: t * t,
    "ease_out": lambda t: 1 - (1 - t) * (1 - t),
    "ease_in_out": lambda t: 3 * t * t - 2 * t * t * t,
    "exponential": lambda t, exp=3: t ** exp,
    "logarithmic": lambda t: math.log1p(t * (math.e - 1)),
    "sine": lambda t, freq=1: 0.5 + 0.5 * math.sin(2 * math.pi * freq * t),
    "bounce": lambda t: abs(math.sin(6.28 * t * 3) * (1 - t)),
    "elastic": lambda t: math.sin(13 * t * 3.14159) * pow(2, -10 * t),
}


if __name__ == "__main__":
    print("Available Automation Recipes:")
    for r in list_recipes():
        print(f"  {r['name']}: {r['description']} (target: {r['target']}, {r['bars']} bars)")
    
    print("\nExample: filter_sweep_up points (first 5):")
    recipe = get_recipe("filter_sweep_up")
    points = recipe.generate_points()
    for p in points[:5]:
        print(f"  beat {p.time:.2f}: {p.value:.3f}")