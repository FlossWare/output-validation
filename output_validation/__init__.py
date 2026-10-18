"""output-validation -- Schema-validated JSON from LLMs with retries.

Zero required external dependencies.  ``jsonschema`` is used for full
JSON Schema validation when installed; a basic fallback validator is
provided otherwise.
"""

from __future__ import annotations

from output_validation.protocol import LLMBackend
from output_validation.structured_output import (
    StructuredOutputBackend,
    structured_output,
)
from output_validation.types import ChatMessage, ChatResponse, StructuredResponse
from output_validation.validation import (
    extract_json,
    normalize_parsed,
    try_parse_json,
    validate_schema,
)

__all__ = [
    "ChatMessage",
    "ChatResponse",
    "LLMBackend",
    "StructuredOutputBackend",
    "StructuredResponse",
    "structured_output",
    "extract_json",
    "normalize_parsed",
    "try_parse_json",
    "validate_schema",
]

__version__ = "0.2"
