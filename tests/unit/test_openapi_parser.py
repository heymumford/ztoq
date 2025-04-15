"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from ztoq.openapi_parser import extract_api_endpoints, load_openapi_spec, validate_zephyr_spec


@pytest.mark.unit
class TestOpenAPIParser:
    def test_load_openapi_spec_missing_file(self):
        """Test loading a missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_openapi_spec(Path("nonexistent.yml"))

    def test_load_openapi_spec_valid_file(self):
        """Test loading a valid OpenAPI spec file."""
        mock_yaml = """
        openapi: 3.0.0
        info:
          title: Zephyr Scale API
          version: 1.0.0
        paths: {}
        """

        m = mock_open(read_data=mock_yaml)
        with patch("builtins.open", m), patch("ztoq.openapi_parser.Path.exists", return_value=True):
            result = load_openapi_spec(Path("z-openapi.yml"))

            assert result is not None
            assert result["openapi"] == "3.0.0"
            assert result["info"]["title"] == "Zephyr Scale API"

    def test_validate_zephyr_spec_valid(self):
        """Test validating a valid Zephyr Scale API spec."""
        valid_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Zephyr Scale API",
                "version": "1.0.0",
            },
            "paths": {},
        }

        assert validate_zephyr_spec(valid_spec) is True

        # Test with description instead of title
        valid_spec_desc = {
            "openapi": "3.0.0",
            "info": {
                "title": "Some API",
                "description": "The Zephyr Scale API allows you to...",
                "version": "1.0.0",
            },
            "paths": {},
        }

        assert validate_zephyr_spec(valid_spec_desc) is True

    def test_validate_zephyr_spec_invalid(self):
        """Test validating an invalid Zephyr Scale API spec."""
        invalid_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Some Other API",
                "version": "1.0.0",
            },
            "paths": {},
        }

        assert validate_zephyr_spec(invalid_spec) is False

        # Not an OpenAPI spec
        not_openapi = {
            "swagger": "2.0",  # Using older format
            "info": {
                "title": "Zephyr Scale API",
                "version": "1.0.0",
            },
        }

        assert validate_zephyr_spec(not_openapi) is False

    def test_extract_api_endpoints(self):
        """Test extracting API endpoints from an OpenAPI spec."""
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Zephyr Scale API",
                "version": "1.0.0",
            },
            "paths": {
                "/testcases": {
                    "get": {
                        "summary": "Get test cases",
                        "description": "Get all test cases",
                        "parameters": [],
                        "responses": {},
                    },
                    "post": {
                        "summary": "Create test case",
                        "description": "Create a new test case",
                        "parameters": [],
                        "responses": {},
                    },
                },
                "/testcases/{id}": {
                    "get": {
                        "summary": "Get test case by ID",
                        "description": "Get a specific test case",
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            },
                        ],
                        "responses": {},
                    },
                    "put": {
                        "summary": "Update test case",
                        "description": "Update an existing test case",
                        "parameters": [],
                        "responses": {},
                    },
                    "delete": {
                        "summary": "Delete test case",
                        "description": "Delete a test case",
                        "parameters": [],
                        "responses": {},
                    },
                },
                # Non-HTTP method property should be ignored
                "/testexecutions": {
                    "get": {
                        "summary": "Get test executions",
                        "description": "Get all test executions",
                        "parameters": [],
                        "responses": {},
                    },
                    "parameters": [  # This should be ignored
                        {"name": "projectKey", "in": "query", "schema": {"type": "string"}},
                    ],
                },
            },
        }

        endpoints = extract_api_endpoints(spec)

        assert len(endpoints) == 6  # 2 for /testcases, 3 for /testcases/{id}, 1 for /testexecutions
        assert "GET /testcases" in endpoints
        assert "POST /testcases" in endpoints
        assert "GET /testcases/{id}" in endpoints
        assert "PUT /testcases/{id}" in endpoints
        assert "DELETE /testcases/{id}" in endpoints

        assert endpoints["GET /testcases"]["summary"] == "Get test cases"
        assert endpoints["POST /testcases"]["description"] == "Create a new test case"
        assert endpoints["GET /testcases/{id}"]["parameters"][0]["name"] == "id"
        assert endpoints["DELETE /testcases/{id}"]["method"] == "delete"
