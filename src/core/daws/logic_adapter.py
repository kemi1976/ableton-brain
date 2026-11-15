"""Logic Pro Adapter for ABLETON BRAIN."""

class LogicAdapter:
    """Adapter for Logic Pro DAW integration."""
    
    def __init__(self, database=None):
        self.database = database or {}
        self.supported_extensions = ['.logicx', '.logic', '.mid']
        self.api_version = "Logic X API"
    
    def get_supported_parameters(self):
        return [
            'track_volume', 'track_pan', 'plugin_param',
            'region_params', 'transport_controls'
        ]
    
    def map_to_logic(self, parameter):
        mapping = {
            'volume': 'ChannelStrip_Volume',
            'pan': 'ChannelStrip_Pan',
            'cutoff': 'Plugin_Param_1',
        }
        return mapping.get(parameter, parameter)