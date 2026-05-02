"""AWS Secrets Manager provider with TTL cache.

TTL: secrets are cached for `cache_ttl_seconds` (default 1 hour). Bump the
secret in Secrets Manager, EC2 picks up the new value within the TTL with
zero deploy.

What this does NOT do:
  - Fall back to env on AWS failure. If Secrets Manager is unreachable at
    startup, the app fails to start. That's correct.
  - Push notifications on rotation. If you need <1h propagation, lower the
    TTL.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


class AwsSecretsManagerProvider:
    def __init__(self, *, cache_ttl_seconds: int | None = None, region: str | None = None) -> None:
        import boto3

        self._cache_ttl = cache_ttl_seconds or int(os.getenv("SECRETS_CACHE_TTL_SECONDS", "3600"))
        self._region = region or os.getenv("AWS_REGION", "eu-west-2")
        self._client = boto3.client("secretsmanager", region_name=self._region)
        self._cache: dict[str, tuple[dict[str, Any], float]] = {}

    def get(self, name: str) -> dict[str, Any]:
        cached = self._cache.get(name)
        now = time.monotonic()
        if cached is not None and (now - cached[1]) < self._cache_ttl:
            return cached[0]

        try:
            resp = self._client.get_secret_value(SecretId=name)
        except Exception as e:
            if cached is not None:
                logger.warning("secrets: AWS fetch failed for %s, serving stale: %s", name, e)
                return cached[0]
            raise RuntimeError(f"Failed to fetch secret {name}: {e}") from e

        raw = resp.get("SecretString")
        if raw is None:
            raise RuntimeError(f"Secret {name} has no SecretString (binary not supported)")

        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Secret {name} is not valid JSON: {e}") from e

        if not isinstance(decoded, dict):
            raise RuntimeError(f"Secret {name} must be a JSON object, got {type(decoded).__name__}")

        self._cache[name] = (decoded, now)
        logger.info("secrets: fetched %s (cache TTL %ds)", name, self._cache_ttl)
        return decoded

    def invalidate(self, name: str | None = None) -> None:
        if name is None:
            self._cache.clear()
        else:
            self._cache.pop(name, None)
