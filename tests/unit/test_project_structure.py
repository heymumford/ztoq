"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.

Unit tests for project structure and configuration.

These tests verify the overall project structure, configuration classes,
and CLI parser functionality.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ztoq.cli import app
from ztoq.core.db_manager import DatabaseConfig
from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig


@pytest.mark.unit
class TestProjectStructure:
    """Tests for verifying the basic project structure and package organization."""

    def test_project_root_structure(self):
        """Test that the project root contains the expected files."""
        root_dir = Path(__file__).parent.parent.parent

        # Essential files that should be in the project root
        essential_files = [
            "pyproject.toml",
            "README.md",
            "LICENSE",
            "pytest.ini",
        ]

        for file in essential_files:
            assert (root_dir / file).exists(), f"Required file {file} not found in project root"

    def test_package_structure(self):
        """Test that the package directory structure is correct."""
        root_dir = Path(__file__).parent.parent.parent

        # Key directories that should exist
        key_dirs = [
            "ztoq",
            "tests",
            "tests/unit",
            "tests/integration",
            "tests/acceptance",
            "tests/performance",
            "tests/system",
            "ztoq/core",
            "ztoq/domain",
            "ztoq/utils",
            "docs",
            "docs/adr",
        ]

        for directory in key_dirs:
            assert (root_dir / directory).is_dir(), f"Required directory {directory} not found"

    def test_module_imports(self):
        """Test that all key modules can be imported."""
        # Core modules that should be importable
        modules = [
            "ztoq",
            "ztoq.cli",
            "ztoq.models",
            "ztoq.core.db_manager",
            "ztoq.core.config",
            "ztoq.core.logging",
            "ztoq.database_factory",
            "ztoq.database_connection_manager",
            "ztoq.connection_pool",
            "ztoq.work_queue",
            "ztoq.utils.dependency_manager",
            "ztoq.utils.package_info",
            "ztoq.utils.version_utils",
            "ztoq.db_indexing",
            "ztoq.workflow_cli",
            "ztoq.workflow_orchestrator",
            "ztoq.migration",
        ]

        for module in modules:
            try:
                __import__(module)
            except ImportError as e:
                pytest.fail(f"Failed to import module {module}: {e}")

    def test_no_personal_directory_references(self):
        """Test that there are no hardcoded personal directory references in the codebase."""
        import getpass
        import re

        # Get project root
        root_dir = Path(__file__).parent.parent.parent

        # Define patterns to search for - using placeholders to avoid failing the test
        current_user = getpass.getuser()
        # Pattern avoids matching this file itself
        personal_reference_pattern = re.compile(
            fr"/home/{current_user}(?!/NativeLinuxProjects/ztoq/tests/unit/test_project_structure.py)",
        )

        # Define directories to exclude from the search
        excluded_dirs = {
            ".git",
            ".pytest_cache",
            "__pycache__",
            "venv",
            "build",
            "dist",
            "*.egg-info",
            "testenv",
            "docenv",
            ".venv",
        }

        # Define file extensions to check
        valid_extensions = {
            ".py", ".md", ".rst", ".yml", ".yaml", ".ini", ".toml", ".sh", ".txt",
            ".css", ".js", ".html", ".json", ".cfg", ".in", ".bat", ".mako",
        }

        # Keep track of files with personal references
        files_with_references = []

        # Walk through the project directory
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Skip excluded directories
            dirnames[:] = [d for d in dirnames if d not in excluded_dirs]

            # Check each file
            for filename in filenames:
                file_path = Path(dirpath) / filename

                # Skip files with extensions we don't care about
                if file_path.suffix.lower() not in valid_extensions:
                    continue

                # Skip if file is too large (binary files or other non-text files)
                max_file_size = 1_000_000  # 1MB limit for text files
                if file_path.stat().st_size > max_file_size:
                    continue

                try:
                    # Read file content
                    with file_path.open(encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    # Check for personal directory reference pattern
                    if personal_reference_pattern.search(content):
                        files_with_references.append(str(file_path.relative_to(root_dir)))
                except (UnicodeDecodeError, PermissionError, OSError) as e:
                    # Skip files that can't be read as text
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug("Skipping file %s: %s", file_path, e)
                    continue

        # Fail the test if any files contain personal directory references
        if files_with_references:
            files_list = ", ".join(files_with_references)
            pytest.fail(f"Found personal directory references in the following files: {files_list}")


@pytest.mark.unit
class TestConfigurationClasses:
    """Tests for configuration classes and their validation."""

    def test_zephyr_config_validation(self):
        """Test that ZephyrConfig validates input correctly."""
        # Valid config
        valid_config = ZephyrConfig(
            base_url="https://api.example.com",
            api_token="valid-token",  # Using a test token
            project_key="TEST",
        )
        assert valid_config.base_url == "https://api.example.com"
        assert valid_config.api_token == "valid-token"
        assert valid_config.project_key == "TEST"

        # Empty project key is allowed for certain operations
        empty_project_config = ZephyrConfig(
            base_url="https://api.example.com",
            api_token="valid-token",  # Using a test token
            project_key="",
        )
        assert empty_project_config.project_key == ""

        # Invalid config - missing required fields
        with pytest.raises(ValueError, match="base_url"):
            ZephyrConfig(base_url="", api_token="valid-token", project_key="TEST")

        with pytest.raises(ValueError, match="api_token"):
            ZephyrConfig(base_url="https://api.example.com", api_token="", project_key="TEST")

    def test_qtest_config_validation(self):
        """Test that QTestConfig validates input correctly."""
        # Valid config
        test_project_id = 123  # Test project ID
        valid_config = QTestConfig(
            base_url="https://qtest.example.com",
            username="user@example.com",
            password="dummy_password",  # Using a dummy password value for tests
            project_id=test_project_id,
        )
        assert valid_config.base_url == "https://qtest.example.com"
        assert valid_config.username == "user@example.com"
        assert valid_config.password == "dummy_password"
        assert valid_config.project_id == test_project_id

        # Invalid config - missing required fields
        # Test for missing base_url
        with pytest.raises(ValueError, match="base_url"):
            QTestConfig(
                base_url="",
                username="user@example.com",
                password="dummy_password",
                project_id=test_project_id,
            )

        # Test for missing username
        with pytest.raises(ValueError, match="username"):
            QTestConfig(
                base_url="https://qtest.example.com",
                username="",
                password="dummy_password",
                project_id=test_project_id,
            )

        # Test for missing password
        with pytest.raises(ValueError, match="password"):
            QTestConfig(
                base_url="https://qtest.example.com",
                username="user@example.com",
                password="",
                project_id=test_project_id,
            )

        # Invalid project ID (negative)
        with pytest.raises(ValueError, match="project_id"):
            QTestConfig(
                base_url="https://qtest.example.com",
                username="user@example.com",
                password="dummy_password",
                project_id=-1,
            )

    def test_database_config_validation(self):
        """Test that DatabaseConfig validates input correctly."""
        # Valid SQLite config
        sqlite_config = DatabaseConfig(
            db_type="sqlite",
            db_path="/path/to/db.sqlite",
        )
        assert sqlite_config.db_type == "sqlite"
        assert sqlite_config.db_path == "/path/to/db.sqlite"

        # Default SQLite path
        default_sqlite_config = DatabaseConfig(db_type="sqlite")
        assert default_sqlite_config.db_path is not None

        # Valid PostgreSQL config
        pg_config = DatabaseConfig(
            db_type="postgresql",
            host="localhost",
            port=5432,
            username="postgres",
            password="dummy_pg_password",  # Using a dummy password for tests
            database="ztoq",
        )
        assert pg_config.db_type == "postgresql"
        assert pg_config.host == "localhost"
        pg_default_port = 5432  # Standard PostgreSQL port
        assert pg_config.port == pg_default_port
        assert pg_config.username == "postgres"
        assert pg_config.database == "ztoq"

        # Invalid PostgreSQL config - missing required fields
        with pytest.raises(ValueError, match="host"):
            DatabaseConfig(
                db_type="postgresql",
                host="",
                username="postgres",
                database="ztoq",
            )

        # Unknown database type
        with pytest.raises(ValueError, match="db_type"):
            DatabaseConfig(db_type="unknown")


@pytest.mark.unit
class TestCLICommands:
    """Tests for CLI commands and argument handling."""

    runner = CliRunner()

    def test_cli_help(self):
        """Test that the CLI help command works."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ZTOQ - Zephyr to qTest" in result.stdout

    def test_cli_command_structure(self):
        """Test that the CLI has the expected command structure."""
        result = self.runner.invoke(app, ["--help"])

        # Main commands
        assert "validate" in result.stdout
        assert "list-endpoints" in result.stdout
        assert "get-projects" in result.stdout
        assert "get-test-cases" in result.stdout
        assert "get-test-cycles" in result.stdout
        assert "export-project" in result.stdout
        assert "export-all" in result.stdout

        # Sub-command groups
        assert "db" in result.stdout
        assert "migrate" in result.stdout
        assert "workflow" in result.stdout

    def test_db_commands(self):
        """Test that the database commands are available."""
        result = self.runner.invoke(app, ["db", "--help"])
        assert result.exit_code == 0

        # DB commands
        assert "init" in result.stdout
        assert "stats" in result.stdout
        assert "migrate" in result.stdout

    def test_migration_commands(self):
        """Test that the migration commands are available."""
        result = self.runner.invoke(app, ["migrate", "--help"])
        assert result.exit_code == 0

        # Migration commands
        assert "run" in result.stdout
        assert "status" in result.stdout

    @patch.dict(os.environ, {"ZTOQ_PG_HOST": "env-host", "ZTOQ_PG_USER": "env-user",
                            "ZTOQ_PG_PASSWORD": "env-pass", "ZTOQ_PG_DATABASE": "env-db"})
    def test_environment_variable_handling(self):
        """Test that environment variables are handled correctly."""
        # We'll test the cli.py module's handling of environment variables
        # This is a simplified test of the environment variable handling logic
        from ztoq.cli import app

        with patch("ztoq.cli.console.print") as mock_print:
            # Call a command that uses environment variables, but exit early
            with patch("ztoq.cli.SQLDatabaseManager", side_effect=Exception("Test exit")):
                self.runner.invoke(
                    app, ["db", "init", "--db-type", "postgresql"],
                )

            # Check that environment variables were read
            mock_print.assert_any_call(
                "Using PostgreSQL settings from environment variables",
                style="blue",
            )


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
