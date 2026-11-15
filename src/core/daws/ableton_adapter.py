"""Ableton Live Adapter for ABLETON BRAIN."""

class AbletonAdapter:
    """Adapter for Ableton Live DAW integration."""
    
    def __init__(self, database=None):
        self.database = database or {}
        self.supported_extensions = ['.als', '.mid', '.midi']
        self.api_version = "Live 11 API"
    
    def get_supported_parameters(self):
        """Return list of supported DAW parameters."""
        return [
            'track_volume', 'track_pan', 'device_on', 
            'device_parameter', 'clip_launch', 'scene_launch',
            'global_contrast', 'global_gamma'
        ]
    
    def map_to_ableton(self, parameter):
        """Map a generic parameter to Ableton-specific path."""
        mapping = {
            'volume': 'track_volume',
            'pan': 'track_pan',
            'cutoff': 'device_parameter_1',
            'resonance': 'device_parameter_2',
            'attack': 'device_parameter_3',
            'release': 'device_parameter_4',
        }
        return mapping.get(parameter, parameter)