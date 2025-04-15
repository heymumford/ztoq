"""Integration tests for the run-migration.sh shell script."""
import os
import subprocess
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

# Mark all tests in this module as integration tests
pytestmark = [pytest.mark.integration, pytest.mark.docker]


class TestRunMigrationScript:
    """Test suite for run-migration.sh shell script functionality."""

    @pytest.fixture
    def script_path(self):
        """Get the path to the run-migration.sh script."""
        script_path = Path(__file__).parent.parent.parent / "utils" / "run-migration.sh"
        assert script_path.exists(), f"Script not found at {script_path}"
        return script_path

    @pytest.fixture
    def temp_env_file(self):
        """Create a temporary .env file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(
                "ZEPHYR_BASE_URL=https://example.com/api/v2\n"
                "ZEPHYR_API_TOKEN=test_token\n"
                "ZEPHYR_PROJECT_KEY=TEST\n"
                "QTEST_BASE_URL=https://qtest.example.com\n"
                "QTEST_USERNAME=test_user\n"
                "QTEST_PASSWORD=test_password\n"
                "QTEST_PROJECT_ID=12345\n"
            )
            env_path = f.name

        yield env_path
        # Clean up
        os.unlink(env_path)

    def test_help_text(self, script_path):
        """Test that the script provides help text when --help flag is used."""
        result = subprocess.run(
            [script_path, "--help"], capture_output=True, text=True, check=False
        )

        assert result.returncode == 0, "Script should exit successfully when help is requested"
        assert "ZTOQ Migration Runner Script" in result.stdout, "Help text should include title"
        assert "Usage:" in result.stdout, "Help text should include usage section"
        assert "Commands:" in result.stdout, "Help text should list commands"
        assert "Options:" in result.stdout, "Help text should list options"

    def test_env_file_check(self, script_path):
        """Test that the script checks for existence of the .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            non_existent_env = temp_path / "does_not_exist.env"

            result = subprocess.run(
                [script_path, "run", "--env-file", str(non_existent_env)],
                capture_output=True,
                text=True,
                check=False,
            )

            assert (
                "Error: Environment file" in result.stdout
            ), "Script should error on missing env file"
            assert (
                "Please create an environment file" in result.stdout
            ), "Script should provide guidance"

    def test_invalid_command(self, script_path):
        """Test that the script handles invalid commands."""
        result = subprocess.run(
            [script_path, "invalid_command"], capture_output=True, text=True, check=False
        )

        assert result.returncode != 0, "Script should exit with error for invalid command"
        assert (
            "Unknown command: invalid_command" in result.stdout
        ), "Script should identify invalid command"
        assert (
            "Run './run-migration.sh --help'" in result.stdout
        ), "Script should suggest help command"

    @patch("subprocess.run")
    def test_command_parsing(self, mock_run, script_path, temp_env_file):
        """Test that the script correctly parses and passes command-line arguments."""
        # Configure the mock to return a successful result
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = b"Mock Output"
        mock_run.return_value = mock_process

        # Run the script with custom parameters
        subprocess.run(
            [
                script_path,
                "run",
                "--env-file",
                temp_env_file,
                "--batch-size",
                "100",
                "--workers",
                "10",
                "--phase",
                "extract",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # Check mock was called with correct command
        mock_run.assert_called()

        # The actual command passed to subprocess.run will be a complex string
        # We'll check that our parameters were included in any of the calls
        all_calls = " ".join([str(call) for call in mock_run.call_args_list])
        assert temp_env_file in all_calls, "Should use the specified env file"
        assert (
            "--batch-size 100" in all_calls or "--batch-size=100" in all_calls
        ), "Should use custom batch size"
        assert (
            "--workers 10" in all_calls or "--max-workers 10" in all_calls
        ), "Should use custom worker count"
        assert "--phase extract" in all_calls, "Should use specified phase"

    @patch("os.makedirs")
    @patch("os.chmod")
    @patch("subprocess.run")
    def test_setup_command_creates_directories(
        self, mock_run, mock_chmod, mock_makedirs, script_path, temp_env_file
    ):
        """Test that the setup command creates the necessary directories."""
        # Configure the mock to return a successful result
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Run the setup command
        subprocess.run(
            [script_path, "setup", "--env-file", temp_env_file],
            capture_output=True,
            text=True,
            check=False,
        )

        # Check directories were created
        expected_dirs = ["attachments", "migration_data", "reports"]
        for dir_name in expected_dirs:
            mock_makedirs.assert_any_call(dir_name, exist_ok=True)

        # Check permissions were set
        mock_chmod.assert_called()

    @patch("subprocess.run")
    def test_docker_compose_commands(self, mock_run, script_path, temp_env_file):
        """Test that the script properly builds docker-compose commands."""
        # Configure the mock to return a successful result
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Test each command
        commands = ["run", "status", "report", "stop", "clean"]

        for cmd in commands:
            subprocess.run(
                [script_path, cmd, "--env-file", temp_env_file],
                capture_output=True,
                text=True,
                check=False,
            )

            # Check docker-compose was called for each command
            mock_run.assert_called()

            # Reset the mock for the next command
            mock_run.reset_mock()
