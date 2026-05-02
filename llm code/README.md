# Databricks A2A Agent — LangGraph orchestrator

Three modes:

- **Real (`agent.py` + `a2a_server.py`)** — LangGraph graph with one node
  (rule drafter), Postgres checkpointer for refinement turns. Deploy to
  Databricks Apps.
- **Mock (`mock_agent.py`)** — emits the same SSE events without LangGraph
  or a database. Use for frontend dev.

## Local dev (mock — fastest path)

```bash
cd databricks_agent
python -m venv .venv && source .venv/bin/activate
# Mock only needs the slim deps:
pip install fastapi uvicorn pydantic httpx
AGENT_SHARED_SECRET=dev-secret-not-for-prod \
  uvicorn mock_agent:app --port 8001 --reload
```

Verify:

```bash
curl -N -X POST http://localhost:8001/ \
     -H "Authorization: Bearer dev-secret-not-for-prod" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":"1","method":"message/stream",
       "params":{"message":{
         "messageId":"m1","role":"user","kind":"message","contextId":"c1",
         "parts":[{"kind":"text","text":"Email must not be null."}],
         "metadata":{"skill_id":"generate_business_rule"}
       }}}'
```

You should see `step` → many `artifact-update` deltas → `status-update completed`.

## Local dev (real LangGraph, no Databricks)

If you want to exercise the real graph code without deploying:

```bash
pip install -r requirements.txt

export LANGGRAPH_CHECKPOINT_DB_URI="postgresql://cdpadmin:****@your-rds:5432/cdp"
export AGENT_SHARED_SECRET="dev-secret-not-for-prod"
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="dapi*****"
export FM_ENDPOINT_NAME="databricks-meta-llama-3-1-70b-instruct"

uvicorn a2a_server:app --port 8001 --reload
```

This requires:
- Network reachability to your RDS from your laptop.
- A Databricks PAT with `CAN_QUERY` on the FM serving endpoint.

## Deploy to Databricks Apps

1. Create a Databricks App (Compute → Apps → Create).
2. Push this folder via Databricks Git folders or `databricks bundle deploy`.
3. Set environment variables (Settings → Environment):

   | Variable | Value |
   |---|---|
   | `AGENT_SHARED_SECRET` | strong random; same as `backend/.env` on EC2 |
   | `FM_ENDPOINT_NAME` | e.g. `databricks-meta-llama-3-1-70b-instruct` |
   | `LANGGRAPH_CHECKPOINT_DB_URI` | `postgresql://cdpadmin:****@<rds>:5432/cdp` |
   | `AGENT_PUBLIC_URL` | shown after deploy |
   | `FASTAPI_CALLBACK_URL` | `https://<your-fastapi>/` (used by Phase 2 tools) |

4. Grant the App's service principal `CAN_QUERY` on the FM serving endpoint.
5. **Verify network reachability App → RDS.** Two common patterns:

   - **Public RDS + security group allowlist.** RDS is publicly accessible;
     security group allows the Databricks workspace's egress IPs. Simplest;
     fine if RDS is dev/internal.
   - **VPC peering or PrivateLink.** RDS in a private subnet; Databricks
     workspace peered or a PrivateLink endpoint set up. Required for prod.

   The App will not start if it can't reach RDS — `setup()` on the
   AsyncPostgresSaver fails fast at lifespan start.

6. Deploy and tail logs: `databricks apps logs <app-name>`.

First start: the checkpointer creates its tables (`checkpoints`,
`checkpoint_blobs`, `checkpoint_writes`) in the configured database. They
live in the `public` schema by default — see `db/04_agent_phase1_langgraph.sql`
for an `agent` schema option.

## What the LangGraph code is doing

When the FastAPI backend sends a `message/stream` request:

1. `a2a_server.py` parses the A2A message envelope: extracts `description`,
   `thread_id` (from `contextId`), `on_behalf_of_token`, `user_id`.
2. It builds an input state `{"description": ...}` and a `RunnableConfig`
   with the per-turn ephemera in `configurable`.
3. It calls `graph.astream_events(input, config, version="v2")`.
4. The graph runs the `draft_rule_node`. The node calls `llm.astream()`,
   which produces `on_chat_model_stream` events for every token.
5. The event mapper translates each event:
   - `on_chain_start` for a labeled node → SSE `step`
   - `on_chat_model_stream` → SSE `artifact-update` with the delta
   - (Phase 2) `on_tool_start/end` → SSE `tool`
6. After the graph completes, the checkpointer has persisted state under
   `thread_id`. A subsequent request with the same `thread_id` rehydrates
   the conversation history (refinement turn).

## Phase 2 hardening

- [ ] Wire actual tools in `tools.py`. Read tools first (lookup dimensions,
      EDE mappings); write tools after the read path is solid.
- [ ] Add intent classifier node (decides which child to invoke).
- [ ] Add validator node (checks the draft against rules, retries on failure).
- [ ] Replace shared-secret auth with OAuth M2M.
- [ ] Move the checkpointer from RDS to Lakebase (one env var change).
