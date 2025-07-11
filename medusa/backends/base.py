"""Base classes for backend implementations."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from urllib.parse import ParseResult

from medusa.utils.exceptions import BackendError


class BackendConverter(ABC):
    """Abstract base class for backend converters."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name."""
        pass
    
    @property
    @abstractmethod
    def supported_schemes(self) -> List[str]:
        """List of supported proxy schemes."""
        pass
    
    @abstractmethod
    def convert(self, parsed_urls: List[ParseResult]) -> List[str]:
        """Convert parsed URLs to backend-specific format.
        
        Args:
            parsed_urls: List of parsed proxy URLs
            
        Returns:
            List of converted configuration strings
            
        Raises:
            BackendError: If conversion fails
        """
        pass
    
    def validate_url(self, parsed_url: ParseResult) -> bool:
        """Validate if URL is supported by this backend.
        
        Args:
            parsed_url: Parsed URL to validate
            
        Returns:
            True if URL is supported
        """
        return parsed_url.scheme in self.supported_schemes


class ProxyHandler(ABC):
    """Abstract base class for proxy protocol handlers."""
    
    @property
    @abstractmethod
    def scheme(self) -> str:
        """Proxy scheme this handler supports."""
        pass
    
    @abstractmethod
    def convert(self, parsed_url: ParseResult) -> str:
        """Convert parsed URL to backend format.
        
        Args:
            parsed_url: Parsed proxy URL
            
        Returns:
            Converted configuration string
            
        Raises:
            BackendError: If conversion fails
        """
        pass
    
    def validate(self, parsed_url: ParseResult) -> None:
        """Validate parsed URL for this handler.
        
        Args:
            parsed_url: Parsed URL to validate
            
        Raises:
            BackendError: If URL is invalid for this handler
        """
        if parsed_url.scheme != self.scheme:
            raise BackendError(
                f"Invalid scheme '{parsed_url.scheme}' for {self.scheme} handler"
            )
        
        if not parsed_url.hostname:
            raise BackendError(f"Missing hostname in {self.scheme} URL")
        
        if not parsed_url.port:
            raise BackendError(f"Missing port in {self.scheme} URL")