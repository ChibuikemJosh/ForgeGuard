"""LangGraph agent mapping custom security violations to source locations.

The agent follows ``system_instructions_validatoragent.md``: it sends the
custom violation details plus the Python files of the project folder to the
Meta Model API and parses the returned violations into filename/line pairs.
Per-session context is retained via a LangGraph checkpointer keyed by the
caller-provided session identifier.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from pydantic import SecretStr

from app.schemas.chat import ChatLocation

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

SYSTEM_INSTRUCTIONS_PATH = Path(__file__).with_name(
    "system_instructions_validatoragent.md"
)
DEFAULT_MODEL = "muse-spark-1.3"
DEFAULT_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MAX_FILES = 100
DEFAULT_MAX_TOTAL_CHARS = 400_000
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


def _investigation_limits() -> tuple[int, int]:
    """Max Python files and total source chars sent to the model per investigation."""
    try:
        max_files = int(os.environ.get("FORGE_INVESTIGATION_MAX_FILES", str(DEFAULT_MAX_FILES)))
    except ValueError:
        max_files = DEFAULT_MAX_FILES
    try:
        max_chars = int(os.environ.get("FORGE_INVESTIGATION_MAX_CHARS", str(DEFAULT_MAX_TOTAL_CHARS)))
    except ValueError:
        max_chars = DEFAULT_MAX_TOTAL_CHARS
    return max(1, max_files), max(1, max_chars)


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


def _is_visible(path: Path, root: Path) -> bool:
    return not any(
        part.startswith(".") or part in SKIPPED_DIR_NAMES
        for part in path.relative_to(root).parts[:-1]
    )


def _collect_python_files(folder: Path) -> tuple[list[tuple[str, str]], bool]:
    """Return [(relative path, content)] for Python files, plus truncated flag."""
    keywords = ("route", "api", "view", "controller", "endpoint", "service", "auth", "handler", "model")
    candidates = sorted(
        (p for p in folder.rglob("*.py") if p.is_file() and _is_visible(p, folder)),
        key=lambda p: (
            0 if any(k in p.relative_to(folder).as_posix().lower() for k in keywords) else 1,
            p.relative_to(folder).as_posix().lower(),
        ),
    )
    max_files, max_total_chars = _investigation_limits()
    collected: list[tuple[str, str]] = []
    total_chars = 0
    truncated = len(candidates) > max_files
    for path in candidates[:max_files]:
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if total_chars + len(content) > max_total_chars:
            truncated = True
            break
        collected.append((path.relative_to(folder).as_posix(), content))
        total_chars += len(content)
    return collected, truncated


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
        self.last_truncated: bool = False
        self.last_files_sent: int = 0

    @staticmethod
    def _api_key() -> str:
        return os.environ.get("META_MODEL_API_KEY", "").strip()

    @staticmethod
    def _system_prompt() -> str:
        instructions = SYSTEM_INSTRUCTIONS_PATH.read_text(encoding="utf-8")
        return f"{instructions}\n\n{RESPONSE_FORMAT}"

    def _build_graph(self, api_key: str):
        client = ChatOpenAI(
            model=self._model,
            base_url=self._base_url,
            api_key=SecretStr(api_key),
            timeout=90.0,
        )
        try:
            invoke_client = client.bind(response_format=STRUCTURED_OUTPUT_FORMAT)
        except Exception:
            invoke_client = client
        system_prompt = self._system_prompt()

        def analyze(state: AgentState) -> dict[str, Any]:
            try:
                response = invoke_client.invoke(
                    [SystemMessage(content=system_prompt)] + state["messages"]
                )
            except Exception:
                # Structured output may be unsupported by a compatible endpoint;
                # retry once unbound and rely on _parse_locations.
                try:
                    response = client.invoke(
                        [SystemMessage(content=system_prompt)] + state["messages"]
                    )
                except Exception as error:
                    raise AgentResponseError(f"Model invocation failed: {error}") from error
            text = _extract_text(response.content if response else None)
            if not text:
                raise AgentResponseError("Model response contained no text content.")
            locations = _parse_locations(text)
            return {
                "messages": [response] if response else [],
                "locations": [location.model_dump() for location in locations],
            }

        graph = StateGraph(AgentState)
        graph.add_node("analyze", analyze)
        graph.set_entry_point("analyze")
        graph.add_edge("analyze", END)
        return graph.compile(checkpointer=MemorySaver())

    def find_violations(
        self,
        custom_security_violation_details: str,
        project_folder: str,
        session_id: str,
        callbacks: list | None = None,
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
        files, truncated = _collect_python_files(folder)
        self.last_truncated = truncated
        self.last_files_sent = len(files)
        if self._graph is None or self._graph_key != api_key:
            self._graph = self._build_graph(api_key)
            self._graph_key = api_key
        parts = [
            "Custom security violation to detect:",
            custom_security_violation_details,
            f"\nPython project at {folder} ({len(files)} files shown"
            + ("; listing truncated" if truncated else "")
            + "):",
        ]
        for filename, content in files:
            parts.append(f"\n--- File: {filename} ---\n{content}")
        result = self._graph.invoke(
            {
                "messages": [HumanMessage(content="\n".join(parts))],
                "locations": [],
            },
            config={"configurable": {"thread_id": session_id}, **({"callbacks": callbacks} if callbacks else {})},
        )
        return [
            ChatLocation.model_validate(item)
            for item in (result.get("locations") or [])
        ]
