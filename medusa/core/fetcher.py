"""URL fetching functionality."""

import random
import time
from typing import Optional, Dict, List
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from medusa.utils.exceptions import FetchError
from medusa.utils.logging import get_logger

logger = get_logger(__name__)


class URLFetcher:
    """Handles fetching content from URLs with proper error handling and retries."""
    
    # Real word User-Agent string list
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0',
    ]
    
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
        session.headers.update(self._get_browser_headers())
        
        return session
    
    def _get_browser_headers(self) -> Dict[str, str]:
        """Get realistic browser headers."""
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    
    def _get_additional_headers(self, url: str) -> Dict[str, str]:
        """Get additional headers based on URL."""
        parsed = urlparse(url)
        headers = {}
        
        # Add referer for some domains
        if any(domain in parsed.netloc for domain in ['github.com', 'gitlab.com', 'bitbucket.org']):
            headers['Referer'] = f"https://{parsed.netloc}/"
        
        # Add origin for API endpoints
        if 'api' in parsed.path or 'subscribe' in parsed.path:
            headers['Origin'] = f"{parsed.scheme}://{parsed.netloc}"
        
        return headers
    
    def fetch(self, url: str) -> bytes:
        """Fetch content from URL with anti-detection measures.
        
        Args:
            url: URL to fetch
            
        Returns:
            Response content as bytes
            
        Raises:
            FetchError: If fetching fails
        """
        logger.info(f"Fetching subscription from {url}")
        
        # add random delay to simulate human behaviour
        time.sleep(random.uniform(0.5, 2.0))
        
        try:
            additional_headers = self._get_additional_headers(url)
            
            # try multiple strategies
            strategies = [
                self._try_direct_request,
                self._try_with_flag_parameter,
                self._try_with_different_headers,
                self._try_with_session_reset,
                self._try_with_curl_headers,
                self._try_with_mobile_headers,
                self._try_with_wget_headers,
            ]
            
            last_error = None
            for i, strategy in enumerate(strategies):
                try:
                    logger.debug(f"Trying strategy {i+1}/{len(strategies)}: {strategy.__name__}")
                    response = strategy(url, additional_headers)
                    
                    if response and response.content:
                        logger.info(f"Successfully fetched {len(response.content)} bytes from {url}")
                        return response.content
                        
                except requests.RequestException as e:
                    last_error = e
                    logger.debug(f"Strategy {strategy.__name__} failed: {e}")
                    # add delay between strategies
                    if i < len(strategies) - 1:
                        time.sleep(random.uniform(1.0, 3.0))
                    continue
            
            # all strategies failed
            error_msg = f"Failed to fetch subscription from {url}: {last_error}"
            logger.error(error_msg)
            raise FetchError(error_msg) from last_error
            
        except Exception as e:
            if isinstance(e, FetchError):
                raise
            error_msg = f"Unexpected error fetching {url}: {e}"
            logger.error(error_msg)
            raise FetchError(error_msg) from e
    
    def _try_direct_request(self, url: str, additional_headers: Dict[str, str]) -> requests.Response:
        """Try direct request with current session."""
        headers = {**additional_headers}
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response
    
    def _try_with_flag_parameter(self, url: str, additional_headers: Dict[str, str]) -> requests.Response:
        """Try with flag parameter if response suggests it."""
        # First try original URL to check response
        response = self.session.get(url, headers=additional_headers, timeout=self.timeout)
        
        # Check if response contains error message suggesting to use flag
        if (
            response.status_code == 200 and
            "flag=ss" in response.text and 
            not any(response.text.startswith(scheme) for scheme in ['ss://', 'trojan://', 'vmess://', 'vless://'])
        ):
            logger.info("Response suggests using flag parameter, trying with &flag=ss")
            flag_url = url + ("&flag=ss" if "?" in url else "?flag=ss")
            response = self.session.get(flag_url, headers=additional_headers, timeout=self.timeout)
            response.raise_for_status()
            logger.info("Successfully fetched with flag parameter")
        else:
            response.raise_for_status()
        
        return response
    
    def _try_with_different_headers(self, url: str, additional_headers: Dict[str, str]) -> requests.Response:
        """Try with different User-Agent and headers."""
        # try with different User-Agent
        headers = {
            **additional_headers,
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/plain, */*',  # 简化Accept头
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        }
        
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response
    
    def _try_with_session_reset(self, url: str, additional_headers: Dict[str, str]) -> requests.Response:
        """Try with a fresh session."""
        # create a new session
        fresh_session = requests.Session()
        
        # set basic headers
        fresh_session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })
        
        headers = {**additional_headers}
        response = fresh_session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response
    
    def _try_with_curl_headers(self, url: str, additional_headers: Dict[str, str]) -> requests.Response:
        """Try with curl-like headers."""
        headers = {
            **additional_headers,
            'User-Agent': 'curl/7.68.0',
            'Accept': '*/*',
        }
        
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response
    
    def _try_with_mobile_headers(self, url: str, additional_headers: Dict[str, str]) -> requests.Response:
        """Try with mobile browser headers."""
        mobile_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
        ]
        
        headers = {
            **additional_headers,
            'User-Agent': random.choice(mobile_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response
    
    def _try_with_wget_headers(self, url: str, additional_headers: Dict[str, str]) -> requests.Response:
        """Try with wget-like headers."""
        headers = {
            **additional_headers,
            'User-Agent': 'Wget/1.20.3 (linux-gnu)',
            'Accept': '*/*',
            'Accept-Encoding': 'identity',
            'Connection': 'Keep-Alive',
        }
        
        response = self.session.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.session.close()