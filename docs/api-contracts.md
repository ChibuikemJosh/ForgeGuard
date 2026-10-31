# Forge Guard API Contracts

This document is the authoritative reference for the currently supported Forge Guard backend HTTP API.

Base URL (local development): `http://127.0.0.1:8000`

All request and response bodies are JSON unless noted. The backend is a modular monolith: it does not run a separate orchestration service, does not use a database, and does not apply changes without human review.

Endpoints are marked **Implemented**.

---

## Application health

### GET /api/health — Implemented

Returns minimal service health metadata.

Response:

```json
{ "status": "ok", "service": "forge-api" }
```

---

## Project workspace

### POST /api/workspace/projects — Implemented

Registers an existing directory inside the configured workspace root.

Request body (`OpenProjectRequest`):

```json
{ "path": "demo", "name": "Demo project" }
```

- `path`: string, optional, default `"."`. Relative path inside the configured workspace root.
- `name`: string or null, optional.

Response `200`: `ProjectReference`

```json
{ "project_id": "project-abc123", "name": "Demo project", "relative_path": "demo" }
```

Errors: `400` if the path is missing, not a directory, outside the workspace root, or uses path traversal.

Workflow: validates and resolves the path within the configured root, assigns a stable project ID from the relative path, stores the project in memory, and returns a client-safe reference.

### GET /api/workspace/projects/{project_id} — Implemented

Returns a registered project reference.

Response `200`: `ProjectReference`.
Errors: `404` unknown project.

### GET /api/workspace/projects/{project_id}/manifest — Implemented

Returns file discovery metadata for a registered project.

Response `200`: `ProjectManifest`

```json
{
  "project_id": "project-abc123",
  "name": "Demo project",
  "relative_path": "demo",
  "file_count": 2,
  "python_file_count": 1,
  "files": [
    { "path": "main.py", "language": "python", "size_bytes": 12, "sha256": "...", "readable": true, "error": null }
  ],
  "ignored_directories": [".git", ".venv", "node_modules", "__pycache__"]
}
```

Workflow: walks the project root, prunes ignored directories, excludes sensitive configuration files, records metadata and SHA-256 hashes, and reports unreadable or oversized files.

### GET /api/workspace/projects/{project_id}/files — Implemented

Returns the discovered file list.

Response `200`:

```json
{ "project_id": "project-abc123", "files": [ { "path": "main.py", "language": "python", "size_bytes": 12, "sha256": "...", "readable": true, "error": null } ] }
```

### GET /api/workspace/projects/{project_id}/index — Implemented

Returns the Python code index for a registered project.

Response `200`: `CodeIndex`

Includes modules, classes, functions, imports, calls, attribute accesses, source references, file hashes, and non-fatal indexing errors.

Workflow: reads registered Python files, parses them with the standard-library `ast` module, and produces structural facts. It does not perform semantic analysis.

### GET /api/workspace/projects/{project_id}/source-graph — Implemented

Builds and returns a read-only SourceGraph from the project index and symbol resolution.

Response `200`: `SourceGraph`

```json
{
  "project_id": "project-abc123",
  "project_name": "Demo project",
  "relative_path": "demo",
  "nodes": [
    { "id": "project:project-abc123", "type": "project", "name": "Demo project", "qualified_name": "demo", "module": null, "file_path": null, "source": null, "file_hash": null, "metadata": { "relative_path": "demo" } }
  ],
  "edges": [],
  "errors": [],
  "summary": { "total_nodes": 1, "total_edges": 0, "projects": 1, "modules": 0, "classes": 0, "functions": 0, "methods": 0, "routes": 0, "resolved_relationships": 0, "ambiguous_relationships": 0, "unresolved_relationships": 0 }
}
```

Workflow: registers project state is not changed; the endpoint indexes the project, resolves structural relationships, and builds graph nodes and edges.

Integration note: This schema is separate from the Function `Graph` schema used by `/api/graph/*`. Frontend consumers should not assume the same node shape.

---

## Graph validation and code generation

### POST /api/graph/validate — Implemented

Validates a Function-node graph without generating code.

Request body: `Graph`

Response `200`: `ValidationResult { valid, errors[] }`

### POST /api/graph/preview — Implemented

Validates a graph and returns deterministic Python.

Request body: `Graph`

Response `200`: `GraphPreviewResponse { valid, syntax_valid, code }`
Response `422`: invalid graph or generation failure.

Workflow: Pydantic validation, graph validation, stable dependency resolution, deterministic Python generation, and `ast.parse` syntax validation. No code is executed or written.

---

## Security analysis

### POST /api/security/analyze — Implemented

Analyzes the controlled order-ownership demonstration.

Query parameters:

- `corrected`: boolean, optional, default `false`.
- `verify`: boolean, optional, default `true`.

No request body.

Response `200`: `SecurityAnalysisResponse`

Includes the stable rule, evidence-backed finding when present, semantic graph, review-only fix proposal, verification result, status, outcome, and error.

### GET /api/security/rules/order-ownership — Implemented

Returns the stable order-ownership rule.

