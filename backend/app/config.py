"""
Configuration management using Pydantic Settings.
Loads from environment variables and .env file.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # NEO4J CONFIGURATION
    # =========================================================================
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="password")
    neo4j_max_pool_size: int = Field(default=50, description="Max connection pool size")

    # =========================================================================
    # LLM CONFIGURATION (via LiteLLM)
    # =========================================================================
    default_llm_model: str = Field(default="gpt-4o-mini")
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    ollama_base_url: str = Field(default="http://localhost:11434")

    # =========================================================================
    # EXTRACTION CONFIGURATION
    # =========================================================================
    extraction_model: str = Field(default="gpt-4o-mini")
    extraction_temperature: float = Field(default=0.0)
    extraction_max_tokens: int = Field(default=4096)

    # =========================================================================
    # RAG CONFIGURATION
    # =========================================================================
    rag_model: str = Field(default="gpt-4o-mini")
    rag_temperature: float = Field(default=0.7)
    rag_max_tokens: int = Field(default=2048)
    rag_max_conversation_history: int = Field(default=10, description="Max conversation turns to keep")

    # =========================================================================
    # CHUNKING CONFIGURATION
    # =========================================================================
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)

    # =========================================================================
    # APPLICATION SETTINGS
    # =========================================================================
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)
    debug: bool = Field(default=True)

    # =========================================================================
    # SCHEMA CONFIGURATION
    # =========================================================================
    active_schema: str = Field(
        default="contract",
        description="Name of the active schema (without .yaml extension)"
    )
    schemas_path: str = Field(default="schemas")

    # =========================================================================
    # STRATEGY CONFIGURATION
    # =========================================================================
    default_strategy_preset: str = Field(
        default="balanced",
        description="Default strategy preset (minimal, balanced, comprehensive, speed, research)"
    )

    # =========================================================================
    # PATHS
    # =========================================================================
    docs_path: str = Field(default="docs")
    upload_path: str = Field(default="uploads")


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses LRU cache to avoid re-reading .env file on every call.
    """
    return Settings()


# Convenience export
settings = get_settings()
