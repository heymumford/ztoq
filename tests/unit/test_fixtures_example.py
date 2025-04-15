"""
Example tests demonstrating the usage of fixtures and factories.

This file demonstrates how to use the test fixtures and factories,
serving as a reference for implementing other tests.
"""

import pytest
from ztoq.models import Project, Case as TestCase
from ztoq.domain.models import OpenAPISpec

# Import fixtures and factories from the fixtures package
from tests.fixtures import (
    # Core fixtures
    base_test_env,
    mock_env_vars,
    temp_dir,
    temp_file,
    # Unit test fixtures
    mock_db_connection,
    mock_file_system,
    # Factories
    ProjectFactory,
    TestCaseFactory,
    OpenAPISpecFactory,
)


@pytest.mark.unit
def test_environment_variables(mock_env_vars):
    """Demonstrate using environment variable fixtures."""
    # The mock_env_vars fixture sets up test environment variables
    import os

    # Access environment variables
    assert os.environ["ZTOQ_LOG_LEVEL"] == "DEBUG"
    assert os.environ["ZEPHYR_API_TOKEN"] == "test_token"
    assert os.environ["QTEST_BASE_URL"] == "https://qtest.example.com"


@pytest.mark.unit
def test_temp_filesystem(temp_dir, temp_file):
    """Demonstrate using temporary file system fixtures."""
    # temp_dir is a temporary directory for test files
    # temp_file is a temporary file created inside temp_dir

    # Create a new file in the temporary directory
    test_file = temp_dir / "example.txt"
    test_file.write_text("Hello, test!")

    # Verify the file was created
    assert test_file.exists()
    assert test_file.read_text() == "Hello, test!"

    # Verify the temp_file also exists
    assert temp_file.exists()


@pytest.mark.unit
def test_mock_database(mock_db_connection):
    """Demonstrate using database mock fixtures."""
    # mock_db_connection is a mock database connection

    # Set up the expected return value
    mock_result = [("row1", 123), ("row2", 456)]
    mock_db_connection.cursor().fetchall.return_value = mock_result

    # Execute a "query" using the mock
    cursor = mock_db_connection.cursor()
    cursor.execute("SELECT * FROM some_table")
    result = cursor.fetchall()

    # Verify the mock returned the expected value
    assert result == mock_result

    # Verify the execute method was called with the expected query
    cursor.execute.assert_called_with("SELECT * FROM some_table")


@pytest.mark.unit
def test_factories_basic():
    """Demonstrate basic usage of model factories."""
    # Create a single project
    project = ProjectFactory.create()

    # Verify it's a valid Project instance with expected fields
    assert isinstance(project, Project)
    assert project.name.startswith("Project-")
    assert project.description is not None

    # Create a project with specific attributes
    custom_project = ProjectFactory.create(
        id="123", name="Custom Project", description="Custom description"
    )

    assert custom_project.id == "123"
    assert custom_project.name == "Custom Project"
    assert custom_project.description == "Custom description"

    # Create a batch of projects
    projects = ProjectFactory.create_batch(5)

    assert len(projects) == 5
    assert all(isinstance(p, Project) for p in projects)
    assert len(set(p.id for p in projects)) == 5  # All have unique IDs

    # Test OpenAPISpec factory
    api_spec = OpenAPISpecFactory.create()
    assert isinstance(api_spec, OpenAPISpec)
    assert api_spec.title.startswith("API Spec ")
    assert isinstance(api_spec.data, dict)
    assert "paths" in api_spec.data


@pytest.mark.unit
def test_factories_relationships():
    """Demonstrate creating related models with factories."""
    # Create a project
    project = ProjectFactory.create(id="456")

    # Create test cases related to the project by key
    test_cases = TestCaseFactory.create_batch(3, folder_name=f"Folder-{project.key}")

    # Verify the folder name relation
    assert all(tc.folder_name.startswith(f"Folder-{project.key}") for tc in test_cases)

    # Create a custom hierarchy
    # - 1 project
    # - 2 test cases under the project
    project = ProjectFactory.create()
    test_case1 = TestCaseFactory.create(
        folder=project.id, folder_name="Folder-Project", name="First Test Case"
    )
    test_case2 = TestCaseFactory.create(
        folder=project.id, folder_name="Folder-Project", name="Second Test Case"
    )

    assert test_case1.folder == project.id
    assert test_case2.folder == project.id
    assert test_case1.name == "First Test Case"
    assert test_case2.name == "Second Test Case"

    # Demonstrate creating a test case with steps
    test_case_with_steps = TestCaseFactory.create_with_steps(step_count=3)
    assert isinstance(test_case_with_steps, TestCase)
    assert len(test_case_with_steps.steps) == 3
    assert all(
        step.description.startswith("Step description") for step in test_case_with_steps.steps
    )


@pytest.mark.unit
def test_mock_filesystem(mock_file_system):
    """Demonstrate using file system mocks."""
    # mock_file_system provides mocks for file system operations
    from pathlib import Path

    # Configure the mock
    mock_file_system["exists"].return_value = True
    mock_file_system["is_file"].return_value = True

    # Use the mocked functions
    path = Path("/some/test/path.txt")
    assert path.exists()
    assert path.is_file()

    # Verify the mock was called as expected
    mock_file_system["exists"].assert_called_with()
    mock_file_system["is_file"].assert_called_with()
