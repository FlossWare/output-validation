#!/usr/bin/env python3
"""Verify output-validation installation and run a quick smoke test."""
import sys


def main():
    try:
        from output_validation import (
            ChatMessage,
            ChatResponse,
            LLMBackend,
            StructuredOutputBackend,
            StructuredResponse,
            structured_output,
        )
    except ImportError as e:
        print(f"FAIL: Could not import output_validation: {e}")
        print("Install: pip install 'git+https://github.com/FlossWare/output-validation.git'")
        sys.exit(1)

    import output_validation

    print(f"output-validation v{output_validation.__version__} installed successfully")
    print(f"Exports: {len(output_validation.__all__)} public symbols")

    # Smoke test: StructuredResponse
    response = StructuredResponse(
        parsed={"answer": "42"},
        raw="The answer is 42",
        schema={"type": "object", "properties": {"answer": {"type": "string"}}},
    )
    print(f"Smoke test: StructuredResponse.parsed = {response.parsed}")

    # Smoke test: decorator exists and is callable
    assert callable(structured_output), "structured_output decorator must be callable"
    print("Smoke test: structured_output decorator is callable")

    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
