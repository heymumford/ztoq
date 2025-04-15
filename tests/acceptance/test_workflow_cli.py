"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from ztoq.workflow_cli import workflow_app


@pytest.mark.acceptance
class TestWorkflowCliCommands:
    """Test suite for workflow CLI commands."""

    @patch("ztoq.workflow_cli.WorkflowOrchestrator")
    def test_workflow_run_command(
        self,
        mock_orchestrator_class: MagicMock,
        cli_runner: CliRunner,
        temp_output_dir: Path,
        temp_db_path: Path,
        mock_zephyr_config: dict,
        mock_qtest_config: dict,
    ):
        """Test the workflow run command."""
        # Configure mocks
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # Mock the run_workflow method to return results
        async_mock = AsyncMock(return_value={"status": "completed"})
        mock_orchestrator.run_workflow = async_mock

        # Run command
        result = cli_runner.invoke(
            workflow_app,
            [
                "run",
                "--project-key", mock_zephyr_config["project_key"],
                "--db-type", "sqlite",
                "--db-path", str(temp_db_path),
                "--zephyr-base-url", mock_zephyr_config["base_url"],
                "--zephyr-api-token", mock_zephyr_config["api_token"],
                "--qtest-base-url", mock_qtest_config["base_url"],
                "--qtest-username", mock_qtest_config["username"],
                "--qtest-password", mock_qtest_config["password"],
                "--qtest-project-id", str(mock_qtest_config["project_id"]),
                "--phases", "all",
                "--batch-size", "50",
                "--max-workers", "5",
                "--output-dir", str(temp_output_dir),
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert f"Starting workflow for project {mock_zephyr_config['project_key']}" in result.stdout
        assert "Workflow completed" in result.stdout

        # Verify that the orchestrator was properly initialized and run
        mock_orchestrator_class.assert_called_once()
        assert mock_orchestrator.run_workflow.called

    @patch("ztoq.workflow_cli.WorkflowOrchestrator")
    def test_workflow_resume_command(
        self,
        mock_orchestrator_class: MagicMock,
        cli_runner: CliRunner,
        temp_output_dir: Path,
        temp_db_path: Path,
        mock_zephyr_config: dict,
        mock_qtest_config: dict,
    ):
        """Test the workflow resume command."""
        # Configure mocks
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # Mock the resume_workflow method to return results
        mock_orchestrator.resume_workflow.return_value = {"status": "completed"}

        # Run command
        result = cli_runner.invoke(
            workflow_app,
            [
                "resume",
                "--project-key", mock_zephyr_config["project_key"],
                "--db-type", "sqlite",
                "--db-path", str(temp_db_path),
                "--zephyr-base-url", mock_zephyr_config["base_url"],
                "--zephyr-api-token", mock_zephyr_config["api_token"],
                "--qtest-base-url", mock_qtest_config["base_url"],
                "--qtest-username", mock_qtest_config["username"],
                "--qtest-password", mock_qtest_config["password"],
                "--qtest-project-id", str(mock_qtest_config["project_id"]),
                "--checkpoint-id", "latest",
                "--output-dir", str(temp_output_dir),
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert f"Resuming workflow for project {mock_zephyr_config['project_key']}" in result.stdout
        assert "Workflow resumed and completed" in result.stdout

        # Verify that the orchestrator was properly initialized and run
        mock_orchestrator_class.assert_called_once()
        assert mock_orchestrator.initialize_checkpoint_manager.called

    @patch("ztoq.workflow_cli.WorkflowOrchestrator")
    def test_workflow_status_command(
        self,
        mock_orchestrator_class: MagicMock,
        cli_runner: CliRunner,
        temp_db_path: Path,
        mock_zephyr_config: dict,
    ):
        """Test the workflow status command."""
        # Configure mocks
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # Mock the get_workflow_status method to return status
        mock_orchestrator.get_workflow_status.return_value = {
            "project_key": mock_zephyr_config["project_key"],
            "phases": {
                "extract": "completed",
                "transform": "completed",
                "load": "in_progress",
                "validate": "not_started",
            },
            "entity_counts": {
                "source": {"test_cases": 100},
                "target": {"test_cases": 50},
                "mappings": {"test_cases": 50},
            },
            "events": [{"timestamp": "2025-01-01T12:00:00", "phase": "load", "status": "in_progress", "message": "Loading test cases"}],
        }

        # Run command
        result = cli_runner.invoke(
            workflow_app,
            [
                "status",
                "--project-key", mock_zephyr_config["project_key"],
                "--db-type", "sqlite",
                "--db-path", str(temp_db_path),
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert f"Workflow Status for Project: {mock_zephyr_config['project_key']}" in result.stdout

        # Verify that the orchestrator was properly initialized and used
        mock_orchestrator_class.assert_called_once()
        mock_orchestrator.get_workflow_status.assert_called_once()
        mock_orchestrator.print_workflow_status.assert_called_once()

    @patch("ztoq.workflow_cli.WorkflowOrchestrator")
    def test_workflow_report_command(
        self,
        mock_orchestrator_class: MagicMock,
        cli_runner: CliRunner,
        temp_output_dir: Path,
        temp_db_path: Path,
        mock_zephyr_config: dict,
    ):
        """Test the workflow report command."""
        # Configure mocks
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # Create report file path
        report_path = temp_output_dir / "report.json"

        # Run command
        result = cli_runner.invoke(
            workflow_app,
            [
                "report",
                "--project-key", mock_zephyr_config["project_key"],
                "--db-type", "sqlite",
                "--db-path", str(temp_db_path),
                "--output-file", str(report_path),
                "--report-format", "json",
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert f"JSON report saved to: {report_path}" in result.stdout

        # Verify that the orchestrator was properly initialized and used
        mock_orchestrator_class.assert_called_once()
        mock_orchestrator.create_workflow_report.assert_called_once_with(str(report_path))

    @patch("ztoq.workflow_cli.get_database_manager")
    def test_workflow_cleanup_command(
        self,
        mock_get_db_manager: MagicMock,
        cli_runner: CliRunner,
        temp_db_path: Path,
        mock_zephyr_config: dict,
    ):
        """Test the workflow cleanup command."""
        # Configure mocks
        mock_db_manager = MagicMock()
        mock_get_db_manager.return_value = mock_db_manager

        # Run command with confirm flag to skip the confirmation prompt
        result = cli_runner.invoke(
            workflow_app,
            [
                "cleanup",
                "--project-key", mock_zephyr_config["project_key"],
                "--db-type", "sqlite",
                "--db-path", str(temp_db_path),
                "--confirm",  # Skip confirmation prompt
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert f"Cleaning up workflow data for project {mock_zephyr_config['project_key']}" in result.stdout
        assert "Cleanup completed successfully" in result.stdout

        # Verify that the database manager was properly used
        mock_get_db_manager.assert_called_once()
        assert mock_db_manager.delete_workflow_events.called
        assert mock_db_manager.delete_validation_issues.called
        assert mock_db_manager.delete_validation_reports.called
        assert mock_db_manager.delete_entity_mappings.called
        assert mock_db_manager.delete_entity_batches.called
        assert mock_db_manager.delete_migration_state.called

    @patch("ztoq.workflow_cli.WorkflowOrchestrator")
    def test_workflow_transform_command(
        self,
        mock_orchestrator_class: MagicMock,
        cli_runner: CliRunner,
        temp_output_dir: Path,
        temp_db_path: Path,
        mock_zephyr_config: dict,
    ):
        """Test the workflow transform command."""
        # Configure mocks
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # Mock the _run_transform_phase method to return results
        async_mock = AsyncMock(return_value={"status": "completed", "processed": 10, "successful": 10, "failed": 0})
        mock_orchestrator._run_transform_phase = async_mock

        # Mock the _run_validation_phase method to return results
        validation_mock = AsyncMock(return_value={
            "total_issues": 0,
            "critical_issues": 0,
            "error_issues": 0,
            "warning_issues": 0,
            "info_issues": 0,
            "recent_issues": [],
        })
        mock_orchestrator._run_validation_phase = validation_mock

        # Mock get_workflow_status to return events
        mock_orchestrator.get_workflow_status.return_value = {
            "events": [
                {
                    "message": "Batch transformation completed",
                    "metadata": {
                        "total": 10,
                        "successful": 10,
                        "failed": 0,
                        "warnings": 0,
                        "batches": 1,
                    },
                },
            ],
        }

        # Run command
        result = cli_runner.invoke(
            workflow_app,
            [
                "transform",
                "--project-key", mock_zephyr_config["project_key"],
                "--db-type", "sqlite",
                "--db-path", str(temp_db_path),
                "--batch-size", "50",
                "--validate",
                "--output-dir", str(temp_output_dir),
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert f"Starting transformation for project {mock_zephyr_config['project_key']}" in result.stdout
        assert "Transformation completed" in result.stdout
        assert "Validation Results" in result.stdout

        # Verify that the orchestrator was properly initialized and used
        mock_orchestrator_class.assert_called_once()
        assert mock_orchestrator._run_transform_phase.called
        assert mock_orchestrator._run_validation_phase.called

    @patch("ztoq.workflow_cli.WorkflowOrchestrator")
    def test_workflow_validate_command(
        self,
        mock_orchestrator_class: MagicMock,
        cli_runner: CliRunner,
        temp_output_dir: Path,
        temp_db_path: Path,
        mock_zephyr_config: dict,
    ):
        """Test the workflow validate command."""
        # Configure mocks
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # Mock the _run_validation_phase method to return results
        async_mock = AsyncMock(return_value={
            "total_issues": 2,
            "critical_issues": 0,
            "error_issues": 0,
            "warning_issues": 1,
            "info_issues": 1,
            "recent_issues": [
                {"level": "warning", "message": "Missing description", "entity_id": "TC-1"},
                {"level": "info", "message": "Field mapping successful", "entity_id": "TC-2"},
            ],
        })
        mock_orchestrator._run_validation_phase = async_mock

        # Create output file path
        output_file = temp_output_dir / "validation.json"

        # Run command
        result = cli_runner.invoke(
            workflow_app,
            [
                "validate",
                "--project-key", mock_zephyr_config["project_key"],
                "--db-type", "sqlite",
                "--db-path", str(temp_db_path),
                "--output-file", str(output_file),
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert f"Running validation for project {mock_zephyr_config['project_key']}" in result.stdout
        assert "Validation completed" in result.stdout
        assert "Validation Summary" in result.stdout
        assert "Recent Validation Issues" in result.stdout
        assert f"Validation report saved to: {output_file}" in result.stdout

        # Verify that the orchestrator was properly initialized and used
        mock_orchestrator_class.assert_called_once()
        assert mock_orchestrator._run_validation_phase.called
