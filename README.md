# Forge Guard

Forge Guard is an early-stage graph based security analysis tool for
AI-assisted Python backend development. Its MVP detects one business-logic
authorization problem: an authenticated customer retrieving another
customer's order.

## Current implementation

- Preserved React + TypeScript + Vite landing page at `/`.
- Existing graph-to-Python workspace at `/workspace`.
- Controlled FastAPI vulnerable and corrected order example.
- Deterministic AST-based ownership analysis for that controlled example.
- Structured security findings, evidence, semantic graph data, fix proposals,
  and verification results.
- FastAPI endpoints for analysis and the stable order-ownership rule.
- Backend tests covering vulnerable and corrected behavior.

The analysis is deliberately narrow. It is not a general Python security
scanner and does not claim coverage of arbitrary FastAPI projects.

## Repository layout

```text
frontend/   React, TypeScript, Vite application and visualiser
backend/    FastAPI application, security models, services, and tests
docs/       Architecture, project model, graph-to-code, and security docs
```

## Prerequisites

- Node.js 20.19+ (or 22.12+)
- npm 10+
- Python 3.11+

## Run the frontend

From `frontend/`:

```powershell
npm install
npm run dev
```

The landing page runs at `http://localhost:5173`. The frontend uses
`VITE_API_BASE_URL` when set and otherwise calls
`http://127.0.0.1:8000`. Copy `frontend/.env.example` to
`frontend/.env.local` to override it.

```powershell
npm run lint
npm run build
```

## Run the backend

From `backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run tests:

```powershell
pytest
```

## Forge Guard demo

The controlled demo uses in-memory orders and an `x-customer-id` header as
minimal authentication input. It has two reproducible states:

```text
GET /api/demo/vulnerable/orders/order-bob
GET /api/demo/corrected/orders/order-bob
```

With `x-customer-id: customer-alice`, the vulnerable route returns Bob's order
while the corrected route returns HTTP 403. No real customer data or
production authentication infrastructure is involved.

Analyze the vulnerable state:

```powershell
curl -X POST http://127.0.0.1:8000/api/security/analyze
```

Analyze the corrected state:

```powershell
curl -X POST "http://127.0.0.1:8000/api/security/analyze?corrected=true"
```

The response contains the stable rule, evidence-backed finding (when present),
semantic graph, review-only remediation proposal, and an executed verification
result. The proposal is not applied automatically.

See [docs/security-analysis.md](docs/security-analysis.md) for the contract and
limitations.

## Existing graph-to-Python workflow

The `/workspace` route still demonstrates the original deterministic graph
workflow for two Function nodes. It is preserved separately from Forge Guard's
security graph and is documented in [docs/graph-to-code.md](docs/graph-to-code.md).

## Agent and tool boundaries

- Ram owns orchestration and the future agentic review loop.
- Bisal owns the reusable Meta model tool.
- Kenny owns the React graph visualiser and workspace UI.
- This backend owns the controlled example, security schemas, deterministic
  analysis, graph construction, and verification contracts.

Project Investigation uses the Meta Model API (Muse) from the backend only.
AI fix proposals require human approval before application; rollback is supported.
No database, Redis, or production authentication infrastructure is implemented.

## Project Investigation (local testing)

Workflow: Select project (SourceGraph builds automatically) → Select rule → Run AI
investigation (Meta Muse model) → View findings → Explore graph → AI-assisted
fix → Review → Apply / Rollback. AI findings are shown as **Potential** (the
backend status verbatim), never Confirmed.

Meta Model API config (`backend/.env`, never in the frontend):

```bash
cp .env.example .env   # then put the real META_MODEL_API_KEY in .env
# META_MODEL_BASE_URL=https://api.meta.ai/v1
# META_MODEL_NAME=muse-spark-1.3   # optional preview: muse-wonder-1.0
```

### Run locally (macOS / zsh)

```bash
# backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then put the real META_MODEL_API_KEY in .env
pytest
uvicorn app.main:app --reload --reload-dir app --host 127.0.0.1 --port 8000

# frontend (new terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173/workspace
```

Note: `--reload-dir app` is required so applying a fix inside
`backend/workspaces/` does not restart the server and wipe in-memory state.
CORS origins can be overridden with `FORGE_CORS_ORIGINS` (comma-separated).

The bundled sample project lives at `backend/workspaces/orders-api/`; use the
**Use sample project: Orders API** button in the workspace picker. You can also upload a project
folder or a `.zip` from the same picker (folders are zipped in the browser,
skipping `.git`/`node_modules`/venvs/`.env`; the zip is extracted safely on the backend,
sensitive files are skipped, code is parsed with `ast` and never executed).
Reset the sample after applying fixes:

```bash
git checkout backend/workspaces/orders-api
```

### Curl smoke test

```bash
PID=$(curl -s -X POST localhost:8000/api/workspace/projects -H 'Content-Type: application/json' -d '{"path":"orders-api"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["project_id"])')
curl -s localhost:8000/api/workspace/projects/$PID/source-graph | python3 -m json.tool | head -40
curl -s -X POST localhost:8000/api/workspace/projects/$PID/investigate -H 'Content-Type: application/json' \
  -d '{"rule":{"rule_id":"order-ownership-authorization","title":"Customers may only access their own orders","invariant":"The authenticated customer ID must be compared with the order owner before the order is returned."}}' | python3 -m json.tool
```

Expected (real Muse): status `completed` with evidence in `routes/orders.py`
and nothing in `routes/profile.py`. Without a key, status `failed` with
"AI provider is not configured", and the UI shows that message verbatim.
