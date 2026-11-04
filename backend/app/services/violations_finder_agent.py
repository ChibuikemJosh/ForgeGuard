"""LangGraph agent mapping custom security violations to source locations.

The agent follows ``system_instructions_validatoragent.md``: it sends the
custom violation details plus the Python files of the project folder to the
Meta Model API and parses the returned violations into filename/line pairs.
Per-session context is retained via a LangGraph checkpointer keyed by the
caller-provided session identifier.

After analysis, an ``enrich`` step invokes one related-nodes LangGraph tool
per location (selected by the file's programming language) and attaches the
resulting SourceGraph nodes as ``relatednodes``. The ``project_id`` scoping
those tools travels through the LangGraph state from the chat request.
"""

from __future__ import annotations

import json
import os
import ast
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from pydantic import SecretStr

from app.schemas.chat import ChatLocation
from app.services.project_workspace import WorkspaceError, WorkspaceService
from app.services.investigation_trace import InvestigationCancelled
from app.services.source_graph_tools import (
    build_related_nodes_tools,
    related_nodes_for_location,
)

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

SYSTEM_INSTRUCTIONS_PATH = Path(__file__).with_name(
    "system_instructions_validatoragent.md"
)
DEFAULT_MODEL = "muse-spark-1.3"
DEFAULT_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_CHUNK_CHARS = 80_000
DEFAULT_CHUNK_OVERLAP_LINES = 8
DEFAULT_MAX_RETRIES = 2
DEFAULT_REQUEST_TIMEOUT = 90.0
DEFAULT_RETRY_BACKOFF = 0.25
SKIPPED_DIR_NAMES = {
    ".git",
    ".hg",
    ".sl",
    ".venv",
    "__pycache__",
    "node_modules",
}

RESPONSE_FORMAT = """# Response format
Respond with ONLY a JSON object, no other text:
{"violations": [{"filename": "<project-relative path>", "linenumber": <1-based line number>}]}
Example: {"violations": [{"filename": "orders/views.py", "linenumber": 42}]}
If the violation is not present, respond with: {"violations": []}"""


def _int_setting(name: str, default: int, minimum: int = 0) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, value)


def _float_setting(name: str, default: float, minimum: float = 0.0) -> float:
    try:
        value = float(os.environ.get(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, value)


@dataclass(frozen=True)
class SourceChunk:
    chunk_id: str
    file_path: str
    line_start: int
    line_end: int
    content: str


def _node_ranges(tree: ast.AST) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for node in getattr(tree, "body", []):
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", None)
        if isinstance(start, int) and isinstance(end, int):
            ranges.append((start, end))
    return ranges


def _split_range(
    lines: list[str],
    start: int,
    end: int,
    max_chars: int,
    overlap_lines: int,
) -> list[tuple[int, int]]:
    if len("".join(lines[start - 1:end])) <= max_chars:
        return [(start, end)]
    result: list[tuple[int, int]] = []
    cursor = start
    while cursor <= end:
        current_end = cursor
        size = 0
        while current_end <= end and (current_end == cursor or size + len(lines[current_end - 1]) <= max_chars):
            size += len(lines[current_end - 1])
            current_end += 1
        current_end -= 1
        result.append((cursor, current_end))
        if current_end >= end:
            break
        next_cursor = max(cursor + 1, current_end - overlap_lines + 1)
        cursor = next_cursor
    return result


def _collect_python_chunks(
    folder: Path,
    allowed_paths: set[str] | None = None,
) -> tuple[list[SourceChunk], list[str]]:
    """Collect every readable Python file as structure-aware bounded chunks."""
    max_chars = _int_setting(
        "FORGE_INVESTIGATION_CHUNK_CHARS", DEFAULT_CHUNK_CHARS, minimum=256
    )
    overlap = _int_setting(
        "FORGE_INVESTIGATION_CHUNK_OVERLAP_LINES",
        DEFAULT_CHUNK_OVERLAP_LINES,
        minimum=0,
    )
    candidates = sorted(
        (
            path
            for path in folder.rglob("*.py")
            if path.is_file()
            and _is_visible(path, folder)
            and (
                allowed_paths is None
                or path.relative_to(folder).as_posix() in allowed_paths
            )
        ),
        key=lambda path: path.relative_to(folder).as_posix().lower(),
    )
    chunks: list[SourceChunk] = []
    failures: list[str] = []
    for path in candidates:
        relative = path.relative_to(folder).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            failures.append(f"{relative}: {error}")
            continue
        lines = source.splitlines(keepends=True)
        if not lines:
            continue
        try:
            ranges = _node_ranges(ast.parse(source, filename=relative))
        except SyntaxError:
            ranges = []
        if not ranges:
            ranges = [(1, len(lines))]
        else:
            covered: list[tuple[int, int]] = []
            cursor = 1
            for start, end in ranges:
                if cursor < start:
                    covered.append((cursor, start - 1))
                covered.append((start, end))
                cursor = end + 1
            if cursor <= len(lines):
                covered.append((cursor, len(lines)))
            ranges = covered
        expanded: list[tuple[int, int]] = []
        for start, end in ranges:
            expanded.extend(_split_range(lines, start, end, max_chars, overlap))
        for index, (start, end) in enumerate(expanded, start=1):
            header_start = 1 if start == 1 else max(1, min(start - 1, 80))
            body = "".join(lines[start - 1:end])
            header = "".join(lines[header_start - 1:start - 1])
            content = header + body
            if len(content) > max_chars:
                content = body
            chunks.append(
                SourceChunk(
                    chunk_id=f"{relative}:{start}-{end}:{index}",
                    file_path=relative,
                    line_start=header_start,
                    line_end=end,
                    content=content,
                )
            )
    return chunks, failures


STRUCTURED_OUTPUT_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "violations",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "violations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "linenumber": {"type": "integer"},
                        },
                        "required": ["filename", "linenumber"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["violations"],
            "additionalProperties": False,
        },
    },
}


