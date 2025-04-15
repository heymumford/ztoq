"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from ztoq.models import Project as ZephyrProject, ZephyrConfig
from ztoq.qtest_client import QTestClient
from ztoq.qtest_mock_server import QTestMockServer
from ztoq.qtest_models import QTestConfig, QTestProject
from ztoq.zephyr_client import ZephyrClient
from ztoq.zephyr_mock_server import ZephyrMockServer


@pytest.mark.integration
@pytest.mark.skip("Compatibility tests need further implementation")
class TestMockServerCompatibility:
    """
    Integration tests verifying that mock server API implementations are compatible
    with their real counterparts in terms of API structure and response formats.
    """

    @pytest.fixture
    def qtest_mock_server(self):
        """Create a QTest mock server instance."""
        return QTestMockServer()

    @pytest.fixture
    def zephyr_mock_server(self):
        """Create a Zephyr mock server instance."""
        return ZephyrMockServer()

    @pytest.fixture
    def qtest_client(self, qtest_mock_server):
        """Create a QTest client configured to use the mock server."""
        # Create a client with mock config
        config = QTestConfig(
            base_url="https://mock.qtest.com",
            username="test_user",
            password="test_password",
            project_id=12345,
        )
        client = QTestClient(config)

        # Patch the requests session to route to the mock server
        def mock_request(method, url, **kwargs):
            # Parse the URL to extract the endpoint
            endpoint = url.replace(config.api_url, "")
            # Handle special case for authentication
            if endpoint.startswith("/oauth/token"):
                response = qtest_mock_server._handle_auth("manager")
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = response
                mock_resp.raise_for_status.return_value = None
                return mock_resp

            # Extract query parameters
            params = kwargs.get("params", {})
            data = kwargs.get("json", {}) or kwargs.get("data", {})
            headers = kwargs.get("headers", {})

            # Route the request to the appropriate handler
            if method.upper() == "GET":
                if endpoint.startswith("/api/v3/projects"):
                    if endpoint == "/api/v3/projects":
                        response = qtest_mock_server._handle_get_projects(params)
                    else:
                        # Handle specific project endpoint
                        project_id = int(endpoint.split("/")[-1])
                        response = qtest_mock_server._handle_get_project(project_id)
                elif endpoint.startswith("/api/v3/projects") and "/modules" in endpoint:
                    project_id = int(endpoint.split("/")[4])
                    response = qtest_mock_server._handle_get_modules(project_id, params)
                elif endpoint.startswith("/api/v3/projects") and "/test-cases" in endpoint:
                    project_id = int(endpoint.split("/")[4])
                    if endpoint.endswith("/test-cases"):
                        response = qtest_mock_server._handle_get_test_cases(project_id, params)
                    else:
                        # Handle specific test case
                        test_case_id = int(endpoint.split("/")[-1])
                        response = qtest_mock_server._handle_get_test_case(test_case_id)
                else:
                    # Default fallback
                    response = {"error": "Endpoint not implemented in mock test"}

            elif method.upper() == "POST":
                if endpoint.startswith("/api/v3/projects") and "/test-cases" in endpoint:
                    project_id = int(endpoint.split("/")[4])
                    response = qtest_mock_server._handle_create_test_case(project_id, data)
                else:
                    # Default fallback
                    response = {"error": "Endpoint not implemented in mock test"}
            else:
                response = {"error": f"Method {method} not implemented in mock test"}

            # Create a mock response
            mock_resp = MagicMock()
            mock_resp.status_code = 200 if "error" not in response else 400
            mock_resp.json.return_value = response
            mock_resp.raise_for_status.return_value = None
            return mock_resp

        # Patch the session request method
        client._session.request = mock_request
        return client

    @pytest.fixture
    def zephyr_client(self, zephyr_mock_server):
        """Create a Zephyr client configured to use the mock server."""
        # Create a client with mock config
        config = ZephyrConfig(
            base_url="https://mock.zephyrscale.com/v2", api_token="mock_token", project_key="DEMO",
        )
        client = ZephyrClient(config)

        # Patch the requests session to route to the mock server
        def mock_request(method, url, **kwargs):
            # Parse the URL to extract the endpoint
            endpoint = url.replace(config.base_url, "")
            if not endpoint.startswith("/"):
                endpoint = "/" + endpoint

            # Extract query parameters
            params = kwargs.get("params", {})
            data = kwargs.get("json", {}) or kwargs.get("data", {})
            headers = kwargs.get("headers", {})

            # Route the request to the appropriate handler
            response = zephyr_mock_server.handle_request(
                method, endpoint, params=params, data=data, headers=headers,
            )

            # Create a mock response
            mock_resp = MagicMock()
            mock_resp.status_code = 200 if "error" not in response else 400
            mock_resp.json.return_value = response
            mock_resp.text = json.dumps(response)
            mock_resp.raise_for_status.return_value = None
            return mock_resp

        # Patch the session request method
        client._session.request = mock_request
        return client

    def test_qtest_projects_endpoint_format(self, qtest_client):
        """Test that the QTest projects endpoint response format matches the expected schema."""
        # Get projects from the mock server
        projects = qtest_client.get_projects()

        # Verify the response structure
        assert isinstance(projects, list)
        assert len(projects) > 0

        # Verify each project has the required fields
        for project in projects:
            assert isinstance(project, QTestProject)
            assert hasattr(project, "id")
            assert hasattr(project, "name")

    def test_zephyr_projects_endpoint_format(self, zephyr_client):
        """Test that the Zephyr projects endpoint response format matches the expected schema."""
        # Get projects from the mock server
        projects = zephyr_client.get_projects()

        # Verify the response structure
        assert isinstance(projects, list)
        assert len(projects) > 0

        # Verify each project has the required fields
        for project in projects:
            assert isinstance(project, ZephyrProject)
            assert hasattr(project, "id")
            assert hasattr(project, "key")
            assert hasattr(project, "name")

    def test_qtest_pagination_compatibility(self, qtest_client):
        """Test that the QTest mock server pagination works the same as the real API."""
        # Test different page sizes
        page_size_1 = qtest_client.get_test_cases(project_id=12345, params={"pageSize": 1})
        page_size_2 = qtest_client.get_test_cases(project_id=12345, params={"pageSize": 2})

        # Get all items from both iterators
        items_1 = list(page_size_1)
        items_2 = list(page_size_2)

        # Verify pagination works correctly
        assert len(items_1) <= 1
        assert len(items_2) <= 2
        assert len(items_2) >= len(items_1)

    def test_zephyr_pagination_compatibility(self, zephyr_client):
        """Test that the Zephyr mock server pagination works the same as the real API."""
        # Get projects to get a valid project key
        projects = zephyr_client.get_projects()
        project_key = projects[0].key if projects else "DEMO"

        # Test different page sizes
        cases_1 = zephyr_client.get_test_cases(project_key=project_key)
        cases_1._params["maxResults"] = 1

        cases_2 = zephyr_client.get_test_cases(project_key=project_key)
        cases_2._params["maxResults"] = 2

        # Get all items from both iterators
        items_1 = list(cases_1)
        items_2 = list(cases_2)

        # Verify pagination works correctly
        assert len(items_1) <= 1
        assert len(items_2) <= 2

    def test_qtest_filtering_compatibility(self, qtest_client):
        """Test that the QTest mock server filtering works the same as the real API."""
        # Test filtering test cases by module
        all_test_cases = list(qtest_client.get_test_cases(project_id=12345))
        filtered_test_cases = list(
            qtest_client.get_test_cases(project_id=12345, params={"parentId": 102}),
        )

        # Verify filtering works correctly
        assert len(filtered_test_cases) <= len(all_test_cases)
        for tc in filtered_test_cases:
            assert tc.module_id == 102

    def test_zephyr_filtering_compatibility(self, zephyr_client):
        """Test that the Zephyr mock server filtering works the same as the real API."""
        # Get project key from first project
        projects = zephyr_client.get_projects()
        project_key = projects[0].key if projects else "DEMO"

        # Test filtering test cases by folder
        all_test_cases = list(zephyr_client.get_test_cases(project_key=project_key))

        # Get a folder ID to filter by
        folders = zephyr_client.get_folders(project_key=project_key)
        if folders:
            folder_id = folders[0].id
            filtered_cases = zephyr_client.get_test_cases(project_key=project_key)
            filtered_cases._params["folderId"] = folder_id
            filtered_test_cases = list(filtered_cases)

            # Verify filtering works correctly
            assert len(filtered_test_cases) <= len(all_test_cases)

    def test_qtest_error_response_format(self, qtest_client):
        """Test that the QTest mock server error responses match the format of real API errors."""
        # Get a non-existent test case to trigger an error
        with pytest.raises(Exception) as e:
            qtest_client.get_test_case(999999)

        # Verify the error response contains the expected fields
        assert "error" in str(e).lower() or "not found" in str(e).lower()

    def test_zephyr_error_response_format(self, zephyr_client):
        """Test that the Zephyr mock server error responses match the format of real API errors."""
        # Get a non-existent test case to trigger an error
        with pytest.raises(Exception) as e:
            zephyr_client._make_request("GET", "/testcases/999999")

        # Verify the error response contains the expected fields
        assert "error" in str(e).lower() or "not found" in str(e).lower()

    @pytest.mark.parametrize(
        "endpoint_path",
        [
            "/projects",
            "/testcases",
            "/testcycles",
            "/folders",
        ],
    )
    def test_zephyr_endpoint_availability(self, zephyr_client, endpoint_path):
        """
        Test that the Zephyr mock server implements the same endpoints as the real API.
        This test verifies that key endpoints are available and respond without errors.
        """
        # Patch the client's request method to test endpoint availability
        with patch.object(
            zephyr_client._session, "request", wraps=zephyr_client._session.request,
        ) as mock_request:
            # Call an appropriate client method based on the endpoint
            try:
                if endpoint_path == "/projects":
                    zephyr_client.get_projects()
                elif endpoint_path == "/testcases":
                    # Get a project key first
                    projects = zephyr_client.get_projects()
                    if projects:
                        zephyr_client.get_test_cases(project_key=projects[0].key)
                elif endpoint_path == "/testcycles":
                    # Get a project key first
                    projects = zephyr_client.get_projects()
                    if projects:
                        zephyr_client.get_test_cycles(project_key=projects[0].key)
                elif endpoint_path == "/folders":
                    # Get a project key first
                    projects = zephyr_client.get_projects()
                    if projects:
                        zephyr_client.get_folders(project_key=projects[0].key)
            except Exception as e:
                pytest.fail(f"Endpoint {endpoint_path} not properly implemented: {e!s}")

            # Verify the request was made with the correct method and endpoint
            mock_request.assert_called()

    @pytest.mark.parametrize(
        "endpoint_path",
        [
            "/api/v3/projects",
            "/api/v3/projects/{project_id}/test-cases",
            "/api/v3/projects/{project_id}/modules",
            "/api/v3/projects/{project_id}/test-cycles",
        ],
    )
    def test_qtest_endpoint_availability(self, qtest_client, endpoint_path):
        """
        Test that the QTest mock server implements the same endpoints as the real API.
        This test verifies that key endpoints are available and respond without errors.
        """
        # Patch the client's request method to test endpoint availability
        with patch.object(
            qtest_client._session, "request", wraps=qtest_client._session.request,
        ) as mock_request:
            # Call an appropriate client method based on the endpoint
            try:
                if endpoint_path == "/api/v3/projects":
                    qtest_client.get_projects()
                elif endpoint_path == "/api/v3/projects/{project_id}/test-cases":
                    qtest_client.get_test_cases(project_id=12345)
                elif endpoint_path == "/api/v3/projects/{project_id}/modules":
                    qtest_client.get_modules(project_id=12345)
                elif endpoint_path == "/api/v3/projects/{project_id}/test-cycles":
                    qtest_client.get_test_cycles(project_id=12345)
            except Exception as e:
                pytest.fail(f"Endpoint {endpoint_path} not properly implemented: {e!s}")

            # Verify the request was made
            mock_request.assert_called()
