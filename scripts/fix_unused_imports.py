#!/usr/bin/env python3
"""
Script to fix unused imports in Python files.

This script removes unused imports that cause F401 flake8 errors.

Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import os
import re

# List of files with unused imports based on flake8 output
FILES_WITH_UNUSED_IMPORTS = {
    "ztoq/data_fetcher.py": [
        "typing.Iterator",
        "typing.Tuple",
        "pathlib.Path",
        "ztoq.models.Case",
        "ztoq.models.CycleInfo",
        "ztoq.models.Plan",
        "ztoq.models.Execution",
        "ztoq.models.Folder",
        "ztoq.models.Status",
        "ztoq.models.Priority",
        "ztoq.models.Environment",
    ],
    "ztoq/database_manager.py": [
        "typing.List",
        "typing.Optional",
        "typing.Tuple",
        "ztoq.models.Attachment",
        "ztoq.models.CaseStep",
        "ztoq.models.CustomField",
    ],
    "ztoq/openapi_parser.py": [
        "json",
        "typing.Union",
        "typing.Set",
        "typing.Callable",
        "typing.Type",
        "typing.get_type_hints",
    ],
    "ztoq/qtest_client.py": [
        "datetime.datetime",
        "base64",
        "ztoq.models.QTestTestExecution",
        "ztoq.models.QTestRelease",
        "ztoq.models.QTestCustomField",
    ],
    "ztoq/qtest_models.py": ["typing.Union", "pydantic.validator"],
    "ztoq/test_generator.py": ["typing.Tuple", "typing.Set", "typing.Union"],
    "ztoq/zephyr_importer.py": ["typing.Callable"],
    "tests/unit/test_data_fetcher.py": ["typing.Dict", "typing.List"],
    "tests/unit/test_database_manager.py": ["pathlib.Path"],
    "tests/unit/test_exporter.py": ["ztoq.models.Case", "ztoq.models.CycleInfo"],
    "tests/unit/test_models.py": ["ztoq.models.CustomFieldType"],
    "tests/unit/test_qtest_client.py": [
        "pathlib.Path",
        "datetime.datetime",
        "json",
        "ztoq.qtest_models.QTestTestCycle",
        "ztoq.qtest_models.QTestDataset",
    ],
    "tests/unit/test_qtest_mock_server.py": [
        "json",
        "unittest.mock.MagicMock",
        "unittest.mock.patch",
        "uuid",
        "datetime.datetime",
    ],
    "tests/unit/test_spec_wrapper.py": ["json", "pathlib.Path"],
}


def fix_unused_imports(file_path, unused_imports):
    """Remove unused imports from a file."""
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist, skipping.")
        return

    with open(file_path) as f:
        content = f.read()

    # Handle imports that are part of multi-import lines
    for unused_import in unused_imports:
        # Split on module/element if applicable
        if "." in unused_import:
            module, element = unused_import.rsplit(".", 1)
        else:
            module, element = None, unused_import

        # Handle "from x import y" format
        if module:
            from_import_pattern = (
                rf"from\s+{module}\s+import\s+([^,\n]+,\s*)*{element}(,\s*[^,\n]+)*"
            )
            from_import_matches = re.finditer(from_import_pattern, content)

            for match in from_import_matches:
                original_import = match.group(0)
                # Parse the import statement
                elements = re.search(rf"from\s+{module}\s+import\s+(.*)", original_import).group(1)
                elements_list = [e.strip() for e in elements.split(",")]

                # Remove the unused import
                if element in elements_list:
                    elements_list.remove(element)

                if not elements_list:
                    # Remove the entire import statement
                    content = content.replace(original_import, "", 1)
                else:
                    # Replace with the import statement without the unused import
                    new_import = f"from {module} import {', '.join(elements_list)}"
                    content = content.replace(original_import, new_import, 1)

        # Handle "import x" format
        else:
            import_pattern = rf"import\s+{element}"
            content = re.sub(import_pattern, "", content)

    # Clean up any resulting empty lines or multiple blank lines
    content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)

    with open(file_path, "w") as f:
        f.write(content)

    print(f"Removed unused imports from {file_path}")


def main():
    """Process all files with unused imports."""
    for file_path, unused_imports in FILES_WITH_UNUSED_IMPORTS.items():
        fix_unused_imports(file_path, unused_imports)

    print(f"Processed {len(FILES_WITH_UNUSED_IMPORTS)} files.")


if __name__ == "__main__":
    main()
