"""
Example system tests demonstrating the usage of fixtures.

This file demonstrates how to use the system test fixtures,
serving as a reference for implementing other system tests.
"""

import json

import pytest

# Import fixtures from the fixtures package
from tests.fixtures import (
    # Core fixtures
    ProjectFactory,
    QTestProjectFactory,
    QTestTestCaseFactory,
    TestCaseFactory,
    TestExecutionFactory,
)

# Import project models


@pytest.mark.system
@pytest.mark.cli
def test_cli_environment(cli_runner):
    """Demonstrate testing CLI functionality with system test fixtures."""
    # cli_runner provides an environment for testing CLI commands

    # Create a test script in the input directory
    script_path = cli_runner["input_dir"] / "test_script.py"
    script_path.write_text(
        """
import os
import sys

def main():
    # Print some environment information
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")

    # Print the environment variables
    for key, value in sorted(os.environ.items()):
        if key.startswith(('ZTOQ_', 'ZEPHYR_', 'QTEST_')):
            print(f"{key}={value}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
    """,
    )

    # Make the script executable
    script_path.chmod(0o755)

    # Use the run_cli_command fixture to run the command
    run_command = pytest.importorskip("tests.fixtures.system").run_cli_command
    result = run_command(["python", str(script_path)], cwd=cli_runner["dir"])

    # Verify the command executed successfully
    assert result["successful"]
    assert result["returncode"] == 0

    # Verify the output contains the expected environment information
    assert "Python version:" in result["stdout"]
    assert "Current directory:" in result["stdout"]
    assert "ZTOQ_LOG_LEVEL=DEBUG" in result["stdout"]
    assert "ZEPHYR_API_TOKEN=test_token" in result["stdout"]
    assert "QTEST_BASE_URL=https://qtest.example.com" in result["stdout"]


@pytest.mark.system
@pytest.mark.docker
def test_docker_environment(skip_if_no_docker, docker_compose_env):
    """Demonstrate testing Docker functionality with system test fixtures."""
    # skip_if_no_docker skips the test if Docker is not available
    # docker_compose_env provides an environment for Docker Compose tests

    # Verify the Docker test directory and subdirectories exist
    assert docker_compose_env["dir"].exists()
    assert docker_compose_env["attachments_dir"].exists()
    assert docker_compose_env["data_dir"].exists()
    assert docker_compose_env["reports_dir"].exists()

    # Verify the .env file was created with the expected content
    env_file = docker_compose_env["env_file"]
    assert env_file.exists()
    env_content = env_file.read_text()

    # Check for the expected environment variables
    assert "ZTOQ_LOG_LEVEL=DEBUG" in env_content
    assert "ZEPHYR_API_TOKEN=test_token" in env_content
    assert "QTEST_BASE_URL=https://qtest.example.com" in env_content


@pytest.mark.system
def test_file_operations_integration(temp_dir):
    """
    Demonstrate more complex system tests with file operations.

    This test simulates a system test that interacts with files,
    directories, and environment variables.
    """
    # Create a directory structure for testing
    data_dir = temp_dir / "data"
    data_dir.mkdir()

    reports_dir = temp_dir / "reports"
    reports_dir.mkdir()

    # Create some test data files
    test_files = {
        "data/file1.txt": "Content of file 1",
        "data/file2.txt": "Content of file 2",
        "data/file3.txt": "Content of file 3",
    }

    for file_path, content in test_files.items():
        full_path = temp_dir / file_path
        full_path.write_text(content)

    # Create a script that processes the files
    process_script = temp_dir / "process_files.py"
    process_script.write_text(
        """
import os
import sys
from pathlib import Path

def process_files(data_dir, reports_dir):
    # Get all text files in the data directory
    data_files = list(Path(data_dir).glob("*.txt"))

    # Process each file
    results = []
    for file_path in data_files:
        content = file_path.read_text()
        results.append({
            "file": file_path.name,
            "length": len(content),
            "words": len(content.split())
        })

    # Generate a report
    report_path = Path(reports_dir) / "report.txt"
    with open(report_path, "w") as f:
        f.write(f"Processed {len(results)} files\\n\\n")
        for result in results:
            f.write(f"File: {result['file']}\\n")
            f.write(f"  Length: {result['length']} characters\\n")
            f.write(f"  Words: {result['words']} words\\n\\n")

    return len(results)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: process_files.py <data_dir> <reports_dir>")
        sys.exit(1)

    data_dir = sys.argv[1]
    reports_dir = sys.argv[2]

    count = process_files(data_dir, reports_dir)
    print(f"Processed {count} files")
    sys.exit(0)
    """,
    )

    # Run the script using subprocess
    import subprocess

    process = subprocess.run(
        ["python", str(process_script), str(data_dir), str(reports_dir)],
        capture_output=True,
        text=True,
        check=False,
    )

    # Verify the script executed successfully
    assert process.returncode == 0
    assert "Processed 3 files" in process.stdout

    # Verify the report file was created with the expected content
    report_path = reports_dir / "report.txt"
    assert report_path.exists()

    report_content = report_path.read_text()
    assert "Processed 3 files" in report_content
    assert "File: file1.txt" in report_content
    assert "File: file2.txt" in report_content
    assert "File: file3.txt" in report_content


