"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from typer.testing import CliRunner
from ztoq.cli import app
from ztoq.models import Project, TestCase

@pytest.mark.integration()


class TestCLICommands:
    @pytest.fixture()
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.fixture()
    def mock_openapi_spec(self):
        """Mock OpenAPI spec loading."""
        valid_spec = {
            "openapi": "3.0.0",
                "info": {"title": "Zephyr Scale API", "version": "1.0.0"},
                "paths": {
                "/testcases": {
                    "get": {
                        "summary": "Get test cases",
                            "description": "Get all test cases",
                        }
                }
            },
            }
        with patch("ztoq.cli.load_openapi_spec", return_value=valid_spec):
            yield valid_spec

    def test_validate_command_valid(self, runner, mock_openapi_spec):
        """Test the validate command with a valid spec."""
        with patch("ztoq.cli.Path.exists", return_value=True):
            result = runner.invoke(app, ["validate", "z-openapi.yml"])
            assert result.exit_code == 0
            assert "Valid Zephyr Scale API specification" in result.stdout

    def test_validate_command_invalid(self, runner):
        """Test the validate command with an invalid spec."""
        invalid_spec = {
            "openapi": "3.0.0",
                "info": {"title": "Some Other API", "version": "1.0.0"},
                "paths": {},
            }
        with patch("ztoq.cli.load_openapi_spec", return_value=invalid_spec):
            with patch("ztoq.cli.Path.exists", return_value=True):
                result = runner.invoke(app, ["validate", "z-openapi.yml"])
                assert result.exit_code == 1
                assert "Not a valid Zephyr Scale API specification" in result.stdout

    def test_validate_command_file_not_found(self, runner):
        """Test the validate command with a missing file."""
        with patch("ztoq.cli.load_openapi_spec", side_effect=FileNotFoundError("File not found")):
            result = runner.invoke(app, ["validate", "nonexistent.yml"])
            assert result.exit_code == 1
            assert "Error: File not found" in result.stdout

    def test_list_endpoints_command(self, runner, mock_openapi_spec):
        """Test the list-endpoints command."""
        with patch("ztoq.cli.Path.exists", return_value=True):
            result = runner.invoke(app, ["list-endpoints", "z-openapi.yml"])
            assert result.exit_code == 0
            assert "Zephyr Scale API Endpoints" in result.stdout
            assert "GET" in result.stdout
            assert "/testcases" in result.stdout

    @patch("ztoq.cli.ZephyrClient")
    def test_get_projects_command(self, mock_client_class, runner, mock_openapi_spec):
        """Test the get-projects command."""
        # Setup mock client
        mock_client = MagicMock()
        mock_client.get_projects.return_value = [
            Project(id="1", key="PROJ1", name="Project 1"),
                Project(id="2", key="PROJ2", name="Project 2"),
            ]
        mock_client_class.from_openapi_spec.return_value = mock_client

        with patch("ztoq.cli.Path.exists", return_value=True):
            result = runner.invoke(
                app,
                    [
                    "get-projects",
                        "z-openapi.yml",
                        "--base-url",
                        "https://api.example.com",
                        "--api-token",
                        "test-token",
                    ],
                )

            assert result.exit_code == 0
            assert "Found 2 projects" in result.stdout
            assert "PROJ1" in result.stdout
            assert "PROJ2" in result.stdout

    @patch("ztoq.cli.ZephyrClient")
    def test_get_test_cases_command(self, mock_client_class, runner, mock_openapi_spec, tmp_path):
        """Test the get-test-cases command."""
        # Setup mock client
        mock_client = MagicMock()
        test_cases = [
            TestCase(id="1", key="TEST-TC-1", name="Test Case 1", status="Draft"),
                TestCase(id="2", key="TEST-TC-2", name="Test Case 2", status="Ready"),
            ]
        # Use a side effect to properly handle the iterator behavior
        mock_client.get_test_cases.return_value.__iter__.return_value = iter(test_cases)
        mock_client_class.from_openapi_spec.return_value = mock_client

        # Create a temporary output file
        output_file = tmp_path / "test_cases.json"

        with patch("ztoq.cli.Path.exists", return_value=True):
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
                        "--output-file",
                        str(output_file),
                        "--limit",
                        "2",
                    ],
                )

            assert result.exit_code == 0
            assert "Found 2 test cases" in result.stdout
            assert f"Test cases written to {output_file}" in result.stdout

            # Verify the output file
            assert output_file.exists()
            with open(output_file) as f:
                saved_cases = json.load(f)
                assert len(saved_cases) == 2
                assert saved_cases[0]["key"] == "TEST-TC-1"
                assert saved_cases[1]["key"] == "TEST-TC-2"

    @patch("ztoq.cli.ZephyrExportManager")
    def test_export_project_command(
        self, mock_export_manager_class, runner, mock_openapi_spec, tmp_path
    ):
        """Test the export-project command."""
        # Setup mock export manager
        mock_export_manager = MagicMock()
        mock_export_manager.export_project.return_value = {
            "test_cases": 10,
                "test_cycles": 5,
                "test_executions": 20,
                "folders": 3,
                "statuses": 4,
                "priorities": 3,
                "environments": 2,
            }
        mock_export_manager_class.return_value = mock_export_manager

        output_dir = tmp_path / "export"

        with patch("ztoq.cli.Path.exists", return_value=True):
            result = runner.invoke(
                app,
                    [
                    "export-project",
                        "z-openapi.yml",
                        "--base-url",
                        "https://api.example.com",
                        "--api-token",
                        "test-token",
                        "--project-key",
                        "TEST",
                        "--output-dir",
                        str(output_dir),
                        "--format",
                        "json",
                        "--concurrency",
                        "2",
                    ],
                )

            assert result.exit_code == 0
            assert "Export Summary for TEST" in result.stdout
            assert "Test Cases" in result.stdout
            assert "10" in result.stdout  # Test case count

            # Verify export manager was called
            mock_export_manager_class.assert_called_once()
            mock_export_manager.export_project.assert_called_once_with("TEST", progress=pytest.any)
