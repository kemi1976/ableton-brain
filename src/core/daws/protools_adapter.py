"""Pro Tools Adapter for ABLETON BRAIN."""

class ProToolsAdapter:
    """Adapter for Pro Tools DAW integration."""
    
    def __init__(self, database=None):
        self.database = database or {}
        self.supported_extensions = ['.ptx', '.sesx', '.mid']
        self.api_version = "Pro Tools S6 API"
    
    def get_supported_parameters(self):
        return [
            'track_volume', 'track_pan', 'aux_send',
            'session_params', 'transport'
        ]
    
    def map_to_protools(self, parameter):
        mapping = {
            'volume': 'TRK_VOL',
            'pan': 'TRK_PAN',
            'cutoff': 'EQ_FREQ_1',
        }
        return mapping.get(parameter, parameter)