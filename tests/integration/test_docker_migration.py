"""Integration tests for Docker-based migration functionality."""
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mark all tests in this module as docker integration tests
pytestmark = [pytest.mark.integration, pytest.mark.docker]


class TestDockerMigration:
    """Test suite for Docker-based migration system."""

    @pytest.fixture
    def docker_env(self, tmp_path):
        """Set up a test environment for Docker-based migration testing."""
        # Create temporary directories
        test_dir = tmp_path / "docker_test"
        test_dir.mkdir()

        # Create necessary subdirectories
        (test_dir / "attachments").mkdir()
        (test_dir / "migration_data").mkdir()
        (test_dir / "reports").mkdir()

        # Create test .env file
        env_file = test_dir / ".env"
        env_file.write_text(
            "ZEPHYR_BASE_URL=https://example.com/api/v2\n"
            "ZEPHYR_API_TOKEN=test_token\n"
            "ZEPHYR_PROJECT_KEY=TEST\n"
            "QTEST_BASE_URL=https://qtest.example.com\n"
            "QTEST_USERNAME=test_user\n"
            "QTEST_PASSWORD=test_password\n"
            "QTEST_PROJECT_ID=12345\n",
        )

        # Copy necessary Docker files to temp directory
        original_dir = Path(__file__).parent.parent.parent

        # Return paths for use in tests
        return {"test_dir": test_dir, "env_file": env_file, "original_dir": original_dir}

    @pytest.fixture
    def mock_docker_compose(self):
        """Mock subprocess calls to docker-compose for testing without actual Docker."""
        with patch("subprocess.run") as mock_run:
            # Configure the mock to return a successful result
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = b"Mock Docker Compose Output"
            mock_run.return_value = mock_process
            yield mock_run

    def test_run_script_setup_command(self, docker_env, mock_docker_compose):
        """Test the setup command in run-migration.sh script."""
        # Mock environment
        env = os.environ.copy()
        env["PATH"] = str(docker_env["original_dir"]) + ":" + env["PATH"]

        # Test the setup command
        with patch("os.chdir"):
            result = subprocess.run(
                [
                    str(docker_env["original_dir"] / "utils" / "run-migration.sh"),
                    "setup",
                    "--env-file",
                    str(docker_env["env_file"]),
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        # Verify docker-compose was called correctly for setup
        setup_calls = [
            call for call in mock_docker_compose.call_args_list if "up -d postgres" in str(call)
        ]
        assert len(setup_calls) > 0, "docker-compose up postgres should be called"

        # Verify db init was called
        init_calls = [call for call in mock_docker_compose.call_args_list if "db init" in str(call)]
        assert len(init_calls) > 0, "db init should be called"

    def test_run_script_migration_command(self, docker_env, mock_docker_compose):
        """Test the run command in run-migration.sh script."""
        # Mock environment
        env = os.environ.copy()
        env["PATH"] = str(docker_env["original_dir"]) + ":" + env["PATH"]

        # Test the run command with custom parameters
        with patch("os.chdir"):
            result = subprocess.run(
                [
                    str(docker_env["original_dir"] / "utils" / "run-migration.sh"),
                    "run",
                    "--env-file",
                    str(docker_env["env_file"]),
                    "--batch-size",
                    "100",
                    "--workers",
                    "10",
                    "--phase",
                    "extract",
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        # Verify docker-compose was called correctly with the right parameters
        run_calls = [
            call
            for call in mock_docker_compose.call_args_list
            if "migrate run" in str(call)
            and "--batch-size 100" in str(call)
            and "--max-workers 10" in str(call)
            and "--phase extract" in str(call)
        ]
        assert len(run_calls) > 0, "migrate run should be called with correct parameters"

    def test_run_script_status_command(self, docker_env, mock_docker_compose):
        """Test the status command in run-migration.sh script."""
        # Mock environment
        env = os.environ.copy()
        env["PATH"] = str(docker_env["original_dir"]) + ":" + env["PATH"]

        # Test the status command
        with patch("os.chdir"):
            result = subprocess.run(
                [
                    str(docker_env["original_dir"] / "utils" / "run-migration.sh"),
                    "status",
                    "--env-file",
                    str(docker_env["env_file"]),
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        # Verify docker-compose was called correctly
        status_calls = [
            call for call in mock_docker_compose.call_args_list if "migration-status" in str(call)
        ]
        assert len(status_calls) > 0, "migration-status should be called"

    def test_run_script_report_command(self, docker_env, mock_docker_compose):
        """Test the report command in run-migration.sh script."""
        # Mock environment
        env = os.environ.copy()
        env["PATH"] = str(docker_env["original_dir"]) + ":" + env["PATH"]

        # Test the report command
        with patch("os.chdir"):
            result = subprocess.run(
                [
                    str(docker_env["original_dir"] / "utils" / "run-migration.sh"),
                    "report",
                    "--env-file",
                    str(docker_env["env_file"]),
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

        # Verify docker-compose was called correctly
        report_calls = [
            call for call in mock_docker_compose.call_args_list if "migration-report" in str(call)
        ]
        assert len(report_calls) > 0, "migration-report should be called"
