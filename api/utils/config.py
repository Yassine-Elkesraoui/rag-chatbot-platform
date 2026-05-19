"""
Configuration management for the RAG Chatbot API.

This module centralizes all application settings using the
pydantic-settings library, following the 12-Factor App methodology
for configuration management (Wiggins, 2017).

Settings are loaded from environment variables (typically defined
in a .env file at the project root) and validated against typed
Pydantic fields. This ensures that misconfigurations are caught
at application startup rather than at runtime.

Usage:
    >>> from api.utils.config import settings
    >>> print(settings.app_version)
    '0.4.0'
    >>> print(settings.api_port)
    8000

Architecture note:
    A single shared `settings` instance is exposed at the bottom
    of this module (singleton pattern). All other modules should
    import this instance rather than creating new Settings objects.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Each attribute corresponds to a key in the .env file. Pydantic
    automatically validates types, applies defaults, and raises
    clear errors if required values are missing.

    Attributes:
        app_name: Human-readable application name (used in API docs).
        app_version: Semantic version of the application.
        app_env: Deployment environment (development, staging, production).
        api_host: Network interface the API listens on.
        api_port: TCP port the API listens on.
        log_level: Minimum severity of log messages to display.
        openai_api_key: Secret key for the OpenAI API (used from Day 7).
        openai_model: Name of the OpenAI model to use for generation.
        database_url: Connection string for the relational database.
        chroma_persist_dir: Local path for ChromaDB persistence.
    """

    # --- Application Settings ---
    app_name: str = "RAG Chatbot Platform"
    app_version: str = "0.4.0"
    app_env: str = "development"

    # --- API Settings ---
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # --- Logging Settings ---
    log_level: str = "INFO"

    # --- OpenAI Settings (used from Day 7 onwards) ---
    # Default empty string allows the app to start without a key,
    # but any code path that needs OpenAI will fail with a clear error.
    openai_api_key: str = ""
    openai_model: str = "gpt-4"

    # --- Database Settings (used in later days) ---
    database_url: str = ""

    # --- ChromaDB Settings (used in later days) ---
    chroma_persist_dir: str = "./chroma_db"

    # --- Pydantic configuration ---
    # Tells pydantic-settings where to find the .env file
    # and how to behave when loading it.
    model_config = SettingsConfigDict(
        env_file=".env",            # Location of the .env file
        env_file_encoding="utf-8",  # Encoding (UTF-8 is the safe default)
        case_sensitive=False,       # Allow APP_NAME and app_name interchangeably
        extra="ignore",             # Silently ignore unknown env variables
    )


# Create a single shared instance of Settings.
# This follows the singleton pattern: every import of `settings`
# from this module returns the SAME object, ensuring consistency
# across the entire application.
settings = Settings()