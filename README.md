# output-validation

**Reusable structured-output validation and normalization for FlossWare.**

This repository validates model responses against schemas, normalizes valid results into predictable representations, and provides bounded handling for malformed or non-conforming output.

## Architectural boundary

Output validation is a **result-contract capability**, not a model backend or orchestration layer.

- `model-gateway` owns provider/model invocation and provider-specific structured-generation mechanisms.
- `output-validation` owns schema validation, parsing/normalization, and validation evidence.
- `evaluation` assesses whether a result satisfies the requested outcome.
- `loom-ai` owns Workers, Arbiters, task-level retries/replanning, execution, and orchestration.

```text
Worker -> model-gateway -> output-validation -> validated result
                                  |
                                  v
                           validation evidence
```

Provider-specific structured-generation features should be adapted by `model-gateway`. This repository provides reusable validation behavior that can also be consumed outside Loom.

## Scope

- Schema-based validation of structured model output
- Parsing and normalization into predictable result representations
- Clear validation failures and supporting evidence
- Bounded repair/retry behavior where explicitly configured
- Transport-independent contracts and tests

Validation must not silently turn invalid output into a successful result. Any repair or retry should be bounded, observable, and distinguish the original response from the accepted result.

## Current implementation and migration note

The existing `structured_output_ai` package exports `StructuredOutputBackend`, `LLMBackend`, and the `structured_output` decorator. That API combines a backend-facing adapter with output extraction and validation; it is not yet a pure, backend-independent validator in every code path. The intended boundary above remains the target architecture, not a claim that all legacy coupling has already been removed.

Keep this capability independently reusable and free of agent-runtime assumptions. Repository-level documentation and links use `output-validation`. The distribution name (`structured-output-ai`) and import package (`structured_output_ai`) remain legacy identifiers for now; changing them requires an explicit compatibility and release decision.

## License

MIT
