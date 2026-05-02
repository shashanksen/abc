# Changes from the original repo

This is the consolidated v2 of the CDP platform with the LLM agent, security
hardening, and admin ops integrated. Below is every file modified or added,
with a one-line description.

## Backend — modified

| File | Change |
|---|---|
| `backend/app/main.py` | Mounts `agent_router`, `admin_ops_router`. Adds SlowAPI rate-limit handler. Drops the `database_url` log line (was leaking secrets). |
| `backend/app/core/errors.py` | Adds `AGENT` and `SECURITY` domains. Adds `CDP-AGT-0070..0080` (11 codes), `CDP-SEC-0100..0102` (3 codes), `CDP-AUT-0007..0008` (2 codes). |
| `backend/app/core/config.py` | Loads sensitive values via `secrets.py` (env or AWS). Splits JWT keys into `jwt_user_session_key` and `jwt_agent_callback_key`. Adds Databricks OAuth settings. |
| `backend/app/core/security.py` | Splits sign/verify by token type. Soft migration on user_session via `user_session_legacy`. Adds `create_agent_callback_token` for on-behalf-of tokens. |
| `backend/app/auth/rbac.py` | `require_module_permission` now accepts both `access` and `agent_callback` token types. For agent_callback, checks the `scope` claim against expected `MODULE:permission`. |
| `backend/app/common/models.py` | Adds `FeatureFlag` ORM model (kill-switch). |
| `backend/requirements.txt` | Adds `httpx`, `slowapi`, `boto3`. |
| `backend/.env.example` | Replaces flat env vars with JSON-encoded secret env vars matching the AWS Secrets Manager shape. **No more real-looking RDS credentials.** |

## Backend — new files

| File | Purpose |
|---|---|
| `backend/app/core/secrets.py` | Pluggable secrets provider (env / aws-secrets-manager). |
| `backend/app/core/secrets_aws.py` | AWS Secrets Manager implementation with TTL cache. |
| `backend/app/admin/admin_ops.py` | Admin endpoints for activity feed, user journey, agent task_log, daily usage, kill-switch toggle. |
| `backend/app/modules/agent/__init__.py` | Module init — re-exports router and limiter. |
| `backend/app/modules/agent/schemas.py` | `GenerateBusinessRuleRequest` Pydantic model. |
| `backend/app/modules/agent/budget.py` | Daily char-cap pre-flight check (CDP-AGT-0077). |
| `backend/app/modules/agent/kill_switch.py` | Reads `core.feature_flags.agent.kill_switch` per request (CDP-AGT-0080). |
| `backend/app/modules/agent/prompt_safety.py` | Prompt-injection input boundary, layer 1 (CDP-SEC-0100). |
| `backend/app/modules/agent/output_validation.py` | Output allowlist, layer 3 (CDP-SEC-0101 / 0102). |
| `backend/app/modules/agent/databricks_oauth.py` | OAuth M2M token cache + minting. |
| `backend/app/modules/agent/client.py` | A2A streaming client. |
| `backend/app/modules/agent/service.py` | `AgentService(BaseService)` — composes pre-flight checks, A2A call, output validation, audit + task_log persistence. |
| `backend/app/modules/agent/router.py` | `/api/agent/dq/business-rule/stream` with RBAC + SlowAPI rate limit. |

## Frontend — modified

| File | Change |
|---|---|
| `frontend/src/lib/coreApi.ts` | Adds 6 admin ops types, 7 admin ops methods on `AdminApi` class. Existing methods unchanged. |
| `frontend/src/app/admin/page.tsx` | Adds `<AgentOpsSection />` and `<ActivityFeedSection />` after the existing Users table. Existing flow unchanged. |
| `frontend/src/app/dq/business-rules/page.tsx` | Wired to real `/api/dq/business-rules` (was using mock data). New "✨ Generate with AI" flow via the modal. |

## Frontend — new files

