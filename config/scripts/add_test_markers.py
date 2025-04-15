#!/usr/bin/env python3
"""
Script to add pytest markers to test files based on their location in the test directory structure.
This ensures all tests follow the test pyramid structure and can be properly categorized and filtered.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Constants
TEST_DIR = Path(__file__).parent.parent / "tests"
UNIT_DIR = TEST_DIR / "unit"
INTEGRATION_DIR = TEST_DIR / "integration"
SYSTEM_DIR = TEST_DIR / "system"


def get_test_files(directory: Path) -> List[Path]:
    """Get all Python test files in a directory."""
    if not directory.exists():
        print(f"Warning: Directory {directory} does not exist")
        return []

    # Find all Python files that start with test_
    return list(directory.glob("test_*.py"))


def check_file_for_marker(file_path: Path, marker: str) -> bool:
    """Check if a file already has a specific pytest marker."""
    with open(file_path, "r") as f:
        content = f.read()

    # Check for the marker in the file
    return f"@pytest.mark.{marker}" in content


def add_marker_to_file(file_path: Path, marker: str) -> bool:
    """Add a pytest marker to a test file if it doesn't already have it."""
    with open(file_path, "r") as f:
        content = f.read()

    # Check if pytest is already imported
    has_pytest_import = "import pytest" in content or "from pytest import" in content

    # Check if the file already has the marker
    if f"@pytest.mark.{marker}" in content:
        print(f"File {file_path} already has marker {marker}")
        return False

    # Identify test class definitions and function definitions
    class_pattern = r'class\s+Test[A-Za-z0-9_]+\(.*\):'
    function_pattern = r'def\s+test_[A-Za-z0-9_]+\(.*\):'

    # Add import if needed
    if not has_pytest_import:
        # Find the right place to add import
        import_section_end = 0
        for match in re.finditer(r'(?:^|\n)(?:import|from)\s+[A-Za-z0-9_.]+(?:\s+import|\s+as)?\s+.*?(?:\n|$)', content):
            end = match.end()
            if end > import_section_end:
                import_section_end = end

        # If we found imports, add after them
        if import_section_end > 0:
            content = content[:import_section_end] + "\nimport pytest" + content[import_section_end:]
        else:
            # Add after docstrings if any
            docstring_pattern = r'""".*?"""'
            docstring_matches = list(re.finditer(docstring_pattern, content, re.DOTALL))

            if docstring_matches:
                content = content[:docstring_matches[-1].end()] + "\n\nimport pytest" + content[docstring_matches[-1].end():]
            else:
                # Add at the beginning
                content = "import pytest\n\n" + content

    # Find all test classes and add the marker
    modified = False
    class_matches = list(re.finditer(class_pattern, content))

    if class_matches:
        # Handle unittest-style test classes
        for match in reversed(class_matches):  # Process from bottom to top to avoid messing up offsets
            # Add the marker before the class definition
            pos = match.start()
            indentation = ""
            line_start = content.rfind("\n", 0, pos) + 1
            if line_start > 0:
                # Get indentation from the previous line
                indent_match = re.match(r'^(\s*)', content[line_start:pos])
                if indent_match:
                    indentation = indent_match.group(1)

            # Add the marker before the class
            content = content[:pos] + f"{indentation}@pytest.mark.{marker}\n{indentation}" + content[pos:]
            modified = True
    else:
        # Handle pytest-style test functions
        function_matches = list(re.finditer(function_pattern, content))

        for match in reversed(function_matches):  # Process from bottom to top
            pos = match.start()
            indentation = ""
            line_start = content.rfind("\n", 0, pos) + 1
            if line_start > 0:
                indent_match = re.match(r'^(\s*)', content[line_start:pos])
                if indent_match:
                    indentation = indent_match.group(1)

            # Make sure we're not adding a marker to a method inside a class
            prev_class_match = None
            for class_match in class_matches:
                if class_match.start() < pos:
                    prev_class_match = class_match

            if not prev_class_match or (prev_class_match and "\nclass " in content[prev_class_match.end():pos]):
                # Add the marker before the function
                content = content[:pos] + f"{indentation}@pytest.mark.{marker}\n{indentation}" + content[pos:]
                modified = True

    if modified:
        with open(file_path, "w") as f:
            f.write(content)
        print(f"Added marker {marker} to {file_path}")
        return True

    print(f"No changes made to {file_path}")
    return False


def process_directory(directory: Path, marker: str) -> Tuple[int, int]:
    """Process all test files in a directory, adding the specified marker if needed."""
    test_files = get_test_files(directory)
    total = len(test_files)
    modified = 0

    for file_path in test_files:
        if add_marker_to_file(file_path, marker):
            modified += 1

    return total, modified


def main() -> int:
    """Main function."""
    # Process each test directory with appropriate marker
    print("Processing test directories...")

    # Unit tests
    unit_total, unit_modified = process_directory(UNIT_DIR, "unit")
    print(f"Processed {unit_total} unit test files, modified {unit_modified}")

    # Integration tests
    integration_total, integration_modified = process_directory(INTEGRATION_DIR, "integration")
    print(f"Processed {integration_total} integration test files, modified {integration_modified}")

    # System tests
    system_total, system_modified = process_directory(SYSTEM_DIR, "system")
    print(f"Processed {system_total} system test files, modified {system_modified}")

    total = unit_total + integration_total + system_total
    modified = unit_modified + integration_modified + system_modified

    print(f"\nTotal: {total} test files processed, {modified} files modified")

    return 0


if __name__ == "__main__":
    sys.exit(main())
