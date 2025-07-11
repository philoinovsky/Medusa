"""Configuration data models."""

from typing import List
from pydantic import BaseModel, HttpUrl, Field


class MedusaConfig(BaseModel):
    """Main configuration model."""
    
    subscriptions: List[HttpUrl] = Field(
        ...,
        description="List of subscription URLs to fetch proxy configurations from",
        min_items=1
    )
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
        extra = "forbid"