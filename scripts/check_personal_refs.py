#!/usr/bin/env python3
"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.

"""

"""
Script to check for personal directory references in the codebase.

This script scans the codebase for references to personal home directories
that could cause portability issues. It excludes certain directories and
only checks specific file types.

Usage:
    python scripts/check_personal_refs.py

Returns:
    Exit code 0 if no personal directory references are found.
    Exit code 1 if personal directory references are found.
"""

import getpass
import os
import re
import sys
from pathlib import Path


def main() -> int:
    """
    Scan the project for personal directory references.

    Returns:
        int: 0 if no personal references are found, 1 otherwise

    """
    # Get project root
    root_dir = Path(__file__).parent.parent.absolute()
    print(f"Scanning directory: {root_dir}")

    # Define patterns to search for
    current_user = getpass.getuser()
    personal_reference_pattern = re.compile(rf"/home/{current_user}")

    # Define directories to exclude from the search
    excluded_dirs = {
        ".git",
        ".pytest_cache",
        "__pycache__",
        "venv",
        "build",
        "dist",
        "*.egg-info",
        "testenv",
        "docenv",
        ".venv",
    }

    # Define file extensions to check
    valid_extensions = {
        ".py",
        ".md",
        ".rst",
        ".yml",
        ".yaml",
        ".ini",
        ".toml",
        ".sh",
        ".txt",
        ".css",
        ".js",
        ".html",
        ".json",
        ".cfg",
        ".in",
        ".bat",
        ".mako",
    }

    # Keep track of files with personal references
    files_with_references = []

    # Pattern to exclude this file and the test file that checks for references
    exclude_files = ["scripts/check_personal_refs.py", "tests/unit/test_project_structure.py"]

    # Walk through the project directory
    print("Checking files...")
    files_checked = 0

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip excluded directories
        dirnames[:] = [d for d in dirnames if d not in excluded_dirs and not d.startswith(".")]

        # Check each file
        for filename in filenames:
            if any(pattern in filename for pattern in ["*", "?"]):
                continue  # Skip files with glob patterns in name

            file_path = Path(dirpath) / filename
            rel_path = file_path.relative_to(root_dir)

            # Skip excluded files
            if any(str(rel_path) == excl for excl in exclude_files):
                continue

            # Skip files with extensions we don't care about
            if file_path.suffix.lower() not in valid_extensions:
                continue

            if not file_path.exists() or not file_path.is_file():
                continue

            try:
                # Skip if file is too large (binary files or other non-text files)
                if file_path.stat().st_size > 1_000_000:  # Skip files > 1MB
                    continue

                files_checked += 1

                # Read file content
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Check for personal directory reference pattern
                if personal_reference_pattern.search(content):
                    files_with_references.append(str(rel_path))
            except Exception as e:
                # Skip files that can't be read as text
                print(f"Error reading file {rel_path}: {e}")
                continue

    # Print the results
    print(f"Checked {files_checked} files.")

    if files_with_references:
        print(f"\nFOUND PERSONAL DIRECTORY REFERENCES in {len(files_with_references)} files:")
        for file in files_with_references:
            print(f"  - {file}")
        return 1

    print("\nNo personal directory references found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
