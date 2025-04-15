"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for CLI framework and command parsing.

These tests verify the CLI framework functionality, including command parsing,
option handling, and debug mode.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ztoq.cli import app


@pytest.mark.unit
class TestCLIFramework:
    """Tests for the CLI framework and command parsing functionality."""

    runner = CliRunner()

    def test_cli_version(self):
        """Test that the version flag works."""
        with patch("ztoq.cli.__version__", "0.4.0"):
            result = self.runner.invoke(app, ["--version"])
            assert result.exit_code == 0
            assert "0.4.0" in result.stdout

    def test_validate_command(self):
        """Test the validate command parsing."""
        # Create a temporary spec file for validation
        test_spec = Path("test_spec.yml")
        try:
            # Create a minimal spec file
            test_spec.write_text("""
            openapi: 3.0.0
            info:
              title: Test API
              version: 1.0.0
            paths:
              /api/v1/test:
                get:
                  summary: Test endpoint
                  responses:
                    200:
                      description: OK
            """)

            # Mock the validation function to always return True
            with patch("ztoq.cli.validate_zephyr_spec", return_value=True):
                result = self.runner.invoke(app, ["validate", str(test_spec)])
                assert result.exit_code == 0
                assert "Validating OpenAPI spec" in result.stdout
                assert "Valid Zephyr Scale API specification" in result.stdout

            # Test with validation failure
            with patch("ztoq.cli.validate_zephyr_spec", return_value=False):
                result = self.runner.invoke(app, ["validate", str(test_spec)])
                assert result.exit_code == 1
                assert "Not a valid Zephyr Scale API specification" in result.stdout

            # Test with nonexistent file
            result = self.runner.invoke(app, ["validate", "nonexistent.yml"])
            assert result.exit_code == 1
            assert "Error:" in result.stdout
        finally:
            # Clean up
            if test_spec.exists():
                test_spec.unlink()

    def test_list_endpoints_command(self):
        """Test the list-endpoints command parsing."""
        test_spec = Path("test_spec.yml")
        try:
            # Create a minimal spec file
            test_spec.write_text("""
            openapi: 3.0.0
            info:
              title: Test API
              version: 1.0.0
            paths:
              /api/v1/test:
                get:
                  summary: Test endpoint
                  responses:
                    200:
                      description: OK
            """)

            # Mock the function to return an endpoint
            mock_endpoints = {
                "get-test": {
                    "method": "get",
                    "path": "/api/v1/test",
                    "summary": "Test endpoint",
                },
            }
            with patch("ztoq.cli.extract_api_endpoints", return_value=mock_endpoints):
                result = self.runner.invoke(app, ["list-endpoints", str(test_spec)])
                assert result.exit_code == 0
                assert "Test endpoint" in result.stdout
        finally:
            # Clean up
            if test_spec.exists():
                test_spec.unlink()

    @patch("ztoq.cli.ZephyrClient")
    def test_get_projects_command(self, mock_client):
        """Test the get-projects command parsing."""
        # Setup mock
        mock_instance = MagicMock()
        mock_client.from_openapi_spec.return_value = mock_instance
        mock_instance.get_projects.return_value = [
            MagicMock(key="PROJ1", name="Project 1", id="1"),
            MagicMock(key="PROJ2", name="Project 2", id="2"),
        ]

        # Test command
        result = self.runner.invoke(app, [
            "get-projects",
            "--spec-path", "fake_spec.yml",
            "--base-url", "https://example.com",
            "--api-token", "fake-token",
        ])

        assert result.exit_code == 0
        assert "PROJ1" in result.stdout
        assert "PROJ2" in result.stdout
        assert "Project 1" in result.stdout
        assert "Project 2" in result.stdout

    @patch("ztoq.cli.ZephyrClient")
    def test_get_test_cases_command(self, mock_client):
        """Test the get-test-cases command parsing."""
        # Setup mock
        mock_instance = MagicMock()
        mock_client.from_openapi_spec.return_value = mock_instance
        mock_instance.get_test_cases.return_value = [
            MagicMock(key="TEST-1", name="Test Case 1", status="Active"),
            MagicMock(key="TEST-2", name="Test Case 2", status="Draft"),
        ]

        # Test command
        result = self.runner.invoke(app, [
            "get-test-cases",
            "--spec-path", "fake_spec.yml",
            "--base-url", "https://example.com",
            "--api-token", "fake-token",
            "--project-key", "TEST",
            "--limit", "2",
        ])

        assert result.exit_code == 0
        assert "TEST-1" in result.stdout
        assert "TEST-2" in result.stdout
        assert "Test Case 1" in result.stdout
        assert "Test Case 2" in result.stdout

    def test_debug_mode_flag(self):
        """Test the debug mode flag sets the correct log level."""
        # Patch the configure_app function to capture the debug flag
        with patch("ztoq.cli.configure_app") as mock_configure:
            # Using the --debug flag
            result = self.runner.invoke(app, ["--debug", "validate", "fake_spec.yml"])
            # Check debug flag was passed to configure_app
            mock_configure.assert_called_with(debug=True)

        # Test without debug flag
        with patch("ztoq.cli.configure_app") as mock_configure:
            result = self.runner.invoke(app, ["validate", "fake_spec.yml"])
            # Check debug flag is False
            mock_configure.assert_called_with(debug=False)


@pytest.mark.unit
class TestCLIEnvironmentVariables:
    """Tests for CLI environment variable handling."""

    def test_environment_variables_precedence(self):
        """Test that environment variables have the correct precedence."""
        # Environment variables should take precedence over defaults but not over CLI arguments

        # Test environment variables for PostgreSQL configuration
        with patch.dict(os.environ, {
            "ZTOQ_PG_HOST": "env-host",
            "ZTOQ_PG_PORT": "5433",
            "ZTOQ_PG_USER": "env-user",
            "ZTOQ_PG_PASSWORD": "env-pass",
            "ZTOQ_PG_DATABASE": "env-db",
        }):
            # Mock database initialization to avoid actual database access
            with patch("ztoq.cli.SQLDatabaseManager") as mock_db:
                with patch("ztoq.cli.command.upgrade") as mock_upgrade:
                    with patch("ztoq.cli.console.print") as mock_print:
                        # Call a command that uses environment variables
                        from ztoq.cli import app
                        runner = CliRunner()
                        runner.invoke(app, ["db", "init", "--db-type", "postgresql"])

                        # Check that environment variables were used
                        mock_print.assert_any_call("Using PostgreSQL settings from environment variables", style="blue")

                        # CLI arguments should take precedence over environment variables
                        runner.invoke(app, [
                            "db", "init",
                            "--db-type", "postgresql",
                            "--host", "cli-host",
                            "--username", "cli-user",
                            "--database", "cli-db",
                        ])

                        # Check the config passed to the database manager
                        db_config = mock_db.call_args[1]["config"]
                        assert db_config.host == "cli-host"
                        assert db_config.username == "cli-user"
                        assert db_config.database == "cli-db"


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
