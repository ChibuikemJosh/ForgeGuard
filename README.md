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

1. Register a Python project.
2. Index its source and generate its SourceGraph.
3. Provide a security or business rule.
4. Run an investigation.
5. Review findings and validated source evidence.
6. Ask for explanations or proposed corrections through chat.
7. Review any correction before application.
8. Re-run the investigation after a correction.

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

Create `backend/app/.env` with:

```text
META_MODEL_API_KEY=<your-key>
```

Optional variables:

```text
META_MODEL_NAME=muse-spark-1.3
META_MODEL_BASE_URL=https://api.meta.ai/v1
FORGE_WORKSPACE_ROOT=<workspace-root>
FORGE_MAX_FILE_SIZE_BYTES=1048576
```

Run the backend:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

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
