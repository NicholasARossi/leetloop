"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App settings
    app_name: str = "LeetLoop API"
    debug: bool = False
    environment: str = "development"

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: Optional[str] = None

    # Database (direct connection for SQLAlchemy)
    database_url: Optional[str] = None

    # Google AI (Gemini)
    google_api_key: Optional[str] = None

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://leetloop.vercel.app",
    ]

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds

    # Cron job authentication
    cron_secret: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars like PORT


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
