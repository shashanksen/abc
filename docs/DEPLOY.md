# Deployment guide

End-to-end deploy of CDP Platform v2 (with the LLM agent + security
hardening + admin ops). The steps are ordered so each one's verification
catches the most likely failure before you depend on it. Don't skip the
verification commands — they exist because each is a step that, in my
experience, breaks silently in roughly 1 in 3 first deploys.

## Topology recap

```
Browser
   │ HTTPS
   ▼
nginx (EC2)
   │
   ├──→ port 3000  Next.js (UI)
   └──→ port 8000  FastAPI (API)
                   │
                   ├──→ AWS Secrets Manager   (secrets)
                   ├──→ RDS Postgres          (data + langgraph checkpoint)
                   └──→ Databricks App        (LLM agent)
```

For local development everything runs on your laptop except the LLM call —
either point at a real Databricks endpoint (with a PAT) or use the mock
agent (no Databricks needed).

---

## Local development (mock agent — no Databricks)

This is the path I recommend for first-time setup. You can deploy to real
Databricks later once everything works locally.

### 1. Database

```bash
psql "$DATABASE_URL" -f db/01_schema.sql
psql "$DATABASE_URL" -f db/02_seed.sql
psql "$DATABASE_URL" -f db/03_agent.sql
psql "$DATABASE_URL" -f db/04_feature_flags.sql
```

**Verify:** all four migrations applied.

```bash
psql "$DATABASE_URL" -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('core','dq','agent');"
psql "$DATABASE_URL" -c "SELECT code, enabled FROM core.feature_flags;"
```

Expected: 3 schemas, 1 feature flag (`agent.kill_switch=false`).

### 2. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`. The example file uses dev-friendly JSON-encoded env vars; you
need to set:
- `CDP_DB_MAIN` — your Postgres connection string
- `CDP_JWT_KEYS` — generate two random strings:
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
- Leave the Databricks vars at their dummy values for now.

```bash
uvicorn app.main:app --reload --port 8000
```

**Verify:**
```bash
curl http://localhost:8000/api/health
# Expected: {"status":"ok"}
```

If you get a `RuntimeError: SECRETS_BACKEND` failure at startup, double-check
`SECRETS_BACKEND=env` is set in your `.env` (it is by default).

### 3. Mock agent

In a separate terminal:

```bash
cd databricks_agent
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn pydantic httpx
AGENT_SHARED_SECRET=dev-secret-not-for-prod \
  uvicorn mock_agent:app --port 8001 --reload
```

**Verify:**
```bash
curl http://localhost:8001/.well-known/agent.json | head -20
```

Expected: JSON agent card.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>.

### 5. End-to-end smoke test

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@cdp.local","password":"AdminPass!2026"}' \
  | jq -r .access_token)

# Hit the agent through the mock
curl -N -X POST http://localhost:8000/api/agent/dq/business-rule/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description":"Customer email must not be null for active accounts."}'
```

You should see streaming SSE events (`thread`, `step`, many `delta`s, then
`completed`). If you instead see HTML or a 502, FastAPI couldn't reach the
mock — check `AGENT_BEARER_OVERRIDE` is set in `.env` and the mock is
actually running on 8001.

### 6. UI smoke test

In the browser:
1. Log in as admin (`admin@cdp.local` / `AdminPass!2026`)
2. Open `/dq/business-rules`
3. Click "New business rule"
4. Type a short description in the seed field
5. Click "✨ Generate with AI"

You should see "Drafting rule…" appear under the button and text streaming
into the rule_text textarea.

7. Open `/admin`. The new "Agent operations" and "Recent activity" sections
should render with at least one entry from the test you just ran.

---

## Staging / production deploy

This is the same code; the difference is what's external (Databricks, AWS
Secrets Manager) and how secrets are managed.

### 1. AWS Secrets Manager — create the four secrets

```bash
aws secretsmanager create-secret --name cdp/db/main \
  --secret-string '{"url":"postgresql+psycopg2://USER:PASS@HOST:5432/cdp"}'

