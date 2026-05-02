"""Centralised settings.

Non-sensitive values come from env / .env. Sensitive values come from the
secrets provider (env in dev, AWS Secrets Manager in prod).

Sensitive values are properties (re-read on each access) so rotation in
Secrets Manager flows through without restart, within the cache TTL.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.secrets import get_secret


class Settings(BaseSettings):
    # ── Non-sensitive (env / .env) ────────────────────────────────────────────
    app_name: str = "CDP Platform"
    app_env:  str = "development"
    cors_origins: str = "*"

    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 8        # 8h
    jwt_refresh_token_expire_minutes: int = 60 * 24 * 7  # 7d

    # Secrets backend selector (env | aws-secrets-manager)
    secrets_backend: str = "env"

    # ── Sensitive (loaded via secrets provider) ───────────────────────────────
    @property
    def database_url(self) -> str:
        return get_secret("cdp/db/main")["url"]

    @property
    def jwt_user_session_key(self) -> str:
        """Active key for signing/verifying user access tokens."""
        return get_secret("cdp/jwt-keys")["user_session"]

    @property
    def jwt_user_session_key_legacy(self) -> str | None:
        """Optional old key, accepted for verify only during migration.

        Set this in the secret JSON during the 8-hour migration window after
        a rotation; remove afterwards.
        """
        return get_secret("cdp/jwt-keys").get("user_session_legacy")

    @property
    def jwt_agent_callback_key(self) -> str:
        """Separate key for short-lived on-behalf-of agent tokens."""
        return get_secret("cdp/jwt-keys")["agent_callback"]

    @property
    def databricks_oauth_client_id(self) -> str:
        return get_secret("cdp/databricks/oauth")["client_id"]

    @property
    def databricks_oauth_client_secret(self) -> str:
        return get_secret("cdp/databricks/oauth")["client_secret"]

    @property
    def databricks_oauth_token_endpoint(self) -> str:
        # Account-level OAuth token endpoint. Format:
        #   https://accounts.cloud.databricks.com/oidc/accounts/<account-id>/v1/token
        # VERIFY against current Databricks docs before going to prod.
        return get_secret("cdp/databricks/oauth")["token_endpoint"]

    @property
    def databricks_agent_base_url(self) -> str:
        return get_secret("cdp/databricks/agent-app")["base_url"]

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