Response `200`: `SecurityRule`

### GET /api/security/proposals/{proposal_id} — Implemented

Returns a stored fix proposal.

Response `200`: `FixProposal`
Errors: `404` unknown proposal.

### POST /api/security/proposals/{proposal_id}/review — Implemented

Records a human review decision.

Request body (`ReviewDecisionRequest`):

```json
{ "decision": "approved", "reviewer": "human-reviewer", "actor": "human", "reason": "Verified" }
```

Response `200`: `ReviewDecisionRecord`
Errors: `404` unknown proposal, `409` proposal not pending.

### POST /api/security/proposals/{proposal_id}/apply — Implemented

Applies an approved proposal and runs controlled verification.

Response `200`: `FixApplicationResponse`
Errors: `404` unknown proposal, `409` not approved or already applied.

### POST /api/security/proposals/{proposal_id}/rollback — Implemented

Restores the exact content captured before application.

Response `200`: `FixApplicationResponse`
Errors: `404` unknown proposal, `409` no rollback available or file changed.

---

## Controlled security demonstration

### GET /api/demo/vulnerable/orders/{order_id} — Implemented

Returns an order after authentication but without ownership authorization.

Requires `x-customer-id` header.

### GET /api/demo/corrected/orders/{order_id} — Implemented

Returns an order only when the authenticated customer owns it.

Requires `x-customer-id` header.

---


## Security investigation

### POST /api/workspace/projects/{project_id}/investigate � Implemented

Investigates a registered project against a user-provided security rule.

Request body (`InvestigateRequest`):

```json
{
  "rule": {
    "rule_id": "order-ownership-authorization",
    "title": "Authenticated customers may access only their own orders",
    "invariant": "The authenticated customer ID must be compared with the retrieved order owner before the order is returned."
  }
}
```

Response `200`: `InvestigationResult`

```json
{
  "investigation_id": "investigation-abc123",
  "project_id": "project-abc123",
  "rule_id": "order-ownership-authorization",
  "status": "completed",
  "findings": [
    {
      "finding_id": "finding-abc123",
      "rule_id": "order-ownership-authorization",
      "title": "Potential violation of Authenticated customers may access only their own orders",
      "description": "The Violations Finder Agent identified source locations that may violate the supplied security rule.",
      "severity": "high",
      "confidence": 0.5,
      "status": "potential",
      "affected_files": ["routes/orders.py"],
      "affected_symbols": ["project-abc123:routes/orders.py:get_order"],
      "related_graph_nodes": ["project-abc123:routes/orders.py:get_order"],
      "evidence": [
        {
          "evidence_id": "evidence-routes/orders.py:12",
          "evidence_type": "source_excerpt",
          "description": "Agent-proposed source location validated by the backend.",
          "file_path": "routes/orders.py",
          "source": { "project_id": "project-abc123", "file_path": "routes/orders.py", "module": "routes.orders", "symbol": "project-abc123:routes/orders.py:get_order", "line_start": 12, "line_end": 12, "file_hash": "..." },
          "excerpt": "return order",
          "symbol_id": "project-abc123:routes/orders.py:get_order",
          "file_hash": "...",
          "observed": false,
          "status": "valid",
          "validation_error": null
        }
      ],
      "reasoning": "The agent returned 1 location(s); 1 passed backend evidence validation.",
      "recommended_remediation": "Review the identified code paths and enforce the security rule.",
      "verification_status": "not_run"
    }
  ],
  "errors": [],
  "summary": "Investigated 1 files; agent returned 1 location(s), 1 validated."
}
```

Workflow: registers nothing; indexes the project, builds its SourceGraph, invokes Ram's Violations Finder Agent with the rule and project folder, then validates every returned location against file existence, containment, line range, excerpt consistency, symbol identity, and file-hash freshness. Invalid locations are reported in `errors` and do not become validated evidence.

Integration note: AI-generated findings are returned as `potential` unless all evidence is valid and directly observed. The backend does not treat the agent's assertion as a confirmed vulnerability.


## Status values

- `AnalysisStatus`: `completed`, `failed`
- `VerificationStatus`: `not_run`, `passed`, `failed`
- `ReviewStatus`: `not_proposed`, `pending`, `approved`, `rejected`
- `ApplicationStatus`: `not_applied`, `applied`, `failed`
- `ResolutionStatus`: `resolved`, `ambiguous`, `unresolved`
- `Severity`: `high`, `info`

## Integration boundaries

| Concern | Owner | Contract |
|---|---|---|
| Backend schemas, analysis, graph, verification | This backend | `schemas/security.py`, `/api/security/*`, `/api/workspace/*` |
| Agent orchestration / review loop | Ram | Consumes `SecurityAnalysisResponse`, `FixProposal`, `SourceGraph`; backend provides structured data and controlled operations |
| Meta model tool | Bisal | Receives a `SecurityFinding`; returns structured explanation or fix proposal |
| React graph visualiser | Kenny | Renders `SecurityGraph` from `/api/security/analyze` and `SourceGraph` from `/api/workspace/projects/{project_id}/source-graph` |
