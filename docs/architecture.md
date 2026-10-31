# Forge Guard Architecture

Forge Guard is a modular FastAPI monolith with two distinct workflows:

1. Source-to-Graph: inspect existing Python projects and represent their architecture.
2. Graph-to-Code: validate user-constructed Function graphs and generate Python.

The backend is authoritative for project data, indexing results, graph data, findings, proposals, and verification results. The frontend renders returned data and does not infer source facts.

## Source-to-Graph pipeline

1. Project registration
   - `WorkspaceService` resolves a client-supplied relative path inside the configured workspace root.
   - It assigns a stable project ID and stores the server-side project root.

2. Workspace discovery
   - Files are enumerated with ignored directories pruned.
   - Sensitive configuration files, oversized files, and files outside the root are excluded or reported.
   - File metadata includes size and SHA-256 hash.

3. Python AST indexing
   - `PythonIndexer` parses Python files using the standard-library `ast` module.
   - It records modules, imports, classes, methods, functions, decorators, parameters, return annotations, calls, attribute accesses, source references, and file hashes.
   - It does not perform semantic analysis or security reasoning.

4. Symbol resolution
   - `SymbolResolver` resolves structural relationships from the `CodeIndex`.
   - It supports absolute and relative imports, imported symbols, cross-module calls, class method definitions, module dependencies, and method calls where a class can be identified.
   - Resolution statuses are `resolved`, `ambiguous`, or `unresolved`.
   - Unresolved calls are retained as observations and are not connected to arbitrary symbols.

5. SourceGraph generation
   - `SourceGraphBuilder` converts the `CodeIndex` and `ResolutionResult` into a read-only `SourceGraph`.
   - Nodes: project, module, class, function, method, route (only when a route decorator is present).
   - Edges: CONTAINS, DEFINES, DEFINES_METHOD, IMPORTS, DEPENDS_ON, CALLS, HANDLES_ROUTE.
   - Every node and edge preserves source references, file hashes, and evidence where available.

6. API exposure
   - Workspace, indexing, and SourceGraph endpoints expose structured data to the frontend and future agent integration.
   - Source code contents are not embedded in graph responses; existing file endpoints provide source details.

## Graph-to-Code workflow

The existing `/api/graph/*` endpoints remain separate and unchanged.

Supported:

- Function nodes.
- `calls` relationships.
- Stable dependency ordering.
- Deterministic Python generation.
- `ast.parse` syntax validation.

Unsupported or rejected:

- Other node types.
- Data-flow edges.
- Cycles, self-calls, multiple calls per caller, and incompatible interfaces.

## Security investigation

Implemented today:

- A controlled order-ownership demonstration in `app/security_demo.py`.
- Deterministic AST evidence extraction for the known vulnerable and corrected functions.
- Evidence-backed findings and an evidence-derived semantic graph.
- Review-only fix proposals.
- Human approval, application, verification, and rollback for the controlled file.
- General project investigation endpoint `POST /api/workspace/projects/{project_id}/investigate`.
- Structured `SecurityRule`, `InvestigationFinding`, `EvidenceItem`, and `InvestigationResult` models.
- Evidence validation against file existence, containment, line range, excerpt consistency, symbol identity, and file-hash freshness.
- Integration with Ram's Violations Finder Agent through its `find_violations` interface. The agent receives the rule text and project folder and returns source locations. The backend validates those locations and returns findings as `potential` unless evidence is validated.
- Investigation prompts also include bounded structural SourceGraph observations and indexing limitations. These observations guide the model but are explicitly not treated as semantic proof.

The backend does not treat AI-generated locations as confirmed vulnerabilities. Missing or invalid evidence yields `inconclusive` or `unsupported` findings.

Ram's agent is a LangGraph/LangChain wrapper around a Meta Model compatible API. It is not a second orchestrator in this backend; the backend calls it as an investigation component.

## Agent integration

The backend provides structured project information, source evidence, graph data, and controlled operations. Ram's orchestration layer coordinates iterative AI reasoning and tool calls. The backend does not implement a second orchestrator.

## Code modification and verification

Implemented capabilities:

- Review-only fix proposals.
- Human-only approval; AI actors cannot approve.
- Path and source-hash checks before application.
- Atomic writes and rollback.
- Controlled HTTP verification with actual outcomes.

General arbitrary file creation and command execution are not implemented.

## Service responsibilities

- `project_workspace.py`: project registration, safe file discovery, metadata, hashing, and reading.
- `python_indexer.py`: structural Python AST facts.
- `symbol_resolution.py`: structural relationship resolution with explicit statuses.
- `source_graph_builder.py`: read-only SourceGraph construction.
- `security_analysis.py`, `security_fixes.py`, `security_verification.py`: controlled security demonstration and fix workflow.
- `graph_validation.py`, `code_generation.py`: Function graph validation and Python generation.
