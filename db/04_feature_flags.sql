-- ═══════════════════════════════════════════════════════════════════════════════
-- Feature flags
-- Run after any earlier migrations.
--
-- A simple key-value table for boolean platform-level flags. The first
-- consumer is the agent kill-switch; future flags slot in without schema
-- changes.
--
-- Why a table instead of an env var? Two reasons:
--   1. Toggling without a redeploy. An admin clicks a button, the flag flips,
--      next request honors it. Env vars need a process restart.
--   2. Audit trail. Every flip is recorded in core.audit_log via the
--      AuditService — we know who turned the kill-switch on and when.
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS core.feature_flags (
    code            VARCHAR(64)  PRIMARY KEY,
    enabled         BOOLEAN      NOT NULL,
    description     TEXT,
    updated_by      UUID         REFERENCES core.users(id),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Seed the agent kill-switch as DISABLED (= agent is allowed to run).
-- The flag is `agent.kill_switch`; when enabled=true, the kill-switch IS
-- active and the agent is blocked. Slightly counterintuitive, but the
-- dominant pattern in feature-flag tables is "enabled=ON," so we keep
-- naming consistent and document the inversion in the admin UI.
INSERT INTO core.feature_flags (code, enabled, description) VALUES
  ('agent.kill_switch', FALSE,
   'When ON, all agent skill invocations are blocked platform-wide. Use during incident response.')
ON CONFLICT (code) DO NOTHING;
