"""Configuration loading and management."""

import os
from functools import cache
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import ValidationError

from medusa.config.models import MedusaConfig
from medusa.utils.exceptions import ConfigurationError
from medusa.utils.logging import get_logger

logger = get_logger(__name__)


class ConfigLoader:
    """Handles loading and validation of configuration files."""
    
    def __init__(self, config_dir: Optional[Path] = None, template_dir: Optional[Path] = None):
        """Initialize config loader.
        
        Args:
            config_dir: Directory containing configuration files
            template_dir: Directory containing template files
        """
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "configs"
        if template_dir is None:
            template_dir = Path(__file__).parent.parent / "templates"
        self.config_dir = Path(config_dir)
        self.template_dir = Path(template_dir)
    
    @cache
    def load_config(self, filename: str = "config.yml") -> MedusaConfig:
        """Load and validate configuration file.
        
        Args:
            filename: Configuration file name or path
            
        Returns:
            Validated configuration object
            
        Raises:
            ConfigurationError: If configuration is invalid or file not found
        """
        # Handle absolute paths
        if Path(filename).is_absolute():
            config_path = Path(filename)
        else:
            config_path = self.config_dir / filename
        
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)
            
            if raw_config is None:
                raise ConfigurationError(f"Empty configuration file: {config_path}")
            
            config = MedusaConfig(**raw_config)
            logger.info(f"Loaded configuration from {config_path}")
            return config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {config_path}: {e}")
        except ValidationError as e:
            raise ConfigurationError(f"Invalid configuration in {config_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {config_path}: {e}")
    
    @cache
    def load_template(self, backend: str) -> List[str]:
        """Load template file for specified backend.
        
        Args:
            backend: Backend name (e.g., 'glider')
            
        Returns:
            Template content as list of lines
            
        Raises:
            ConfigurationError: If template file not found
        """
        template_path = self.template_dir / f"{backend}_template.conf"
        
        if not template_path.exists():
            raise ConfigurationError(f"Template file not found: {template_path}")
        
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.readlines()
            
            logger.info(f"Loaded template from {template_path}")
            return content
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load template from {template_path}: {e}")


# Global instance for backward compatibility
_config_loader = ConfigLoader()


def load_config(filename: str = "config.yml") -> MedusaConfig:
    """Load configuration using global loader."""
    return _config_loader.load_config(filename)


def load_template(backend: str) -> List[str]:
    """Load template using global loader."""
    return _config_loader.load_template(backend)