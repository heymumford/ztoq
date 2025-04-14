#!/usr/bin/env python3
"""
Script to add license headers to Python files and footers to Markdown files.

This script automatically adds MIT license headers to all Python source files
and license footers to all Markdown documentation files in the project.
It handles both code files and documentation files differently:
- Python files: Adds a license header at the top of the file
- Markdown files: Adds a license footer at the bottom of the file

Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import os

PYTHON_HEADER = '''"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

'''

MARKDOWN_FOOTER = """

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../../LICENSE)*"""

ROOT_MARKDOWN_FOOTER = """

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](LICENSE)*"""

PYTHON_FILES = [
    # ztoq files
    "ztoq/__init__.py",
    "ztoq/cli.py",
    "ztoq/data_fetcher.py",
    "ztoq/database_manager.py",
    "ztoq/exporter.py",
    "ztoq/main.py",
    "ztoq/models.py",
    "ztoq/openapi_parser.py",
    "ztoq/qtest_client.py",
    "ztoq/qtest_mock_server.py",
    "ztoq/qtest_models.py",
    "ztoq/storage.py",
    "ztoq/test_generator.py",
    "ztoq/zephyr_client.py",
    "ztoq/zephyr_importer.py",
    "ztoq/core/__init__.py",
    "ztoq/core/services.py",
    "ztoq/domain/__init__.py",
    "ztoq/domain/models.py",
    # test files
    "tests/__init__.py",
    "tests/integration/test_api.py",
    "tests/integration/test_cli.py",
    "tests/integration/test_cli_commands.py",
    "tests/unit/test_data_fetcher.py",
    "tests/unit/test_database_manager.py",
    "tests/unit/test_exporter.py",
    "tests/unit/test_models.py",
    "tests/unit/test_openapi.py",
    "tests/unit/test_openapi_parser.py",
    "tests/unit/test_qtest_client.py",
    "tests/unit/test_qtest_mock_server.py",
    "tests/unit/test_qtest_models.py",
    "tests/unit/test_spec_wrapper.py",
    "tests/unit/test_storage.py",
    "tests/unit/test_test_generator.py",
    "tests/unit/test_zephyr_client.py",
]

MARKDOWN_FILES = [
    "README.md",
    "CLAUDE.md",
    "docs/adr/001-use-poetry-for-dependency-management.md",
    "docs/adr/002-storage-formats.md",
    "docs/adr/003-use-pydantic-models.md",
    "docs/adr/004-pagination-handling.md",
    "docs/adr/005-cli-structure.md",
    "docs/adr/006-sphinx-documentation.md",
    "docs/adr/007-database-manager-implementation.md",
    "docs/adr/008-test-driven-development.md",
    "docs/adr/009-error-handling-strategy.md",
    "docs/adr/010-logging-strategy.md",
    "docs/adr/011-qtest-integration-architecture.md",
    "docs/adr/012-test-driven-development-approach.md",
    "docs/adr/013-etl-migration-workflow.md",
    "docs/adr/README.md",
    "docs/c4-diagram.md",
    "docs/conversion-process.md",
    "docs/custom-fields-attachments.md",
    "docs/docs-contribution-guide.md",
    "docs/entity-mapping.md",
    "docs/kanban.md",
    "docs/maintenance.md",
    "docs/openapi-integration.md",
    "docs/qtest-migration-architecture.md",
    "docs/test-strategy.md",
]

ROOT_MARKDOWN_FILES = [
    "README.md",
    "CLAUDE.md",
]


def add_python_header(file_path):
    """Add license header to a Python file if it doesn't already have it."""
    absolute_path = os.path.join(os.getcwd(), file_path)

    # Check if file exists
    if not os.path.exists(absolute_path):
        print(f"Warning: File {absolute_path} does not exist, skipping.")
        return

    # Read file content
    with open(absolute_path) as f:
        content = f.read()

    # Check if header already exists
    if "Copyright (c) 2025 Eric C. Mumford" in content:
        print(f"Header already exists in {file_path}, skipping.")
        return

    # Handle shebang line if it exists
    if content.startswith("#!"):
        shebang_end = content.find("\n") + 1
        shebang = content[:shebang_end]
        content = content[shebang_end:]
        new_content = shebang + PYTHON_HEADER + content
    else:
        new_content = PYTHON_HEADER + content

    # Write modified content back
    with open(absolute_path, "w") as f:
        f.write(new_content)

    print(f"Added header to {file_path}")


def add_markdown_footer(file_path):
    """Add license footer to a Markdown file if it doesn't already have it."""
    absolute_path = os.path.join(os.getcwd(), file_path)

    # Check if file exists
    if not os.path.exists(absolute_path):
        print(f"Warning: File {absolute_path} does not exist, skipping.")
        return

    # Read file content
    with open(absolute_path) as f:
        content = f.read()

    # Check if footer already exists
    if "Copyright (c) 2025 Eric C. Mumford" in content:
        print(f"Footer already exists in {file_path}, skipping.")
        return

    # Use appropriate footer based on file location
    footer = ROOT_MARKDOWN_FOOTER if file_path in ROOT_MARKDOWN_FILES else MARKDOWN_FOOTER

    # Add footer
    new_content = content.rstrip() + footer

    # Write modified content back
    with open(absolute_path, "w") as f:
        f.write(new_content)

    print(f"Added footer to {file_path}")


def main():
    """Main function to add headers/footers to files."""
    print("Adding license headers to Python files...")
    for file_path in PYTHON_FILES:
        add_python_header(file_path)

    print("\nAdding license footers to Markdown files...")
    for file_path in MARKDOWN_FILES:
        add_markdown_footer(file_path)

    print("\nDone!")


if __name__ == "__main__":
    main()
