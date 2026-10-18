#!/bin/bash
# Add output-validation integration to your CLAUDE.md
set -e

CLAUDE_MD="${CLAUDE_MD:-./CLAUDE.md}"

if [ ! -f "$CLAUDE_MD" ]; then
    echo "Creating $CLAUDE_MD"
    touch "$CLAUDE_MD"
fi

cat >> "$CLAUDE_MD" << 'EOF'

## Structured Output (output-validation)

This project uses [output-validation](https://github.com/FlossWare/output-validation) for type-safe LLM responses.

**Install:** `pip install "git+https://github.com/FlossWare/output-validation.git"`

**Key imports:**
```python
from output_validation import structured_output, StructuredOutputBackend, StructuredResponse
```

**Usage patterns:**
- Decorator: `@structured_output(schema={...})` to auto-parse LLM responses
- Backend wrapper: `StructuredOutputBackend(backend, default_schema=schema)`
- Response: `StructuredResponse` with `.parsed` (typed dict) and `.raw` (original)
- Zero external dependencies (stdlib only)
EOF

echo "Added output-validation integration to $CLAUDE_MD"
