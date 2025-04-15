"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
API client fixtures for the ZTOQ testing framework.

This module provides fixtures for working with API clients at different
levels of the testing pyramid, from unit tests with mocked clients
to integration tests with real but isolated clients.
"""

import json
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

# Import the API mocking harness
from tests.fixtures.mocks.api_harness import (
    QTestAPIHarness,
    ZephyrAPIHarness,
)
from ztoq.models import ZephyrConfig
from ztoq.qtest_client import QTestClient
from ztoq.qtest_models import QTestConfig
from ztoq.zephyr_client import ZephyrClient


@pytest.fixture
def zephyr_config() -> ZephyrConfig:
    """
    Create a Zephyr configuration for testing.

    This fixture provides a standard Zephyr configuration that can be
    used for tests requiring a Zephyr client.

    Returns:
        ZephyrConfig: Zephyr configuration
    """
    return ZephyrConfig(
        base_url="https://api.zephyrscale.example.com/v2",
        api_token="test-token",
        project_key="TEST",
    )


@pytest.fixture
def qtest_config() -> QTestConfig:
    """
    Create a qTest configuration for testing.

    This fixture provides a standard qTest configuration that can be
    used for tests requiring a qTest client.

    Returns:
        QTestConfig: qTest configuration
    """
    return QTestConfig(
        base_url="https://api.qtest.example.com",
        username="test-user",
        password="test-password",
        project_id=12345,
    )


@pytest.fixture
def mock_zephyr_client() -> MagicMock:
    """
    Create a mock Zephyr client for unit testing.

    This fixture provides a mock Zephyr client that can be used for
    unit tests without making actual API calls.

    Returns:
        MagicMock: Mock Zephyr client
    """
    mock = MagicMock(spec=ZephyrClient)

    # Mock common methods
    mock.get_projects.return_value = [
        MagicMock(id="1001", key="PROJ1", name="Project One"),
        MagicMock(id="1002", key="PROJ2", name="Project Two"),
    ]

    mock.get_test_cases.return_value = MagicMock()
    mock.get_test_cycles.return_value = MagicMock()
    mock.get_test_executions.return_value = MagicMock()

    return mock


@pytest.fixture
def mock_qtest_client() -> MagicMock:
    """
    Create a mock qTest client for unit testing.

    This fixture provides a mock qTest client that can be used for
    unit tests without making actual API calls.

    Returns:
        MagicMock: Mock qTest client
    """
    mock = MagicMock(spec=QTestClient)

    # Mock common methods
    mock.get_projects.return_value = [
        MagicMock(id=1001, name="Project One"),
        MagicMock(id=1002, name="Project Two"),
    ]

    mock.get_test_cases.return_value = MagicMock()
    mock.get_test_cycles.return_value = MagicMock()
    mock.get_modules.return_value = MagicMock()

    return mock


@pytest.fixture
def patch_zephyr_client() -> Generator[MagicMock, None, None]:
    """
    Patch the ZephyrClient class for unit testing.

    This fixture patches the ZephyrClient class with a mock for unit tests
    that create their own client instances.

    Yields:
        MagicMock: Mock ZephyrClient class
    """
    with patch("ztoq.zephyr_client.ZephyrClient", autospec=True) as mock_class:
        # Configure the mock instance that will be returned by the constructor
        mock_instance = MagicMock(spec=ZephyrClient)

        # Setup default return values for common methods
        mock_instance.get_projects.return_value = [
            MagicMock(id="1001", key="PROJ1", name="Project One"),
            MagicMock(id="1002", key="PROJ2", name="Project Two"),
        ]

        mock_instance.get_test_cases.return_value = MagicMock()
        mock_instance.get_test_cycles.return_value = MagicMock()
        mock_instance.get_test_executions.return_value = MagicMock()

        # Configure the mock class to return the mock instance
        mock_class.return_value = mock_instance

        yield mock_class


@pytest.fixture
def patch_qtest_client() -> Generator[MagicMock, None, None]:
    """
    Patch the QTestClient class for unit testing.

    This fixture patches the QTestClient class with a mock for unit tests
    that create their own client instances.

    Yields:
        MagicMock: Mock QTestClient class
    """
    with patch("ztoq.qtest_client.QTestClient", autospec=True) as mock_class:
        # Configure the mock instance that will be returned by the constructor
        mock_instance = MagicMock(spec=QTestClient)

        # Setup default return values for common methods
        mock_instance.get_projects.return_value = [
            MagicMock(id=1001, name="Project One"),
            MagicMock(id=1002, name="Project Two"),
        ]

        mock_instance.get_test_cases.return_value = MagicMock()
        mock_instance.get_test_cycles.return_value = MagicMock()
        mock_instance.get_modules.return_value = MagicMock()

        # Configure the mock class to return the mock instance
        mock_class.return_value = mock_instance

        yield mock_class


@pytest.fixture
def zephyr_client_with_mock_api(zephyr_config: ZephyrConfig) -> Generator[ZephyrClient, None, None]:
    """
    Create a Zephyr client with mock API responses for integration testing.

    This fixture provides a real Zephyr client that uses the API mocking harness
    to simulate API responses, which is useful for integration tests that need
    to test the client's behavior without making actual API calls.

    Args:
        zephyr_config: Zephyr configuration

    Yields:
        ZephyrClient: Zephyr client with mock API
    """
    # Create the API harness
    harness = ZephyrAPIHarness(base_url=zephyr_config.base_url)

    # Configure mock responses
    harness.add_response(
        "GET",
        "/projects",
        {
            "values": [
                {"id": "1001", "key": "TEST", "name": "Test Project"},
                {"id": "1002", "key": "DEMO", "name": "Demo Project"},
            ],
        },
    )

    harness.add_response(
        "GET",
        "/testcases",
        {
            "total": 2,
            "startAt": 0,
            "maxResults": 50,
            "isLast": True,
            "values": [
                {
                    "id": "TC-1",
                    "key": "TEST-T1",
                    "name": "Test Case 1",
                    "status": "Active",
                    "folder": {"id": "F-1", "name": "Test Folder"},
                    "priority": {"id": "P-1", "name": "High"},
                    "steps": [
                        {
                            "id": "S-1",
                            "index": 1,
                            "description": "Step 1",
                            "expectedResult": "Expected 1",
                        },
                    ],
                },
                {
                    "id": "TC-2",
                    "key": "TEST-T2",
                    "name": "Test Case 2",
                    "status": "Active",
                    "folder": {"id": "F-1", "name": "Test Folder"},
                    "priority": {"id": "P-2", "name": "Medium"},
                    "steps": [],
                },
            ],
        },
    )

    # Start the mock patching
    with harness.mock_requests():
        # Create the client with the mocked API
        client = ZephyrClient(zephyr_config)
        yield client


@pytest.fixture
def qtest_client_with_mock_api(qtest_config: QTestConfig) -> Generator[QTestClient, None, None]:
    """
    Create a qTest client with mock API responses for integration testing.

    This fixture provides a real qTest client that uses the API mocking harness
    to simulate API responses, which is useful for integration tests that need
    to test the client's behavior without making actual API calls.

    Args:
        qtest_config: qTest configuration

    Yields:
        QTestClient: qTest client with mock API
    """
    # Create the API harness
    harness = QTestAPIHarness(base_url=qtest_config.base_url)

    # Configure mock responses
    harness.add_response(
        "POST",
        "/oauth/token",
        {"access_token": "mock-token", "token_type": "bearer", "expires_in": 3600},
    )

    harness.add_response(
        "GET",
        "/api/v3/projects",
        {
            "total": 2,
            "page": 1,
            "pageSize": 50,
            "items": [{"id": 12345, "name": "Test Project"}, {"id": 67890, "name": "Demo Project"}],
        },
    )

    harness.add_response(
        "GET",
        "/api/v3/projects/12345/test-cases",
        {
            "total": 2,
            "page": 1,
            "pageSize": 50,
            "items": [
                {
                    "id": 1001,
                    "name": "Test Case 1",
                    "pid": "TC-1",
                    "description": "Test case description",
                    "module_id": 2001,
                    "test_steps": [
                        {"description": "Step 1", "expectedResult": "Expected 1", "order": 1},
                    ],
                },
                {
                    "id": 1002,
                    "name": "Test Case 2",
                    "pid": "TC-2",
                    "description": "Test case description",
                    "module_id": 2001,
                    "test_steps": [],
                },
            ],
        },
    )

    # Start the mock patching
    with harness.mock_requests():
        # Create the client with the mocked API
        client = QTestClient(qtest_config)
        yield client


@pytest.fixture
def mock_response_factory() -> callable:
    """
    Provide a factory function for creating mock responses.

    This fixture returns a function that can be used to create mock responses
    with custom status codes, headers, and content, which is useful for unit
    tests that need to test various response scenarios.

    Returns:
        callable: Function to create mock responses
    """

    def _create_response(
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        content: str | bytes | None = None,
        raise_for_status: bool = True,
    ) -> MagicMock:
        """
        Create a mock HTTP response.

        Args:
            status_code: HTTP status code
            json_data: JSON response data
            headers: Response headers
            content: Response content (as string or bytes)
            raise_for_status: Whether raise_for_status should raise an exception

        Returns:
            MagicMock: Mock response object
        """
        mock = MagicMock()
        mock.status_code = status_code

        # Set JSON data
        mock.json.return_value = json_data or {}

        # Set headers
        mock.headers = headers or {"Content-Type": "application/json"}

        # Set content
        if content is not None:
            if isinstance(content, str):
                mock.content = content.encode("utf-8")
                mock.text = content
            else:
                mock.content = content
                mock.text = content.decode("utf-8", errors="ignore")
        elif json_data is not None:
            content_str = json.dumps(json_data)
            mock.content = content_str.encode("utf-8")
            mock.text = content_str
        else:
            mock.content = b""
            mock.text = ""

        # Set raise_for_status behavior
        if raise_for_status and status_code >= 400:
            http_error = requests.exceptions.HTTPError(f"HTTP Error: {status_code}")
            http_error.response = mock
            mock.raise_for_status.side_effect = http_error
        else:
            mock.raise_for_status.return_value = None

        return mock

    return _create_response
