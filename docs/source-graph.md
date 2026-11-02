# SourceGraph API and Frontend Integration

## Endpoint

```http
GET /api/workspace/projects/{project_id}/source-graph
```

Returns a read-only SourceGraph for a registered project.

## Response shape

```json
{
  "project_id": "project-abc123",
  "project_name": "demo",
  "relative_path": "demo",
  "nodes": [
    {
      "id": "project:project-abc123",
      "type": "project",
      "name": "demo",
      "qualified_name": "demo",
      "module": null,
      "file_path": null,
      "source": null,
      "file_hash": null,
      "metadata": { "relative_path": "demo" }
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "project:project-abc123",
      "target": "module:project-abc123:routes/orders.py",
      "type": "CONTAINS",
      "status": "resolved",
      "observed": true,
      "source_ref": { "...": "..." },
      "evidence": "Project contains module."
    }
  ],
  "errors": [],
  "summary": {
    "total_nodes": 0,
    "total_edges": 0,
    "projects": 1,
    "modules": 1,
    "classes": 0,
    "functions": 0,
    "methods": 0,
    "routes": 0,
    "resolved_relationships": 0,
    "ambiguous_relationships": 0,
    "unresolved_relationships": 0
  }
}
```

## Node types

- `project`
- `module`
- `class`
- `function`
- `method`
- `route`

## Edge types

- `CONTAINS`
- `DEFINES`
- `DEFINES_METHOD`
- `IMPORTS`
- `DEPENDS_ON`
- `CALLS`
- `HANDLES_ROUTE`

## Resolution statuses

- `resolved`
- `ambiguous`
- `unresolved`

Unresolved and ambiguous calls are returned as `CALLS` edges with `target: null` and the corresponding status. They are not connected to arbitrary targets.

## Source reference

`source` / `source_ref` use `SourceReference`:

- `project_id`
- `file_path`
- `module`
- `symbol`
- `line_start`
- `line_end`
- `file_hash`

## Investigation node lookup contract

The backend computes node matches for each validated evidence location with the pure function `match_nodes_at_location(graph, file_path, line_number)` in `backend/app/services/source_graph_lookup.py`. Its matches are **authoritative**: nodes containing the line in that file, ordered narrowest first (route/method/function, then class, then module; smaller line span first within a type), each with its `parent_node_id` from containment edges. The agent's `relatednodes` are optional hints, kept only when the `node_id` exists in the graph and its `file_path` equals the evidence file, and de-duplicated against backend matches. `SourceGraphNodeLookup.get_nodes_on_path_python` validates project, path, and line range, then delegates to `match_nodes_at_location`. A mapping failure is recorded in the investigation `errors` and as a failed `mapping` step; it never fails the investigation.

## Frontend notes

- React Flow nodes can be created directly from `nodes[].id`, `type`, and `name`.
- Edges use `source` and `target`; edges with `target: null` should be rendered as unresolved observations (for example dashed) or shown in an inspector instead of as connected edges.
- Source details can be fetched with existing workspace endpoints (`/api/workspace/projects/{project_id}/files` and `/api/workspace/projects/{project_id}/manifest`); the graph response intentionally omits file contents.
- This schema is separate from the existing Function `Graph` schema used by `/api/graph/*`. Do not assume the same node shape.
