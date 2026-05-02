"""Prompt safety — input boundary for LLM-bound user text.

Layer 1 of the prompt-injection defense. Catches blatant injection markers.
Sophisticated attacks slip past — that's why layer 4 (RBAC + on-behalf-of
token) is what actually protects the system.

Rejection policy: generic CDP-SEC-0100 to the user, full diagnostic detail
logged at WARNING level for security review.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from uuid import UUID

from app.core.errors import AppError

logger = logging.getLogger("security.prompt_safety")


_INJECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("override.ignore_instructions", re.compile(
        r"\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above|earlier|the)\s+"
        r"(instructions?|prompt|context|rules|directives)\b",
        re.IGNORECASE,
    )),
    ("override.new_instructions", re.compile(
        r"\b(your\s+new|new\s+task|updated\s+(?:instructions?|task|directive))\s+(?:is|are)\b",
        re.IGNORECASE,
    )),
    ("role.system_marker", re.compile(
        r"(?:^|\n)\s*(?:system|assistant|user)\s*:\s*",
        re.IGNORECASE,
    )),
    ("role.chat_template", re.compile(
        r"<\|(?:im_start|im_end|system|user|assistant|begin_of_text|end_of_text|"
        r"start_header_id|end_header_id|eot_id)\|?>",
        re.IGNORECASE,
    )),
    ("jailbreak.dan", re.compile(
        r"\b(?:DAN|do\s+anything\s+now|developer\s+mode\s+enabled)\b",
        re.IGNORECASE,
    )),
    ("jailbreak.unrestricted", re.compile(
        r"\b(?:unrestricted|uncensored|no\s+(?:restrictions?|filters?|rules?|guidelines?))\s+"
        r"(?:mode|version|model|assistant|ai)\b",
        re.IGNORECASE,
    )),
    ("tool.hijack", re.compile(
        r"\b(?:execute|run|invoke|call)\s+(?:tool|function|api)\s*[:\(]",
        re.IGNORECASE,
    )),
    ("tool.dump_secrets", re.compile(
        r"\b(?:print|reveal|show|dump|output)\s+(?:your\s+)?(?:system\s+prompt|instructions|"
        r"api\s+key|secret|token|password|credentials?)\b",
        re.IGNORECASE,
    )),
    ("indirect.code_block_with_instruction", re.compile(
        r"```[\s\S]*?\b(ignore|disregard|forget|override)\s+(previous|prior|above)",
        re.IGNORECASE,
    )),
]


_MAX_INPUT_CHARS = 2000
_STRIP_CONTROL_CATEGORIES = {"Cc", "Cf", "Cs"}


def assert_safe_input(
    text: str,
    *,
    user_id: UUID | None = None,
    context: str = "agent_input",
) -> str:
    """Run all safety checks on user-supplied text bound for the LLM.

    Returns the cleaned text if all checks pass.
    Raises AppError("CDP-SEC-0100") if any check fails.
    """
    if not isinstance(text, str):
        _log_rejection(user_id=user_id, label="type.not_string", preview="<non-string>", context=context)
        raise AppError("CDP-SEC-0100")

    if len(text) > _MAX_INPUT_CHARS:
        _log_rejection(
            user_id=user_id, label="length.exceeded",
            preview=text[:80], context=context,
            extra={"length": len(text)},
        )
        raise AppError("CDP-SEC-0100")

    # NFKC collapses compatibility characters so attackers can't bypass with
    # lookalikes like fullwidth ASCII.
    normalized = unicodedata.normalize("NFKC", text)
    cleaned = "".join(
        ch for ch in normalized
        if (unicodedata.category(ch) not in _STRIP_CONTROL_CATEGORIES) or (ch in "\n\r\t")
    )

    for label, pattern in _INJECTION_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            _log_rejection(
                user_id=user_id, label=label,
                preview=cleaned[:80], context=context,
                extra={"matched": match.group(0)[:100]},
            )
            raise AppError("CDP-SEC-0100")

    return cleaned


def _log_rejection(
    *, user_id: UUID | None, label: str, preview: str, context: str, extra: dict | None = None,
) -> None:
    logger.warning(
        "prompt_injection_detected label=%s user=%s context=%s preview=%r extra=%s",
        label,
        str(user_id) if user_id else "anonymous",
        context,
        preview,
        extra or {},
    )
