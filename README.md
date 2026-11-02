# Forge Guard

Forge Guard is an AI-powered software engineering and security analysis environment.
It inspects existing Python projects, builds a read-only SourceGraph from their
structure, and investigates user-defined security or business rules with a
Meta Muse-powered agent. Findings are evidence-gated: the backend validates
reported source locations before returning them.

## Problem statement

Modern applications often fail in business logic and authorization paths that are
hard to see from framework-level scanning alone. Forge Guard connects project
structure, source evidence, and AI-assisted investigation so that potential
violations can be traced to real files, symbols, and graph nodes.

## Current MVP features

- Register an existing Python project inside a configured workspace root.
- Discover and index Python source files.
- Resolve structural symbols and relationships.
- Generate a read-only SourceGraph.
- Investigate user-provided security rules with Meta Muse.
- Validate model-proposed source locations against actual source.
- Map valid findings to SourceGraph nodes.
- Review, apply, roll back, and verify controlled corrections.
- Chat endpoint for violation-location lookup.
- Deterministic backend tests for investigation and evidence validation.

## Core user workflow

1. Upload a Python project folder (or open the sample — each visitor gets their own copy).
2. Index its source and generate its SourceGraph (Map).
3. Provide a security or business rule and run an investigation, watching live agent activity. The sample project uses the 3 demo preset rules; an uploaded project gets only rules generated from its own routes and resource IDs, or a custom rule you write.
4. Understand findings and validated source evidence with SourceGraph node matches.
5. Review the proposed fix side-by-side on the Changes tab; approve or reject it.
6. Apply the fix, or roll it back.
7. Re-run the investigation to verify.
8. Download your fixes as a `.patch` (apply with `git apply`) or download the project copy as a `.zip`.

## Architecture overview

Forge Guard is a modular FastAPI monolith.

- `WorkspaceService` discovers and safely reads project files.
- `PythonIndexer` extracts structural AST facts.
- `SymbolResolver` resolves structural relationships with explicit statuses.
- `SourceGraphBuilder` creates a read-only SourceGraph.
- `SecurityInvestigationService` prepares rule context and validates findings.
- `ViolationsFinderAgent` calls Meta Muse and parses locations.
- `EvidenceValidator` independently validates source evidence.
- Existing security services provide controlled demonstration analysis, proposals, approval, application, rollback, and verification.

The frontend renders backend-provided data and does not infer source facts.

## Technology stack

Backend:

- Python 3.11+
- FastAPI
- Pydantic
- LangChain and LangGraph
- Meta Muse API
- pytest

Frontend:

- React
- TypeScript
- Vite

## Repository structure

```text
frontend/   React, TypeScript, and Vite application
backend/    FastAPI application, schemas, services, and tests
docs/       Architecture and API contract documentation
agent_loop/ Ram's orchestration implementation
```

## Setup and installation

### Backend

From `backend/`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `backend/.env` with:

```text
META_MODEL_API_KEY=<your-key>
```

Optional variables:

```text
META_MODEL_NAME=muse-spark-1.3
META_MODEL_BASE_URL=https://api.meta.ai/v1
FORGE_WORKSPACE_ROOT=<workspace-root>
FORGE_MAX_FILE_SIZE_BYTES=1048576
FORGE_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

Run the backend:

```powershell
uvicorn app.main:app --reload --reload-dir app --host 127.0.0.1 --port 8000
```

`--reload-dir app` prevents uploaded projects in `workspaces/` from restarting the server.

Run tests:

```powershell
pytest
```

### Frontend

From `frontend/`:

```powershell
npm install
npm run dev
```

## Current limitations

- Investigation is Python-only.
- Large projects may be truncated during investigation.
- AI findings are potential, not confirmed vulnerabilities.
- Evidence validation checks source legitimacy, not rule truth.
- General arbitrary-file correction is not implemented.
- Fix proposals and verification are controlled-demo capabilities.
- ConstructionGraph and advanced data-flow analysis are planned, not implemented.

## Future roadmap

- Multi-language project analysis.
- More advanced security and business-rule analysis.
- Graph-based software engineering and system design.
- Visual representation of components and relationships.
- Cross-layer dependency and impact analysis.
- AI-assisted explanation, correction, and generation.
- Intelligent context retrieval for large projects.
- Advanced engineering workflows.

## Agent and tool boundaries

- Ram owns orchestration in `agent_loop/`.
- Bisal owns the reusable Meta model tool.
- Kenny owns the React visualiser and workspace UI.
- The backend owns schemas, workspace, indexing, graph construction, investigation, evidence validation, and controlled operations.

Project Investigation uses the Meta Model API (Muse) from the backend only.
AI fix proposals require human approval before application; rollback is supported.
No database, Redis, or production authentication infrastructure is implemented.

## Project Investigation (local testing)

Workflow: Select project (SourceGraph builds automatically) → Select rule → Run AI
investigation (Meta Muse model) → View findings → Explore graph → AI-assisted
fix → Review → Apply / Rollback. AI findings are shown as **Potential** (the
backend status verbatim), never Confirmed. Rules are loaded per project: the
sample project shows the 3 demo preset rules (defaulting to order ownership),
while uploaded projects show only rules generated from their own routes and
resource IDs — an upload with no routes gets no generated rules, so write a
custom rule there.

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

Note: `--reload-dir app` prevents uploaded projects in `workspaces/` from restarting the server (it also stops applying a fix inside `backend/workspaces/` from wiping in-memory state).
CORS origins can be overridden with `FORGE_CORS_ORIGINS` (comma-separated).

The bundled sample project lives at `backend/workspaces/orders-api/`; use the
**Use sample project: Orders API** button in the workspace picker. You can also upload a project
folder from the same picker (folders are zipped in the browser,
skipping `.git`/`node_modules`/venvs/`.env`; the zip is extracted safely on the backend,
sensitive files are skipped, code is parsed with `ast` and never executed).
Opening the sample copies it per visitor (`orders-api-<id>`), so applying a fix never changes the tracked sample or another visitor's copy. Old copies are cleaned up after `FORGE_UPLOAD_TTL_HOURS` (default 6).

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


## Deploying (hackathon)

No authentication by design. Projects are lost on browser refresh or backend restart; uploaded code is sent to the Meta model API for investigation. Folder uploads only (max 10 MB after skipping ignored folders; files over 1 MB are skipped).

- **Backend (Render / Railway, native Python service):** root directory `backend/`, build command `pip install -r requirements.txt`, start command
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'`
  (no `--reload`, no extra workers; `--proxy-headers` lets the per-IP rate limit see real client IPs behind the host's proxy). Set `META_MODEL_API_KEY`, `META_MODEL_BASE_URL`, `META_MODEL_NAME`, `FORGE_ENV=production`, and `FORGE_CORS_ORIGINS=https://<frontend-domain>`. Run a **single instance** (state is in memory).
- **Frontend (Vercel / Netlify):** root directory `frontend/`, build command `npm run build`, output `dist`; set `VITE_API_BASE_URL=https://<backend-domain>` at build time.
- In production only sample projects can be opened by path, the legacy security demo apply/rollback are disabled, and AI endpoints are rate-limited per IP (10/hour). Polling, cancelling, and downloads are not rate-limited.
- **Single uvicorn worker required; running investigations and project copies are lost on restart.** Downloads then return "This project copy has expired. Re-upload the project folder."
