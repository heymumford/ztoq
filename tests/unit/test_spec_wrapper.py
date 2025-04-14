"""
Unit tests for the ZephyrApiSpecWrapper class.
"""

import pytest
import json
from typing import Dict, Any
from pathlib import Path

from ztoq.openapi_parser import ZephyrApiSpecWrapper


# Sample OpenAPI specification for testing
@pytest.fixture
def sample_spec() -> Dict[str, Any]:
    """Create a sample OpenAPI spec for testing."""
    return {
        "openapi": "3.0.1",
        "info": {
            "title": "Zephyr Scale API",
            "description": "API for Zephyr Scale test management",
            "version": "1.0.0",
        },
        "paths": {
            "/testcases": {
                "get": {
                    "summary": "Get test cases",
                    "operationId": "getTestCases",
                    "tags": ["test-cases"],
                    "parameters": [
                        {
                            "name": "projectKey",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "maxResults",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "minimum": 1, "maximum": 1000},
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/TestCasesResponse"}
                                }
                            },
                        },
                        "400": {"description": "Invalid parameters"},
                        "401": {"description": "Unauthorized"},
                    },
                },
                "post": {
                    "summary": "Create test case",
                    "operationId": "createTestCase",
                    "tags": ["test-cases"],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/TestCaseInput"}
                            }
                        },
                        "required": True,
                    },
                    "responses": {
                        "201": {
                            "description": "Test case created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/TestCase"}
                                }
                            },
                        }
                    },
                },
            },
            "/testcases/{id}": {
                "get": {
                    "summary": "Get test case by ID",
                    "operationId": "getTestCaseById",
                    "tags": ["test-cases"],
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/TestCase"}
                                }
                            },
                        },
                        "404": {"description": "Test case not found"},
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "TestCasesResponse": {
                    "type": "object",
                    "properties": {
                        "values": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/TestCase"},
                        },
                        "total": {"type": "integer"},
                        "startAt": {"type": "integer"},
                        "isLast": {"type": "boolean"},
                    },
                    "required": ["values", "total", "startAt", "isLast"],
                },
                "TestCase": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "key": {"type": "string"},
                        "name": {"type": "string"},
                        "status": {"type": "string"},
                        "priority": {"type": "string"},
                        "folder": {"type": "string"},
                        "createdOn": {"type": "string", "format": "date-time"},
                        "updatedOn": {"type": "string", "format": "date-time"},
                    },
                    "required": ["id", "key", "name"],
                },
                "TestCaseInput": {
                    "type": "object",
                    "properties": {
                        "projectKey": {"type": "string"},
                        "name": {"type": "string"},
                        "status": {"type": "string"},
                        "priority": {"type": "string"},
                        "folder": {"type": "string"},
                    },
                    "required": ["projectKey", "name"],
                },
            }
        },
    }


@pytest.fixture
def spec_wrapper(sample_spec):
    """Create a spec wrapper for testing."""
    return ZephyrApiSpecWrapper(sample_spec)


def test_extract_endpoints(spec_wrapper):
    """Test the extraction of endpoints from the spec."""
    endpoints = spec_wrapper.endpoints
    assert len(endpoints) == 3
    assert ("/testcases", "get") in endpoints
    assert ("/testcases", "post") in endpoints
    assert ("/testcases/{id}", "get") in endpoints


def test_get_endpoint_info(spec_wrapper):
    """Test retrieving information about a specific endpoint."""
    endpoint_info = spec_wrapper.get_endpoint_info("/testcases", "get")
    assert endpoint_info is not None
    assert endpoint_info["operation_id"] == "getTestCases"
    assert "test-cases" in endpoint_info["tags"]
    assert len(endpoint_info["parameters"]) == 2


def test_find_endpoints_by_tag(spec_wrapper):
    """Test finding endpoints by tag."""
    endpoints = spec_wrapper.find_endpoints_by_tag("test-cases")
    assert len(endpoints) == 3
    assert ("/testcases", "get") in endpoints
    assert ("/testcases", "post") in endpoints
    assert ("/testcases/{id}", "get") in endpoints


def test_find_endpoints_by_operation_id(spec_wrapper):
    """Test finding endpoints by operation ID."""
    endpoint = spec_wrapper.find_endpoints_by_operation_id("getTestCaseById")
    assert endpoint == ("/testcases/{id}", "get")

    # Test with non-existent operation ID
    endpoint = spec_wrapper.find_endpoints_by_operation_id("nonExistentOperationId")
    assert endpoint is None


def test_find_endpoints_by_pattern(spec_wrapper):
    """Test finding endpoints by regex pattern."""
    endpoints = spec_wrapper.find_endpoints_by_pattern(r"/testcases/\{.*\}")
    assert len(endpoints) == 1
    assert ("/testcases/{id}", "get") in endpoints


