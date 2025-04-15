"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Example tests demonstrating the usage of the ZTOQ test fixtures.

This module provides examples of how to use the various fixtures
and factory classes provided by the ZTOQ testing framework.
"""


import pytest

from tests.fixtures import (
    # Factory classes
    TestCaseFactory,
)
from ztoq.models import Case, ZephyrConfig
from ztoq.qtest_client import QTestClient
from ztoq.qtest_models import QTestConfig
from ztoq.zephyr_client import ZephyrClient


# Example 1: Unit Test with Mocked Dependencies
@pytest.mark.unit
def test_unit_with_mocked_dependencies(mock_zephyr_client, mock_sqlalchemy_session):
    """Example of a unit test with mocked dependencies."""
    # Arrange: Configure the mocks
    test_case = TestCaseFactory.create(key="TEST-T1", name="Test Case 1")
    mock_zephyr_client.get_test_cases.return_value = [test_case]

    # Act: Call the function under test (example)
    def import_test_cases(client, session):
        """Example function that would be under test."""
        test_cases = client.get_test_cases()
        for test_case in test_cases:
            session.add(test_case)
        session.commit()
        return len(test_cases)

    result = import_test_cases(mock_zephyr_client, mock_sqlalchemy_session)

    # Assert: Verify the results
    assert result == 1
    mock_zephyr_client.get_test_cases.assert_called_once()
    mock_sqlalchemy_session.add.assert_called_once_with(test_case)
    mock_sqlalchemy_session.commit.assert_called_once()


# Example 2: Integration Test with API Mocking
@pytest.mark.integration
def test_integration_with_api_mocking(mock_zephyr_api, sqlalchemy_memory_session):
    """Example of an integration test with API mocking."""
    # Arrange: Configure the mock API
    mock_zephyr_api.add_response(
        "GET", "/projects", {"values": [{"id": "1001", "key": "TEST", "name": "Test Project"}]},
    )

    mock_zephyr_api.add_response(
        "GET",
        "/testcases",
        {
            "total": 1,
            "startAt": 0,
            "maxResults": 50,
            "isLast": True,
            "values": [{"id": "TC-1", "key": "TEST-T1", "name": "Test Case 1", "status": "Active"}],
        },
    )

    # Act: Create a real client and use it with the mocked API
    config = ZephyrConfig(
        base_url="https://api.zephyrscale.example.com/v2",
        api_token="mock-token",
        project_key="TEST",
    )
    client = ZephyrClient(config)

    # Get data from the mocked API
    projects = client.get_projects()
    test_cases = list(client.get_test_cases())

    # Assert: Verify the results
    assert len(projects) == 1
    assert projects[0].key == "TEST"
    assert len(test_cases) == 1
    assert test_cases[0].key == "TEST-T1"


# Example 3: Integration Test with Database
@pytest.mark.integration
def test_integration_with_database(sqlalchemy_memory_session, populate_test_db):
    """Example of an integration test with a database."""
    # Arrange: Populate the database with test data
    populate_test_db(sqlalchemy_memory_session)

    # Act: Query the database
    result = sqlalchemy_memory_session.execute("SELECT * FROM Project").fetchall()

    # Assert: Verify the results
    assert len(result) == 2
    assert result[0]["project_key"] == "PROJ1"
    assert result[1]["project_key"] == "PROJ2"


# Example 4: Using Model Factories
@pytest.mark.unit
def test_using_model_factories():
    """Example of using model factories to create test data."""
    # Create a single test case
    test_case = TestCaseFactory.create(key="TEST-T1", name="Test Case 1")
    assert test_case.key == "TEST-T1"
    assert test_case.name == "Test Case 1"

    # Create a test case with steps
    test_case_with_steps = TestCaseFactory.create_with_steps(step_count=3)
    assert len(test_case_with_steps.steps) == 3
    assert test_case_with_steps.steps[0].index == 1
    assert test_case_with_steps.steps[1].index == 2
    assert test_case_with_steps.steps[2].index == 3

    # Create a batch of test cases
    test_cases = TestCaseFactory.create_batch(size=5)
    assert len(test_cases) == 5
    assert all(isinstance(tc, Case) for tc in test_cases)


# Example 5: Testing Multiple APIs Together
@pytest.mark.integration
def test_integration_with_multiple_apis(mock_both_apis):
    """Example of an integration test with multiple mocked APIs."""
    # Destructure the tuple from the fixture
    zephyr_harness, qtest_harness = mock_both_apis

    # Configure Zephyr API
    zephyr_harness.add_response(
        "GET", "/projects", {"values": [{"id": "1001", "key": "TEST", "name": "Test Project"}]},
    )

    # Configure qTest API
    qtest_harness.add_response(
        "POST",
        "/oauth/token",
        {"access_token": "mock-token", "token_type": "bearer", "expires_in": 3600},
    )

    qtest_harness.add_response(
        "GET",
        "/api/v3/projects",
        {"total": 1, "page": 1, "pageSize": 50, "items": [{"id": 12345, "name": "Test Project"}]},
    )

    # Create clients
    zephyr_config_obj = ZephyrConfig(
        base_url="https://api.zephyrscale.example.com/v2",
        api_token="mock-token",
        project_key="TEST",
    )
    zephyr_client = ZephyrClient(zephyr_config_obj)

    qtest_config_obj = QTestConfig(
        base_url="https://api.qtest.example.com",
        username="test-user",
        password="test-password",
        project_id=12345,
    )
    qtest_client = QTestClient(qtest_config_obj)

    # Act: Use both clients
    zephyr_projects = zephyr_client.get_projects()
    qtest_projects = qtest_client.get_projects()

    # Assert: Verify results from both APIs
    assert len(zephyr_projects) == 1
    assert zephyr_projects[0].key == "TEST"
    assert len(qtest_projects) == 1
    assert qtest_projects[0].id == 12345


# Example 6: Using Pre-Configured Client Fixtures
@pytest.mark.integration
def test_integration_with_client_fixtures(zephyr_client_with_mock_api, qtest_client_with_mock_api):
    """Example of an integration test with pre-configured client fixtures."""
    # These clients are already configured with mock responses

    # Act: Use the clients
    zephyr_projects = zephyr_client_with_mock_api.get_projects()
    zephyr_test_cases = list(zephyr_client_with_mock_api.get_test_cases())

    qtest_projects = qtest_client_with_mock_api.get_projects()
    qtest_test_cases = list(qtest_client_with_mock_api.get_test_cases())

    # Assert: Verify results
    assert len(zephyr_projects) == 2
    assert zephyr_projects[0].key == "TEST"
    assert len(zephyr_test_cases) == 2
    assert zephyr_test_cases[0].key == "TEST-T1"

    assert len(qtest_projects) == 2
    assert qtest_projects[0].id == 12345
    assert len(qtest_test_cases) == 2
    assert qtest_test_cases[0].pid == "TC-1"


# Example 7: System Test with Mock External Services
@pytest.mark.system
def test_system_with_mock_externals(mock_env_vars, cli_runner, run_cli_command):
    """Example of a system test with mock external services."""
    # This example mocks the environment and CLI output

    # Define a simple CLI command to test
    cmd = ["echo", "Hello, ZTOQ!"]

    # Run the command
    result = run_cli_command(cmd)

    # Assert: Verify the command output
    assert result["successful"] == True
    assert "Hello, ZTOQ!" in result["stdout"]
    assert result["returncode"] == 0
