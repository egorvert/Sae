"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # OpenAI (required)
    openai_api_key: str

    # Pinecone (optional - for future RAG integration)
    pinecone_api_key: str | None = None
    pinecone_index_name: str = "sae-legal"

    # Authentication (optional - set API_KEY to enable)
    api_key: str | None = None

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 30

    # CORS (set CORS_ORIGINS as comma-separated list in production)
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # Application
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    environment: Literal["development", "staging", "production"] = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Agent
    agent_name: str = "Sae Legal Agent"
    agent_version: str = "0.1.0"
    agent_description: str = "Contract clause review and risk analysis"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
