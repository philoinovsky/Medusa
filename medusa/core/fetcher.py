"""URL fetching functionality."""

from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from medusa.utils.exceptions import FetchError
from medusa.utils.logging import get_logger

logger = get_logger(__name__)


class URLFetcher:
    """Handles fetching content from URLs with proper error handling and retries."""
    
    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.3
    ):
        """Initialize URL fetcher.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for retries
        """
        self.timeout = timeout
        self.session = self._create_session(max_retries, backoff_factor)
    
    def _create_session(self, max_retries: int, backoff_factor: float) -> requests.Session:
        """Create configured requests session with retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers to simulate browser request
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        })
        
        return session
    
    def fetch(self, url: str) -> bytes:
        """Fetch content from URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            Response content as bytes
            
        Raises:
            FetchError: If fetching fails
        """
        logger.info(f"Fetching subscription from {url}")
        
        try:
            # First try the original URL
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # Check if response contains error message suggesting to use flag
            if (
                "flag=ss" in response.text 
                and not any(
                    response.text.startswith(scheme) 
                    for scheme in ['ss://', 'trojan://', 'vmess://', 'vless://']
                )
            ):
                logger.info("Original URL returned error message, trying with &flag=ss")
                # Try with flag parameter
                flag_url = url + ("&flag=ss" if "?" in url else "?flag=ss")
                response = self.session.get(flag_url, timeout=self.timeout)
                response.raise_for_status()
                logger.info("Successfully fetched with flag parameter")
            
            logger.info(f"Successfully fetched {len(response.content)} bytes from {url}")
            return response.content
            
        except requests.RequestException as e:
            error_msg = f"Failed to fetch subscription from {url}: {e}"
            logger.error(error_msg)
            raise FetchError(error_msg) from e
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.session.close()