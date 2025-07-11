"""Tests for Glider backend."""

import pytest
from urllib.parse import urlparse

from medusa.backends.glider import GliderConverter, ShadowsocksHandler, TrojanHandler
from medusa.utils.exceptions import BackendError


class TestShadowsocksHandler:
    """Test ShadowsocksHandler."""
    
    def test_convert_valid_ss_url(self):
        """Test converting valid ss:// URL."""
        handler = ShadowsocksHandler()
        parsed_url = urlparse("ss://aes-256-gcm:password@example.com:443#test")
        
        result = handler.convert(parsed_url)
        expected = "forward=ss://aes-256-gcm:password@example.com:443#test"
        assert result == expected
    
    def test_convert_missing_credentials(self):
        """Test converting ss:// URL without credentials."""
        handler = ShadowsocksHandler()
        parsed_url = urlparse("ss://example.com:443#test")
        
        with pytest.raises(BackendError, match="Missing username/password"):
            handler.convert(parsed_url)


class TestTrojanHandler:
    """Test TrojanHandler."""
    
    def test_convert_valid_trojan_url(self):
        """Test converting valid trojan:// URL."""
        handler = TrojanHandler()
        parsed_url = urlparse("trojan://password@example.com:443?sni=example.com#test")
        
        result = handler.convert(parsed_url)
        assert "forward=trojan://password@example.com:443" in result
        assert "serverName=example.com" in result
        assert "skip-cert-verify=true" in result
        assert "#test" in result
    
    def test_convert_missing_password(self):
        """Test converting trojan:// URL without password."""
        handler = TrojanHandler()
        parsed_url = urlparse("trojan://example.com:443#test")
        
        with pytest.raises(BackendError, match="Missing password"):
            handler.convert(parsed_url)


class TestGliderConverter:
    """Test GliderConverter."""
    
    def test_convert_shadowsocks_urls(self):
        """Test converting Shadowsocks URLs."""
        converter = GliderConverter()
        parsed_urls = [
            urlparse("ss://aes-256-gcm:password1@example1.com:443#test1"),
            urlparse("ss://aes-256-gcm:password2@example2.com:443#test2"),
        ]
        
        result = converter.convert(parsed_urls)
        assert len(result) == 2
        assert all("forward=ss://" in config for config in result)
    
    def test_convert_mixed_urls(self):
        """Test converting mixed proxy URLs."""
        converter = GliderConverter()
        parsed_urls = [
            urlparse("ss://aes-256-gcm:password@example.com:443#test1"),
            urlparse("trojan://password@example.com:443#test2"),
        ]
        
        result = converter.convert(parsed_urls)
        assert len(result) == 2
        assert any("forward=ss://" in config for config in result)
        assert any("forward=trojan://" in config for config in result)
    
    def test_convert_unsupported_scheme(self):
        """Test converting URLs with unsupported schemes."""
        converter = GliderConverter()
        parsed_urls = [
            urlparse("http://example.com:80"),  # Unsupported scheme
        ]
        
        with pytest.raises(BackendError, match="All conversions failed"):
            converter.convert(parsed_urls)
    
    def test_convert_empty_list(self):
        """Test converting empty URL list."""
        converter = GliderConverter()
        
        result = converter.convert([])
        assert result == []
    
    def test_dedup_urls(self):
        """Test URL deduplication."""
        converter = GliderConverter()
        parsed_urls = [
            urlparse("ss://aes-256-gcm:password@example.com:443#test1"),
            urlparse("ss://aes-256-gcm:password@example.com:443#test2"),  # Same base, different fragment
            urlparse("ss://aes-256-gcm:password@example.com:443#test1"),  # Duplicate
        ]
        
        result = converter.convert(parsed_urls)
        # Should have 2 unique URLs (same base URL with different fragments)
        assert len(result) == 2