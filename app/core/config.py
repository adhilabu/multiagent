"""Core configuration module for the FastAPI application."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env
    )
    
    # API Keys
    openai_api_key: str
    tavily_api_key: str
    
    # Model configuration
    openai_model: str = "gpt-4o-mini"
    
    # Application settings
    debug: bool = False
    app_name: str = "Self-Correcting Research Assistant"
    version: str = "0.1.0"
    
    # Database
    checkpoint_db_path: str = "research_checkpoints.db"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
