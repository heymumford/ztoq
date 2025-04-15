"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Examples of using the API mocking harness for ZTOQ.

This file demonstrates how to use the API mocking harness with both the qTest and Zephyr APIs.
It shows different mocking approaches and common usage patterns.
"""

import json

import pytest
import requests

from tests.fixtures.mocks.api_harness import (
    FastAPIHarness,
    MockAPITestBase,
    ZephyrAPIHarness,
)
from ztoq.models import ZephyrConfig
from ztoq.qtest_client import QTestClient
from ztoq.qtest_models import QTestConfig, QTestTestCase
from ztoq.zephyr_client import ZephyrClient


# Example 1: Using the MockAPITestBase class
class TestAPIHarnessWithBaseClass(MockAPITestBase):
    """
    Example of using the MockAPITestBase class for API testing.

    This approach uses class fixtures to set up the API harnesses
    and provides methods for common operations.
    """

    def test_zephyr_api_basic(self, mock_zephyr_api):
        """Test basic Zephyr API operations."""
        # Configure test data
        mock_zephyr_api.add_response(
            "GET",
            "/projects",
            {
                "values": [
                    {"id": "1001", "key": "DEMO", "name": "Demo Project"},
                    {"id": "1002", "key": "TEST", "name": "Test Project"},
                ],
            },
        )

        # Create Zephyr client
        config = ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
            api_token="mock-token",
            project_key="DEMO",
        )
        client = ZephyrClient(config)

        # Call API
        projects = client.get_projects()

        # Verify results
        assert len(projects) == 2
        assert projects[0].id == "1001"
        assert projects[0].key == "DEMO"
        assert projects[1].id == "1002"
        assert projects[1].key == "TEST"

        # Verify requests were tracked
        requests = mock_zephyr_api.get_requests(method="GET", path="/projects")
        assert len(requests) == 1

    def test_qtest_api_basic(self, mock_qtest_api):
        """Test basic qTest API operations."""
        # Configure mock responses
        mock_qtest_api.add_response(
            "POST",
            "/oauth/token",
            {"access_token": "mock-qtest-token", "token_type": "bearer", "expires_in": 3600},
        )

        mock_qtest_api.add_response(
            "GET",
            "/api/v3/projects",
            {
                "total": 2,
                "page": 1,
                "pageSize": 100,
                "items": [{"id": 1, "name": "Project One"}, {"id": 2, "name": "Project Two"}],
            },
        )

        # Create qTest client
        config = QTestConfig(
            base_url="https://api.qtest.example.com",
            username="test-user",
            password="test-password",
            project_id=1,
        )
        client = QTestClient(config)

        # Call API
        projects = client.get_projects()

        # Verify results
        assert len(projects) == 2
        assert projects[0].id == 1
        assert projects[0].name == "Project One"
        assert projects[1].id == 2
        assert projects[1].name == "Project Two"

        # Verify requests were tracked
        auth_requests = mock_qtest_api.get_requests(method="POST", path="/oauth/token")
        assert len(auth_requests) == 1

        project_requests = mock_qtest_api.get_requests(method="GET", path="/api/v3/projects")
        assert len(project_requests) == 1


# Example 2: Using standalone fixtures
class TestAPIHarnessWithFixtures:
    """
    Example of using standalone fixtures for API testing.

    This approach uses pytest fixtures directly for simpler test cases.
    """

    def test_zephyr_api_with_error(self, mock_zephyr_api):
        """Test handling API errors with the Zephyr harness."""
        # Configure mock to return an error response
        mock_zephyr_api.add_error_response(
            "GET", "/testcases", "Invalid project key", status_code=400,
        )

        # Set error rate for random failures
        mock_zephyr_api.set_error_rate(0.0)  # No random errors

        # Create Zephyr client
        config = ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
            api_token="mock-token",
            project_key="INVALID",
        )
        client = ZephyrClient(config)

        # Call API and expect exception
        with pytest.raises(requests.exceptions.HTTPError) as excinfo:
            list(client.get_test_cases())

        # Verify error details
        assert "400" in str(excinfo.value)  # Status code

        # Verify request was tracked
        requests = mock_zephyr_api.get_requests(path="/testcases")
        assert len(requests) == 1

    def test_qtest_api_pagination(self, mock_qtest_api):
        """Test API pagination with the qTest harness."""
        # Configure mock responses for paginated requests
        mock_qtest_api.add_response(
            "POST",
            "/oauth/token",
            {"access_token": "mock-qtest-token", "token_type": "bearer", "expires_in": 3600},
        )

        # First page of test cases
        mock_qtest_api.add_response(
            "GET",
            "/api/v3/projects/1/test-cases",
            {
                "total": 3,
                "page": 1,
                "pageSize": 2,
                "items": [{"id": 101, "name": "Test Case 1"}, {"id": 102, "name": "Test Case 2"}],
            },
        )

        # Second page of test cases (with page=2 parameter)
        def page_two_response(method, path, params, data, headers, files):
            if params and params.get("page") == 2:
                return {
                    "data": {
                        "total": 3,
                        "page": 2,
                        "pageSize": 2,
                        "items": [{"id": 103, "name": "Test Case 3"}],
                    },
                }, 200
            return None, 404

        # Use a request handler to check query parameters
        mock_qtest_api._handle_request = page_two_response

        # Create qTest client
        config = QTestConfig(
            base_url="https://api.qtest.example.com",
            username="test-user",
            password="test-password",
            project_id=1,
        )

        # Here we would simulate the pagination
        # In a real test, we'd use the actual client interface


# Example 3: Using context managers
class TestAPIHarnessWithContextManagers:
    """
    Example of using context managers for API testing.

    This approach gives more control over mocking lifecycle.
    """

    def test_using_request_context(self):
        """Test using the requests mock context manager."""
        # Create API harness
        zephyr_harness = ZephyrAPIHarness()

        # Configure test data
        zephyr_harness.add_response(
            "GET", "/projects", {"values": [{"id": "1001", "key": "DEMO", "name": "Demo Project"}]},
        )

        # Use context manager to patch requests
        with zephyr_harness.mock_requests():
            # Create Zephyr client
            config = ZephyrConfig(
                base_url="https://api.zephyrscale.example.com/v2",
                api_token="mock-token",
                project_key="DEMO",
            )
            client = ZephyrClient(config)

            # Call API
            projects = client.get_projects()

            # Verify results
            assert len(projects) == 1
            assert projects[0].id == "1001"
            assert projects[0].key == "DEMO"

        # Verify the mock was removed when context exited
        # This would fail outside the context manager
        # client.get_projects()  # This would make a real HTTP request

    def test_using_both_apis(self, mock_both_apis):
        """Test using both API harnesses together."""
        # Destructure the tuple from the fixture
        zephyr_harness, qtest_harness = mock_both_apis

        # Configure Zephyr responses
        zephyr_harness.add_response(
            "GET", "/projects", {"values": [{"id": "1001", "key": "DEMO", "name": "Demo Project"}]},
        )

        # Configure qTest responses
        qtest_harness.add_response(
            "POST",
            "/oauth/token",
            {"access_token": "mock-qtest-token", "token_type": "bearer", "expires_in": 3600},
        )

        qtest_harness.add_response(
            "GET",
            "/api/v3/projects",
            {"total": 1, "page": 1, "pageSize": 100, "items": [{"id": 1, "name": "Project One"}]},
        )

        # Create clients
        zephyr_config = ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
            api_token="mock-token",
            project_key="DEMO",
        )
        zephyr_client = ZephyrClient(zephyr_config)

        qtest_config = QTestConfig(
            base_url="https://api.qtest.example.com",
            username="test-user",
            password="test-password",
            project_id=1,
        )
        qtest_client = QTestClient(qtest_config)

        # Call both APIs
        zephyr_projects = zephyr_client.get_projects()
        qtest_projects = qtest_client.get_projects()

        # Verify results
        assert len(zephyr_projects) == 1
        assert zephyr_projects[0].key == "DEMO"

        assert len(qtest_projects) == 1
        assert qtest_projects[0].name == "Project One"


# Example 4: FastAPI harness for more realistic API testing
class TestWithFastAPIHarness:
    """
    Example of using the FastAPI harness for more realistic API testing.

    This approach runs an actual API server for testing.
    """

    @pytest.fixture
    def api_server(self):
        """Fixture to provide a running API server."""
        harness = FastAPIHarness(port=8123)  # Use a port unlikely to conflict
        with harness.server_context():
            yield harness

    def test_with_real_server(self, api_server):
        """Test using a real API server."""
        # Create clients using server URLs
        zephyr_config = ZephyrConfig(
            base_url=f"{api_server.zephyr_url}", api_token="test-token", project_key="TEST",
        )
        zephyr_client = ZephyrClient(zephyr_config)

        qtest_config = QTestConfig(
            base_url=f"{api_server.base_url}",
            username="test-user",
            password="test-password",
            project_id=1,
        )
        qtest_client = QTestClient(qtest_config)

        # Make requests to the running server
        # Note: These will hit the actual FastAPI server running locally
        zephyr_response = requests.get(
            f"{api_server.zephyr_url}/projects", headers={"Authorization": "Bearer test-token"},
        )
        qtest_response = requests.post(
            f"{api_server.base_url}/oauth/token",
            json={"username": "test-user", "password": "test-password"},
        )

        # Verify responses
        assert zephyr_response.status_code == 200
        assert "values" in zephyr_response.json()

        assert qtest_response.status_code == 200
        assert "access_token" in qtest_response.json()


# Example a real-world scenario: Testing a migration function that uses both APIs
def migrate_test_case(
    zephyr_client: ZephyrClient, qtest_client: QTestClient, zephyr_case_key: str,
) -> int:
    """
    Migrate a test case from Zephyr Scale to qTest.

    Args:
        zephyr_client: Zephyr Scale client
        qtest_client: qTest client
        zephyr_case_key: Zephyr test case key

    Returns:
        qTest test case ID
    """
    # Get test case details from Zephyr
    zephyr_test_cases = list(zephyr_client.get_test_cases())
    zephyr_case = next((tc for tc in zephyr_test_cases if tc.key == zephyr_case_key), None)

    if not zephyr_case:
        raise ValueError(f"Test case with key {zephyr_case_key} not found")

    # Convert to qTest test case
    qtest_case = QTestTestCase(
        name=zephyr_case.name,
        description=zephyr_case.description or "",
        precondition=getattr(zephyr_case, "precondition", ""),
        test_steps=[
            {
                "description": step.get("description", ""),
                "expectedResult": step.get("expectedResult", ""),
                "order": i + 1,
            }
            for i, step in enumerate(getattr(zephyr_case, "steps", []))
        ],
    )

    # Create in qTest
    created_case = qtest_client.create_test_case(qtest_case)
    return created_case.id


class TestMigrationFunction:
    """Test the test case migration function."""

    def test_migrate_test_case(self, mock_both_apis):
        """Test migrating a test case from Zephyr to qTest."""
        # Destructure the tuple from the fixture
        zephyr_harness, qtest_harness = mock_both_apis

        # Configure Zephyr mock
        zephyr_test_case = {
            "id": "12345",
            "key": "DEMO-T1",
            "name": "Login Test",
            "description": "Test login functionality",
            "steps": [
                {
                    "description": "Navigate to login page",
                    "expectedResult": "Login page is displayed",
                },
                {"description": "Enter valid credentials", "expectedResult": "User is logged in"},
            ],
        }

        zephyr_harness.add_response(
            "GET",
            "/testcases",
            {
                "total": 1,
                "startAt": 0,
                "maxResults": 50,
                "isLast": True,
                "values": [zephyr_test_case],
            },
        )

        # Configure qTest mock
        qtest_harness.add_response(
            "POST",
            "/oauth/token",
            {"access_token": "mock-qtest-token", "token_type": "bearer", "expires_in": 3600},
        )

        # Mock the create test case response
        qtest_harness.add_response(
            "POST",
            "/api/v3/projects/1/test-cases",
            {
                "id": 1001,
                "name": "Login Test",
                "description": "Test login functionality",
                "precondition": "",
                "test_steps": [
                    {
                        "description": "Navigate to login page",
                        "expectedResult": "Login page is displayed",
                        "order": 1,
                    },
                    {
                        "description": "Enter valid credentials",
                        "expectedResult": "User is logged in",
                        "order": 2,
                    },
                ],
            },
        )

        # Create clients
        zephyr_config = ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
            api_token="mock-token",
            project_key="DEMO",
        )
        zephyr_client = ZephyrClient(zephyr_config)

        qtest_config = QTestConfig(
            base_url="https://api.qtest.example.com",
            username="test-user",
            password="test-password",
            project_id=1,
        )
        qtest_client = QTestClient(qtest_config)

        # Call the migration function
        qtest_case_id = migrate_test_case(zephyr_client, qtest_client, "DEMO-T1")

        # Verify results
        assert qtest_case_id == 1001

        # Verify requests were made correctly
        zephyr_requests = zephyr_harness.get_requests(method="GET", path="/testcases")
        assert len(zephyr_requests) == 1

        qtest_requests = qtest_harness.get_requests(
            method="POST", path="/api/v3/projects/1/test-cases",
        )
        assert len(qtest_requests) == 1
        assert "Login Test" in json.dumps(qtest_requests[0]["data"])


# Example 5: Testing error conditions
class TestErrorConditions:
    """Test API error conditions."""

    def test_rate_limiting(self, mock_zephyr_api):
        """Test handling API rate limiting."""
        # Configure the harness to simulate rate limiting
        mock_zephyr_api.set_error_rate(0.0)  # No random errors

        # Add a rate limit error for the first request
        mock_zephyr_api.add_error_response(
            "GET", "/testcases", "Rate limit exceeded", status_code=429,
        )

        # Add success response for subsequent requests
        def conditional_response(method, path, params, data, headers, files):
            # Get the number of requests made to this endpoint
            requests = mock_zephyr_api.get_requests(method="GET", path="/testcases")

            # Return success for second request
            if len(requests) > 0:
                return {
                    "total": 1,
                    "startAt": 0,
                    "maxResults": 50,
                    "isLast": True,
                    "values": [{"id": "12345", "key": "DEMO-T1", "name": "Test Case"}],
                }, 200

            # Default to using the configured responses (which has our 429 error)
            return None, None

        # Set up the conditional response
        mock_zephyr_api._handle_request = conditional_response

        # Create client
        config = ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
            api_token="mock-token",
            project_key="DEMO",
        )
        client = ZephyrClient(config)

        # First request should fail with rate limit
        with pytest.raises(requests.exceptions.HTTPError) as excinfo:
            list(client.get_test_cases())
        assert "429" in str(excinfo.value)

        # Simulate retry after rate limit window
        # In a real scenario, you might use mock_api.reset() or similar

        # Second request should succeed (handled by our conditional_response)
        mock_zephyr_api.add_response(
            "GET",
            "/testcases",
            {
                "total": 1,
                "startAt": 0,
                "maxResults": 50,
                "isLast": True,
                "values": [{"id": "12345", "key": "DEMO-T1", "name": "Test Case"}],
            },
        )

        # Verify successful request
        test_cases = list(client.get_test_cases())
        assert len(test_cases) == 1
        assert test_cases[0].key == "DEMO-T1"


# Example 6: Test with delayed responses
class TestPerformanceSimulation:
    """Test API performance simulations."""

    def test_delayed_responses(self, mock_zephyr_api):
        """Test handling delayed API responses."""
        # Configure the harness with delays
        mock_zephyr_api.set_delay_range(0.01, 0.02)  # 10-20ms delays

        # Add response
        mock_zephyr_api.add_response(
            "GET", "/projects", {"values": [{"id": "1001", "key": "DEMO", "name": "Demo Project"}]},
        )

        # Create client
        config = ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
            api_token="mock-token",
            project_key="DEMO",
        )
        client = ZephyrClient(config)

        # Call API and measure time
        import time

        start_time = time.time()
        projects = client.get_projects()
        end_time = time.time()

        # Verify results
        assert len(projects) == 1
        assert projects[0].key == "DEMO"

        # Verify delay was applied
        elapsed_time = end_time - start_time
        assert elapsed_time >= 0.01  # At least 10ms delay
