"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for the ZephyrTestGenerator class.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from ztoq.test_generator import ZephyrTestGenerator
from ztoq.openapi_parser import ZephyrApiSpecWrapper


@pytest.fixture
def mock_spec_wrapper():
    """Create a mock ZephyrApiSpecWrapper for testing."""
    mock_wrapper = MagicMock(spec=ZephyrApiSpecWrapper)

    # Setup endpoints
    mock_wrapper.endpoints = {
        ("/testcases", "get"): {
            "path": "/testcases",
            "method": "get",
            "operation_id": "getTestCases",
            "tags": ["test-cases"],
            "parameters": [
                {
                    "name": "projectKey",
                    "in": "query",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
            "responses": {"200": {"description": "Success"}, "400": {"description": "Bad Request"}},
        }
    }

    # Setup mock methods
    mock_wrapper.get_endpoint_info.return_value = mock_wrapper.endpoints[("/testcases", "get")]
    mock_wrapper.get_request_schema.return_value = None  # GET doesn't have request body
    mock_wrapper.get_response_schema.return_value = {
        "type": "object",
        "properties": {
            "values": {"type": "array", "items": {"type": "object"}},
            "total": {"type": "integer"},
        },
    }
    mock_wrapper.generate_mock_data.return_value = {"test": "data"}
    mock_wrapper.generate_mock_response.return_value = {
        "values": [{"id": "1", "name": "Test"}],
        "total": 1,
    }

    return mock_wrapper


@pytest.fixture
def test_generator(mock_spec_wrapper):
    """Create a test generator with mock wrapper."""
    return ZephyrTestGenerator(mock_spec_wrapper)


def test_generate_endpoint_tests(test_generator, mock_spec_wrapper):
    """Test the generation of test cases for an endpoint."""
    tests = test_generator.generate_endpoint_tests("/testcases", "get")

    # Should generate tests
    assert len(tests) > 0

    # Each test should have basic properties
    for test in tests:
        assert "name" in test
        assert "description" in test
        assert "path" in test
        assert "method" in test
        assert test["path"] == "/testcases"
        assert test["method"] == "get"

    # Verify calls to wrapper methods
    mock_spec_wrapper.get_endpoint_info.assert_called_with("/testcases", "get")
    mock_spec_wrapper.get_response_schema.assert_called_with("/testcases", "get", "200")


def test_generate_happy_path_test(test_generator):
    """Test generation of a happy path test case."""
    test = test_generator._generate_happy_path_test("/testcases", "get")

    assert test["name"] == "test_getTestCases_happy_path"
    assert "description" in test
    assert test["path"] == "/testcases"
    assert test["method"] == "get"
    assert "params" in test
    assert "projectKey" in test["params"]
    assert test["expected_status"] == 200
    assert test["validate_schema"] is True


def test_generate_parameter_tests(test_generator):
    """Test generation of parameter validation tests."""
    tests = test_generator._generate_parameter_tests("/testcases", "get")

    # Should generate at least one test for the required parameter
    assert len(tests) > 0

    # Find the test for missing required parameter
    missing_param_test = None
    for test in tests:
        if "missing_projectKey" in test["name"]:
            missing_param_test = test
            break

    assert missing_param_test is not None
    assert missing_param_test["expected_status"] == 400
    assert "projectKey" not in missing_param_test["params"]


def test_generate_test_suite(test_generator, mock_spec_wrapper):
    """Test generation of a complete test suite."""
    # Setup for finding endpoints
    mock_spec_wrapper.find_endpoints_by_tag.return_value = [("/testcases", "get")]

    # Test with tag
    test_suite = test_generator.generate_test_suite(tag="test-cases")
    assert "GET /testcases" in test_suite
    assert len(test_suite["GET /testcases"]) > 0

    # Test without tag
    mock_spec_wrapper.find_endpoints_by_tag.reset_mock()
    test_suite = test_generator.generate_test_suite()
    assert "GET /testcases" in test_suite

    # Verify correct method was called
    mock_spec_wrapper.find_endpoints_by_tag.assert_not_called()


def test_export_test_suite_to_json(test_generator):
    """Test exporting a test suite to JSON."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_suite.json"

        with patch.object(test_generator, "generate_test_suite") as mock_generate:
            mock_generate.return_value = {
                "GET /testcases": [
                    {
                        "name": "test_getTestCases_happy_path",
                        "path": "/testcases",
                        "method": "get",
                        "expected_status": 200,
                    }
                ]
            }

            test_generator.export_test_suite_to_json(output_path)

            # Verify the file was created
            assert output_path.exists()

            # Verify content
            with open(output_path) as f:
                content = json.load(f)
                assert "GET /testcases" in content
                assert len(content["GET /testcases"]) == 1
                assert content["GET /testcases"][0]["name"] == "test_getTestCases_happy_path"


def test_generate_test_function(test_generator):
    """Test generation of a pytest function."""
    test = {
        "name": "test_getTestCases_happy_path",
        "description": "Test happy path for GET /testcases",
        "path": "/testcases",
        "method": "get",
        "params": {"projectKey": "TEST"},
        "expected_status": 200,
        "validate_schema": True,
    }

    function_code = test_generator.generate_test_function(test)

    # Verify the function definition
    assert function_code.startswith("def test_getTestCases_happy_path(zephyr_client):")
    assert "Test happy path for GET /testcases" in function_code

    # Verify params
    assert "params = {" in function_code
    assert '"projectKey": "TEST"' in function_code

    # Verify API call
    assert "zephyr_client._make_request(" in function_code
    assert "'GET'" in function_code
    assert "'/testcases'" in function_code

    # Should use try-except for successful test
    assert "try:" in function_code
    assert "assert response is not None" in function_code


def test_generate_test_function_error_case(test_generator):
    """Test generation of a pytest function for an error case."""
    test = {
        "name": "test_getTestCases_missing_param",
        "description": "Test GET /testcases with missing parameter",
        "path": "/testcases",
        "method": "get",
        "params": {},
        "expected_status": 400,
        "validate_schema": False,
    }

    function_code = test_generator.generate_test_function(test)

    # Verify error handling
    assert "with pytest.raises(requests.exceptions.HTTPError) as excinfo:" in function_code
    assert "assert excinfo.value.response.status_code == 400" in function_code


def test_generate_pytest_file(test_generator):
    """Test generation of a pytest file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_api.py"

        with patch.object(test_generator, "generate_test_suite") as mock_generate:
            mock_generate.return_value = {
                "GET /testcases": [
                    {
                        "name": "test_getTestCases_happy_path",
                        "description": "Test happy path",
                        "path": "/testcases",
                        "method": "get",
                        "params": {"projectKey": "TEST"},
                        "expected_status": 200,
                        "validate_schema": True,
                    }
                ]
            }

            test_generator.generate_pytest_file(output_path)

            # Verify the file was created
            assert output_path.exists()

            # Verify content
            with open(output_path) as f:
                content = f.read()
                assert "import pytest" in content
                assert "def test_getTestCases_happy_path(zephyr_client):" in content
                assert "@pytest.fixture" in content
                assert "def zephyr_client():" in content
