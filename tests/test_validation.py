"""Tests for backend-independent output validation primitives."""

from __future__ import annotations

from output_validation import extract_json, try_parse_json, validate_schema


def test_extract_json_from_markdown_fence() -> None:
    assert extract_json(' ```json\n{"ok": true}\n``` ') == '{"ok": true}'


def test_parse_json_returns_value_and_no_error() -> None:
    parsed, error = try_parse_json('{"answer": 42}')
    assert parsed == {"answer": 42}
    assert error is None


def test_parse_json_reports_invalid_input() -> None:
    parsed, error = try_parse_json("not json")
    assert parsed is None
    assert error


def test_schema_validation_checks_required_keys() -> None:
    valid, error = validate_schema({"answer": 42}, {
        "type": "object",
        "properties": {"answer": {"type": "integer"}},
        "required": ["answer"],
    })
    assert valid
    assert error == ""
