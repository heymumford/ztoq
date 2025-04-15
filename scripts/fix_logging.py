#!/usr/bin/env python3
"""
Script to fix logging format issues in Python files.

This script helps convert f-string logging calls (G004) to use proper string formatting.
"""

import os
import re
import sys
from pathlib import Path

LOGGING_PATTERN = r'(logging\.\w+)\(f["\'](.+?)["\'](.*)\)'


def find_python_files(directory: str) -> list[Path]:
    """Find all Python files in the specified directory and its subdirectories."""
    python_files = []
    exclude_dirs = {
        ".git", "__pycache__", "venv", ".venv", "build", "dist",
        ".pytest_cache", ".mypy_cache", ".ruff_cache",
    }

    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    return python_files


def fix_logging_fstrings(file_path: Path) -> int:
    """
    Fix f-string logging calls in a file.

    Returns:
        The number of fixes made

    """
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Find all logging calls with f-strings
    matches = re.findall(LOGGING_PATTERN, content)
    if not matches:
        return 0

    fixes_made = 0
    new_content = content

    for logging_method, message, args in matches:
        # Extract variables from the f-string
        var_pattern = r"{([^{}:]*)(?::[^{}]*)?}"
        variables = re.findall(var_pattern, message)

        if variables:
            # Replace f-string with %-formatting
            new_message = re.sub(var_pattern, "%s", message)
            new_args = f', {", ".join(variables)}{args}'

            # Create the new logging call
            old_call = f'{logging_method}(f"{message}"{args})'
            new_call = f'{logging_method}("{new_message}"{new_args})'

            new_content = new_content.replace(old_call, new_call)
            fixes_made += 1

    if fixes_made > 0:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Fixed {fixes_made} logging calls in {file_path}")

    return fixes_made


def main() -> int:
    """Parse command line arguments and run the logging fix script."""
    min_args = 2
    if len(sys.argv) < min_args:
        print("Usage: python fix_logging.py <directory>")
        return 1

    directory = sys.argv[1]
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        return 1

    python_files = find_python_files(directory)
    print(f"Found {len(python_files)} Python files to analyze")

    total_fixes = 0
    for file in python_files:
        total_fixes += fix_logging_fstrings(file)

    print(f"\nComplete! Fixed {total_fixes} logging calls.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
