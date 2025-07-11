"""Custom exceptions for Medusa."""


class MedusaError(Exception):
    """Base exception for all Medusa errors."""
    pass


class ConfigurationError(MedusaError):
    """Raised when there's an issue with configuration."""
    pass


class FetchError(MedusaError):
    """Raised when URL fetching fails."""
    pass


class DecodingError(MedusaError):
    """Raised when decoding subscription data fails."""
    pass


class ConversionError(MedusaError):
    """Raised when converting proxy configurations fails."""
    pass


class BackendError(MedusaError):
    """Raised when backend-specific operations fail."""
    pass


class ValidationError(MedusaError):
    """Raised when data validation fails."""
    pass