def test_get_request_schema(spec_wrapper):
    """Test retrieving the request schema for an endpoint."""
    # POST should have a request schema
    schema = spec_wrapper.get_request_schema("/testcases", "post")
    assert schema is not None
    assert "$ref" in schema

    # GET shouldn't have a request schema
    schema = spec_wrapper.get_request_schema("/testcases", "get")
    assert schema is None


def test_get_response_schema(spec_wrapper):
    """Test retrieving the response schema for an endpoint."""
    # 200 response schema
    schema = spec_wrapper.get_response_schema("/testcases", "get", "200")
    assert schema is not None
    assert "$ref" in schema

    # 400 response does not have a schema
    schema = spec_wrapper.get_response_schema("/testcases", "get", "400")
    assert schema is None

    # Non-existent response code
    schema = spec_wrapper.get_response_schema("/testcases", "get", "500")
    assert schema is None


def test_validate_request(spec_wrapper):
    """Test request validation against schema."""
    # Valid request
    valid_data = {"projectKey": "TEST", "name": "Test Case"}
    is_valid, error = spec_wrapper.validate_request("/testcases", "post", valid_data)
    assert is_valid
    assert error is None

    # Invalid request (missing required field)
    invalid_data = {"name": "Test Case"}
    is_valid, error = spec_wrapper.validate_request("/testcases", "post", invalid_data)
    assert not is_valid
    assert error is not None
    assert "projectKey" in error


def test_validate_response(spec_wrapper):
    """Test response validation against schema."""
    # Valid response
    valid_data = {
        "values": [{"id": "1", "key": "TEST-1", "name": "Test Case"}],
        "total": 1,
        "startAt": 0,
        "isLast": True,
    }
    is_valid, error = spec_wrapper.validate_response("/testcases", "get", "200", valid_data)
    assert is_valid
    assert error is None

    # Invalid response (missing required field)
    invalid_data = {
        "values": [
            {
                "id": "1",
                "key": "TEST-1",
                # missing 'name'
            }
        ],
        "total": 1,
        "startAt": 0,
        "isLast": True,
    }
    is_valid, error = spec_wrapper.validate_response("/testcases", "get", "200", invalid_data)
    assert not is_valid
    assert error is not None
    assert "name" in error


def test_resolve_schema_refs(spec_wrapper):
    """Test the resolution of schema references."""
    schema_with_ref = {"$ref": "#/components/schemas/TestCase"}
    resolved = spec_wrapper._resolve_schema_refs(schema_with_ref)
    assert resolved is not None
    assert "properties" in resolved
    assert "id" in resolved["properties"]
    assert "name" in resolved["properties"]


def test_generate_mock_data(spec_wrapper):
    """Test generation of mock data from schema."""
    # Simple object schema
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "count": {"type": "integer"},
            "isActive": {"type": "boolean"},
        },
        "required": ["id", "count"],
    }
    mock_data = spec_wrapper.generate_mock_data(schema)
    assert isinstance(mock_data, dict)
    assert "id" in mock_data
    assert "count" in mock_data
    assert isinstance(mock_data["id"], str)
    assert isinstance(mock_data["count"], int)

    # Array schema
    array_schema = {"type": "array", "items": {"type": "string"}}
    mock_array = spec_wrapper.generate_mock_data(array_schema)
    assert isinstance(mock_array, list)
    assert all(isinstance(item, str) for item in mock_array)


def test_generate_mock_request(spec_wrapper):
    """Test generation of mock request data for an endpoint."""
    mock_request = spec_wrapper.generate_mock_request("/testcases", "post")
    assert isinstance(mock_request, dict)
    assert "projectKey" in mock_request
    assert "name" in mock_request


def test_generate_mock_response(spec_wrapper):
    """Test generation of mock response data for an endpoint."""
    mock_response = spec_wrapper.generate_mock_response("/testcases", "get", "200")
    assert isinstance(mock_response, dict)
    assert "values" in mock_response
    assert "total" in mock_response
    assert "startAt" in mock_response
    assert "isLast" in mock_response
    assert isinstance(mock_response["values"], list)


def test_validate_parameters(spec_wrapper):
    """Test validation of request parameters."""
    # Valid parameters
    valid_params = {"projectKey": "TEST", "maxResults": 50}
    is_valid, error = spec_wrapper.validate_parameters("/testcases", "get", valid_params)
    assert is_valid
    assert error is None

    # Missing required parameter
    invalid_params = {"maxResults": 50}
    is_valid, error = spec_wrapper.validate_parameters("/testcases", "get", invalid_params)
    assert not is_valid
    assert error is not None
    assert "projectKey" in error

    # Parameter out of range
    invalid_range = {"projectKey": "TEST", "maxResults": 2000}  # Max is 1000
    is_valid, error = spec_wrapper.validate_parameters("/testcases", "get", invalid_range)
    assert not is_valid
    assert error is not None
    assert "maxResults" in error
