#!/usr/bin/env bash
# Helper script to run flake8 with our configuration focusing only on critical issues
# This script will run flake8 on the entire codebase and identify critical issues

cd "$(dirname "$0")/.." || exit

echo "Running flake8 on ztoq package (focusing on CRITICAL issues only)..."
echo "These issues should be fixed before committing:"
echo "  F401: imported but unused - remove unused imports"
echo "  F821: undefined name - fix undefined variables"
echo "  F841: local variable assigned but never used - remove or use variables"
echo "  E501: line too long - consider breaking long lines"
echo ""

poetry run flake8 ztoq/ --select=F401,F821,F841,E501

echo -e "\n=========================================\n"
echo "Running flake8 on tests (CRITICAL issues only)..."
poetry run flake8 tests/ --select=F401,F821,F841,E501