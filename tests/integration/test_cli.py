"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

from unittest.mock import MagicMock, patch
import pytest
from typer.testing import CliRunner
from ztoq.cli import app
from ztoq.models import TestCase


@pytest.mark.integration()
class TestCLI:
    @pytest.fixture()
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture()
    def mock_openapi_spec(self):
        """Mock the OpenAPI spec for testing."""
        valid_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Zephyr Scale API", "version": "1.0.0"},
            "paths": {},
        }
        with patch("ztoq.openapi_parser.load_openapi_spec", return_value=valid_spec):
            yield

    def test_validate_command_valid(self, runner, mock_openapi_spec):
        """Test the validate command with a valid spec."""
        with patch("ztoq.openapi_parser.Path.exists", return_value=True):
            result = runner.invoke(app, ["validate", "z-openapi.yml"])
            assert result.exit_code == 0
            assert "Valid Zephyr Scale API specification" in result.stdout

    @patch("ztoq.cli.extract_api_endpoints")
    def test_list_endpoints_command(self, mock_extract, runner, mock_openapi_spec):
        """Test the list-endpoints command."""
        mock_extract.return_value = {
            "GET /testcases": {
                "path": "/testcases",
                "method": "get",
                "summary": "Get test cases",
            },
        }

        with patch("ztoq.openapi_parser.Path.exists", return_value=True):
            result = runner.invoke(app, ["list-endpoints", "z-openapi.yml"])
            assert result.exit_code == 0
            assert "Zephyr Scale API Endpoints" in result.stdout
            assert "GET" in result.stdout
            assert "/testcases" in result.stdout
            assert "Get test cases" in result.stdout

    @patch("ztoq.zephyr_client.ZephyrClient.from_openapi_spec")
    def test_get_test_cases_command(self, mock_client_factory, runner, mock_openapi_spec):
        """Test the get-test-cases command."""
        mock_client = MagicMock()
        mock_client.get_test_cases.return_value = [
            TestCase(id="1", key="TEST-TC-1", name="Test Case 1", status="Draft"),
            TestCase(id="2", key="TEST-TC-2", name="Test Case 2", status="Ready"),
        ]
        mock_client_factory.return_value = mock_client

        with patch("ztoq.openapi_parser.Path.exists", return_value=True):
            result = runner.invoke(
                app,
                [
                    "get-test-cases",
                    "z-openapi.yml",
                    "--base-url",
                    "https://api.example.com",
                    "--api-token",
                    "test-token",
                    "--project-key",
                    "TEST",
                ],
            )

            assert result.exit_code == 0
            assert "Found 2 test cases" in result.stdout
            assert "TEST-TC-1" in result.stdout
            assert "TEST-TC-2" in result.stdout
