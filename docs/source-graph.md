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

## Frontend notes

- React Flow nodes can be created directly from `nodes[].id`, `type`, and `name`.
- Edges use `source` and `target`; edges with `target: null` should be rendered as unresolved observations (for example dashed) or shown in an inspector instead of as connected edges.
- Source details can be fetched with existing workspace endpoints (`/api/workspace/projects/{project_id}/files` and `/api/workspace/projects/{project_id}/manifest`); the graph response intentionally omits file contents.
- This schema is separate from the existing Function `Graph` schema used by `/api/graph/*`. Do not assume the same node shape.

## Investigation node lookup contract

Backend service function:

```python
get_nodes_on_path_python(
    project_id: str,
    file_path: str,
    line_number: int,
) -> list[SourceGraphNodeMatch]
```

The backend router function delegates to
`SourceGraphNodeLookup(workspace_service)`. The lookup validates the project,
normalizes Windows and POSIX separators,
requires a positive 1-based line number, and matches the exact project-relative
path. It rebuilds the existing index, resolution result, and SourceGraph; it
does not accept a caller-supplied graph.

Each result contains:

```json
{
  "node_id": "project-abc123:services.orders:OrderService.get_order",
  "node_type": "method",
  "name": "get_order",
  "qualified_name": "OrderService.get_order",
  "file_path": "services/orders.py",
  "start_line": 2,
  "end_line": 3,
  "parent_node_id": "..."
}
```

Results use actual SourceGraph node IDs and include matching symbols plus
relevant containing class/module nodes. Missing projects, invalid paths, and
invalid line numbers raise `SourceGraphLookupError`; a valid file and line with
no matching indexed node returns an empty list.

Ram's tool should expose the logical contract:

```text
Tool: get_nodes_on_path_python
Inputs: project_id (string), file_path (string), line_number (integer)
Output: list of SourceGraphNodeMatch objects
```

The agent should call it once per evidence location after backend evidence
validation. The agent must use the active investigation's project ID and must
not accept arbitrary project IDs from untrusted model output. Kenny's frontend
can highlight `node_id` values through the existing `related_graph_nodes`
finding field.
