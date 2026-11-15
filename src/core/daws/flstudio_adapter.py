"""FL Studio Adapter for ABLETON BRAIN."""

class FLStudioAdapter:
    """Adapter for FL Studio DAW integration."""
    
    def __init__(self, database=None):
        self.database = database or {}
        self.supported_extensions = ['.flp', '.mid']
        self.api_version = "FL Studio API 20+"
    
    def get_supported_parameters(self):
        return [
            'track_volume', 'track_pan', 'plugin_param',
            'step sequencer', 'playlist'
        ]
    
    def map_to_flstudio(self, parameter):
        mapping = {
            'volume': 'MAIN_VOLUME',
            'pan': 'MAIN_PAN',
            'cutoff': 'PLUGIN_CUTOFF',
        }
        return mapping.get(parameter, parameter)