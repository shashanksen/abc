"""Pydantic schemas for the agent module."""
from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateBusinessRuleRequest(BaseModel):
    description: str = Field(
        min_length=10,
        max_length=2000,
        description="Short natural-language description of what the rule should check.",
    )
    thread_id: str | None = Field(
        default=None,
        max_length=64,
        description="Optional thread_id for refinement turns. Phase 1 UI doesn't use it.",
    )
