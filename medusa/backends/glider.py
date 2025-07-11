"""Glider backend implementation."""

import base64
from typing import List, Dict, Type
from urllib.parse import ParseResult, unquote, parse_qs, urlparse, urlunparse

from medusa.backends.base import BackendConverter, ProxyHandler
from medusa.utils.exceptions import BackendError
from medusa.utils.logging import get_logger

logger = get_logger(__name__)


def b64decode_urlsafe(s: str) -> str:
    """Decode URL-safe base64 with padding correction."""
    missing_padding = len(s) % 4
    if missing_padding != 0:
        s += "=" * (4 - missing_padding)
    return base64.urlsafe_b64decode(s).decode()


class ShadowsocksHandler(ProxyHandler):
    """Handler for Shadowsocks (ss://) URLs."""
    
    @property
    def scheme(self) -> str:
        return "ss"
    
    def convert(self, parsed_url: ParseResult) -> str:
        """Convert ss:// URL to Glider format."""
        self.validate(parsed_url)
        
        # Handle base64 encoded netloc
        if parsed_url.username is None:
            try:
                netloc = b64decode_urlsafe(parsed_url.netloc)
                parsed_url = urlparse(urlunparse(parsed_url).replace(parsed_url.netloc, netloc))
            except Exception as e:
                raise BackendError(f"Failed to decode ss:// netloc: {e}")
        
        # Handle base64 encoded username (method:password)
        if parsed_url.password is None and parsed_url.username:
            try:
                username = b64decode_urlsafe(parsed_url.username)
                parsed_url = urlparse(urlunparse(parsed_url).replace(parsed_url.username, username))
            except Exception as e:
                raise BackendError(f"Failed to decode ss:// username: {e}")
        
        if not parsed_url.username or not parsed_url.password:
            raise BackendError("Missing username/password in ss:// URL")
        
        result = "".join([
            "forward=",
            parsed_url.scheme,
            "://",
            parsed_url.username,
            ":",
            parsed_url.password,
            "@",
            parsed_url.hostname,
            ":",
            str(parsed_url.port),
            "#",
            unquote(parsed_url.fragment) if parsed_url.fragment else "",
        ])
        
        return result


class TrojanHandler(ProxyHandler):
    """Handler for Trojan URLs."""
    
    @property
    def scheme(self) -> str:
        return "trojan"
    
    def convert(self, parsed_url: ParseResult) -> str:
        """Convert trojan:// URL to Glider format."""
        self.validate(parsed_url)
        
        if not parsed_url.username:
            raise BackendError("Missing password in trojan:// URL")
        
        # Parse query parameters
        query_params = parse_qs(parsed_url.query) if parsed_url.query else {}
        sni = query_params.get('sni', [None])[0]
        
        result = "".join([
            "forward=",
            parsed_url.scheme,
            "://",
            parsed_url.username,
            "@",
            parsed_url.hostname,
            ":",
            str(parsed_url.port),
            "?",
            f"serverName={sni}" if sni else "",
            "&skip-cert-verify=true",
            "#",
            unquote(parsed_url.fragment) if parsed_url.fragment else "",
        ])
        
        return result


class VmessHandler(ProxyHandler):
    """Handler for VMess URLs."""
    
    @property
    def scheme(self) -> str:
        return "vmess"
    
    def convert(self, parsed_url: ParseResult) -> str:
        """Convert vmess:// URL to Glider format."""
        self.validate(parsed_url)
        # VMess conversion logic would go here
        # For now, raise not implemented
        raise BackendError("VMess conversion not yet implemented")


class VlessHandler(ProxyHandler):
    """Handler for VLESS URLs."""
    
    @property
    def scheme(self) -> str:
        return "vless"
    
    def convert(self, parsed_url: ParseResult) -> str:
        """Convert vless:// URL to Glider format."""
        self.validate(parsed_url)
        # VLESS conversion logic would go here
        # For now, raise not implemented
        raise BackendError("VLESS conversion not yet implemented")


class GliderConverter(BackendConverter):
    """Glider backend converter."""
    
    def __init__(self):
        """Initialize Glider converter with handlers."""
        self._handlers: Dict[str, ProxyHandler] = {
            "ss": ShadowsocksHandler(),
            "trojan": TrojanHandler(),
            "vmess": VmessHandler(),
            "vless": VlessHandler(),
        }
    
    @property
    def name(self) -> str:
        return "glider"
    
    @property
    def supported_schemes(self) -> List[str]:
        return list(self._handlers.keys())
    
    def convert(self, parsed_urls: List[ParseResult]) -> List[str]:
        """Convert parsed URLs to Glider format.
        
        Args:
            parsed_urls: List of parsed proxy URLs
            
        Returns:
            List of Glider configuration strings
            
        Raises:
            BackendError: If conversion fails
        """
        if not parsed_urls:
            return []
        
        results = []
        errors = []
        
        for parsed_url in parsed_urls:
            try:
                logger.info(f"Converting {parsed_url.scheme}://{parsed_url.netloc}")
                
                handler = self._handlers.get(parsed_url.scheme)
                if not handler:
                    errors.append(f"Unsupported scheme: {parsed_url.scheme}")
                    continue
                
                converted = handler.convert(parsed_url)
                results.append(converted)
                logger.info(f"Successfully converted: {converted}")
                
            except Exception as e:
                error_msg = f"Failed to convert {parsed_url}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        if not results and errors:
            raise BackendError(f"All conversions failed: {'; '.join(errors)}")
        
        if errors:
            logger.warning(f"Some conversions failed: {'; '.join(errors)}")
        
        # Remove duplicates while preserving order
        return self._dedup_urls(results)
    
    def _dedup_urls(self, urls: List[str]) -> List[str]:
        """Remove duplicate URLs while preserving order.
        
        Args:
            urls: List of URLs to deduplicate
            
        Returns:
            Deduplicated list of URLs
        """
        seen = set()
        result = []
        
        for url in urls:
            # Extract URL without fragment for comparison
            if "#" in url:
                url_base = url.split("#")[0]
                fragment = url.split("#")[1]
            else:
                url_base = url
                fragment = ""
            
            if url_base not in seen:
                seen.add(url_base)
                result.append(url)
        
        logger.info(f"Deduplicated {len(urls)} URLs to {len(result)} unique URLs")
        return result