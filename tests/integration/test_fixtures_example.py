"""
Example integration tests demonstrating the usage of fixtures.

This file demonstrates how to use the integration test fixtures,
serving as a reference for implementing other integration tests.
"""


import pytest
from sqlalchemy import text

# Import fixtures from the fixtures package
from tests.fixtures import (
    # Factories
    ProjectFactory,
    QTestProjectFactory,
    QTestTestCaseFactory,
    TestCaseFactory,
)

# Import project models


@pytest.mark.integration
def test_sqlite_memory_database(sqlite_memory_connection):
    """Demonstrate using an in-memory SQLite database."""
    # sqlite_memory_connection is a SQLAlchemy session with an in-memory database

    # Create a test table
    sqlite_memory_connection.execute(
        text(
            """
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    """,
        ),
    )

    # Insert some data
    sqlite_memory_connection.execute(
        text(
            """
        INSERT INTO test_table (name) VALUES
        ('Item 1'),
        ('Item 2'),
        ('Item 3')
    """,
        ),
    )

    # Query the data
    result = sqlite_memory_connection.execute(text("SELECT * FROM test_table")).fetchall()

    # Verify the results
    assert len(result) == 3
    assert result[0][1] == "Item 1"
    assert result[1][1] == "Item 2"
    assert result[2][1] == "Item 3"


@pytest.mark.integration
def test_sqlite_file_database(sqlite_file_engine):
    """Demonstrate using a file-based SQLite database."""
    # sqlite_file_engine is a SQLAlchemy engine with a file-based database

    # Create a connection
    with sqlite_file_engine.connect() as conn:
        # Create a test table
        conn.execute(
            text(
                """
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """,
            ),
        )

        # Insert some data
        conn.execute(
            text(
                """
            INSERT INTO test_table (name) VALUES
            ('Item 1'),
            ('Item 2'),
            ('Item 3')
        """,
            ),
        )

        # Commit the transaction
        conn.commit()

        # Query the data
        result = conn.execute(text("SELECT * FROM test_table")).fetchall()

        # Verify the results
        assert len(result) == 3
        assert result[0][1] == "Item 1"
        assert result[1][1] == "Item 2"
        assert result[2][1] == "Item 3"


@pytest.mark.integration
def test_mocked_external_apis(mock_external_api):
    """Demonstrate mocking external APIs in integration tests."""
    # mock_external_api provides mock instances of external API clients

    # Configure the mocks
    mock_external_api["zephyr"].get_test_cases.return_value = [
        {"id": 1, "key": "TC-1", "name": "Test Case 1"},
        {"id": 2, "key": "TC-2", "name": "Test Case 2"},
    ]

    mock_external_api["qtest"].get_test_cases.return_value = [
        {"id": 101, "pid": "TC-101", "name": "qTest Case 1"},
        {"id": 102, "pid": "TC-102", "name": "qTest Case 2"},
    ]

    # Use the mock clients
    zephyr_cases = mock_external_api["zephyr"].get_test_cases()
    qtest_cases = mock_external_api["qtest"].get_test_cases()

    # Verify the results
    assert len(zephyr_cases) == 2
    assert zephyr_cases[0]["key"] == "TC-1"

    assert len(qtest_cases) == 2
    assert qtest_cases[0]["pid"] == "TC-101"

    # Verify the mocks were called as expected
    mock_external_api["zephyr"].get_test_cases.assert_called_once()
    mock_external_api["qtest"].get_test_cases.assert_called_once()


@pytest.mark.integration
def test_test_data_directory(test_data_dir):
    """Demonstrate using a directory with test data files."""
    # test_data_dir is a directory containing sample test data files

    # Verify the directory exists
    assert test_data_dir.exists()
    assert test_data_dir.is_dir()

    # Check for the expected test data files
    assert (test_data_dir / "test_cases.json").exists()
    assert (test_data_dir / "test_cycles.json").exists()
    assert (test_data_dir / "test_executions.json").exists()

    # Read and verify the content of a test data file
    test_cases_content = (test_data_dir / "test_cases.json").read_text()
    assert "Test Case 1" in test_cases_content
    assert "Test Case 2" in test_cases_content


@pytest.mark.integration
def test_factories_with_mock_api(mock_external_api):
    """Demonstrate using factories with mock API."""
    # Create test data using factories
    zephyr_project = ProjectFactory.create(key="DEMO", name="Demo Zephyr Project")

    qtest_project = QTestProjectFactory.create(id=1001, name="Demo qTest Project")

    # Configure the mock APIs to return our factory-generated data
    mock_external_api["zephyr"].get_project.return_value = zephyr_project.model_dump()
    mock_external_api["qtest"].get_project.return_value = qtest_project.model_dump()

    # Use the mock APIs
    zephyr_result = mock_external_api["zephyr"].get_project()
    qtest_result = mock_external_api["qtest"].get_project()

    # Verify the results match our factory data
    assert zephyr_result["key"] == "DEMO"
    assert zephyr_result["name"] == "Demo Zephyr Project"

    assert qtest_result["id"] == 1001
    assert qtest_result["name"] == "Demo qTest Project"

    # Generate data for test cases
    zephyr_test_cases = TestCaseFactory.create_batch(3)
    qtest_test_cases = QTestTestCaseFactory.create_batch(3)

    # Configure mocks to return batches
    mock_external_api["zephyr"].get_test_cases.return_value = [
        tc.model_dump() for tc in zephyr_test_cases
    ]
    mock_external_api["qtest"].get_test_cases.return_value = [
        tc.model_dump() for tc in qtest_test_cases
    ]

    # Use the mock APIs for batch retrieval
    zephyr_cases = mock_external_api["zephyr"].get_test_cases()
    qtest_cases = mock_external_api["qtest"].get_test_cases()

    # Verify correct number of items
    assert len(zephyr_cases) == 3
    assert len(qtest_cases) == 3
