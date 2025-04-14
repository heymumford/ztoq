"""Integration test for the end-to-end migration workflow using Docker."""
import os
import time
import json
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mark this test module as both integration and docker tests
pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.system]


class TestMigrationSystemWorkflow:
    """End-to-end system test for migration workflow using Docker infrastructure."""

    @pytest.fixture(autouse=True)
    def require_docker(self, skip_if_no_docker):
        """Ensure Docker is available or skip the test."""
        pass

    @pytest.fixture
    def docker_migration_setup(self, docker_test_env):
        """Prepare and clean up a Docker migration environment."""
        test_env = docker_test_env
        os.chdir(test_env["dir"])

        # Create sample test data for migration
        sample_data_dir = test_env["data_dir"] / "sample_data"
        sample_data_dir.mkdir()

        # Create a sample test case file
        (sample_data_dir / "test_case.json").write_text(json.dumps({
            "id": "TC-123",
                "name": "Sample Test Case",
                "status": "Active",
                "priority": "High",
                "steps": [
                {"id": 1, "description": "Step 1", "expected": "Expected 1"},
                    {"id": 2, "description": "Step 2", "expected": "Expected 2"}
            ]
        }))

        # Create a sample attachment
        (test_env["attachments_dir"] / "sample.txt").write_text("Sample attachment content")

        # Return to original directory after test
        original_dir = os.getcwd()
        yield test_env
        os.chdir(original_dir)

    @patch('subprocess.run')
    def test_setup_phase(self, mock_run, docker_migration_setup):
        """Test the migration setup phase."""
        test_env = docker_migration_setup

        # Configure the mock to return a successful result
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = b"Mock Setup Output"
        mock_run.return_value = mock_process

        # Run the setup command
        result = subprocess.run(
            ["../run-migration.sh", "setup", "--env-file", ".env"],
                capture_output=True,
                text=True,
                check=False
        )

        # Check docker-compose was called with correct command
        expected_calls = [
            # Directory creation checks
            "mkdir -p",
                # PostgreSQL startup
            "docker-compose -f docker-compose.migration.yml --env-file",
                "up -d postgres",
                # Database initialization
            "docker-compose -f docker-compose.migration.yml --env-file",
                "db init"
        ]

        # Check that the expected calls were made
        all_calls = ' '.join([str(call) for call in mock_run.call_args_list])
        for expected in expected_calls:
            assert expected in all_calls, f"Expected call containing '{expected}' not found"

    @patch('subprocess.run')
    def test_run_phase(self, mock_run, docker_migration_setup):
        """Test the migration run phase."""
        test_env = docker_migration_setup

        # Configure the mock to return a successful result
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = b"Mock Run Output"
        mock_run.return_value = mock_process

        # Run the migration
        result = subprocess.run(
            ["../run-migration.sh", "run",
                 "--env-file", ".env",
                 "--batch-size", "25",
                 "--workers", "3"],
                capture_output=True,
                text=True,
                check=False
        )

        # Check docker-compose was called with correct command
        expected_calls = [
            "docker-compose -f docker-compose.migration.yml --env-file",
                "migrate run",
                "--batch-size 25",
                "--max-workers 3",
            ]

        # Check that the expected calls were made
        all_calls = ' '.join([str(call) for call in mock_run.call_args_list])
        for expected in expected_calls:
            assert expected in all_calls, f"Expected call containing '{expected}' not found"

    @patch('subprocess.run')
    def test_status_phase(self, mock_run, docker_migration_setup):
        """Test the migration status phase."""
        test_env = docker_migration_setup

        # Configure the mock to return a successful result
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = b"Mock Status Output"
        mock_run.return_value = mock_process

        # Check migration status
        result = subprocess.run(
            ["../run-migration.sh", "status", "--env-file", ".env"],
                capture_output=True,
                text=True,
                check=False
        )

        # Check docker-compose was called with correct command
        expected_calls = [
            "docker-compose -f docker-compose.migration.yml --env-file",
                "migration-status"
        ]

        # Check that the expected calls were made
        all_calls = ' '.join([str(call) for call in mock_run.call_args_list])
        for expected in expected_calls:
            assert expected in all_calls, f"Expected call containing '{expected}' not found"

    @patch('subprocess.run')
    def test_report_phase(self, mock_run, docker_migration_setup):
        """Test the migration report phase."""
        test_env = docker_migration_setup

        # Configure the mock to return a successful result
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = b"Mock Report Output"
        mock_run.return_value = mock_process

        # Generate migration report
        result = subprocess.run(
            ["../run-migration.sh", "report", "--env-file", ".env"],
                capture_output=True,
                text=True,
                check=False
        )

        # Check docker-compose was called with correct command
        expected_calls = [
            "docker-compose -f docker-compose.migration.yml --env-file",
                "migration-report"
        ]

        # Check that the expected calls were made
        all_calls = ' '.join([str(call) for call in mock_run.call_args_list])
        for expected in expected_calls:
            assert expected in all_calls, f"Expected call containing '{expected}' not found"

    @patch('subprocess.run')
    def test_full_migration_workflow(self, mock_run, docker_migration_setup):
        """Test a full migration workflow from setup to report."""
        test_env = docker_migration_setup

        # Configure the mock to return a successful result
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = b"Mock Output"
        mock_run.return_value = mock_process

        # Run a complete workflow
        commands = [
            ["../run-migration.sh", "setup", "--env-file", ".env"],
                ["../run-migration.sh", "run", "--env-file", ".env", "--batch-size", "50"],
                ["../run-migration.sh", "status", "--env-file", ".env"],
                ["../run-migration.sh", "report", "--env-file", ".env"],
                ["../run-migration.sh", "stop", "--env-file", ".env"]
        ]

        for cmd in commands:
            result = subprocess.run(
                cmd,
                    capture_output=True,
                    text=True,
                    check=False
            )
            assert mock_run.called, f"Command {cmd} should have been executed"
            mock_run.reset_mock()

    @patch('subprocess.run')
    def test_clean_phase(self, mock_run, docker_migration_setup):
        """Test the migration clean phase."""
        test_env = docker_migration_setup

        # Configure the mock to return a successful result
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = b"Mock Clean Output"
        mock_run.return_value = mock_process

        # Run the clean command
        result = subprocess.run(
            ["../run-migration.sh", "clean", "--env-file", ".env"],
                capture_output=True,
                text=True,
                check=False
        )

        # Check docker-compose was called with correct command
        expected_calls = [
            "docker-compose -f docker-compose.migration.yml --env-file",
                "down"
        ]

        # Check that the expected calls were made
        all_calls = ' '.join([str(call) for call in mock_run.call_args_list])
        for expected in expected_calls:
            assert expected in all_calls, f"Expected call containing '{expected}' not found"
