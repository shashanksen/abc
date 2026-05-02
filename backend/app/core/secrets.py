"""Secrets abstraction.

One interface, two implementations: env-var (dev) and AWS Secrets Manager
(prod). Anything that needs a secret reads through here, never directly
from os.environ.

Selecting the backend: SECRETS_BACKEND env var.
  - "env"                   → read from process env (dev default)
  - "aws-secrets-manager"   → read from AWS Secrets Manager (prod)

Note on env-mode: this provider also loads a sibling .env file at module
import (same file pydantic-settings reads). This matters because process
managers like PM2 sometimes don't inject JSON-shaped values into the
process environment. Loading via python-dotenv handles them correctly
and matches what pydantic-settings already does for non-secret fields.
"""
from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

# Load .env into os.environ at module import.
# Uses override=False so any value already set in the real env wins —
# important for production where Secrets Manager values arrive via env,
# not .env.
try:
    from dotenv import load_dotenv
    _ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"
    if _ENV_FILE.is_file():
        load_dotenv(_ENV_FILE, override=False)
except ImportError:
    pass

logger = logging.getLogger(__name__)


class SecretsProvider(ABC):
    @abstractmethod
    def get(self, name: str) -> dict[str, Any]:
        ...


class EnvSecretsProvider(SecretsProvider):
    """Reads secrets from process env vars.

    Mapping: secret name "cdp/jwt-keys" → env var "CDP_JWT_KEYS" containing JSON.
    """

    def get(self, name: str) -> dict[str, Any]:
        env_name = name.upper().replace("/", "_").replace("-", "_")
        raw = os.getenv(env_name)
        if raw is None:
            raise KeyError(f"Secret {name} not found in env (looked for {env_name})")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Secret {name} is not valid JSON: {e}") from e


_provider: SecretsProvider | None = None


def get_provider() -> SecretsProvider:
    global _provider
    if _provider is not None:
        return _provider

    backend = os.getenv("SECRETS_BACKEND", "env").lower()
    if backend == "env":
        logger.info("secrets: using env-var provider")
        _provider = EnvSecretsProvider()
    elif backend == "aws-secrets-manager":
        from .secrets_aws import AwsSecretsManagerProvider
        logger.info("secrets: using AWS Secrets Manager provider")
        _provider = AwsSecretsManagerProvider()
    else:
        raise RuntimeError(f"Unknown SECRETS_BACKEND: {backend!r}")

    return _provider


def get_secret(name: str) -> dict[str, Any]:
    return get_provider().get(name)


def _set_provider_for_tests(provider: SecretsProvider) -> None:
    global _provider
    _provider = provider


def _reset_provider() -> None:
    global _provider
    _provider = None