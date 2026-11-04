"""Unit tests for the ViolationsFinderAgent response parsing."""

import pytest
from pathlib import Path

from app.services.violations_finder_agent import (
    AgentResponseError,
    _collect_python_chunks,
    _parse_locations,
)


def test_parse_locations_accepts_bare_array() -> None:
    locations = _parse_locations('[{"filename": "a.py", "linenumber": 3}]')

    assert [(loc.filename, loc.linenumber) for loc in locations] == [("a.py", 3)]


def test_parse_locations_strips_code_fences() -> None:
    locations = _parse_locations(
        '```json\n[{"filename": "a.py", "linenumber": 3}]\n```'
    )

    assert [(loc.filename, loc.linenumber) for loc in locations] == [("a.py", 3)]


def test_parse_locations_accepts_line_number_variant() -> None:
    locations = _parse_locations('[{"filename": "a.py", "line_number": "7"}]')

    assert [(loc.filename, loc.linenumber) for loc in locations] == [("a.py", 7)]


def test_parse_locations_accepts_empty_array() -> None:
    assert _parse_locations("[]") == []


def test_parse_locations_rejects_non_json() -> None:
    with pytest.raises(AgentResponseError):
        _parse_locations("no violations here")


def test_parse_locations_rejects_bad_entries() -> None:
    with pytest.raises(AgentResponseError):
        _parse_locations('[{"filename": "a.py"}]')


def test_extract_text_from_string_and_blocks():
    from app.services.violations_finder_agent import _extract_text

    assert _extract_text("hello") == "hello"
    assert _extract_text([{"type": "text", "text": '{"violations": []}'}, {"type": "reasoning", "text": "skip"}]) == '{"violations": []}'
    # reasoning-only blocks are ignored (type != text); text blocks join
    assert _extract_text([{"type": "text", "text": "a"}, "b"]) == "ab"


def test_parse_locations_accepts_structured_wrapper():
    locations = _parse_locations('{"violations": [{"filename": "x.py", "linenumber": 2}]}')
    assert [(loc.filename, loc.linenumber) for loc in locations] == [("x.py", 2)]


def test_large_python_file_is_split_without_losing_original_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = "\n".join(
        [f"def function_{index}():\n    return {index}" for index in range(40)]
    )
    path = tmp_path / "large.py"
    path.write_text(source, encoding="utf-8")
    monkeypatch.setenv("FORGE_INVESTIGATION_CHUNK_CHARS", "180")
    chunks, failures = _collect_python_chunks(tmp_path)

    assert not failures
    assert len(chunks) > 1
    assert {chunk.file_path for chunk in chunks} == {"large.py"}
    assert min(chunk.line_start for chunk in chunks) == 1
    assert max(chunk.line_end for chunk in chunks) == len(source.splitlines())


def test_retry_recovers_from_malformed_model_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from langchain_core.messages import AIMessage
    from app.services import violations_finder_agent as module

    (tmp_path / "one.py").write_text("def check():\n    return True\n", encoding="utf-8")
    monkeypatch.setenv("META_MODEL_API_KEY", "test-key")
    monkeypatch.setenv("FORGE_INVESTIGATION_MAX_RETRIES", "1")
    monkeypatch.setenv("FORGE_INVESTIGATION_MAX_FOLLOW_UP_ROUNDS", "0")

    class RetryModel:
        calls = 0

        def __init__(self, *args, **kwargs):
            pass

        def bind(self, *args, **kwargs):
            return self

        def invoke(self, messages):
            self.calls += 1
            payload = "not json" if self.calls == 1 else '{"violations": []}'
            return AIMessage(content=payload)

    monkeypatch.setattr(module, "ChatOpenAI", RetryModel)
    agent = module.ViolationsFinderAgent()
    assert agent.find_violations("check rule", str(tmp_path), "retry-test") == []
    assert agent.last_retried_chunks == 1
