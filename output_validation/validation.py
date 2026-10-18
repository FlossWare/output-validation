"""Backend-independent parsing, normalization, and schema validation."""

from __future__ import annotations

import json
from typing import Any

# Optional dependency. The fallback intentionally provides only basic validation.
try:
    import jsonschema  # type: ignore[import-untyped]

    _HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]
    _HAS_JSONSCHEMA = False


def extract_json(text: str) -> str:
    """Extract a JSON object or array from *text*.

    Handles the common case where models wrap JSON in a Markdown
    code fence (````json ... ````).  Falls back to returning *text*
    unchanged so ``json.loads`` can attempt parsing directly.
    """
    stripped = text.strip()

    # Strip markdown code fences
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # Remove opening fence (```json or ```)
        lines = lines[1:]
        # Remove closing fence if present
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    return stripped


def validate_schema(parsed: Any, schema: dict) -> tuple[bool, str]:
    """Validate *parsed* against *schema*.

    Returns ``(is_valid, error_message)``.  Uses ``jsonschema`` when
    available; otherwise checks that all ``required`` keys are present
    and all ``properties`` keys are a subset of the parsed dict.
    """
    if _HAS_JSONSCHEMA:
        try:
            jsonschema.validate(instance=parsed, schema=schema)
            return True, ""
        except (jsonschema.ValidationError, jsonschema.SchemaError) as exc:
            return False, str(exc.message)

    # Fallback: basic type + key checking
    schema_type = schema.get("type")
    if schema_type == "object" and not isinstance(parsed, dict):
        return False, f"Expected object, got {type(parsed).__name__}"
    if schema_type == "array" and not isinstance(parsed, list):
        return False, f"Expected array, got {type(parsed).__name__}"

    if not isinstance(parsed, dict):
        return True, ""

    required = schema.get("required", [])
    properties = schema.get("properties", {})

    missing = [k for k in required if k not in parsed]
    if missing:
        return False, f"Missing required keys: {missing}"

    if properties:
        extra = [k for k in parsed if k not in properties]
        if extra and schema.get("additionalProperties") is False:
            return False, f"Unexpected keys: {extra}"

    return True, ""


def try_parse_json(raw_text: str) -> tuple[Any, str | None]:
    """Extract and parse JSON from *raw_text*.

    Returns ``(parsed_value, error_message)``.  On success,
    *error_message* is ``None``.  On failure, *parsed_value* is ``None``
    and *error_message* describes the parse error.
    """
    try:
        extracted = extract_json(raw_text)
        return json.loads(extracted), None
    except ValueError as exc:
        return None, str(exc)


def normalize_parsed(parsed: Any) -> dict | list | Any:
    """Return parsed value as-is; dicts and lists pass through directly."""
    return parsed

__all__ = ["extract_json", "normalize_parsed", "try_parse_json", "validate_schema"]
