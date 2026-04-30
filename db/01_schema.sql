-- ═══════════════════════════════════════════════════════════════════════════════
-- CDP Platform — Core Schema
-- PostgreSQL 16
--
-- Naming conventions:
--   - tables: snake_case plural (users, modules)
--   - PKs: id (UUID for entities, BIGSERIAL for high-volume e.g. audit_log)
--   - FKs: <table_singular>_id
--   - timestamps: created_at, updated_at, deleted_at (soft delete)
--   - all timestamps in UTC (TIMESTAMPTZ)
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Schema: core ──────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS core;

-- ─── Users ────────────────────────────────────────────────────────────────────
CREATE TABLE core.users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    full_name       VARCHAR(255) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,    -- bcrypt
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_admin        BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX idx_users_email          ON core.users (email)         WHERE deleted_at IS NULL;
CREATE INDEX idx_users_active         ON core.users (is_active)     WHERE deleted_at IS NULL;

-- ─── Modules (registry) ───────────────────────────────────────────────────────
-- A "module" is a top-level product/feature (DQ, Lineage, Catalog, etc.)
-- Defined via config (seed) — adding a new module = INSERT row, no schema change.
CREATE TABLE core.modules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(50) NOT NULL UNIQUE,    -- e.g. "DQ", "LINEAGE"
    name            VARCHAR(100) NOT NULL,           -- e.g. "Data Quality"
    description     TEXT,
    icon            VARCHAR(50),                     -- icon name for UI
    is_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── Module Features (sub-tabs / functionality within a module) ───────────────
-- e.g. DQ module has features: Dimensions, Business Rules, Technical Rules
CREATE TABLE core.module_features (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    module_id       UUID NOT NULL REFERENCES core.modules(id) ON DELETE CASCADE,
    code            VARCHAR(100) NOT NULL,    -- e.g. "DIMENSIONS", "BUSINESS_RULES"
    name            VARCHAR(150) NOT NULL,    -- "DQ Dimensions"
    description     TEXT,
    is_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (module_id, code)
);

-- ─── Roles per module (admin / editor / viewer) ───────────────────────────────
CREATE TABLE core.module_roles (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    module_id       UUID NOT NULL REFERENCES core.modules(id) ON DELETE CASCADE,
    code            VARCHAR(50) NOT NULL,    -- "ADMIN", "EDITOR", "VIEWER"
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    permissions     JSONB NOT NULL DEFAULT '[]'::jsonb,  -- e.g. ["read","write","delete"]
    UNIQUE (module_id, code)
);

-- ─── User → Module access (granted by admin) ──────────────────────────────────
CREATE TABLE core.user_module_access (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
    module_id       UUID NOT NULL REFERENCES core.modules(id) ON DELETE CASCADE,
    role_id         UUID NOT NULL REFERENCES core.module_roles(id),
    granted_by      UUID REFERENCES core.users(id),
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at      TIMESTAMPTZ,
    UNIQUE (user_id, module_id)
);
CREATE INDEX idx_uma_user_active ON core.user_module_access (user_id) WHERE revoked_at IS NULL;

-- ─── Per-feature access (optional override; if absent, role permissions apply) ─
CREATE TABLE core.user_feature_access (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
    module_feature_id UUID NOT NULL REFERENCES core.module_features(id) ON DELETE CASCADE,
    can_view        BOOLEAN NOT NULL DEFAULT TRUE,
    can_edit        BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (user_id, module_feature_id)
);

-- ─── Access requests (user requests, admin approves/denies) ───────────────────
CREATE TYPE core.request_status AS ENUM ('PENDING', 'APPROVED', 'DENIED', 'CANCELLED');

