-- ═══════════════════════════════════════════════════════════════════════════════
-- Agent module — Phase 1 with LangGraph orchestrator
-- Run after 02_seed.sql.
-- Replaces 03_agent_schema.sql (or, if you ran that, this is additive).
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE SCHEMA IF NOT EXISTS agent;

-- ─── task_log ─────────────────────────────────────────────────────────────────
-- One row per LLM invocation. Adds `thread_id` over the simple Phase 1 schema
-- so refinement turns can be correlated.
CREATE TABLE IF NOT EXISTS agent.task_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES core.users(id) ON DELETE RESTRICT,
    skill_id        VARCHAR(64)  NOT NULL,
    thread_id       VARCHAR(64),                    -- correlates refinement turns
    state           VARCHAR(20)  NOT NULL,           -- submitted | working | completed | failed
    input_text      TEXT         NOT NULL,
    output_text     TEXT,
    error           TEXT,
    duration_ms     INTEGER,
    output_chars    INTEGER,
    metadata        JSONB        NOT NULL DEFAULT '{}'::jsonb,
    started_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agent_task_log_user_started
    ON agent.task_log (user_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_task_log_thread
    ON agent.task_log (thread_id) WHERE thread_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_agent_task_log_skill_state
    ON agent.task_log (skill_id, state);

-- ─── Daily usage view (used by budget checker) ────────────────────────────────
CREATE OR REPLACE VIEW agent.daily_usage AS
SELECT user_id,
       date_trunc('day', started_at)        AS day,
       COUNT(*)                             AS task_count,
       COALESCE(SUM(output_chars), 0)       AS total_output_chars,
       COUNT(*) FILTER (WHERE state='failed') AS failure_count
FROM   agent.task_log
GROUP  BY user_id, date_trunc('day', started_at);

-- ─── LangGraph checkpoints ────────────────────────────────────────────────────
-- LangGraph's PostgresSaver creates its own tables on first run via
-- `await saver.setup()` — `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`.
-- They land in the `public` schema by default.
--
-- We DO NOT create them here — let LangGraph manage them. We just document the
-- expected presence so an ops person searching for the tables knows where they
-- come from.
--
-- If you want them in a dedicated schema, set the search_path on the connection
-- string used by the agent (Postgres-side option), or fork the LangGraph saver
-- to take a schema name. For Phase 1 we keep them in `public`; that's fine.
--
-- Tables LangGraph will create:
--   public.checkpoints         — graph state per (thread_id, checkpoint_id)
--   public.checkpoint_blobs    — large state values (channel writes)
--   public.checkpoint_writes   — per-channel write log
--
-- Don't ALTER these tables. If you need to move them, drop and let LangGraph
-- recreate.
