"""Tests for decoder functionality."""

import base64
import pytest

from medusa.core.decoder import ContentDecoder, Base64Decoder, URLSafeBase64Decoder, PlainTextDecoder
from medusa.utils.exceptions import DecodingError


class TestBase64Decoder:
    """Test Base64Decoder."""
    
    def test_decode_valid_base64(self):
        """Test decoding valid base64 content."""
        decoder = Base64Decoder()
        test_url = "ss://aes-256-gcm:password@example.com:443#test"
        encoded = base64.b64encode(test_url.encode())
        
        result = decoder.decode(encoded)
        assert len(result) == 1
        assert result[0] == test_url
    
    def test_decode_invalid_base64(self):
        """Test decoding invalid base64 content."""
        decoder = Base64Decoder()
        
        with pytest.raises(DecodingError):
            decoder.decode(b"invalid base64!")


class TestURLSafeBase64Decoder:
    """Test URLSafeBase64Decoder."""
    
    def test_decode_with_padding(self):
        """Test decoding URL-safe base64 with padding correction."""
        decoder = URLSafeBase64Decoder()
        test_url = "ss://aes-256-gcm:password@example.com:443#test"
        # Create URL-safe base64 without proper padding
        encoded = base64.urlsafe_b64encode(test_url.encode()).decode().rstrip('=')
        
        result = decoder.decode(encoded.encode())
        assert len(result) == 1
        assert result[0] == test_url


class TestPlainTextDecoder:
    """Test PlainTextDecoder."""
    
    def test_decode_valid_plain_text(self):
        """Test decoding valid plain text proxy URLs."""
        decoder = PlainTextDecoder()
        test_urls = "ss://aes-256-gcm:password@example.com:443#test\ntrojan://password@example.com:443#test2"
        
        result = decoder.decode(test_urls.encode())
        assert len(result) == 2
        assert "ss://" in result[0]
        assert "trojan://" in result[1]
    
    def test_decode_invalid_plain_text(self):
        """Test decoding invalid plain text."""
        decoder = PlainTextDecoder()
        
        with pytest.raises(DecodingError):
            decoder.decode(b"This is not a proxy URL")


class TestContentDecoder:
    """Test ContentDecoder."""
    
    def test_decode_base64_content(self):
        """Test decoding base64 encoded content."""
        decoder = ContentDecoder()
        test_url = "ss://aes-256-gcm:password@example.com:443#test"
        encoded = base64.b64encode(test_url.encode())
        
        result = decoder.decode(encoded)
        assert len(result) == 1
        assert result[0] == test_url
    
    def test_decode_plain_text_content(self):
        """Test decoding plain text content."""
        decoder = ContentDecoder()
        test_url = "ss://aes-256-gcm:password@example.com:443#test"
        
        result = decoder.decode(test_url.encode())
        assert len(result) == 1
        assert result[0] == test_url
    
    def test_decode_empty_content(self):
        """Test decoding empty content."""
        decoder = ContentDecoder()
        
        with pytest.raises(DecodingError, match="Empty content provided"):
            decoder.decode(b"")
    
    def test_decode_invalid_content(self):
        """Test decoding completely invalid content."""
        decoder = ContentDecoder()
        
        with pytest.raises(DecodingError, match="All decoding methods failed"):
            decoder.decode(b"completely invalid content that cannot be decoded")