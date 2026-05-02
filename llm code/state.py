"""LangGraph state for the DQ orchestrator.

The state is what the checkpointer persists between turns. Anything in here
is durable — the user's description, the conversation history, the latest
draft. Anything *not* in here (the on-behalf-of JWT, request IDs, the
user_id) goes through `config["configurable"]` instead, which is per-turn
and never persisted. This separation is deliberate — we don't want
short-lived tokens or PII in the checkpoint table.

Adding more state for Phase 2 (intent classification result, tool call
results, validation feedback, etc.) is a one-line addition here.
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict, total=False):
    """Persistable graph state.

    Fields are `total=False` so partial updates don't have to fill in
    everything — a node returning `{"draft_text": "..."}` won't blow away
    `messages`, and vice versa.
    """

    # ─── Input ────────────────────────────────────────────────────────────
    # The user's prompt for this turn. On the first turn, this seeds the
    # conversation. On refinement turns (same thread_id), this is the user's
    # new feedback or follow-up question.
    description: str

    # ─── Output ───────────────────────────────────────────────────────────
    # The latest generated rule text. Replaced (not appended) each turn —
    # think of it as "the current draft," not history.
    draft_text: str

    # ─── History ──────────────────────────────────────────────────────────
    # Conversation history across turns. The `add_messages` reducer makes
    # this an append-only list — when a node returns `{"messages": [m1, m2]}`,
    # those get appended to whatever was already there. Critical for
    # refinement: turn 2's draft node sees turn 1's exchange.
    messages: Annotated[list[BaseMessage], add_messages]