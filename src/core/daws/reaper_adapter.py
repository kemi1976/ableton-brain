"""Reaper Adapter for ABLETON BRAIN."""

class ReaperAdapter:
    """Adapter for REAPER DAW integration using ReaScript."""
    
    def __init__(self, database=None):
        self.database = database or {}
        self.supported_extensions = ['.rpp', '.rppb', '.mid']
        self.api_version = "ReaScript 6.0"
    
    def get_supported_parameters(self):
        return [
            'track_volume', 'track_pan', 'send_level',
            'plugin_param', 'transport_play', 'transport_stop',
            'track_mute', 'track_solo'
        ]
    
    def map_to_reaper(self, parameter):
        mapping = {
            'volume': 'TRACK_VOLUME',
            'pan': 'TRACK_PAN',
            'cutoff': 'FX_PARAM_1',
            'attack': 'FX_PARAM_2',
        }
        return mapping.get(parameter, parameter)