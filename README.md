# CDP Platform — v0.2.0

Modular multi-tenant data platform with login/registration, RBAC, admin
console, audit log, and pluggable modules. **v0.2.0** adds an LLM agent
layer (A2A protocol → LangGraph orchestrator on Databricks Apps), security
hardening (AWS Secrets Manager, OAuth M2M, layered prompt-injection
defenses), and admin operations UI.

First module: **Data Quality** (DQ).

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Next.js (App Router, OOP)                     │
│   • Module Registry (config-driven left nav)                        │
│   • BaseApiClient → AuthApi, ModulesApi, AccessApi, AdminApi, DqApi │
│   • RouteGuard + AuthProvider                                       │
│   • streaming SSE consumer for agent endpoints (agentStream.ts)     │
└──────────────────┬──────────────────────────────────────────────────┘
                   │  /api/* (proxied via nginx; /api/agent/* SSE-tuned)
┌──────────────────┴──────────────────────────────────────────────────┐
│                       FastAPI (OOP, modular)                        │
│   • core/     settings, db, JWT (split keys), errors, secrets       │
│   • auth/     register, login, RBAC dependency                      │
│   • admin/    modules, access, users, audit + admin_ops             │
│   • modules/  DQ + agent (A2A client, OBO tokens, prompt safety)    │
└──────────────────┬──────────────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │ A2A JSON-RPC (streaming SSE)
        ▼                     ▼
┌──────────────────┐   ┌──────────────────────────────────────────────┐
│   PostgreSQL     │   │  Databricks Apps                             │
│   core / dq /    │   │  • LangGraph orchestrator                    │
│   agent schemas  │◄──│  • Postgres checkpointer (refinement turns)  │
│                  │   │  • FM API: Llama 3.1 70B (default)           │
└──────────────────┘   └──────────────────────────────────────────────┘
```

The A2A boundary is the only stable contract; everything below it (LangGraph
graph, FM model, checkpointer location, tool implementations) is replaceable
without touching the FastAPI or UI side.

## Documentation

- **[docs/DEPLOY.md](docs/DEPLOY.md)** — step-by-step deploy guide for local
  dev (with mock agent, no Databricks needed) and production (AWS Secrets
  Manager + Databricks SP). Includes verification commands at every step
  and a ranked list of common gotchas.
- **[docs/SECURITY.md](docs/SECURITY.md)** — threat model, four-layer
  prompt-injection defense, JWT and SP rotation runbooks, monitoring
  alerts, incident response.
- **[docs/CHANGES.md](docs/CHANGES.md)** — exhaustive list of every file
  changed or added in v0.2.0, with one-line descriptions. Useful for code
  review.
- **[docs/ADD_NEW_MODULE.md](docs/ADD_NEW_MODULE.md)** — how to add a new
  module (e.g., MDM, Lineage) following the same pattern as DQ.

## Quick start (local development, mock agent)

```bash
# Database
psql "$DATABASE_URL" -f db/01_schema.sql
psql "$DATABASE_URL" -f db/02_seed.sql
psql "$DATABASE_URL" -f db/03_agent.sql
psql "$DATABASE_URL" -f db/04_feature_flags.sql

# Backend
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then edit
uvicorn app.main:app --reload --port 8000

# Mock agent (separate terminal)
cd databricks_agent && python3 -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn pydantic httpx
AGENT_SHARED_SECRET=dev-secret-not-for-prod uvicorn mock_agent:app --port 8001 --reload

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Open <http://localhost:3000>. Login: `admin@cdp.local` / `AdminPass!2026`.

Full instructions, including production deploy, are in **[docs/DEPLOY.md](docs/DEPLOY.md)**.

## Repository layout

```
backend/
  app/
    core/         # settings, JWT, errors, secrets (env / AWS), database
    auth/         # register, login, RBAC dependency
    common/       # ORM models, audit service
    admin/        # admin.py (existing) + admin_ops.py (agent ops, journey, kill-switch)
    modules/
      dq/         # data quality module
      agent/      # A2A client, OBO tokens, prompt safety, output validation, kill-switch
    main.py
  requirements.txt
  .env.example

databricks_agent/  # NEW: deployed to Databricks Apps
  agent.py         # LangGraph orchestrator (one node in Phase 1)
  state.py
  tools.py         # callback tool scaffolding (Phase 2)
  a2a_server.py    # A2A streaming server, AUTH_MODE selects shared-secret / OAuth
  auth.py          # shared-secret bearer (dev / mock)
  oauth_verify.py  # production OAuth JWKs verifier
  mock_agent.py    # local mock — same SSE wire format, no Databricks needed
  app.yaml         # Databricks Apps manifest
  requirements.txt
  README.md

frontend/
  src/
    app/
      admin/                          # admin console (with new agent ops + activity feed)
      admin/users/[id]/journey/       # NEW: per-user timeline
      dq/business-rules/              # wired to real backend; AI generate flow
      ...
    components/dq/AIGenerateButton.tsx  # NEW
    lib/agentStream.ts                  # NEW: SSE consumer
    modules/dq/agentApi.ts              # NEW: typed agent API wrapper

db/
  01_schema.sql        # core + dq schemas (existing)
  02_seed.sql          # seed data (existing)
  03_agent.sql         # NEW: agent schema + task_log + daily_usage view
  04_feature_flags.sql # NEW: kill-switch flag

config/
  nginx-cdp.conf       # UPDATED: /api/agent/ block with proxy_buffering off
  ecosystem.config.js  # PM2 (existing)

docs/
  DEPLOY.md            # NEW
  SECURITY.md          # NEW
  CHANGES.md           # NEW (this delta)
  ADD_NEW_MODULE.md    # existing, unchanged
```

## Default credentials (seed)

Email: `admin@cdp.local`
Password: `AdminPass!2026`

Change immediately on first deploy.

## Operating runbook

Live ops procedures (kill-switch, key rotation, incident response) are in
**[docs/SECURITY.md](docs/SECURITY.md)**. The TL;DR:

- **Kill-switch:** admin → `/admin` → "Disable agent" button. Takes effect
  on the next request, no restart.
- **JWT rotation:** add new key alongside old in AWS Secrets Manager,
  wait 8 hours (longest access-token lifetime), remove old.
- **Databricks SP rotation:** dual-secret pattern in AWS Secrets Manager;
  zero-downtime.

## License

Internal — not for distribution.
