"""Unit tests for the CodeFixAgent response parsing."""

import pytest

from app.services.codefixagent import (
    AgentResponseError,
    _parse_fixes,
)


def test_parse_fixes_accepts_bare_array() -> None:
    fixes = _parse_fixes('[{"filename": "a.py", "fixedCode": "x = 1\\n"}]')

    assert [(fix.filename, fix.fixedCode) for fix in fixes] == [("a.py", "x = 1\n")]


def test_parse_fixes_strips_code_fences() -> None:
    fixes = _parse_fixes(
        '```json\n[{"filename": "a.py", "fixedCode": "x = 1\\n"}]\n```'
    )

    assert [(fix.filename, fix.fixedCode) for fix in fixes] == [("a.py", "x = 1\n")]


def test_parse_fixes_accepts_fixed_code_variant() -> None:
    fixes = _parse_fixes('[{"filename": "a.py", "fixed_code": "x = 1\\n"}]')

    assert [(fix.filename, fix.fixedCode) for fix in fixes] == [("a.py", "x = 1\n")]


def test_parse_fixes_accepts_structured_wrapper() -> None:
    fixes = _parse_fixes(
        '{"fixes": [{"filename": "x.py", "fixedCode": "y = 2\\n"}]}'
    )

    assert [(fix.filename, fix.fixedCode) for fix in fixes] == [("x.py", "y = 2\n")]


def test_parse_fixes_accepts_empty_array() -> None:
    assert _parse_fixes("[]") == []


def test_parse_fixes_rejects_non_json() -> None:
    with pytest.raises(AgentResponseError):
        _parse_fixes("no fixes here")


def test_parse_fixes_rejects_bad_entries() -> None:
    with pytest.raises(AgentResponseError):
        _parse_fixes('[{"filename": "a.py"}]')


def test_parse_fixes_rejects_invalid_python() -> None:
    with pytest.raises(AgentResponseError):
        _parse_fixes('[{"filename": "a.py", "fixedCode": "def broken(:\\n"}]')
