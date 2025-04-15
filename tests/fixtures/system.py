"""
System test fixtures for the ZTOQ testing framework.

This module provides fixtures specifically designed for system tests,
focusing on testing the complete application with real dependencies.
"""

import os
import sys
import pytest
import subprocess
from pathlib import Path
from typing import Dict, Any, Generator, Optional, List
from unittest.mock import MagicMock, patch

# Import the base fixtures
from tests.fixtures.base import base_test_env, mock_env_vars, temp_dir, temp_file, temp_db_path


@pytest.fixture
def skip_if_no_docker() -> None:
    """
    Skip a test if Docker is not available.

    This fixture checks if Docker is available on the system and skips
    the test if it's not, which is useful for system tests that require
    Docker to run.
    """
    if os.environ.get("SKIP_DOCKER_TESTS") == "1":
        pytest.skip("Skipping Docker test due to SKIP_DOCKER_TESTS=1")

    try:
        result = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            pytest.skip("Docker not available")
    except (FileNotFoundError, subprocess.SubprocessError):
        pytest.skip("Docker not available")


@pytest.fixture
def docker_compose_env(
    temp_dir: Path, base_test_env: Dict[str, str]
) -> Generator[Dict[str, Any], None, None]:
    """
    Set up a Docker Compose environment for system testing.

    This fixture creates a test environment suitable for running
    Docker Compose-based system tests, including creating necessary
    directories and files.

    Args:
        temp_dir: Temporary directory for test files
        base_test_env: Base testing environment variables

    Yields:
        Dict[str, Any]: Dictionary containing Docker Compose test environment details
    """
    # Create necessary directories for Docker tests
    docker_test_dir = temp_dir / "docker_test"
    docker_test_dir.mkdir()

    # Create subdirectories
    attachments_dir = docker_test_dir / "attachments"
    attachments_dir.mkdir()

    data_dir = docker_test_dir / "migration_data"
    data_dir.mkdir()

    reports_dir = docker_test_dir / "reports"
    reports_dir.mkdir()

    # Create a .env file for Docker Compose
    env_file = docker_test_dir / ".env"
    env_content = "\n".join([f"{k}={v}" for k, v in base_test_env.items()])
    env_file.write_text(env_content)

    # Return the environment information
    env_info = {
        "dir": docker_test_dir,
        "env_file": env_file,
        "attachments_dir": attachments_dir,
        "data_dir": data_dir,
        "reports_dir": reports_dir,
        "env_vars": base_test_env,
    }

    yield env_info

    # Clean up is handled by the temp_dir fixture


@pytest.fixture
def cli_runner(
    temp_dir: Path, base_test_env: Dict[str, str]
) -> Generator[Dict[str, Any], None, None]:
    """
    Set up an environment for testing the CLI application.

    This fixture creates an environment for running and testing the CLI
    application in system tests, including setting up necessary directories
    and environment variables.

    Args:
        temp_dir: Temporary directory for test files
        base_test_env: Base testing environment variables

    Yields:
        Dict[str, Any]: Dictionary containing CLI test environment details
    """
    # Create test directories
    cli_test_dir = temp_dir / "cli_test"
    cli_test_dir.mkdir()

    # Create input and output directories
    input_dir = cli_test_dir / "input"
    input_dir.mkdir()

    output_dir = cli_test_dir / "output"
    output_dir.mkdir()

    # Save original environment
    original_env = os.environ.copy()

    # Set up test environment
    os.environ.update(base_test_env)

    # Return the environment information
    env_info = {
        "dir": cli_test_dir,
        "input_dir": input_dir,
        "output_dir": output_dir,
        "env_vars": base_test_env,
        "original_env": original_env,
    }

    yield env_info

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def run_cli_command() -> Generator[callable, None, None]:
    """
    Provide a function to run CLI commands for system testing.

    This fixture provides a function that can be used to run CLI commands
    in system tests, capturing their output and exit status.

    Yields:
        callable: Function to run CLI commands
    """

    def _run_command(command: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
        """
        Run a CLI command and return its results.

        Args:
            command: List of command parts to run
            cwd: Current working directory for the command

        Returns:
            Dict[str, Any]: Command execution results
        """
        try:
            # Prefix with python -m if needed for module-based commands
            if command[0] == "ztoq" and Path("ztoq").is_dir():
                command = ["python", "-m", "ztoq"] + command[1:]

            # Run the command
            process = subprocess.run(
                command, capture_output=True, text=True, check=False, cwd=str(cwd) if cwd else None
            )

            # Return results
            return {
                "returncode": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "successful": process.returncode == 0,
            }
        except subprocess.SubprocessError as e:
            # Handle subprocess errors
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "successful": False,
                "error": e,
            }

    yield _run_command