CREATE TABLE core.access_requests (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
    module_id           UUID NOT NULL REFERENCES core.modules(id) ON DELETE CASCADE,
    requested_role_id   UUID NOT NULL REFERENCES core.module_roles(id),
    justification       TEXT,
    status              core.request_status NOT NULL DEFAULT 'PENDING',
    decided_by          UUID REFERENCES core.users(id),
    decided_at          TIMESTAMPTZ,
    decision_note       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_access_requests_status ON core.access_requests (status, created_at DESC);
CREATE INDEX idx_access_requests_user   ON core.access_requests (user_id, status);

-- ─── Audit log (every state change tracked) ──────────────────────────────────
CREATE TABLE core.audit_log (
    id              BIGSERIAL PRIMARY KEY,
    actor_id        UUID REFERENCES core.users(id),    -- who did it (NULL = system)
    actor_email     VARCHAR(255),                       -- denormalised for survival after user delete
    action          VARCHAR(100) NOT NULL,              -- "USER_LOGIN", "ACCESS_APPROVED", etc.
    entity_type     VARCHAR(50) NOT NULL,               -- "USER", "ACCESS_REQUEST", "DQ_DIMENSION"
    entity_id       VARCHAR(100),                       -- UUID or composite key
    before_state    JSONB,
    after_state     JSONB,
    metadata        JSONB DEFAULT '{}'::jsonb,          -- IP, user-agent, request_id, etc.
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_actor    ON core.audit_log (actor_id, created_at DESC);
CREATE INDEX idx_audit_entity   ON core.audit_log (entity_type, entity_id, created_at DESC);
CREATE INDEX idx_audit_action   ON core.audit_log (action, created_at DESC);

-- ─── User session activity (for "user journey" admin dashboard) ──────────────
CREATE TABLE core.user_activity (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES core.users(id) ON DELETE CASCADE,
    activity_type   VARCHAR(50) NOT NULL,    -- "LOGIN", "MODULE_VIEW", "FEATURE_USE"
    module_code     VARCHAR(50),
    feature_code    VARCHAR(100),
    metadata        JSONB DEFAULT '{}'::jsonb,
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_activity_user_time ON core.user_activity (user_id, created_at DESC);
CREATE INDEX idx_activity_module    ON core.user_activity (module_code, created_at DESC);

-- ═══════════════════════════════════════════════════════════════════════════════
-- Schema: dq (Data Quality module)
-- Each module gets its own schema for clean isolation.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE SCHEMA IF NOT EXISTS dq;

-- ─── DQ Dimensions (Completeness, Accuracy, Timeliness, etc.) ────────────────
CREATE TABLE dq.dimensions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(100) NOT NULL,
    definition      TEXT NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(20) NOT NULL DEFAULT 'DRAFT',  -- DRAFT|ACTIVE|RETIRED
    status_changed_by UUID REFERENCES core.users(id),
    status_changed_at TIMESTAMPTZ,
    created_by      UUID REFERENCES core.users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- ─── DQ Business Rules ────────────────────────────────────────────────────────
CREATE TABLE dq.business_rules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(100) NOT NULL UNIQUE,
    dimension_id    UUID REFERENCES dq.dimensions(id),
    ede_mapping     VARCHAR(255),
    rule_text       TEXT NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_by      UUID REFERENCES core.users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- ─── DQ Technical Rules ───────────────────────────────────────────────────────
CREATE TABLE dq.technical_rules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(100) NOT NULL UNIQUE,
    dimension_id    UUID REFERENCES dq.dimensions(id),
    ede             VARCHAR(255),
    cde             VARCHAR(255),
    attribute       VARCHAR(255),
    rule_expr       TEXT NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_by      UUID REFERENCES core.users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- ─── Trigger: keep updated_at fresh ──────────────────────────────────────────
CREATE OR REPLACE FUNCTION core.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ DECLARE r RECORD; BEGIN
    FOR r IN
        SELECT n.nspname, c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('core','dq')
          AND c.relkind = 'r'
          AND EXISTS (
              SELECT 1 FROM pg_attribute a
              WHERE a.attrelid = c.oid AND a.attname = 'updated_at'
          )
    LOOP
        EXECUTE format(
          'DROP TRIGGER IF EXISTS trg_%I_updated_at ON %I.%I;
           CREATE TRIGGER trg_%I_updated_at BEFORE UPDATE ON %I.%I
             FOR EACH ROW EXECUTE FUNCTION core.set_updated_at();',
          r.relname, r.nspname, r.relname,
          r.relname, r.nspname, r.relname
        );
    END LOOP;
END $$;
