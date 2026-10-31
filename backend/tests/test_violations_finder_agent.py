"""Unit tests for the ViolationsFinderAgent response parsing."""

import pytest

from app.services.violations_finder_agent import (
    AgentResponseError,
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

