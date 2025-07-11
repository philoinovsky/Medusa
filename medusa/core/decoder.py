"""Content decoding functionality."""

import base64
from typing import List, Protocol

from medusa.utils.exceptions import DecodingError
from medusa.utils.logging import get_logger

logger = get_logger(__name__)


class DecoderProtocol(Protocol):
    """Protocol for content decoders."""
    
    def decode(self, content: bytes) -> List[str]:
        """Decode content and return list of proxy URLs."""
        ...


class Base64Decoder:
    """Standard base64 decoder."""
    
    def decode(self, content: bytes) -> List[str]:
        """Decode standard base64 content.
        
        Args:
            content: Base64 encoded content
            
        Returns:
            List of decoded proxy URLs
            
        Raises:
            DecodingError: If decoding fails
        """
        try:
            decoded = base64.b64decode(content).decode('utf-8')
            urls = decoded.splitlines(keepends=False)
            logger.info(f"Successfully decoded using standard base64: {len(urls)} URLs")
            return [url for url in urls if url.strip()]
        except Exception as e:
            raise DecodingError(f"Standard base64 decoding failed: {e}") from e


class URLSafeBase64Decoder:
    """URL-safe base64 decoder with padding correction."""
    
    def decode(self, content: bytes) -> List[str]:
        """Decode URL-safe base64 content with padding correction.
        
        Args:
            content: URL-safe base64 encoded content
            
        Returns:
            List of decoded proxy URLs
            
        Raises:
            DecodingError: If decoding fails
        """
        try:
            content_str = content.decode('utf-8')
            # Add padding if necessary
            missing_padding = len(content_str) % 4
            if missing_padding != 0:
                content_str += "=" * (4 - missing_padding)
            
            decoded = base64.urlsafe_b64decode(content_str).decode('utf-8')
            urls = decoded.splitlines(keepends=False)
            logger.info(f"Successfully decoded using URL-safe base64: {len(urls)} URLs")
            return [url for url in urls if url.strip()]
        except Exception as e:
            raise DecodingError(f"URL-safe base64 decoding failed: {e}") from e


class PlainTextDecoder:
    """Plain text decoder for non-encoded content."""
    
    def decode(self, content: bytes) -> List[str]:
        """Decode plain text content.
        
        Args:
            content: Plain text content
            
        Returns:
            List of proxy URLs
            
        Raises:
            DecodingError: If content is not valid plain text
        """
        try:
            text_content = content.decode('utf-8')
            urls = text_content.splitlines(keepends=False)
            
            # Validate that content contains proxy URLs
            valid_schemes = ['ss://', 'trojan://', 'vmess://', 'vless://']
            if not any(
                any(url.strip().startswith(scheme) for scheme in valid_schemes)
                for url in urls
            ):
                raise DecodingError("Content doesn't appear to contain valid proxy URLs")
            
            logger.info(f"Successfully processed as plain text: {len(urls)} URLs")
            return [url for url in urls if url.strip()]
        except UnicodeDecodeError as e:
            raise DecodingError(f"Plain text decoding failed: {e}") from e


class ContentDecoder:
    """Main decoder that tries multiple decoding strategies."""
    
    def __init__(self):
        """Initialize decoder with available strategies."""
        self.decoders: List[DecoderProtocol] = [
            Base64Decoder(),
            URLSafeBase64Decoder(),
            PlainTextDecoder(),
        ]
    
    def decode(self, content: bytes) -> List[str]:
        """Decode content using multiple strategies.
        
        Args:
            content: Content to decode
            
        Returns:
            List of decoded proxy URLs
            
        Raises:
            DecodingError: If all decoding strategies fail
        """
        if not content:
            raise DecodingError("Empty content provided")
        
        errors = []
        
        for decoder in self.decoders:
            try:
                urls = decoder.decode(content)
                if urls:  # Only return if we got valid URLs
                    return urls
            except DecodingError as e:
                errors.append(f"{decoder.__class__.__name__}: {e}")
                continue
        
        # If we get here, all decoders failed
        error_msg = f"All decoding methods failed: {'; '.join(errors)}"
        logger.error(error_msg)
        raise DecodingError(error_msg)