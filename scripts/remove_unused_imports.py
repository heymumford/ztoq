#!/usr/bin/env python3
"""
Script to detect and remove unused imports in Python files.

This script helps identify and fix unused imports in Python files,
which is a common issue flagged by ruff (F401).
"""

import os
import re
import sys
from pathlib import Path


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


def analyze_imports(file_path: Path) -> tuple[set[str], set[str]]:
    """
    Analyze a Python file for unused imports.

    Returns:
        tuple of (all_imports, used_names)

    """
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Find all import statements
    import_pattern = r"^(?:from\s+\S+\s+import\s+(?:\S+(?:\s+as\s+\S+)?(?:,\s*\S+(?:\s+as\s+\S+)?)*|[^;]+)|import\s+(?:\S+(?:\s+as\s+\S+)?(?:,\s*\S+(?:\s+as\s+\S+)?)*))(?:\s*#.*)?\s*$"
    imports = re.findall(import_pattern, content, re.MULTILINE)

    imported_names = set()
    for imp in imports:
        if imp.startswith("from"):
            # Handle 'from module import name'
            match = re.match(r"from\s+\S+\s+import\s+(.*?)(?:\s*#.*)?$", imp)
            if match:
                names_str = match.group(1)
                for name_part_raw in names_str.split(","):
                    name_part = name_part_raw.strip()
                    if " as " in name_part:
                        _, alias = name_part.split(" as ")
                        imported_names.add(alias.strip())
                    else:
                        imported_names.add(name_part)
        else:
            # Handle 'import module'
            match = re.match(r"import\s+(.*?)(?:\s*#.*)?$", imp)
            if match:
                modules_str = match.group(1)
                for module_part_raw in modules_str.split(","):
                    module_part = module_part_raw.strip()
                    if " as " in module_part:
                        _, alias = module_part.split(" as ")
                        imported_names.add(alias.strip())
                    else:
                        imported_names.add(module_part.split(".")[0])

    # Find all used names
    used_names = set()
    # Remove strings to avoid false positives
    content_no_strings = re.sub(r'""".*?"""|\'\'\'.*?\'\'\'|".*?"|\'.*?\'', "", content, flags=re.DOTALL)

    # Check each imported name
    for name in imported_names:
        # Check for usage patterns (word boundaries to avoid partial matches)
        if re.search(rf"\b{re.escape(name)}\b", content_no_strings):
            used_names.add(name)

    return imported_names, used_names


def suggest_fixes(file_path: Path) -> None:
    """
    Analyze a file and suggest fixes for unused imports.
    """
    try:
        imported_names, used_names = analyze_imports(file_path)
        unused_names = imported_names - used_names

        if unused_names:
            print(f"\nIn {file_path}:")
            for name in unused_names:
                print(f"  - Unused import: {name}")
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")


def main() -> int:
    """Parse command line arguments and run the import analysis script."""
    min_args = 2
    if len(sys.argv) < min_args:
        print("Usage: python remove_unused_imports.py <directory>")
        return 1

    directory = sys.argv[1]
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        return 1

    python_files = find_python_files(directory)
    print(f"Found {len(python_files)} Python files to analyze")

    for file in python_files:
        suggest_fixes(file)

    print("\nComplete! Use 'ruff --fix' to automatically remove unused imports.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
