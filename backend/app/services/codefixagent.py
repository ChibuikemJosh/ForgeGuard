"""LangGraph agent generating fixed Python code for custom security violations.

The agent follows ``system_instructions_codefixagent.md``: it sends the
custom security violation details plus the contents of the given Python
files to the Meta Model API and parses the returned fixes into
filename/fixedCode pairs.
"""

from __future__ import annotations

import ast
import json
import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from pydantic import SecretStr

from app.schemas.fix import FixResult

load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

SYSTEM_INSTRUCTIONS_PATH = Path(__file__).with_name(
    "system_instructions_codefixagent.md"
)
DEFAULT_MODEL = "muse-spark-1.3"
DEFAULT_BASE_URL = "https://api.meta.ai/v1"
MAX_FILES = 50
MAX_TOTAL_CHARS = 200_000

RESPONSE_FORMAT = """# Response format
Respond with ONLY a JSON array, no other text:
[{"filename": "<path as given>", "fixedCode": "<full corrected file content>"}]
Example: [{"filename": "routes/orders.py", "fixedCode": "from fastapi import APIRouter\\n"}]
If no fix is needed, respond with: []"""

STRUCTURED_OUTPUT_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "fixes",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "fixes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "fixedCode": {"type": "string"},
                        },
                        "required": ["filename", "fixedCode"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["fixes"],
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


class FixFileError(ValueError):
    """A requested file is missing or unreadable."""


class AgentResponseError(RuntimeError):
    """The model response could not be parsed into fixes."""


class AgentState(MessagesState):
    fixes: list[dict[str, Any]]


def _parse_fixes(raw: str) -> list[FixResult]:
    """Parse model output into validated fixes.

    Accepts a bare JSON array (optionally fenced), a dict wrapping the
    array, a single fix object, and ``fixed_code``/``fixedcode`` key variants.
    Every fixed file must be non-empty, valid Python.
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
        for key in ("fixes", "violations", "locations", "results"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            data = [data]
    if not isinstance(data, list):
        raise AgentResponseError("Model response was not a JSON array.")
    fixes = []
    for item in data:
        if not isinstance(item, dict):
            raise AgentResponseError(f"Invalid fix entry: {item!r}")
        fixed = item.get(
            "fixedCode",
            item.get(
                "fixed_code",
                item.get("fixedcode", item.get("proposed_content", item.get("content"))),
            ),
        )
        try:
            fix = FixResult.model_validate(
                {"filename": item.get("filename"), "fixedCode": fixed}
            )
        except (ValueError, TypeError) as error:
            raise AgentResponseError(
                f"Invalid fix entry: {item!r}"
            ) from error
        try:
            ast.parse(fix.fixedCode)
        except SyntaxError as error:
            raise AgentResponseError(
                f"Fix for {fix.filename!r} is not valid Python: {error}"
            ) from error
        fixes.append(fix)
    return fixes


class CodeFixAgent:
    """LangGraph agent fixing violations via the Meta Model API."""

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
        self.last_truncated = False
        self.last_file_count = 0

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

        def fix(state: AgentState) -> dict[str, Any]:
            try:
                response = invoke_client.invoke(
                    [SystemMessage(content=system_prompt)] + state["messages"]
                )
            except Exception:
                # Structured output may be unsupported by a compatible endpoint;
                # retry once unbound and rely on _parse_fixes.
                try:
                    response = client.invoke(
                        [SystemMessage(content=system_prompt)] + state["messages"]
                    )
                except Exception as error:
                    raise AgentResponseError(f"Model invocation failed: {error}") from error
            text = _extract_text(response.content if response else None)
            if not text:
                raise AgentResponseError("Model response contained no text content.")
            fixes = _parse_fixes(text)
            return {
                "messages": [response] if response else [],
                "fixes": [fix_result.model_dump() for fix_result in fixes],
            }

        graph = StateGraph(AgentState)
        graph.add_node("fix", fix)
        graph.set_entry_point("fix")
        graph.add_edge("fix", END)
        return graph.compile(checkpointer=MemorySaver())

    def fix_violations(
        self,
        customviolation: str,
        filenames: list[str],
    ) -> list[FixResult]:
        """Return fixed code for the given files and custom violation."""
        api_key = self._api_key()
        if not api_key:
            raise AgentConfigurationError(
                "META_MODEL_API_KEY is not set. Add your Meta Model API key "
                "to the .env file."
            )
        if not customviolation or not customviolation.strip():
            raise FixFileError("customviolation must be a non-empty string.")
        if not filenames:
            self.last_truncated = False
            self.last_file_count = 0
            return []
        files: list[tuple[str, str]] = []
        total_chars = 0
        truncated = len(filenames) > MAX_FILES
        for name in filenames[:MAX_FILES]:
            path = Path(name).expanduser()
            if not path.is_file():
                raise FixFileError(f"File does not exist: {name}")
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                raise FixFileError(f"File cannot be read: {name} ({error})") from error
            if total_chars + len(content) > MAX_TOTAL_CHARS:
                truncated = True
                break
            files.append((name, content))
            total_chars += len(content)
        self.last_truncated = truncated
        self.last_file_count = len(files)
        if self._graph is None or self._graph_key != api_key:
            self._graph = self._build_graph(api_key)
            self._graph_key = api_key
        parts = [
            "Custom security violation to fix:",
            customviolation.strip(),
            f"\nPython files to fix ({len(files)} files shown"
            + ("; listing truncated" if truncated else "")
            + "); return the FULL corrected content of each file:",
        ]
        for filename, content in files:
            parts.append(f"\n--- File: {filename} ---\n{content}")
        result = self._graph.invoke(
            {
                "messages": [HumanMessage(content="\n".join(parts))],
                "fixes": [],
            },
            config={"configurable": {"thread_id": uuid.uuid4().hex}},
        )
        return [
            FixResult.model_validate(item)
            for item in (result.get("fixes") or [])
        ]