def _extract_text(content: Any) -> str:
    """Extract text from a string or a list of model content blocks."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") in (None, "text") and isinstance(block.get("text"), str):
                    parts.append(block["text"])
            else:
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    text = getattr(content, "text", None)
    return text if isinstance(text, str) else str(content)


class AgentConfigurationError(RuntimeError):
    """The Meta Model API key is not configured."""


class ProjectFolderError(ValueError):
    """The requested project folder is missing or unreadable."""


class AgentResponseError(RuntimeError):
    """The model response could not be parsed into locations."""


class AgentState(MessagesState):
    locations: list[dict[str, Any]]
    project_id: str | None
    chunk: dict[str, Any]


def _is_visible(path: Path, root: Path) -> bool:
    return not any(
        part.startswith(".") or part in SKIPPED_DIR_NAMES
        for part in path.relative_to(root).parts[:-1]
    )


def _parse_locations(raw: str) -> list[ChatLocation]:
    """Parse model output into validated locations.

    Accepts a bare JSON array (optionally fenced), a dict wrapping the
    array, and ``line_number``/``line number`` key variants.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise AgentResponseError(
            f"Model response was not valid JSON: {error}"
        ) from error
    if isinstance(data, dict):
        for key in ("violations", "locations", "results"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise AgentResponseError("Model response was not a JSON array.")
    locations = []
    for item in data:
        if not isinstance(item, dict):
            raise AgentResponseError(f"Invalid location entry: {item!r}")
        line = item.get("linenumber", item.get("line_number", item.get("line number")))
        try:
            locations.append(
                ChatLocation.model_validate(
                    {"filename": item.get("filename"), "linenumber": int(line)}  # type: ignore[arg-type]
                )
            )
        except (ValueError, TypeError) as error:
            raise AgentResponseError(
                f"Invalid location entry: {item!r}"
            ) from error
    return locations


def _resolve_enrichment_context(
    project_folder: Path, project_id: str | None
) -> tuple[WorkspaceService, str]:
    """Return the workspace and effective project id for related-node lookup.

    A caller-provided id must already be registered (via the workspace APIs)
    on the shared workspace service; otherwise the project folder itself is
    registered on an ephemeral workspace scoped to this request.
    """
    if project_id:
        # Local import: the shared workspace lives on the workspace router;
        # importing it here avoids a module-level services -> router import.
        from app.api.routers.workspace import workspace_service

        try:
            workspace_service.get_project(project_id)
            registered_folder = workspace_service.project_root(project_id)
        except WorkspaceError as error:
            raise WorkspaceError(f"Unknown project: {project_id}") from error
        if project_folder.resolve() != registered_folder:
            raise WorkspaceError(
                "Project folder does not match the registered project."
            )
        return workspace_service, project_id
    workspace = WorkspaceService(project_folder)
    reference = workspace.register_project(".")
    return workspace, reference.project_id


class ViolationsFinderAgent:
    """LangGraph agent finding violation locations via the Meta Model API."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._model = model or os.environ.get("META_MODEL_NAME", DEFAULT_MODEL)
        self._base_url = base_url or os.environ.get(
            "META_MODEL_BASE_URL", DEFAULT_BASE_URL
        )
        self._graph = None
        self._graph_key: str | None = None
        self._checkpointer = MemorySaver()
        self.last_truncated: bool = False
        self.last_files_sent: int = 0
        self.last_project_id: str | None = None
        self.last_tool_names: list[str] = []
        self.last_chunk_stats: list[dict[str, Any]] = []
        self.last_retried_chunks: int = 0
        self.last_incomplete: bool = False

    @staticmethod
    def _api_key() -> str:
        return os.environ.get("META_MODEL_API_KEY", "").strip()

    @staticmethod
    def _system_prompt() -> str:
        instructions = SYSTEM_INSTRUCTIONS_PATH.read_text(encoding="utf-8")
        return f"{instructions}\n\n{RESPONSE_FORMAT}"

    def _build_graph(
        self,
        api_key: str,
        tools_by_project: dict[str, dict[str, BaseTool]],
        default_project_id: str,
    ):
        client = ChatOpenAI(
            model=self._model,
            base_url=self._base_url,
            api_key=SecretStr(api_key),
            timeout=_float_setting(
                "FORGE_INVESTIGATION_REQUEST_TIMEOUT",
                DEFAULT_REQUEST_TIMEOUT,
                minimum=1.0,
            ),
        )
        try:
            invoke_client = client.bind(response_format=STRUCTURED_OUTPUT_FORMAT)
        except Exception:
            invoke_client = client
        system_prompt = self._system_prompt()

        def analyze(state: AgentState) -> dict[str, Any]:
            chunk = state["chunk"]
            user_message = HumanMessage(
                content=(
                    f"_extract_text({state['messages'][-1].content})\n\nChunk {chunk['chunk_id']} from {chunk['file_path']} (original lines {chunk['line_start']}-{chunk['line_end']}):\n" + chunk["content"]
                )
            )
            response, locations, retries = self._invoke_with_retries(
                invoke_client,
                client,
                [SystemMessage(content=system_prompt), user_message],
            )
            self.last_retried_chunks += 1 if retries else 0
            return {
                "messages": [response] if response else [],
                "locations": [location.model_dump() for location in locations],
            }

        def enrich(state: AgentState) -> dict[str, Any]:
            project_id = state.get("project_id") or default_project_id
            tools = tools_by_project.get(project_id, {})
            enriched: list[dict[str, Any]] = []
            for item in state.get("locations") or []:
                filename = item.get("filename")
                linenumber = item.get("linenumber")
                if (
                    isinstance(filename, str)
                    and isinstance(linenumber, int)
                    and not isinstance(linenumber, bool)
                ):
                    related = related_nodes_for_location(
                        tools, filename, linenumber
                    )
                else:
                    related = []
                enriched.append(
                    {
                        **item,
                        "relatednodes": [node.model_dump() for node in related],
                    }
                )
            return {"locations": enriched}

        graph = StateGraph(AgentState)
        graph.add_node("analyze", analyze)
        graph.add_node("enrich", enrich)
        graph.set_entry_point("analyze")
        graph.add_edge("analyze", "enrich")
        graph.add_edge("enrich", END)
        return graph.compile(checkpointer=self._checkpointer)

    @staticmethod
    def _permanent_error(error: Exception) -> bool:
        status = getattr(error, "status_code", None)
        if status is None:
            response = getattr(error, "response", None)
            status = getattr(response, "status_code", None)
        return status in {400, 401, 403, 404, 422}

    def _invoke_with_retries(self, structured_client, client, messages):
        retries = _int_setting(
            "FORGE_INVESTIGATION_MAX_RETRIES", DEFAULT_MAX_RETRIES, minimum=0
        )
        backoff = _float_setting(
            "FORGE_INVESTIGATION_RETRY_BACKOFF", DEFAULT_RETRY_BACKOFF
        )
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                request_messages = messages
                if attempt:
                    request_messages = list(messages)
                    original = request_messages[-1].content
                    if isinstance(original, str):
                        marker = "\n\nChunk "
                        marker_index = original.find(marker)
                        if marker_index >= 0:
                            prefix = original[: marker_index + len(marker)]
                            body = original[marker_index + len(marker):]
                            budget = max(512, int(len(body) * 0.6**attempt))
                            body = body[:budget] + (
                                "\n[Context shortened for retry; use available evidence only.]"
                            )
                            request_messages[-1] = HumanMessage(
                                content=prefix + body
                            )
                try:
                    response = structured_client.invoke(request_messages)
                except Exception:
                    response = client.invoke(request_messages)
                metadata = getattr(response, "response_metadata", {}) or {}
                finish_reason = metadata.get("finish_reason")
                if finish_reason in {"length", "max_tokens", "content_filter"}:
                    raise AgentResponseError(
                        f"Model response was incomplete ({finish_reason})."
                    )
                text = _extract_text(response.content if response else None)
                if not text:
                    raise AgentResponseError("Model response contained no text content.")
                return response, _parse_locations(text), attempt
            except Exception as error:
                if isinstance(error, InvestigationCancelled):
                    raise
                last_error = error
                if self._permanent_error(error) or attempt >= retries:
                    if isinstance(error, AgentResponseError):
                        raise
                    raise AgentResponseError(
                        f"Model invocation failed after {attempt} retry(s)."
                    ) from error
                time.sleep(backoff * (2**attempt) + random.uniform(0, backoff))
        raise AgentResponseError("Model invocation failed.") from last_error

    def find_violations(
        self,
        custom_security_violation_details: str,
        project_folder: str,
        session_id: str,
        context_files: set[str] | None = None,
        follow_up: bool = False,
        project_id: str | None = None,
        callbacks: list[Any] | None = None,
    ) -> list[ChatLocation]:
        """Map violation details to source locations for one session."""
        api_key = self._api_key()
        if not api_key:
            raise AgentConfigurationError(
                "META_MODEL_API_KEY is not set. Add your Meta Model API key "
                "to the .env file."
            )
        folder = Path(project_folder).expanduser()
        if not folder.is_dir():
            raise ProjectFolderError(
                f"Project folder does not exist: {project_folder}"
            )
        workspace, effective_project_id = _resolve_enrichment_context(
            folder, project_id
        )
        self.last_retried_chunks = 0
        tools = build_related_nodes_tools(workspace, effective_project_id)
        self.last_project_id = effective_project_id
        self.last_tool_names = [tool.name for tool in tools.values()]
        chunks, collection_failures = _collect_python_chunks(
            folder, allowed_paths=context_files
        )
        self.last_truncated = bool(collection_failures)
        self.last_incomplete = bool(collection_failures)
        self.last_chunk_stats = [
            {"chunk_id": chunk.chunk_id, "file_path": chunk.file_path, "status": "queued"}
            for chunk in chunks
        ]
        self.last_chunk_stats.extend(
            {"chunk_id": f"read-error-{index}", "file_path": error, "status": "failed"}
            for index, error in enumerate(collection_failures, start=1)
        )
        self.last_files_sent = len({chunk.file_path for chunk in chunks})
        self._graph = self._build_graph(
            api_key, {effective_project_id: tools}, effective_project_id
        )
        self._graph_key = api_key
        parts = [
            "Custom security violation to detect:",
            custom_security_violation_details,
            (
                "\nThis is a bounded follow-up analysis. Re-examine the supplied "
                "context and return only newly supported locations."
                if follow_up
                else ""
            ),
            f"\nPython project at {folder} ({self.last_files_sent} files, "
            f"{len(chunks)} bounded chunks):",
        ]
        details = "\n".join(parts)
        locations: list[ChatLocation] = []
        for index, chunk in enumerate(chunks):
            if callbacks:
                for callback in callbacks:
                    callback.recorder.check_cancelled()
            invoke_config: RunnableConfig = {
                "configurable": {"thread_id": f"{session_id}:{chunk.chunk_id}"},
            }
            if callbacks:
                invoke_config["callbacks"] = callbacks
            try:
                result = self._graph.invoke(
                    {
                        "messages": [HumanMessage(content=details)],
                        "locations": [],
                        "project_id": effective_project_id,
                        "chunk": {
                            "chunk_id": chunk.chunk_id,
                            "file_path": chunk.file_path,
                            "line_start": chunk.line_start,
                            "line_end": chunk.line_end,
                            "content": chunk.content,
                        },
                    },
                    config=invoke_config,
                )
                locations.extend(
                    ChatLocation.model_validate(item)
                    for item in (result.get("locations") or [])
                )
                self.last_chunk_stats[index]["status"] = "succeeded"
            except AgentResponseError as error:
                self.last_chunk_stats[index]["status"] = "failed"
                self.last_chunk_stats[index]["error"] = str(error)
                self.last_incomplete = True
        return locations
