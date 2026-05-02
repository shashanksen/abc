"""A2A server for the CDP DQ agent.

Lifespan opens a Lakebase-aware Postgres connection pool — the pool refreshes
the OAuth token on every new connection, which is how Databricks Apps
authenticate to Lakebase Autoscaling (token TTL = 1 hour). The pool is handed
to LangGraph's AsyncPostgresSaver as the checkpointer.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import psycopg
from databricks.sdk import WorkspaceClient
from fastapi import FastAPI, Header, Request
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from sse_starlette.sse import EventSourceResponse

# Local modules — all sit in repo root.
from agent import NODE_LABELS, build_graph
from state import GraphState

log = logging.getLogger("a2a_server")
logging.basicConfig(level=logging.INFO)

# ─── Lakebase config (auto-injected by Databricks Apps when Lakebase is bound) ──
PGHOST     = os.environ["PGHOST"]
PGPORT     = os.environ.get("PGPORT", "5432")
PGUSER     = os.environ["PGUSER"]                  # service principal client_id
PGDATABASE = os.environ.get("PGDATABASE", "databricks_postgres")
PGSSLMODE  = os.environ.get("PGSSLMODE", "require")

# ─── Lakebase Autoscaling endpoint resource name ──────────────────────────────
# Required. Format: projects/<project>/branches/<branch>/endpoints/<endpoint-id>
# Get this value from Lakebase Console → project → Branches → production →
# Computes → primary → Get ID → Copy resource name.
LAKEBASE_ENDPOINT = os.environ["LAKEBASE_ENDPOINT_NAME"]

# WorkspaceClient picks up DATABRICKS_HOST/CLIENT_ID/CLIENT_SECRET from env
# automatically — these are auto-injected by Databricks Apps.
_w = WorkspaceClient()


class TokenRefreshingAsyncConnection(psycopg.AsyncConnection):
    """psycopg AsyncConnection that pulls a fresh OAuth token at connect-time.

    Called by the connection pool every time it opens a new connection.
    Existing connections keep their (initial) token until they're closed —
    Lakebase only enforces token expiry at login, so an open connection
    survives token expiry until the next operation that re-authenticates.
    """
    @classmethod
    async def connect(cls, conninfo: str = "", **kwargs):
        cred = _w.postgres.generate_database_credential(
            endpoint=LAKEBASE_ENDPOINT,
        )
        kwargs["password"] = cred.token
        return await super().connect(conninfo, **kwargs)


# ─── Build the conninfo string (no password — pool fills it in per conn) ──────
CONN_INFO = (
    f"host={PGHOST} port={PGPORT} dbname={PGDATABASE} user={PGUSER} sslmode={PGSSLMODE}"
)


# ─── Auth mode (shared secret OR OAuth verification) ──────────────────────────
AUTH_MODE = os.environ.get("AUTH_MODE", "shared_secret")
OAUTH_VERIFY_DISABLED = os.environ.get("OAUTH_VERIFY_DISABLED", "false").lower() == "true"

if AUTH_MODE == "oauth" and not OAUTH_VERIFY_DISABLED:
    from oauth_verify import verify_caller_token as _verify
else:
    from auth import verify_bearer as _verify


# ─── Migration runner with per-statement error visibility ─────────────────────
async def _setup_with_diagnostics(checkpointer: AsyncPostgresSaver) -> None:
    """Run LangGraph's migrations one at a time, logging which one fails.

    Why this exists: LangGraph's built-in setup() runs all migrations in a
    single transaction. If migration #2 fails, migrations #3+ all return
    'InFailedSqlTransaction', hiding the real cause. Running them on their
    own connections (with autocommit) surfaces the actual error.

    The MIGRATIONS list is copied from langgraph-checkpoint-postgres==2.0.5
    (langgraph/checkpoint/postgres/base.py). If you upgrade the package and
    its migrations change, this list needs updating — but for a one-time
    setup() debug, copying is fine.
    """
    from langgraph.checkpoint.postgres.base import MIGRATIONS

    log.info("Running %d LangGraph migrations one at a time…", len(MIGRATIONS))

    async with checkpointer.conn.connection() as conn:
        await conn.set_autocommit(True)
        async with conn.cursor() as cur:
            for i, migration in enumerate(MIGRATIONS):
                preview = migration.strip().split("\n")[0][:80]
                log.info("Migration %d/%d: %s…", i + 1, len(MIGRATIONS), preview)
                try:
                    await cur.execute(migration)
                    log.info("Migration %d OK", i + 1)
                except Exception:
                    log.exception("Migration %d FAILED — full SQL:\n%s", i + 1, migration)
                    raise


# ─── Lifespan ─────────────────────────────────────────────────────────────────
_pool: AsyncConnectionPool | None = None
_checkpointer: AsyncPostgresSaver | None = None
_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool, _checkpointer, _graph

    log.info("Opening Lakebase connection pool (endpoint=%s, host=%s)", LAKEBASE_ENDPOINT, PGHOST)
    _pool = AsyncConnectionPool(
        conninfo=CONN_INFO,
        connection_class=TokenRefreshingAsyncConnection,
        min_size=1,
        max_size=10,
        open=False,
    )
    await _pool.open()

    _checkpointer = AsyncPostgresSaver(_pool)
    try:
        await _setup_with_diagnostics(_checkpointer)
        log.info("LangGraph checkpointer ready")
    except Exception:
        log.exception("Checkpointer setup failed — root cause:")
        raise

    _graph = build_graph(_checkpointer)
    log.info("Agent graph built")

    try:
        yield
    finally:
        log.info("Closing connection pool")
        await _pool.close()


app = FastAPI(lifespan=lifespan)


# ─── A2A endpoint ─────────────────────────────────────────────────────────────
@app.post("/a2a/skills/{skill_id}/stream")
async def stream_skill(
    skill_id: str,
    request: Request,
    authorization: str = Header(default=""),
):
    _verify(authorization)

    body = await request.json()
    message  = body.get("message", {})
    metadata = message.get("metadata", {}) or {}
    user_id  = metadata.get("user_id", "unknown")
    thread_id = metadata.get("thread_id") or str(uuid.uuid4())
    text = message.get("parts", [{}])[0].get("text", "")

    log.info("Skill=%s user=%s thread=%s", skill_id, user_id, thread_id)

    return EventSourceResponse(_run(skill_id, text, user_id, thread_id))


async def _run(skill_id: str, text: str, user_id: str, thread_id: str) -> AsyncIterator[dict]:
    """Map LangGraph events → A2A protocol events."""
    yield {"event": "thread", "data": json.dumps({"thread_id": thread_id})}

    config = {"configurable": {"thread_id": thread_id}}
    state: GraphState = {"description": text, "messages": []}

    try:
        async for event in _graph.astream_events(state, config, version="v2"):
            kind = event["event"]
            name = event.get("name", "")

            if kind == "on_chain_start" and name in NODE_LABELS:
                yield {"event": "step", "data": json.dumps({"label": NODE_LABELS[name]})}

            elif kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                content = getattr(chunk, "content", "")
                if content:
                    yield {"event": "artifact-update", "data": json.dumps({"delta": content})}

            elif kind == "on_tool_start":
                yield {"event": "tool", "data": json.dumps({"phase": "start", "name": name})}
            elif kind == "on_tool_end":
                yield {"event": "tool", "data": json.dumps({"phase": "end", "name": name})}

        yield {"event": "completed", "data": json.dumps({"thread_id": thread_id})}

    except Exception as e:
        log.exception("Agent run failed")
        yield {"event": "error", "data": json.dumps({"message": str(e)})}


@app.get("/health")
async def health():
    return {"ok": True, "endpoint": LAKEBASE_ENDPOINT}