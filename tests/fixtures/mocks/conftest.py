"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Pytest fixtures for API mocking.

This module provides fixtures that make it easy to use the API mocking harnesses
in tests across the ZTOQ codebase.
"""

import pytest
from typing import Dict, List, Any, Tuple

from ztoq.qtest_client import QTestClient
from ztoq.qtest_models import QTestConfig
from ztoq.zephyr_client import ZephyrClient
from ztoq.models import ZephyrConfig

from tests.fixtures.mocks.api_harness import (
    ZephyrAPIHarness,
    QTestAPIHarness,
    FastAPIHarness,
)


@pytest.fixture
def mock_zephyr_api() -> ZephyrAPIHarness:
    """
    Fixture that provides a ZephyrAPIHarness with requests patching.

    Returns:
        Configured ZephyrAPIHarness instance with active request patching
    """
    harness = ZephyrAPIHarness()
    with harness.mock_requests():
        yield harness


@pytest.fixture
def mock_qtest_api() -> QTestAPIHarness:
    """
    Fixture that provides a QTestAPIHarness with requests patching.

    Returns:
        Configured QTestAPIHarness instance with active request patching
    """
    harness = QTestAPIHarness()
    with harness.mock_requests():
        yield harness


@pytest.fixture
def mock_both_apis() -> Tuple[ZephyrAPIHarness, QTestAPIHarness]:
    """
    Fixture that provides both API harnesses with requests patching.

    Returns:
        Tuple of (ZephyrAPIHarness, QTestAPIHarness) with active request patching
    """
    zephyr_harness = ZephyrAPIHarness()
    qtest_harness = QTestAPIHarness()

    with zephyr_harness.mock_requests():
        with qtest_harness.mock_requests():
            yield zephyr_harness, qtest_harness


@pytest.fixture
def api_server() -> FastAPIHarness:
    """
    Fixture that provides a running FastAPI harness server.

    Returns:
        FastAPIHarness instance with a running server
    """
    harness = FastAPIHarness()
    with harness.server_context():
        yield harness


@pytest.fixture
def zephyr_client_config() -> ZephyrConfig:
    """
    Fixture that provides a standard Zephyr client configuration for tests.

    Returns:
        ZephyrConfig instance
    """
    return ZephyrConfig(
        base_url="https://api.zephyrscale.example.com/v2",
        api_token="mock-token",
        project_key="DEMO",
    )


@pytest.fixture
def qtest_client_config() -> QTestConfig:
    """
    Fixture that provides a standard qTest client configuration for tests.

    Returns:
        QTestConfig instance
    """
    return QTestConfig(
        base_url="https://api.qtest.example.com",
        username="test-user",
        password="test-password",
        project_id=1,
    )


@pytest.fixture
def mock_zephyr_client(mock_zephyr_api, zephyr_client_config) -> ZephyrClient:
    """
    Fixture that provides a ZephyrClient with mocked API.

    This is a convenience fixture that combines the mock_zephyr_api and
    zephyr_client_config fixtures to provide a fully configured client
    that uses the mock API.

    Args:
        mock_zephyr_api: The mocked Zephyr API harness
        zephyr_client_config: The Zephyr client configuration

    Returns:
        ZephyrClient instance configured to use the mock API
    """
    # Add standard authentication response
    mock_zephyr_api.add_response(
        "GET", "/projects", {"values": [{"id": "1001", "key": "DEMO", "name": "Demo Project"}]}
    )

    return ZephyrClient(zephyr_client_config)


@pytest.fixture
def mock_qtest_client(mock_qtest_api, qtest_client_config) -> QTestClient:
    """
    Fixture that provides a QTestClient with mocked API.

    This is a convenience fixture that combines the mock_qtest_api and
    qtest_client_config fixtures to provide a fully configured client
    that uses the mock API.

    Args:
        mock_qtest_api: The mocked qTest API harness
        qtest_client_config: The qTest client configuration

    Returns:
        QTestClient instance configured to use the mock API
    """
    # Add standard authentication response
    mock_qtest_api.add_response(
        "POST",
        "/oauth/token",
        {"access_token": "mock-qtest-token", "token_type": "bearer", "expires_in": 3600},
    )

    # Add standard project response
    mock_qtest_api.add_response(
        "GET",
        "/api/v3/projects",
        {
            "total": 1,
            "page": 1,
            "pageSize": 100,
            "items": [{"id": 1, "name": "qTest Demo Project"}],
        },
    )

    return QTestClient(qtest_client_config)


@pytest.fixture
def mock_both_clients(
    mock_both_apis, zephyr_client_config, qtest_client_config
) -> Tuple[ZephyrClient, QTestClient]:
    """
    Fixture that provides both clients with mocked APIs.

    This is a convenience fixture that provides both fully configured clients
    that use the mock APIs.

    Args:
        mock_both_apis: The mocked API harnesses
        zephyr_client_config: The Zephyr client configuration
        qtest_client_config: The qTest client configuration

    Returns:
        Tuple of (ZephyrClient, QTestClient) configured to use the mock APIs
    """
    zephyr_harness, qtest_harness = mock_both_apis

    # Add standard Zephyr responses
    zephyr_harness.add_response(
        "GET", "/projects", {"values": [{"id": "1001", "key": "DEMO", "name": "Demo Project"}]}
    )

    # Add standard qTest responses
    qtest_harness.add_response(
        "POST",
        "/oauth/token",
        {"access_token": "mock-qtest-token", "token_type": "bearer", "expires_in": 3600},
    )

    qtest_harness.add_response(
        "GET",
        "/api/v3/projects",
        {
            "total": 1,
            "page": 1,
            "pageSize": 100,
            "items": [{"id": 1, "name": "qTest Demo Project"}],
        },
    )

    return ZephyrClient(zephyr_client_config), QTestClient(qtest_client_config)
