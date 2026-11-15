"""Base DAW Adapter class."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class BaseDAWAdapter(ABC):
    """Abstract base class for DAW adapters."""
    
    def __init__(self, database: Optional[Dict] = None):
        self.database = database or {}
        self._initialized = False
    
    @abstractmethod
    def get_supported_parameters(self) -> List[str]:
        """Return list of parameters this DAW supports."""
        pass
    
    @abstractmethod
    def map_to_daw(self, parameter: str) -> str:
        """Map a generic parameter to DAW-specific identifier."""
        pass
    
    def is_connected(self) -> bool:
        """Check if DAW is connected and ready."""
        return self._initialized
    
    def initialize(self) -> bool:
        """Initialize the adapter connection to DAW."""
        # Override in subclasses for actual implementation
        self._initialized = True
        return True
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return adapter capabilities."""
        return {
            'supported_parameters': self.get_supported_parameters(),
            'connected': self.is_connected(),
            'api_version': getattr(self, 'api_version', 'unknown'),
        }