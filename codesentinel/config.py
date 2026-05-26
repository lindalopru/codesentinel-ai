"""Runtime configuration loaded from environment variables / .env file."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ollama_host: str = Field(default="http://127.0.0.1:11434")
    ollama_model: str = Field(default="qwen2.5-coder:7b-instruct-q4_K_M")
    ollama_num_ctx: int = Field(default=16384, ge=512)
    ollama_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    ollama_top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    ollama_timeout: int = Field(default=180, ge=10)

    max_file_lines: int = Field(default=1500, ge=100)
    concurrency: int = Field(default=2, ge=1, le=8)

    enable_bandit: bool = True
    enable_ruff: bool = True
    enable_eslint: bool = True


_settings: Settings | None = None


def get_settings() -> Settings:
    """Singleton accessor. Allows tests to patch via reset_settings()."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    global _settings
    _settings = None
