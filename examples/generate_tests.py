#!/usr/bin/env python3
"""
Example of using the test generator to create test cases from OpenAPI spec.

This example demonstrates how to:
1. Load an OpenAPI spec
2. Generate test cases for all endpoints
3. Export the test cases to a JSON file
4. Generate a pytest file with test functions
"""

import sys
import logging
from pathlib import Path

# Add the parent directory to the path to allow importing ztoq
sys.path.insert(0, str(Path(__file__).parent.parent))

from ztoq.test_generator import ZephyrTestGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def main():
    # Path to the OpenAPI spec
    spec_path = Path(__file__).parent.parent / "docs" / "specs" / "z-openapi.yml"

    # Initialize the test generator
    test_gen = ZephyrTestGenerator.from_spec_path(spec_path)

    # Option 1: Generate test cases for a specific endpoint
    tests = test_gen.generate_endpoint_tests("/testcases", "get")
    print(f"Generated {len(tests)} tests for GET /testcases")

    # Option 2: Export all tests to a JSON file
    output_dir = Path(__file__).parent.parent / "tests" / "generated"
    output_dir.mkdir(exist_ok=True, parents=True)

    json_path = output_dir / "test_suite.json"
    test_gen.export_test_suite_to_json(json_path)
    print(f"Exported test suite to {json_path}")

    # Option 3: Generate a pytest file with test functions
    pytest_path = output_dir / "test_zephyr_api.py"
    test_gen.generate_pytest_file(pytest_path)
    print(f"Generated pytest file at {pytest_path}")

    # Option 4: Generate tests for a specific tag
    tag_specific_path = output_dir / "test_testcases_api.py"
    test_gen.generate_pytest_file(tag_specific_path, tag="test-cases")
    print(f"Generated tag-specific pytest file at {tag_specific_path}")


if __name__ == "__main__":
    main()