@pytest.mark.system
def test_factories_with_json_files(temp_dir):
    """
    Demonstrate using factories to generate test data files.

    This test shows how to use factories to create test data
    and save it to JSON files for use in system tests.
    """
    # Create a data directory
    data_dir = temp_dir / "test_data"
    data_dir.mkdir()

    # Generate test projects
    zephyr_projects = ProjectFactory.create_batch(3)
    qtest_projects = QTestProjectFactory.create_batch(3)

    # Generate test cases
    zephyr_test_cases = []
    for project in zephyr_projects:
        # Create 2 test cases per project
        zephyr_test_cases.extend(
            TestCaseFactory.create_batch(2, folder=project.id, folder_name=f"Folder-{project.key}"),
        )

    qtest_test_cases = []
    for project in qtest_projects:
        # Create 2 test cases per project
        qtest_test_cases.extend(QTestTestCaseFactory.create_batch(2, project_id=project.id))

    # Create test executions
    zephyr_executions = []
    for test_case in zephyr_test_cases:
        # Create an execution for each test case
        zephyr_executions.append(TestExecutionFactory.create(test_case_key=test_case.key))

    # Save test data to JSON files
    with open(data_dir / "zephyr_projects.json", "w") as f:
        json.dump([p.model_dump() for p in zephyr_projects], f, indent=2, default=str)

    with open(data_dir / "qtest_projects.json", "w") as f:
        json.dump([p.model_dump() for p in qtest_projects], f, indent=2, default=str)

    with open(data_dir / "zephyr_test_cases.json", "w") as f:
        json.dump([tc.model_dump() for tc in zephyr_test_cases], f, indent=2, default=str)

    with open(data_dir / "qtest_test_cases.json", "w") as f:
        json.dump([tc.model_dump() for tc in qtest_test_cases], f, indent=2, default=str)

    with open(data_dir / "zephyr_executions.json", "w") as f:
        json.dump([e.model_dump() for e in zephyr_executions], f, indent=2, default=str)

    # Verify the files were created
    assert (data_dir / "zephyr_projects.json").exists()
    assert (data_dir / "qtest_projects.json").exists()
    assert (data_dir / "zephyr_test_cases.json").exists()
    assert (data_dir / "qtest_test_cases.json").exists()
    assert (data_dir / "zephyr_executions.json").exists()

    # Read the files back in and verify the structure
    with open(data_dir / "zephyr_projects.json") as f:
        loaded_projects = json.load(f)
        assert len(loaded_projects) == 3
        assert "key" in loaded_projects[0]
        assert "name" in loaded_projects[0]

    with open(data_dir / "zephyr_test_cases.json") as f:
        loaded_test_cases = json.load(f)
        assert len(loaded_test_cases) == 6  # 2 test cases for each of 3 projects
        assert "key" in loaded_test_cases[0]
        assert "folder" in loaded_test_cases[0]

    # Demonstrate using test data from a file
    with open(data_dir / "zephyr_executions.json") as f:
        loaded_executions = json.load(f)
        assert len(loaded_executions) == 6  # 1 execution for each test case

        # Verify all executions have a test case key
        test_case_keys = [tc["key"] for tc in loaded_test_cases]
        for execution in loaded_executions:
            assert execution["test_case_key"] in test_case_keys
