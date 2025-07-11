"""URL parsing functionality."""

from typing import List
from urllib.parse import ParseResult, urlparse

from medusa.utils.exceptions import ValidationError
from medusa.utils.logging import get_logger

logger = get_logger(__name__)


class URLParser:
    """Handles parsing and validation of proxy URLs."""
    
    SUPPORTED_SCHEMES = {'ss', 'trojan', 'vmess', 'vless'}
    
    def parse_urls(self, urls: List[str]) -> List[ParseResult]:
        """Parse and validate proxy URLs.
        
        Args:
            urls: List of proxy URL strings
            
        Returns:
            List of parsed URL objects
            
        Raises:
            ValidationError: If no valid URLs found
        """
        if not urls:
            raise ValidationError("No URLs provided")
        
        parsed_urls = []
        invalid_count = 0
        
        for url in urls:
            url = url.strip()
            if not url:
                continue
                
            try:
                parsed = urlparse(url)
                
                if not self._is_valid_proxy_url(parsed):
                    invalid_count += 1
                    logger.debug(f"Skipping invalid URL: {url}")
                    continue
                
                parsed_urls.append(parsed)
                logger.debug(f"Successfully parsed URL: {parsed.scheme}://{parsed.netloc}")
                
            except Exception as e:
                invalid_count += 1
                logger.warning(f"Failed to parse URL '{url}': {e}")
                continue
        
        if not parsed_urls:
            raise ValidationError(
                f"No valid proxy URLs found. "
                f"Processed {len(urls)} URLs, {invalid_count} were invalid. "
                f"Supported schemes: {', '.join(self.SUPPORTED_SCHEMES)}"
            )
        
        logger.info(
            f"Successfully parsed {len(parsed_urls)} URLs "
            f"({invalid_count} invalid URLs skipped)"
        )
        return parsed_urls
    
    def _is_valid_proxy_url(self, parsed: ParseResult) -> bool:
        """Check if parsed URL is a valid proxy URL.
        
        Args:
            parsed: Parsed URL object
            
        Returns:
            True if URL is valid proxy URL
        """
        # Check scheme
        if parsed.scheme not in self.SUPPORTED_SCHEMES:
            return False
        
        # Check hostname
        if not parsed.hostname:
            return False
        
        # Check port (should be present and valid)
        if not parsed.port or not (1 <= parsed.port <= 65535):
            return False
        
        return True