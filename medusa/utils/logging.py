"""Logging configuration for Medusa."""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "medusa",
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Set up and configure logger.
    
    Args:
        name: Logger name
        level: Logging level
        format_string: Custom format string
        
    Returns:
        Configured logger instance
    """
    if format_string is None:
        format_string = "[%(asctime)s] [%(levelname)s] - %(message)s - [%(filename)s:%(lineno)d]"
    
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers if logger already exists
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        format_string,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


def get_logger(name: str = "medusa") -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)