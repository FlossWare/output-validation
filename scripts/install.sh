#!/bin/bash
# Install output-validation from GitHub
set -e

pip install "git+https://github.com/FlossWare/output-validation.git"

echo "output-validation installed successfully"
echo "Verify: python3 -c 'import output_validation; print(output_validation.__version__)'"
