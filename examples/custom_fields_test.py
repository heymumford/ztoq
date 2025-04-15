#!/usr/bin/env python3
"""
Example script to demonstrate testing custom fields and attachments in Zephyr Scale.

This example:
1. Creates specific tests for custom fields of different types
2. Tests binary file attachments with test cases and test steps
3. Validates that custom fields and attachments are properly processed
"""

import logging
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ztoq.test_generator import ZephyrTestGenerator

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def main():
    # Define paths
    spec_path = Path(__file__).parent.parent / "docs" / "specs" / "z-openapi.yml"

    # Create a test generator
    test_gen = ZephyrTestGenerator.from_spec_path(spec_path)

    # Create output directories
    output_dir = Path(__file__).parent.parent / "tests" / "generated"
    output_dir.mkdir(exist_ok=True, parents=True)

    # Generate tests focused on custom fields
    generate_custom_field_tests(test_gen, output_dir)

    # Generate tests focused on attachments
    generate_attachment_tests(test_gen, output_dir)

    print("Custom field and attachment tests generated successfully.")


def generate_custom_field_tests(test_gen: ZephyrTestGenerator, output_dir: Path):
    """Generate test cases for custom fields.

    Args:
        test_gen: The test generator instance
        output_dir: Output directory for generated tests
    """
    # Find all endpoints that likely involve custom fields
    custom_field_endpoints = []

    for path, method in test_gen.spec_wrapper.endpoints:
        if test_gen._is_entity_endpoint(path):
            # Make sure it's an endpoint that accepts POST/PUT (can create/update entities)
            if method.lower() in ["post", "put", "patch"]:
                custom_field_endpoints.append((path, method))

    # Generate custom field tests
    test_suite = {}
    for path, method in custom_field_endpoints:
        endpoint_id = f"{method.upper()} {path}"
        tests = test_gen._generate_custom_field_tests(path, method)
        if tests:
            test_suite[endpoint_id] = tests

    # Export to JSON
    custom_fields_json = output_dir / "custom_fields_test_suite.json"
    with open(custom_fields_json, "w") as f:
        import json

        json.dump(test_suite, f, indent=2)

    # Generate pytest file
    custom_fields_pytest = output_dir / "test_custom_fields.py"

    # Create pytest file with imports and fixture
    lines = [
        "import pytest",
        "import requests",
        "import base64",
        "import json",
        "from pathlib import Path",
        "",
        "from ztoq.models import ZephyrConfig, CustomField, CustomFieldType",
        "from ztoq.zephyr_client import ZephyrClient",
        "",
        "@pytest.fixture",
        "def zephyr_client():",
        '    """Create a Zephyr client for testing custom fields."""',
        "    config = ZephyrConfig(",
        "        base_url='https://api.zephyrscale.smartbear.com/v2',",
        "        api_token='test-token',",
        "        project_key='TEST'",
        "    )",
        "    client = ZephyrClient.from_openapi_spec(",
        "        Path('docs/specs/z-openapi.yml'),",
        "        config,",
        "        log_level='DEBUG'",
        "    )",
        "    return client",
        "",
        "# Create helper functions for custom field validation",
        "def validate_custom_field(field, expected_type, expected_value=None):",
        '    """Validate a custom field\'s type and optionally its value."""',
        "    assert 'id' in field",
        "    assert 'name' in field",
        "    assert 'type' in field",
        "    assert field['type'] == expected_type",
        "    ",
        "    if expected_value is not None:",
        "        assert 'value' in field",
        "        assert field['value'] == expected_value",
        "",
    ]

    # Add test functions
    for endpoint_id, tests in test_suite.items():
        lines.append(f"# Tests for {endpoint_id}")
        for test in tests:
            lines.append(test_gen.generate_test_function(test))
            lines.append("")  # Empty line between functions

    with open(custom_fields_pytest, "w") as f:
        f.write("\n".join(lines))

    print(f"Generated custom field tests at {custom_fields_pytest}")


def generate_attachment_tests(test_gen: ZephyrTestGenerator, output_dir: Path):
    """Generate test cases for attachments.

    Args:
        test_gen: The test generator instance
        output_dir: Output directory for generated tests
    """
    # Find all endpoints that likely involve attachments
    attachment_endpoints = []

    for path, method in test_gen.spec_wrapper.endpoints:
        if test_gen._supports_attachments(path):
            attachment_endpoints.append((path, method))

    # Generate attachment tests
    test_suite = {}
    for path, method in attachment_endpoints:
        endpoint_id = f"{method.upper()} {path}"
        tests = test_gen._generate_attachment_tests(path, method)
        if tests:
            test_suite[endpoint_id] = tests

    # Export to JSON
    attachments_json = output_dir / "attachments_test_suite.json"
    with open(attachments_json, "w") as f:
        import json

        json.dump(test_suite, f, indent=2)

    # Generate pytest file
    attachments_pytest = output_dir / "test_attachments.py"

    # Create pytest file with imports and fixture
    lines = [
        "import pytest",
        "import requests",
        "import base64",
        "import json",
        "from pathlib import Path",
        "",
        "from ztoq.models import ZephyrConfig, Attachment",
        "from ztoq.zephyr_client import ZephyrClient",
        "",
        "@pytest.fixture",
        "def zephyr_client():",
        '    """Create a Zephyr client for testing attachments."""',
        "    config = ZephyrConfig(",
        "        base_url='https://api.zephyrscale.smartbear.com/v2',",
        "        api_token='test-token',",
        "        project_key='TEST'",
        "    )",
        "    client = ZephyrClient.from_openapi_spec(",
        "        Path('docs/specs/z-openapi.yml'),",
        "        config,",
        "        log_level='DEBUG'",
        "    )",
        "    return client",
        "",
        "# Helper function to create binary test files",
        "def create_test_file(filename, content=None):",
        '    """Create a test file with some content."""',
        "    content = content or f'Test content for {filename}'.encode('utf-8')",
        "    test_path = Path(f'./test_files/{filename}')",
        "    test_path.parent.mkdir(exist_ok=True, parents=True)",
        "    test_path.write_bytes(content)",
        "    return test_path",
        "",
    ]

    # Add test functions
    for endpoint_id, tests in test_suite.items():
        lines.append(f"# Tests for {endpoint_id}")
        for test in tests:
            lines.append(test_gen.generate_test_function(test))
            lines.append("")  # Empty line between functions

    with open(attachments_pytest, "w") as f:
        f.write("\n".join(lines))

    print(f"Generated attachment tests at {attachments_pytest}")


if __name__ == "__main__":
    main()
