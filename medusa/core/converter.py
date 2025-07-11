"""Core conversion functionality."""

from typing import Dict, Type, List
from urllib.parse import ParseResult

from medusa.backends.base import BackendConverter
from medusa.backends.glider import GliderConverter
from medusa.utils.exceptions import BackendError
from medusa.utils.logging import get_logger

logger = get_logger(__name__)


class ConverterRegistry:
    """Registry for backend converters."""
    
    def __init__(self):
        """Initialize converter registry."""
        self._converters: Dict[str, BackendConverter] = {}
        self._register_default_converters()
    
    def _register_default_converters(self):
        """Register default converters."""
        self.register(GliderConverter())
    
    def register(self, converter: BackendConverter):
        """Register a backend converter.
        
        Args:
            converter: Backend converter to register
        """
        self._converters[converter.name] = converter
        logger.info(f"Registered converter for backend: {converter.name}")
    
    def get_converter(self, backend: str) -> BackendConverter:
        """Get converter for specified backend.
        
        Args:
            backend: Backend name
            
        Returns:
            Backend converter instance
            
        Raises:
            BackendError: If backend is not supported
        """
        converter = self._converters.get(backend)
        if not converter:
            available = list(self._converters.keys())
            raise BackendError(
                f"Unsupported backend '{backend}'. Available backends: {available}"
            )
        return converter
    
    def list_backends(self) -> List[str]:
        """List available backend names."""
        return list(self._converters.keys())


class ProxyConverter:
    """Main proxy converter that orchestrates the conversion process."""
    
    def __init__(self, registry: ConverterRegistry = None):
        """Initialize proxy converter.
        
        Args:
            registry: Converter registry (creates default if None)
        """
        self.registry = registry or ConverterRegistry()
    
    def convert(self, backend: str, parsed_urls: List[ParseResult]) -> List[str]:
        """Convert parsed URLs to specified backend format.
        
        Args:
            backend: Target backend name
            parsed_urls: List of parsed proxy URLs
            
        Returns:
            List of converted configuration strings
            
        Raises:
            BackendError: If conversion fails
        """
        if not parsed_urls:
            logger.warning("No URLs provided for conversion")
            return []
        
        converter = self.registry.get_converter(backend)
        logger.info(f"Converting {len(parsed_urls)} URLs using {backend} backend")
        
        return converter.convert(parsed_urls)


# Global instance for backward compatibility
_converter = ProxyConverter()


def convert_urls(backend: str, parsed_urls: List[ParseResult]) -> List[str]:
    """Convert URLs using global converter."""
    return _converter.convert(backend, parsed_urls)