# CDP Platform

Modular multi-tenant data platform with login/registration, RBAC, admin
console, and pluggable modules. First module: **Data Quality** (DQ).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                            Next.js (App Router, OOP)                │
│   • Module Registry (config-driven left nav)                        │
│   • BaseApiClient → AuthApi, ModulesApi, AccessApi, AdminApi, DqApi │
│   • RouteGuard + AuthProvider                                       │
└──────────────────┬──────────────────────────────────────────────────┘
                   │  /api/* (proxied via nginx in prod)
┌──────────────────┴──────────────────────────────────────────────────┐
│                         FastAPI (OOP, modular)                      │
│   • core/    — settings, db, JWT, errors catalog, BaseRepository    │
│   • auth/    — register, login, RBAC dependency                     │
│   • admin/   — modules, access requests, users, audit               │
│   • modules/ — DQ (and any new module dropped in here)              │
└──────────────────┬──────────────────────────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────────────────────────┐
│                          PostgreSQL                                 │
│   schema "core" : users, modules, module_features, module_roles,    │
│                   user_module_access, access_requests, audit_log,   │
│                   user_activity                                     │
│   schema "dq"   : dimensions, business_rules, technical_rules       │
└─────────────────────────────────────────────────────────────────────┘
```

## Repo layout

```
cdp-platform/
├── db/
│   ├── 01_schema.sql          # PostgreSQL schema (core + dq)
│   └── 02_seed.sql            # default admin, modules, roles
├── backend/                   # FastAPI
│   ├── app/
│   │   ├── core/              # settings, db, security, errors, base
│   │   ├── common/            # shared ORM, audit service
│   │   ├── auth/              # /api/auth, RBAC dependency
│   │   ├── admin/             # /api/modules /api/access /api/admin
│   │   └── modules/dq/        # DQ module (template for new ones)
│   ├── requirements.txt
│   └── .env.example
├── frontend/                  # Next.js
│   ├── src/
│   │   ├── app/               # routes (login, register, dashboard, admin, dq)
│   │   ├── components/        # AppShell, RouteGuard
│   │   ├── hooks/useAuth.tsx
│   │   ├── lib/               # apiClient, errors, moduleRegistry, ...
│   │   └── modules/dq/api.ts  # DQ module client
│   ├── package.json
│   └── tsconfig.json
└── docs/
    └── ADD_NEW_MODULE.md
```

## Quick start (local)

### 1. Database

```bash
psql "$DATABASE_URL" -f db/01_schema.sql
psql "$DATABASE_URL" -f db/02_seed.sql
```

This creates:
- User: `admin@cdp.local` / **password: `AdminPass!2026`** (change after first login)
- 3 modules: DQ, LINEAGE, CATALOG
- 3 roles per module: ADMIN, EDITOR, VIEWER
- 6 features for DQ

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit DATABASE_URL + JWT_SECRET_KEY
uvicorn app.main:app --reload --port 8000
```

API docs at <http://localhost:8000/api/docs>.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>.

## Custom error codes

All errors use the format `CDP-<DOMAIN>-<NUMBER>`. The catalog lives at
`backend/app/core/errors.py`. Operations teams can grep this file to
understand any code seen in logs or returned by the API.

| Domain | Prefix |
|--------|--------|
| Auth   | `CDP-AUT-*` |
| User   | `CDP-USR-*` |
| Module | `CDP-MOD-*` |
| Access | `CDP-ACC-*` |
| DQ Dim | `CDP-DQD-*` |
| DQ Rule| `CDP-DQR-*` |
| System | `CDP-SYS-*` |

API responses on error look like:

```json
{
  "error": {
    "code":    "CDP-AUT-0001",
    "message": "Invalid email or password",
    "detail":  null,
    "context": {}
  }
}
```

The frontend `ApiError` class maps codes to user-friendly messages.

## Adding a new module

See [docs/ADD_NEW_MODULE.md](docs/ADD_NEW_MODULE.md).

## RBAC model

```
User ─┬─ has access to → Module ── has → Roles (ADMIN/EDITOR/VIEWER)
      │                              └─→ Features (DASHBOARD, etc.)
      │
      └─ when admin grants access:
              role decides which permissions ("read","write","delete","manage")
              feature-level overrides supported via core.user_feature_access
```

`require_module_permission("DQ", permission="write")` is the FastAPI
dependency that gates routes.

## Audit

Every state change calls `AuditService.record(...)` which writes to
`core.audit_log` with before/after JSON. User logins / module views log
to `core.user_activity` for the admin "user journey" dashboard.
