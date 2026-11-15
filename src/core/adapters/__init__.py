"""
Ableton Brain - Core Adapters Package
"""

from .base_adapter import (
    BaseDAWAdapter,
    DAWAdapterRegistry,
    DAWPlatform,
    TrackType,
    TrackInfo,
    DeviceInfo,
    ProjectInfo,
    daw_registry,
    connect_daw,
    quick_action
)

from .reaper_adapter import ReaperAdapter

# Phase 2: Additional DAW adapters (Pro Features)
try:
    from .logic_adapter import LogicAdapter
except ImportError:
    LogicAdapter = None

try:
    from .flstudio_adapter import FLStudioAdapter
except ImportError:
    FLStudioAdapter = None

try:
    from .ableton_adapter import AbletonAdapter
except ImportError:
    AbletonAdapter = None

try:
    from .cubase_adapter import CubaseAdapter
except ImportError:
    CubaseAdapter = None

try:
    from .protools_adapter import ProToolsAdapter
except ImportError:
    ProToolsAdapter = None

# Future adapters (stubs ready)
# from .cubase_adapter import CubaseAdapter
# from .protools_adapter import ProToolsAdapter

__all__ = [
    "BaseDAWAdapter",
    "DAWAdapterRegistry",
    "DAWPlatform",
    "TrackType",
    "TrackInfo",
    "DeviceInfo",
    "ProjectInfo",
    "daw_registry",
    "connect_daw",
    "quick_action",
    "ReaperAdapter",
    "LogicAdapter",
    "FLStudioAdapter",
    "AbletonAdapter",
    "CubaseAdapter",
    "ProToolsAdapter",
]

# Register all available adapters
daw_registry.register(ReaperAdapter())

if LogicAdapter:
    daw_registry.register(LogicAdapter())

if FLStudioAdapter:
    daw_registry.register(FLStudioAdapter())

if AbletonAdapter:
    daw_registry.register(AbletonAdapter())

if CubaseAdapter:
    daw_registry.register(CubaseAdapter())

if ProToolsAdapter:
    daw_registry.register(ProToolsAdapter())

# Print registered adapters
print(f"Ableton Brain: Registered DAW adapters: {daw_registry.list_available()}")