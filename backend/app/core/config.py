"""Centralised settings loaded from environment / .env"""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str

    # ── JWT ───────────────────────────────────────────────────────────────────
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 8       # 8h
    jwt_refresh_token_expire_minutes: int = 60 * 24 * 7 # 7d

    # ── App ───────────────────────────────────────────────────────────────────
    app_name: str = "CDP Platform"
    app_env: str = "development"
    cors_origins: str = "*"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