aws secretsmanager create-secret --name cdp/jwt-keys \
  --secret-string "{\"user_session\":\"$(python3 -c 'import secrets;print(secrets.token_urlsafe(64))')\",\"agent_callback\":\"$(python3 -c 'import secrets;print(secrets.token_urlsafe(64))')\"}"

aws secretsmanager create-secret --name cdp/databricks/oauth \
  --secret-string '{"client_id":"<SP_CLIENT_ID>","client_secret":"<SP_CLIENT_SECRET>","token_endpoint":"https://accounts.cloud.databricks.com/oidc/accounts/<ACCOUNT_ID>/v1/token"}'

aws secretsmanager create-secret --name cdp/databricks/agent-app \
  --secret-string '{"base_url":"https://<your-app>.databricksapps.com","scope":"all-apis"}'
```

**Verify:**
```bash
aws secretsmanager list-secrets --query 'SecretList[?starts_with(Name, `cdp/`)].Name'
```

Expected: 4 names.

### 2. EC2 IAM policy — least privilege

Attach to the EC2 instance profile:

```json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": [
    "arn:aws:secretsmanager:eu-west-2:<ACCOUNT>:secret:cdp/db/main-*",
    "arn:aws:secretsmanager:eu-west-2:<ACCOUNT>:secret:cdp/jwt-keys-*",
    "arn:aws:secretsmanager:eu-west-2:<ACCOUNT>:secret:cdp/databricks/oauth-*",
    "arn:aws:secretsmanager:eu-west-2:<ACCOUNT>:secret:cdp/databricks/agent-app-*"
  ]
}
```

**Verify** from the EC2 box:
```bash
aws secretsmanager get-secret-value --secret-id cdp/jwt-keys --query SecretString --output text | jq .
```

If you get AccessDenied, the IAM role isn't attached or the policy didn't
land. If you get a JSON object back, you're good.

### 3. Databricks — create the service principal

In the Databricks **account console** (not workspace):

1. Identity → Service Principals → Create. Name it `cdp-fastapi-agent-caller`.
2. OAuth → Generate client secret. Copy `client_id` + `client_secret` immediately
   (the secret is shown once). Update `cdp/databricks/oauth` if not already set.
3. Workspace permissions → assign the SP to your workspace.
4. App permissions → grant the SP `CAN_INVOKE` on the agent App you'll deploy
   in step 5.

**Verify**: from EC2 (after step 4 below), curl the OAuth token endpoint:

```bash
ENDPOINT=$(aws secretsmanager get-secret-value --secret-id cdp/databricks/oauth \
  --query SecretString --output text | jq -r .token_endpoint)
CID=$(aws secretsmanager get-secret-value --secret-id cdp/databricks/oauth \
  --query SecretString --output text | jq -r .client_id)
CSEC=$(aws secretsmanager get-secret-value --secret-id cdp/databricks/oauth \
  --query SecretString --output text | jq -r .client_secret)

curl -X POST "$ENDPOINT" \
  -u "$CID:$CSEC" \
  -d 'grant_type=client_credentials&scope=all-apis'
```

Expected: a JSON response with `access_token`, `expires_in`. If you get
`invalid_client` your client_secret is wrong. If you get DNS errors, the
endpoint URL is wrong (check the account ID in the URL).

### 4. Database — apply migrations

Same as local, against your prod Postgres:

```bash
psql "$DATABASE_URL" -f db/01_schema.sql
psql "$DATABASE_URL" -f db/02_seed.sql
psql "$DATABASE_URL" -f db/03_agent.sql
psql "$DATABASE_URL" -f db/04_feature_flags.sql
```

If you're upgrading an existing prod DB that has 01 and 02 applied, just
run 03 and 04 — they're additive.

### 5. Databricks App — deploy the agent

```bash
cd databricks_agent
databricks apps create cdp-dq-agent  # if not already created
databricks bundle deploy             # or push via Git folder
```

Set environment variables on the App (Compute → Apps → cdp-dq-agent → Settings → Environment):

| Variable | Value |
|---|---|
| `AUTH_MODE` | `oauth` |
| `OAUTH_ISSUER_URL` | `https://accounts.cloud.databricks.com/oidc/accounts/<ACCOUNT>` |
| `OAUTH_JWKS_URL` | `https://accounts.cloud.databricks.com/oidc/accounts/<ACCOUNT>/jwks` (verify exact path against current Databricks docs) |
| `OAUTH_EXPECTED_SP_ID` | the SP id from step 3 |
| `OAUTH_AUDIENCE_CHECK` | `false` (start lenient; flip to `true` after observing actual `aud` claim) |
| `FM_ENDPOINT_NAME` | `databricks-meta-llama-3-1-70b-instruct` (or your chosen model) |
| `LANGGRAPH_CHECKPOINT_DB_URI` | `postgresql://USER:PASS@<rds-host>:5432/cdp` |
| `AGENT_PUBLIC_URL` | (Databricks shows this) |
| `AGENT_SHARED_SECRET` | random; only used as the OAUTH_VERIFY_DISABLED fallback. Keep set even when AUTH_MODE=oauth. |

