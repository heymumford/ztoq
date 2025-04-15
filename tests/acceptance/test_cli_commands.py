"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ztoq.cli import __version__, app
from ztoq.models import ZephyrProject, ZephyrTestCase


@pytest.mark.acceptance
class TestCliCommands:
    """Test suite for CLI commands."""

    def test_version_command(self, cli_runner: CliRunner):
        """Test the --version option."""
        result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert f"ZTOQ version: {__version__}" in result.stdout

    def test_help_command(self, cli_runner: CliRunner):
        """Test the --help option."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ZTOQ - A tool for migrating test data from Zephyr Scale to qTest." in result.stdout

    @patch("ztoq.cli.load_openapi_spec")
    @patch("ztoq.cli.validate_zephyr_spec")
    def test_validate_spec_command_valid(
        self, mock_validate: MagicMock, mock_load: MagicMock, cli_runner: CliRunner, temp_output_dir: Path,
    ):
        """Test the validate command with a valid spec."""
        # Create a dummy spec file
        spec_path = temp_output_dir / "test_spec.yml"
        spec_path.touch()

        # Configure mocks
        mock_load.return_value = {"openapi": "3.0.0"}
        mock_validate.return_value = True

        result = cli_runner.invoke(app, ["validate", str(spec_path)])
        assert result.exit_code == 0
        assert "Valid Zephyr Scale API specification" in result.stdout
        mock_load.assert_called_once_with(spec_path)
        mock_validate.assert_called_once()

    @patch("ztoq.cli.load_openapi_spec")
    @patch("ztoq.cli.validate_zephyr_spec")
    def test_validate_spec_command_invalid(
        self, mock_validate: MagicMock, mock_load: MagicMock, cli_runner: CliRunner, temp_output_dir: Path,
    ):
        """Test the validate command with an invalid spec."""
        # Create a dummy spec file
        spec_path = temp_output_dir / "test_spec.yml"
        spec_path.touch()

        # Configure mocks
        mock_load.return_value = {"openapi": "3.0.0"}
        mock_validate.return_value = False

        result = cli_runner.invoke(app, ["validate", str(spec_path)])
        assert result.exit_code == 1
        assert "Not a valid Zephyr Scale API specification" in result.stdout

    @patch("ztoq.cli.load_openapi_spec")
    @patch("ztoq.cli.extract_api_endpoints")
    def test_list_endpoints_command(
        self, mock_extract: MagicMock, mock_load: MagicMock, cli_runner: CliRunner, temp_output_dir: Path,
    ):
        """Test the list-endpoints command."""
        # Create a dummy spec file
        spec_path = temp_output_dir / "test_spec.yml"
        spec_path.touch()

        # Configure mocks
        mock_load.return_value = {"openapi": "3.0.0"}
        mock_extract.return_value = {
            "endpoint1": {
                "method": "get",
                "path": "/api/v1/test-cases",
                "summary": "Get test cases",
            },
            "endpoint2": {
                "method": "post",
                "path": "/api/v1/test-cases",
                "summary": "Create test case",
            },
        }

        result = cli_runner.invoke(app, ["list-endpoints", str(spec_path)])
        assert result.exit_code == 0
        assert "Zephyr Scale API Endpoints" in result.stdout
        assert "GET" in result.stdout
        assert "POST" in result.stdout
        assert "/api/v1/test-cases" in result.stdout
        assert "Get test cases" in result.stdout
        assert "Create test case" in result.stdout

    @patch("ztoq.cli.ZephyrClient")
    def test_get_projects_command(
        self, mock_client_class: MagicMock, cli_runner: CliRunner, temp_output_dir: Path, mock_zephyr_config: dict,
    ):
        """Test the get-projects command."""
        # Create a dummy spec file
        spec_path = temp_output_dir / "test_spec.yml"
        spec_path.touch()

        # Configure mocks
        mock_client = MagicMock()
        mock_client_class.from_openapi_spec.return_value = mock_client

        mock_projects = [
            ZephyrProject(id="1", key="PROJ1", name="Project One", description="First project"),
            ZephyrProject(id="2", key="PROJ2", name="Project Two", description="Second project"),
        ]
        mock_client.get_projects.return_value = mock_projects

        # Run command
        result = cli_runner.invoke(
            app,
            [
                "get-projects",
                str(spec_path),
                "--base-url", mock_zephyr_config["base_url"],
                "--api-token", mock_zephyr_config["api_token"],
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert "Zephyr Scale Projects" in result.stdout
        assert "PROJ1" in result.stdout
        assert "Project One" in result.stdout
        assert "PROJ2" in result.stdout
        assert "Project Two" in result.stdout

    @patch("ztoq.cli.ZephyrClient")
    def test_get_projects_command_with_output_file(
        self, mock_client_class: MagicMock, cli_runner: CliRunner, temp_output_dir: Path, mock_zephyr_config: dict,
    ):
        """Test the get-projects command with output to a file."""
        # Create a dummy spec file and output file
        spec_path = temp_output_dir / "test_spec.yml"
        spec_path.touch()
        output_file = temp_output_dir / "projects.json"

        # Configure mocks
        mock_client = MagicMock()
        mock_client_class.from_openapi_spec.return_value = mock_client

        mock_projects = [
            ZephyrProject(id="1", key="PROJ1", name="Project One", description="First project"),
            ZephyrProject(id="2", key="PROJ2", name="Project Two", description="Second project"),
        ]
        mock_client.get_projects.return_value = mock_projects

        # Run command
        result = cli_runner.invoke(
            app,
            [
                "get-projects",
                str(spec_path),
                "--base-url", mock_zephyr_config["base_url"],
                "--api-token", mock_zephyr_config["api_token"],
                "--output-file", str(output_file),
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert f"Projects written to {output_file}" in result.stdout

        # Check file was created and contains the expected content
        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
            assert len(data) == 2
            assert data[0]["key"] == "PROJ1"
            assert data[1]["key"] == "PROJ2"

    @patch("ztoq.cli.ZephyrClient")
    def test_get_test_cases_command(
        self, mock_client_class: MagicMock, cli_runner: CliRunner, temp_output_dir: Path, mock_zephyr_config: dict,
    ):
        """Test the get-test-cases command."""
        # Create a dummy spec file
        spec_path = temp_output_dir / "test_spec.yml"
        spec_path.touch()

        # Configure mocks
        mock_client = MagicMock()
        mock_client_class.from_openapi_spec.return_value = mock_client

        mock_test_cases = [
            ZephyrTestCase(id="1", key="TC-1", name="Test Case 1", status="Active"),
            ZephyrTestCase(id="2", key="TC-2", name="Test Case 2", status="Draft"),
        ]
        mock_client.get_test_cases.return_value = mock_test_cases

        # Run command
        result = cli_runner.invoke(
            app,
            [
                "get-test-cases",
                str(spec_path),
                "--base-url", mock_zephyr_config["base_url"],
                "--api-token", mock_zephyr_config["api_token"],
                "--project-key", mock_zephyr_config["project_key"],
                "--limit", "10",
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert f"Fetching test cases for project: {mock_zephyr_config['project_key']}" in result.stdout
        assert "Test Cases for" in result.stdout
        assert "TC-1" in result.stdout
        assert "Test Case 1" in result.stdout
        assert "Active" in result.stdout
        assert "TC-2" in result.stdout
        assert "Test Case 2" in result.stdout
        assert "Draft" in result.stdout

    @patch("ztoq.cli.command")
    @patch("ztoq.cli.Config")
    @patch("ztoq.cli.ZephyrExportManager")
    def test_export_project_command_json_format(
        self,
        mock_export_manager_class: MagicMock,
        mock_config_class: MagicMock,
        mock_command: MagicMock,
        cli_runner: CliRunner,
        temp_output_dir: Path,
        mock_zephyr_config: dict,
    ):
        """Test the export-project command with JSON format."""
        # Create a dummy spec file
        spec_path = temp_output_dir / "test_spec.yml"
        spec_path.touch()

        # Configure mocks
        mock_export_manager = MagicMock()
        mock_export_manager_class.return_value = mock_export_manager
        mock_export_manager.export_project.return_value = {
            "test_cases": 10,
            "test_cycles": 2,
            "test_executions": 5,
        }

        # Run command
        result = cli_runner.invoke(
            app,
            [
                "export-project",
                str(spec_path),
                "--base-url", mock_zephyr_config["base_url"],
                "--api-token", mock_zephyr_config["api_token"],
                "--project-key", mock_zephyr_config["project_key"],
                "--output-dir", str(temp_output_dir),
                "--format", "json",
                "--concurrency", "2",
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert f"Exporting project {mock_zephyr_config['project_key']} to" in result.stdout
        assert "Export Summary for" in result.stdout
        assert "Test Cases" in result.stdout
        assert "10" in result.stdout
        assert "Test Cycles" in result.stdout
        assert "2" in result.stdout
        assert "Test Executions" in result.stdout
        assert "5" in result.stdout
        assert f"All test data exported to {temp_output_dir}" in result.stdout

    @patch("ztoq.cli.command")
    @patch("ztoq.cli.Config")
    @patch("ztoq.cli.SQLDatabaseManager")
    @patch("ztoq.cli.ZephyrClient")
    def test_export_project_command_sql_format(
        self,
        mock_client_class: MagicMock,
        mock_db_manager_class: MagicMock,
        mock_config_class: MagicMock,
        mock_command: MagicMock,
        cli_runner: CliRunner,
        temp_output_dir: Path,
        temp_db_path: Path,
        mock_zephyr_config: dict,
    ):
        """Test the export-project command with SQL format."""
        # Create a dummy spec file
        spec_path = temp_output_dir / "test_spec.yml"
        spec_path.touch()

        # Configure mocks
        mock_db_manager = MagicMock()
        mock_db_manager_class.return_value = mock_db_manager
        mock_db_manager.save_project_data.return_value = {
            "test_cases": 10,
            "test_cycles": 2,
            "test_executions": 5,
        }

        mock_client = MagicMock()
        mock_client_class.from_openapi_spec.return_value = mock_client
        mock_client.get_project.return_value = ZephyrProject(id="1", key=mock_zephyr_config["project_key"], name="Test Project")
        mock_client.get_folders.return_value = []
        mock_client.get_statuses.return_value = []
        mock_client.get_priorities.return_value = []
        mock_client.get_environments.return_value = []
        mock_client.get_test_cases.return_value = []
        mock_client.get_test_cycles.return_value = []
        mock_client.get_test_executions.return_value = []
        mock_client.create_fetch_result.return_value = {}

        # Run command
        result = cli_runner.invoke(
            app,
            [
                "export-project",
                str(spec_path),
                "--base-url", mock_zephyr_config["base_url"],
                "--api-token", mock_zephyr_config["api_token"],
                "--project-key", mock_zephyr_config["project_key"],
                "--output-dir", str(temp_output_dir),
                "--format", "sql",
                "--db-type", "sqlite",
                "--db-path", str(temp_db_path),
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert f"Exporting project {mock_zephyr_config['project_key']} to SQL database" in result.stdout
        assert "Export Summary for" in result.stdout
        assert "All test data exported to SQL database" in result.stdout

        # Verify the database manager was properly initialized and used
        mock_db_manager_class.assert_called_once()
        mock_db_manager.save_project_data.assert_called_once()

    @patch("ztoq.cli.command")
    @patch("ztoq.cli.Config")
    def test_db_init_command(
        self,
        mock_config_class: MagicMock,
        mock_command: MagicMock,
        cli_runner: CliRunner,
        temp_db_path: Path,
    ):
        """Test the db init command."""
        # Configure mocks
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        # Run command
        result = cli_runner.invoke(
            app,
            [
                "db", "init",
                "--db-type", "sqlite",
                "--db-path", str(temp_db_path),
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert "Applying database migrations" in result.stdout
        assert "Database schema initialized successfully" in result.stdout

        # Verify that Alembic commands were called
        mock_command.upgrade.assert_called_once_with(mock_config, "head")

    @patch("ztoq.cli.ZephyrToQTestMigration")
    @patch("ztoq.cli.command")
    @patch("ztoq.cli.Config")
    @patch("ztoq.cli.DatabaseFactory")
    def test_migrate_run_command(
        self,
        mock_db_factory: MagicMock,
        mock_config_class: MagicMock,
        mock_command: MagicMock,
        mock_migration_class: MagicMock,
        cli_runner: CliRunner,
        temp_db_path: Path,
        mock_zephyr_config: dict,
        mock_qtest_config: dict,
    ):
        """Test the migrate run command."""
        # Configure mocks
        mock_db_manager = MagicMock()
        mock_db_factory.create_database_manager.return_value = mock_db_manager

        mock_migration = MagicMock()
        mock_migration_class.return_value = mock_migration
        mock_migration.state.extraction_status = "completed"
        mock_migration.state.transformation_status = "completed"
        mock_migration.state.loading_status = "completed"
        mock_migration.state.error_message = None

        # Run command
        result = cli_runner.invoke(
            app,
            [
                "migrate", "run",
                "--zephyr-base-url", mock_zephyr_config["base_url"],
                "--zephyr-api-token", mock_zephyr_config["api_token"],
                "--zephyr-project-key", mock_zephyr_config["project_key"],
                "--qtest-base-url", mock_qtest_config["base_url"],
                "--qtest-username", mock_qtest_config["username"],
                "--qtest-password", mock_qtest_config["password"],
                "--qtest-project-id", str(mock_qtest_config["project_id"]),
                "--db-type", "sqlite",
                "--db-path", str(temp_db_path),
                "--phase", "all",
                "--batch-size", "50",
                "--max-workers", "5",
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert f"Starting migration for project {mock_zephyr_config['project_key']} to qTest project {mock_qtest_config['project_id']}" in result.stdout
        assert "Running phases: extract, transform, load" in result.stdout
        assert "Migration Status for" in result.stdout
        assert "Migration completed successfully" in result.stdout

        # Verify that the migration was properly initialized and run
        mock_migration_class.assert_called_once()
        mock_migration.run_migration.assert_called_once_with(phases=["extract", "transform", "load"])
