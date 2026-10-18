"""Structured-output backend wrapping any LLMBackend.

Adds schema-validated JSON output with automatic retries to any
existing ``LLMBackend`` implementation.  Satisfies the
``StructuredOutputMixin`` protocol via structural subtyping.

Optional dependency: ``jsonschema`` is used for full JSON Schema
validation when available; otherwise a basic dict-key check is used.

Zero required external dependencies beyond the standard library.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from output_validation.types import ChatMessage, ChatResponse, StructuredResponse

if TYPE_CHECKING:
    from output_validation.protocol import LLMBackend

# -- optional jsonschema import ---------------------------------------------

try:
    import jsonschema  # type: ignore[import-untyped]

    _HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore[assignment]
    _HAS_JSONSCHEMA = False


# -- helpers -----------------------------------------------------------------


from output_validation.validation import (
    extract_json,
    normalize_parsed,
    try_parse_json,
    validate_schema,
)

# Private aliases preserve internal imports while the public core lives in validation.py.
_extract_json = extract_json
_validate_schema = validate_schema
_try_parse_json = try_parse_json
_normalize_parsed = normalize_parsed


def _append_retry_messages(
    messages: list[ChatMessage],
    assistant_text: str,
    fix_prompt: str,
) -> None:
    """Append an assistant reply and a user fix-prompt to *messages*."""
    messages.append(ChatMessage(role="assistant", content=assistant_text))
    messages.append(ChatMessage(role="user", content=fix_prompt))


def _build_response(
    raw_text: str,
    parsed: Any | None,
    *,
    schema_valid: bool,
    retries_used: int,
) -> StructuredResponse:
    """Build a ``StructuredResponse`` from the given parts."""
    return StructuredResponse(
        content=raw_text,
        parsed=parsed,
        schema_valid=schema_valid,
        raw_text=raw_text,
        retries_used=retries_used,
    )


class StructuredOutputBackend:
    """Wraps any ``LLMBackend`` to add structured-output support.

    Parameters
    ----------
    backend:
        Any object satisfying the ``LLMBackend`` protocol.
    default_model:
        Model id passed to the underlying backend when callers do not
        specify one via ``**kwargs``.
    """

    def __init__(
        self,
        backend: LLMBackend,
        *,
        default_model: str | None = None,
    ) -> None:
        self._backend = backend
        self._default_model = default_model

    async def chat_structured(
        self,
        messages: list[ChatMessage],
        *,
        schema: dict | None = None,
        tools: list[dict] | None = None,
        response_format: str = "text",
        max_retries: int = 3,
        **kwargs: Any,
    ) -> StructuredResponse:
        """Send a chat completion request with structured output constraints.

        When *response_format* is ``"json"``, a system message is
        prepended instructing the model to respond with valid JSON.

        If *schema* is provided, each response is validated against it
        and retries are attempted (up to *max_retries*) with a fix
        prompt appended to the conversation.
        """
        _ = tools  # accepted for protocol compliance; not used here

        working_messages = list(messages)

        # Prepend a JSON instruction when response_format="json"
        if response_format == "json":
            json_instruction = ChatMessage(
                role="system",
                content=(
                    "You must respond with valid JSON only. "
                    "Do not include any text outside the JSON object."
                ),
            )
            working_messages = [json_instruction, *working_messages]

        model = kwargs.pop("model", self._default_model)
        temperature = kwargs.pop("temperature", 0.7)

        raw_text = ""
        retries_used = 0

        for attempt in range(1 + max_retries):
            response: ChatResponse = await self._backend.chat(
                working_messages,
                model=model,
                temperature=temperature,
            )
            raw_text = response.content

            parsed, parse_error = _try_parse_json(raw_text)

            if parse_error is not None:
                if attempt < max_retries:
                    retries_used += 1
                    _append_retry_messages(
                        working_messages,
                        raw_text,
                        "Your previous response was not valid JSON. "
                        "Please respond with valid JSON only.",
                    )
                    continue
                return _build_response(
                    raw_text, None, schema_valid=False, retries_used=retries_used
                )

            # If no schema, parsed JSON is good enough
            if schema is None:
                return _build_response(
                    raw_text,
                    _normalize_parsed(parsed),
                    schema_valid=True,
                    retries_used=retries_used,
                )

            # Validate against schema
            is_valid, error_msg = _validate_schema(parsed, schema)

            if is_valid:
                return _build_response(
                    raw_text,
                    _normalize_parsed(parsed),
                    schema_valid=True,
                    retries_used=retries_used,
                )

            # Schema validation failed -- retry with a fix prompt
            if attempt < max_retries:
                retries_used += 1
                _append_retry_messages(
                    working_messages,
                    raw_text,
                    "Your JSON response did not match the "
                    f"required schema. Error: {error_msg}. "
                    "Please fix and respond with valid JSON "
                    "matching the schema.",
                )
                continue

            # Exhausted retries with schema failure
            return _build_response(
                raw_text,
                _normalize_parsed(parsed),
                schema_valid=False,
                retries_used=retries_used,
            )

        # Should not reach here, but satisfy the type checker
        return _build_response(  # pragma: no cover
            raw_text, None, schema_valid=False, retries_used=retries_used
        )


# -- decorator (ADR-0006: Cross-Cutting Decorators) -------------------------


def structured_output(
    schema: dict | None = None,
    *,
    max_retries: int = 3,
) -> Callable:
    """Decorator that wraps an async LLM call with JSON schema validation.

    The decorated function must be an async callable that accepts
    ``messages: list[ChatMessage]`` and keyword arguments, and returns a
    ``ChatResponse``.  The decorator replaces the return type with
    ``StructuredResponse``, adding automatic JSON parsing, schema
    validation, and retry-with-correction on failure.

    This is a convenience wrapper around :class:`StructuredOutputBackend`
    that adheres to ADR-0006 (Cross-Cutting Decorators) -- structured
    output enforcement is applied explicitly via decorator opt-in.

    Parameters
    ----------
    schema:
        JSON Schema dict to validate against.  ``None`` skips validation
        and only requires valid JSON.
    max_retries:
        Maximum number of retry attempts when the model returns invalid
        JSON or JSON that does not match the schema.

    Example
    -------
    ::

        @structured_output(schema={"type": "object", "required": ["name"]})
        async def get_profile(messages, *, model=None, temperature=0.7, **kw):
            return ChatResponse(content=await call_llm(messages))

        result = await get_profile([ChatMessage(role="user", content="...")])
        assert result.schema_valid
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(
            messages: list[ChatMessage],
            **kwargs: Any,
        ) -> StructuredResponse:
            working_messages = list(messages)
            raw_text = ""
            retries_used = 0

            for attempt in range(1 + max_retries):
                response: ChatResponse = await fn(working_messages, **kwargs)
                raw_text = response.content

                parsed, parse_error = _try_parse_json(raw_text)

                if parse_error is not None:
                    if attempt < max_retries:
                        retries_used += 1
                        _append_retry_messages(
                            working_messages,
                            raw_text,
                            "Your previous response was not valid JSON. "
                            "Please respond with valid JSON only.",
                        )
                        continue
                    return _build_response(
                        raw_text,
                        None,
                        schema_valid=False,
                        retries_used=retries_used,
                    )

                if schema is None:
                    return _build_response(
                        raw_text,
                        _normalize_parsed(parsed),
                        schema_valid=True,
                        retries_used=retries_used,
                    )

                is_valid, error_msg = _validate_schema(parsed, schema)

                if is_valid:
                    return _build_response(
                        raw_text,
                        _normalize_parsed(parsed),
                        schema_valid=True,
                        retries_used=retries_used,
                    )

                if attempt < max_retries:
                    retries_used += 1
                    _append_retry_messages(
                        working_messages,
                        raw_text,
                        "Your JSON response did not match the "
                        f"required schema. Error: {error_msg}. "
                        "Please fix and respond with valid JSON "
                        "matching the schema.",
                    )
                    continue

                return _build_response(
                    raw_text,
                    _normalize_parsed(parsed),
                    schema_valid=False,
                    retries_used=retries_used,
                )

            return _build_response(  # pragma: no cover
                raw_text, None, schema_valid=False, retries_used=retries_used
            )

        return wrapper

    return decorator