| File | Purpose |
|---|---|
| `frontend/src/lib/agentStream.ts` | fetch + ReadableStream SSE helper for streaming agent endpoints. |
| `frontend/src/modules/dq/agentApi.ts` | `DqAgentApi` class — typed wrapper over `postStream`. |
| `frontend/src/components/dq/AIGenerateButton.tsx` | Reusable button with phase indicator + abort-on-stop. |
| `frontend/src/app/dq/business-rules/CreateBusinessRuleModal.tsx` | Form for creating a business rule with AI generation. |
| `frontend/src/app/admin/AdminOpsSections.tsx` | Two new admin sections: agent ops (kill-switch, recent runs, top users) + activity feed. |
| `frontend/src/app/admin/users/[id]/journey/page.tsx` | Per-user timeline page reachable from the activity feed. |

## Databricks-side — new folder

| File | Purpose |
|---|---|
| `databricks_agent/agent.py` | LangGraph graph with one node (`draft_rule_node`). System prompt hardened against prompt injection (layer 2). |
| `databricks_agent/state.py` | `GraphState` TypedDict. |
| `databricks_agent/tools.py` | Authenticated callback tool scaffolding (no tools registered in Phase 1). |
| `databricks_agent/a2a_server.py` | A2A server with streaming SSE event mapping from `astream_events`. AUTH_MODE selects shared-secret vs OAuth. |
| `databricks_agent/auth.py` | Shared-secret bearer verifier (used by mock + dev). |
| `databricks_agent/oauth_verify.py` | Production OAuth verifier (JWKs-based). |
| `databricks_agent/mock_agent.py` | Local mock — same SSE wire format, no Databricks needed. |
| `databricks_agent/app.yaml` | Databricks Apps manifest. |
| `databricks_agent/requirements.txt` | LangGraph + Postgres checkpointer + databricks-langchain. |
| `databricks_agent/README.md` | Local dev + deploy instructions. |

## DB — new migrations

| File | Purpose |
|---|---|
| `db/03_agent.sql` | `agent` schema, `agent.task_log` table, `agent.daily_usage` view. |
| `db/04_feature_flags.sql` | `core.feature_flags` table. Seeds `agent.kill_switch=false`. |

## Config — modified

| File | Change |
|---|---|
| `config/nginx-cdp.conf` | New `/api/agent/` block carved out before `/api/`, with `proxy_buffering off`, `proxy_read_timeout 300s`, `X-Accel-Buffering: no`. Required for SSE. |

## Docs — new

| File | Purpose |
|---|---|
| `docs/DEPLOY.md` | Step-by-step deployment guide. |
| `docs/SECURITY.md` | Threat model, rotation runbook, incident response. |
| `docs/CHANGES.md` | This file. |

## Files NOT changed (preserved verbatim)

These files are exactly as you uploaded them:

- All of `backend/app/admin/admin.py`, `auth/auth.py`, `common/audit.py`, `core/base.py`, `core/database.py`, `modules/dq/*`
- All of `frontend/src/app/access/`, `dashboard/`, `login/`, `register/`, `settings/`, `dq/dimensions/`, `dq/dq-dashboard/`, `dq/ede-mappings/`, `dq/layout.tsx`, `dq/page.tsx`, `dq/technical-rules/`, `globals.css`, `layout.tsx`, `page.tsx`
- All of `frontend/src/components/AppShell.tsx`, `PublicTopbar.tsx`, `RouteGuard.tsx`, `ThemeToggle.tsx`, `dq/DqMetricCard.tsx`, `dq/WorkflowActionGroup.tsx`, `ui/*`
- All of `frontend/src/hooks/*`, `frontend/src/lib/apiClient.ts`, `authApi.ts`, `demoData.ts`, `errors.ts`, `moduleRegistry.ts`, `tokenStorage.ts`
- All of `frontend/src/modules/dq/api.ts`, `mockData.ts`, `frontend/src/types/styles.d.ts`
- All of `frontend/package.json`, `package-lock.json`, `next-env.d.ts`, `next.config.js`, `tsconfig.json`
- `db/01_schema.sql`, `db/02_seed.sql`
- `config/ecosystem.config.js`
- `docs/ADD_NEW_MODULE.md`