**Verify network reachability App → RDS** (most common failure point):

The App will fail to start if it can't reach RDS on 5432. Either:
- RDS is publicly accessible + security group allowlists Databricks egress IPs, or
- VPC peering / PrivateLink between Databricks and your VPC.

Tail logs after deploy:
```bash
databricks apps logs cdp-dq-agent
```

Look for `LangGraph compiled with Postgres checkpointer`. If you see
`psycopg.OperationalError`, the App can't reach RDS — fix networking.

### 6. EC2 — deploy backend + frontend

```bash
# On EC2
cd /opt/cdp-platform-v2
git pull   # or whatever your deploy mechanism is
cd backend && pip install -r requirements.txt
cd ../frontend && npm install && npm run build
```

Set in EC2 environment:
```
SECRETS_BACKEND=aws-secrets-manager
AWS_REGION=eu-west-2
APP_ENV=production
CORS_ORIGINS=https://your-domain.com
```

(NOT in `.env` anymore in prod — set via systemd, EC2 user data, or your
process manager.)

Restart services:
```bash
sudo systemctl restart cdp-backend cdp-frontend
sudo systemctl reload nginx
```

### 7. Production smoke test

Same as local step 5/6, but against your prod URL. The streaming endpoint
test is the most important — if SSE is buffered by nginx, you'll see one
big response at the end instead of streaming events.

If streaming doesn't work in prod but worked locally:
- Check `nginx -T | grep -A 20 'location /api/agent/'` — `proxy_buffering off`
  must be there.
- Check `journalctl -u cdp-backend --since '5 min ago'` for OAuth errors.

---

## Things to verify before going live with users

Walk through `docs/SECURITY.md` § "Things to verify before going to prod"
once before opening to users. The list is short; missing any of them is the
kind of thing that bites you in prod.

---

## Common gotchas, ranked by frequency I've seen them

1. **Streaming returns one giant chunk instead of streaming.** nginx
   `proxy_buffering off` not applied to `/api/agent/`. Fix: check the
   nginx config, reload nginx.

2. **App can't reach RDS.** Network reachability between Databricks and your
   VPC. Fix: security group + public IP, or VPC peering, or PrivateLink.

3. **OAuth 400 / invalid_client.** The token_endpoint URL is wrong, or the
   client_secret was rotated and the secret in AWS wasn't updated. Fix:
   re-run the verification curl in step 3.

4. **JWKs verification fails.** The JWKs URL is wrong, or the audience claim
   doesn't match `OAUTH_EXPECTED_AUDIENCE`. Fix: set `OAUTH_AUDIENCE_CHECK=false`,
   inspect a real token's `aud` claim from logs, then set the right value.

5. **Existing user JWTs all rejected after deploy.** The split-key migration
   wasn't done correctly — you removed the legacy key before 8 hours had
   passed. Fix: regenerate `cdp/jwt-keys` with the current value also under
   `user_session_legacy`.

6. **`agent.daily_usage` view doesn't exist.** Migration 03 wasn't applied,
   only 04. Fix: re-run migrations in order.

7. **Mock agent returns 401.** `AGENT_BEARER_OVERRIDE` in `.env` doesn't match
   `AGENT_SHARED_SECRET` set when starting the mock. Fix: make them match.
