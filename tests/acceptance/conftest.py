"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """Return a Typer CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """Create a temporary SQLite database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        yield Path(path)
    finally:
        if os.path.exists(path):
            os.unlink(path)


@pytest.fixture
def temp_output_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for output files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_zephyr_config() -> dict[str, Any]:
    """Return mock Zephyr configuration parameters."""
    return {
        "base_url": "https://zephyr.example.com/api",
        "api_token": "mock-zephyr-token",
        "project_key": "TEST1",
    }


@pytest.fixture
def mock_qtest_config() -> dict[str, Any]:
    """Return mock qTest configuration parameters."""
    return {
        "base_url": "https://qtest.example.com/api",
        "username": "mock-user",
        "password": "mock-password",
        "project_id": 123,
    }


@pytest.fixture
def mock_openapi_spec() -> Path:
    """Return the path to the test OpenAPI spec."""
    return Path(__file__).parent.parent.parent / "docs" / "specs" / "z-openapi.yml"


@pytest.fixture
def mock_db_config() -> dict[str, Any]:
    """Return mock database configuration parameters."""
    return {
        "db_type": "sqlite",
        "db_path": ":memory:",
    }


@pytest.fixture
def mock_cli_env(
    mock_zephyr_config: dict[str, Any],
    mock_qtest_config: dict[str, Any],
    mock_db_config: dict[str, Any],
    temp_output_dir: Path,
) -> dict[str, str]:
    """Return environment variables for CLI tests."""
    return {
        "ZTOQ_ZEPHYR_BASE_URL": mock_zephyr_config["base_url"],
        "ZTOQ_ZEPHYR_API_TOKEN": mock_zephyr_config["api_token"],
        "ZTOQ_ZEPHYR_PROJECT_KEY": mock_zephyr_config["project_key"],
        "ZTOQ_QTEST_BASE_URL": mock_qtest_config["base_url"],
        "ZTOQ_QTEST_USERNAME": mock_qtest_config["username"],
        "ZTOQ_QTEST_PASSWORD": mock_qtest_config["password"],
        "ZTOQ_QTEST_PROJECT_ID": str(mock_qtest_config["project_id"]),
        "ZTOQ_DB_TYPE": mock_db_config["db_type"],
        "ZTOQ_DB_PATH": mock_db_config["db_path"],
        "ZTOQ_OUTPUT_DIR": str(temp_output_dir),
    }
