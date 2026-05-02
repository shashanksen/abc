-- ═══════════════════════════════════════════════════════════════════════════════
-- Seed data — modules, roles, default admin
-- Run after 01_schema.sql
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── Modules ──────────────────────────────────────────────────────────────────
INSERT INTO core.modules (code, name, description, icon, sort_order) VALUES
    ('DQ',      'Data Quality',     'Data quality dimensions, business rules and technical rules', 'shield-check', 10),
    ('LINEAGE', 'Data Lineage',     'Track data flow across systems',                              'git-branch',   20),
    ('CATALOG', 'Data Catalog',     'Searchable inventory of data assets',                         'book',         30)
ON CONFLICT (code) DO NOTHING;

-- ─── Module roles (admin / editor / viewer) per module ────────────────────────
INSERT INTO core.module_roles (module_id, code, name, description, permissions)
SELECT id, 'ADMIN',  'Module Admin',  'Full control of this module',          '["read","write","delete","manage"]'::jsonb FROM core.modules
UNION ALL
SELECT id, 'EDITOR', 'Module Editor', 'Can create and update content',         '["read","write"]'::jsonb               FROM core.modules
UNION ALL
SELECT id, 'VIEWER', 'Module Viewer', 'Read-only access',                      '["read"]'::jsonb                       FROM core.modules
ON CONFLICT (module_id, code) DO NOTHING;

-- ─── DQ module features (tabs from your screenshot) ───────────────────────────
INSERT INTO core.module_features (module_id, code, name, description, sort_order)
SELECT m.id, 'DASHBOARD',      'My Dashboard',     'User landing dashboard',         10 FROM core.modules m WHERE m.code = 'DQ'
UNION ALL SELECT m.id, 'DIMENSIONS',     'DQ Dimensions',    'Manage DQ dimensions',           20 FROM core.modules m WHERE m.code = 'DQ'
UNION ALL SELECT m.id, 'EDE_MAPPINGS',   'EDE Mappings',     'Enterprise Data Element maps',   30 FROM core.modules m WHERE m.code = 'DQ'
UNION ALL SELECT m.id, 'BUSINESS_RULES', 'Business Rules',   'Business-level DQ rules',        40 FROM core.modules m WHERE m.code = 'DQ'
UNION ALL SELECT m.id, 'TECHNICAL_RULES','Technical Rules',  'Technical-level DQ rules',       50 FROM core.modules m WHERE m.code = 'DQ'
UNION ALL SELECT m.id, 'DQ_DASHBOARD',   'DQ Dashboard',     'Quality scores and trends',      60 FROM core.modules m WHERE m.code = 'DQ'
ON CONFLICT (module_id, code) DO NOTHING;

-- ─── Default admin user ──────────────────────────────────────────────────────
-- Password: AdminPass!2026 (bcrypt hash) — CHANGE THIS IN PRODUCTION
INSERT INTO core.users (email, full_name, password_hash, is_admin) VALUES
  ('admin@cdp.example', 'CDP Admin',
   '$2b$12$LQ3xXKKVgRtMKPxN8FqHa.6E/xRYn9aTjC4mOe9fPQXpNNRyo8oXG',
   TRUE)
ON CONFLICT (email) DO NOTHING;
