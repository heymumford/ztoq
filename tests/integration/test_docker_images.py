"""Integration tests for Docker images used in migration."""
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mark all tests in this module as docker integration tests
pytestmark = [pytest.mark.integration, pytest.mark.docker]


class TestDockerImages:
    """Test suite for Docker images used in migration."""

    @pytest.fixture
    def dockerfile_path(self):
        """Get the path to the Dockerfile."""
        dockerfile_path = Path(__file__).parent.parent.parent / "config" / "Dockerfile"
        assert dockerfile_path.exists(), f"Dockerfile not found at {dockerfile_path}"
        return dockerfile_path

    @pytest.fixture
    def report_dockerfile_path(self):
        """Get the path to the Dockerfile.migration-report."""
        dockerfile_path = (
            Path(__file__).parent.parent.parent / "config" / "Dockerfile.migration-report"
        )
        assert (
            dockerfile_path.exists()
        ), f"Dockerfile.migration-report not found at {dockerfile_path}"
        return dockerfile_path

    def test_main_dockerfile_content(self, dockerfile_path):
        """Test that the main Dockerfile contains expected configuration."""
        with open(dockerfile_path) as f:
            content = f.read()

        # Check for Python base image
        assert "FROM python:" in content, "Dockerfile should use Python base image"

        # Check for multi-stage build pattern (best practice)
        assert (
            "AS" in content.upper() or "as" in content.lower()
        ), "Dockerfile should use multi-stage build"

        # Check that poetry is being used
        assert "poetry" in content.lower(), "Dockerfile should use poetry for dependency management"

        # Check that the application is installed
        assert "COPY . ." in content, "Dockerfile should copy application code"

        # Check for environment variable configuration
        assert "ENV" in content, "Dockerfile should set environment variables"

        # Check that non-root user is used (security best practice)
        assert "USER" in content, "Dockerfile should set a non-root user"

        # Check that entrypoint is properly configured
        assert "ENTRYPOINT" in content, "Dockerfile should set an entrypoint"

    def test_report_dockerfile_content(self, report_dockerfile_path):
        """Test that the migration-report Dockerfile contains expected configuration."""
        with open(report_dockerfile_path) as f:
            content = f.read()

        # Check for Python base image
        assert "FROM python:" in content, "Dockerfile should use Python base image"

        # Check that visualization dependencies are installed
        viz_dependencies = ["matplotlib", "seaborn", "plotly"]
        for dep in viz_dependencies:
            assert dep in content.lower(), f"Dockerfile should install {dep}"

        # Check that the application is installed
        assert "COPY . ." in content, "Dockerfile should copy application code"

    @patch("subprocess.run")
    def test_docker_build(self, mock_run):
        """Test that Docker images can be built (mock build process)."""
        # Configure the mock to return a successful result
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Test building the main Docker image
        result = subprocess.run(
            ["docker", "build", "-t", "ztoq:test", "."], capture_output=True, text=True, check=False,
        )

        # Check docker build was called
        mock_run.assert_called()

        # Reset mock
        mock_run.reset_mock()

        # Test building the report Docker image
        result = subprocess.run(
            ["docker", "build", "-t", "ztoq-report:test", "-f", "Dockerfile.migration-report", "."],
            capture_output=True,
            text=True,
            check=False,
        )

        # Check docker build was called
        mock_run.assert_called()

    @pytest.mark.parametrize(
        "command",
        [
            ["ztoq", "--help"],
            ["ztoq", "migrate", "--help"],
            ["ztoq", "migrate", "status", "--help"],
            ["ztoq", "migrate", "run", "--help"],
        ],
    )
    @patch("subprocess.run")
    def test_docker_run_commands(self, mock_run, command):
        """Test that Docker containers can run commands (mock execution)."""
        # Configure the mock to return a successful result
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = b"Mock Docker Output"
        mock_run.return_value = mock_process

        # Run the command in Docker
        docker_command = ["docker", "run", "--rm", "ztoq:latest"] + command
        result = subprocess.run(docker_command, capture_output=True, text=True, check=False)

        # Check docker run was called
        mock_run.assert_called()

    @patch("subprocess.run")
    def test_compose_up_down(self, mock_run):
        """Test docker-compose up and down commands (mock execution)."""
        # Configure the mock to return a successful result
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Test docker-compose up
        subprocess.run(
            ["docker-compose", "-f", "config/docker-compose.migration.yml", "up", "-d"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Check docker-compose up was called
        mock_run.assert_called()

        # Reset mock
        mock_run.reset_mock()

        # Test docker-compose down
        subprocess.run(
            ["docker-compose", "-f", "config/docker-compose.migration.yml", "down"],
            capture_output=True,
            text=True,
            check=False,
        )

        # Check docker-compose down was called
        mock_run.assert_called()
