#!/usr/bin/env bash
# Helper script to run flake8 with our configuration
# This script will run flake8 on the entire codebase and help identify issues

cd "$(dirname "$0")/.." || exit

echo "Running flake8 on ztoq package (common style issues are ignored)..."
echo "See .flake8 for configuration settings"
poetry run flake8 ztoq/

echo -e "\n=========================================\n"
echo "Running flake8 on tests..."
poetry run flake8 tests/

echo -e "\n=========================================\n"
echo "To check a specific file, run:"
echo "poetry run flake8 path/to/file.py"