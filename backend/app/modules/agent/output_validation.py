"""Output validation — allowlist what the LLM may produce.

Layer 3 of the prompt-injection defense. Doesn't depend on the LLM behaving
correctly — it just checks the output shape against what the application
expects.
"""
from __future__ import annotations

import logging
import re

from app.core.errors import AppError

logger = logging.getLogger("security.output_validation")


_RULE_TEXT_FORBIDDEN = [
    ("contains.code_block",      re.compile(r"```", re.MULTILINE)),
    ("contains.role_marker",     re.compile(r"^\s*(?:system|user|assistant)\s*:", re.IGNORECASE | re.MULTILINE)),
    ("contains.chat_template",   re.compile(r"<\|(?:im_start|im_end|system|user|assistant)\|>", re.IGNORECASE)),
    ("contains.api_key_pattern", re.compile(r"\b(?:sk-|dapi[a-f0-9]{20,}|aws_[a-z_]+_key|secret[_-]?key\s*=)\b", re.IGNORECASE)),
    ("contains.injection_echo",  re.compile(r"\b(?:ignore|disregard)\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions?|prompt)\b", re.IGNORECASE)),
]

_RULE_TEXT_MIN_LENGTH = 20
_RULE_TEXT_MAX_LENGTH = 4000


def validate_business_rule_text(text: str) -> None:
    """Validate a streamed business rule before showing it to the user.

    Raises AppError("CDP-SEC-0101") if the output is outside the allowlist.
    Runs at the END of the stream, not per-token.
    """
    if not isinstance(text, str) or not text.strip():
        logger.warning("output_validation.rule_text empty_or_non_string")
        raise AppError("CDP-SEC-0101")

    length = len(text)
    if length < _RULE_TEXT_MIN_LENGTH:
        logger.warning("output_validation.rule_text too_short length=%d", length)
        raise AppError("CDP-SEC-0101")
    if length > _RULE_TEXT_MAX_LENGTH:
        logger.warning("output_validation.rule_text too_long length=%d", length)
        raise AppError("CDP-SEC-0101")

    for label, pattern in _RULE_TEXT_FORBIDDEN:
        m = pattern.search(text)
        if m:
            logger.warning(
                "output_validation.rule_text rejected label=%s match=%r preview=%r",
                label, m.group(0)[:80], text[:120],
            )
            raise AppError("CDP-SEC-0101")


# ─── Tool input validation (Phase 2 scaffolding) ──────────────────────────────
class _ToolValidator:
    """Per-tool input validator. Subclass and register in TOOL_VALIDATORS."""

    def validate(self, args: dict) -> None:
        raise NotImplementedError


TOOL_VALIDATORS: dict[str, _ToolValidator] = {
    # "save_draft_rule": SaveDraftRuleValidator(),    # ← Phase 2
}


def validate_tool_input(tool_name: str, args: dict) -> None:
    """Phase 2 entry point. Validates a proposed tool call.

    No-op in Phase 1. Hooked here so when a tool call arrives without a
    registered validator, we fail closed (refuse).
    """
    validator = TOOL_VALIDATORS.get(tool_name)
    if validator is None:
        logger.error("output_validation.tool_input no_validator tool=%s", tool_name)
        raise AppError("CDP-SEC-0102", context={"tool": tool_name})
    validator.validate(args)
