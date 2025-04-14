"""Test configuration and fixtures for the ztoq project."""
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: mark a test as a unit test")
    config.addinivalue_line("markers", "integration: mark a test as an integration test")
    config.addinivalue_line("markers", "system: mark a test as a system test")
    config.addinivalue_line("markers", "docker: mark a test as a Docker-related test")


@pytest.fixture


def mock_env_vars():
    """Mock environment variables for testing."""
    original_environ = os.environ.copy()

    # Set up test environment variables
    test_env = {
        "ZTOQ_LOG_LEVEL": "DEBUG",
            "ZTOQ_DB_TYPE": "sqlite",
            "ZTOQ_DB_PATH": ":memory:",
            "ZEPHYR_BASE_URL": "https://api.example.com/v2",
            "ZEPHYR_API_TOKEN": "test_token",
            "ZEPHYR_PROJECT_KEY": "TEST",
            "QTEST_BASE_URL": "https://qtest.example.com",
            "QTEST_USERNAME": "test_user",
            "QTEST_PASSWORD": "test_password",
            "QTEST_PROJECT_ID": "12345"
    }

    os.environ.update(test_env)

    yield test_env

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_environ)


@pytest.fixture


def temp_db_path(tmp_path):
    """Create a temporary database path."""
    db_file = tmp_path / "test_ztoq.db"
    return str(db_file)


@pytest.fixture


def skip_if_no_docker():
    """Skip a test if Docker is not available."""
    if os.environ.get("SKIP_DOCKER_TESTS") == "1":
        pytest.skip("Skipping Docker test due to SKIP_DOCKER_TESTS=1")

    try:
        import subprocess
        result = subprocess.run(["docker", "--version"],
                                   capture_output=True,
                                   text=True,
                                   check=False)
        if result.returncode != 0:
            pytest.skip("Docker not available")
    except (FileNotFoundError, subprocess.SubprocessError):
        pytest.skip("Docker not available")


@pytest.fixture


def mock_docker_available():
    """Mock Docker availability for tests."""
    with patch('subprocess.run') as mock_run:
        # Configure the mock to indicate Docker is available
        mock_process = mock_run.return_value
        mock_process.returncode = 0
        mock_process.stdout = b"Docker version 20.10.12, build e91ed57"
        yield mock_run


@pytest.fixture


def mock_docker_compose_available():
    """Mock Docker Compose availability for tests."""
    with patch('subprocess.run') as mock_run:
        # Configure the mock to indicate Docker Compose is available
        mock_process = mock_run.return_value
        mock_process.returncode = 0
        mock_process.stdout = b"Docker Compose version v2.5.0"
        yield mock_run


@pytest.fixture


def docker_test_env(tmp_path, mock_env_vars):
    """Set up a test environment for Docker testing."""
    test_dir = tmp_path / "docker_test"
    test_dir.mkdir()

    # Create dummy files/directories needed for testing
    (test_dir / "attachments").mkdir()
    (test_dir / "migration_data").mkdir()
    (test_dir / "reports").mkdir()

    # Create a dummy .env file
    env_file = test_dir / ".env"
    env_content = "\n".join([f"{k}={v}" for k, v in mock_env_vars.items()])
    env_file.write_text(env_content)

    return {
        "dir": test_dir,
            "env_file": env_file,
            "attachments_dir": test_dir / "attachments",
            "data_dir": test_dir / "migration_data",
            "reports_dir": test_dir / "reports"
    }
