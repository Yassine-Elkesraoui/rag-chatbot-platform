"""
config.py
─────────
Centralized application configuration using pydantic-settings.

All configuration values are loaded from environment variables (or .env file)
following the 12-Factor App methodology (Wiggins, 2017), which mandates strict
separation between code and configuration.

This module exposes a single `Settings` class consumed by the rest of the
application via the `get_settings()` factory function.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Pydantic automatically reads values from the .env file at module import
    time, validates their types, and exposes them as typed attributes.

    Attributes:
        app_name: Human-readable application identifier.
        app_version: Semantic version string (major.minor.patch).
        app_env: Deployment environment (development | staging | production).
        api_host: Network interface the API binds to.
        api_port: Port number the API listens on.
        log_level: Minimum log severity (DEBUG | INFO | WARNING | ERROR).

        ollama_model: Identifier of the Ollama model to use for inference.
        ollama_temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).
        ollama_max_tokens: Maximum number of tokens to generate per response.
    """

    # ─── Application metadata ───────────────────────────────────────────
    app_name: str = "RAG Chatbot Platform"
    app_version: str = "0.5.0"
    app_env: str = "development"

    # ─── API server configuration ───────────────────────────────────────
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    log_level: str = "INFO"

    # ─── Ollama / Phi-3 Mini configuration ──────────────────────────────
    ollama_model: str = "phi3"
    ollama_temperature: float = 0.7
    ollama_max_tokens: int = 512

    # ─── Pydantic configuration ─────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Factory function returning a cached Settings instance.

    The `@lru_cache` decorator ensures Settings is instantiated only once
    per process — subsequent calls return the same object. This avoids
    repeatedly re-parsing the .env file on every API request.

    Returns:
        The singleton Settings instance.
    """
    return Settings()