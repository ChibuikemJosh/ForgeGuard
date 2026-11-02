"""LangGraph tools resolving SourceGraph nodes related to a location.

One tool exists per supported programming language (Python today). Each tool
is pre-scoped to a single project: the workspace and ``project_id`` are bound
when the tool is built, so callers only supply ``file_path`` and
``line_number`` and can never invent a project scope.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool, tool

from app.schemas.source_graph import SourceGraphNodeMatch
from app.services.project_workspace import LANGUAGE_BY_SUFFIX, WorkspaceService
from app.services.source_graph_lookup import SourceGraphNodeLookup

PYTHON_TOOL_NAME = "get_nodes_on_path_python"


def detect_language(file_path: str) -> str | None:
    """Return the workspace language label for a file path, if known."""
    if not isinstance(file_path, str) or not file_path.strip():
        return None
    return LANGUAGE_BY_SUFFIX.get(Path(file_path).suffix.lower())


def build_python_tool(
    workspace: WorkspaceService, project_id: str
) -> BaseTool:
    """Build the Python related-nodes tool bound to one project."""
    lookup = SourceGraphNodeLookup(workspace)

    @tool(PYTHON_TOOL_NAME)
    def get_nodes_on_path_python(
        file_path: str, line_number: int
    ) -> list[dict]:
        """Return SourceGraph nodes related to a Python source location.

        Use this tool only for Python (.py) files. The project is already
        scoped: pass the project-relative file path and 1-based line number
        of the violation. Returns the matching module/class/function/method
        nodes as a list of node dictionaries.
        """
        matches = lookup.get_nodes_on_path_python(
            project_id, file_path, line_number
        )
        return [match.model_dump() for match in matches]

    return get_nodes_on_path_python


def build_related_nodes_tools(
    workspace: WorkspaceService, project_id: str
) -> dict[str, BaseTool]:
    """Build one related-nodes tool per supported language, keyed by language."""
    return {"python": build_python_tool(workspace, project_id)}


def select_tool(
    tools: dict[str, BaseTool], file_path: str
) -> BaseTool | None:
    """Select the related-nodes tool for a file, or None when unsupported."""
    language = detect_language(file_path)
    if language is None:
        return None
    return tools.get(language)


def related_nodes_for_location(
    tools: dict[str, BaseTool], file_path: str, line_number: int
) -> list[SourceGraphNodeMatch]:
    """Invoke the language-appropriate tool for one location.

    Returns an empty list when no tool supports the file's language or when
    the lookup fails, so one bad location never fails the whole response.
    """
    selected = select_tool(tools, file_path)
    if selected is None:
        return []
    try:
        raw = selected.invoke(
            {"file_path": file_path, "line_number": line_number}
        )
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    matches: list[SourceGraphNodeMatch] = []
    for item in raw:
        if not isinstance(item, dict):
            return []
        try:
            matches.append(SourceGraphNodeMatch.model_validate(item))
        except Exception:
            return []
    return matches
