"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import pytest
from ztoq.zephyr_mock_server import ZephyrMockServer
from ztoq.models import (
    Case,
    CycleInfo,
    Execution,
    Folder,
    Project,
)


@pytest.mark.unit()
class TestZephyrMockServer:
    """Test suite for the Zephyr mock server."""

    def setup_method(self):
        """Set up test method by creating a fresh server instance."""
        self.server = ZephyrMockServer()

    def test_server_initialization(self):
        """Test server initialization and sample data."""
        # Check if server is initialized with data
        assert self.server.data is not None
        assert "projects" in self.server.data
        assert "test_cases" in self.server.data
        assert "test_cycles" in self.server.data
        assert "test_executions" in self.server.data

        # Check if sample data is populated
        assert len(self.server.data["projects"]) > 0
        assert len(self.server.data["folders"]) > 0
        assert len(self.server.data["test_cases"]) > 0
        assert len(self.server.data["test_cycles"]) > 0
        assert len(self.server.data["test_executions"]) > 0

    def test_authentication(self):
        """Test authentication endpoint."""
        # Test authentication request
        response = self.server.handle_request(
            "POST", "/authorize", data={"username": "test_user", "password": "test_password"}
        )

        # Verify response format
        assert "access_token" in response
        assert "token_type" in response
        assert "expires_in" in response
        assert response["token_type"] == "bearer"

        # Verify token was added to valid tokens
        assert response["access_token"] in self.server.valid_tokens

    def test_projects_listing(self):
        """Test projects listing endpoint."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Test projects listing
        response = self.server.handle_request(
            "GET", "/projects", headers={"Authorization": f"Bearer {token}"}
        )

        # Verify response format
        assert "values" in response
        assert "maxResults" in response
        assert "startAt" in response
        assert "isLast" in response
        assert "totalCount" in response

        # Verify projects data
        assert len(response["values"]) > 0
        for project in response["values"]:
            assert "id" in project
            assert "key" in project
            assert "name" in project

    def test_project_by_key(self):
        """Test getting a project by key."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Get a project key from the sample data
        project_key = next(iter(self.server.data["projects"].values()))["key"]

        # Test getting project by key
        response = self.server.handle_request(
            "GET", f"/projects/{project_key}", headers={"Authorization": f"Bearer {token}"}
        )

        # Verify project data
        assert response["key"] == project_key
        assert "id" in response
        assert "name" in response
        assert "description" in response

    def test_folders_listing(self):
        """Test folders listing endpoint."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Get a project key from the sample data
        project_key = next(iter(self.server.data["projects"].values()))["key"]

        # Test folders listing for a project
        response = self.server.handle_request(
            "GET",
            "/folders",
            params={"projectKey": project_key},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify response format
        assert "values" in response
        assert "maxResults" in response
        assert "startAt" in response
        assert "isLast" in response
        assert "totalCount" in response

        # Verify folders data
        assert len(response["values"]) > 0
        for folder in response["values"]:
            assert "id" in folder
            assert "name" in folder
            assert "folder_type" in folder
            assert "project_key" in folder
            assert folder["project_key"] == project_key

    def test_create_folder(self):
        """Test creating a folder."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Get a project key from the sample data
        project_key = next(iter(self.server.data["projects"].values()))["key"]

        # Test creating a folder
        folder_data = {
            "id": "12345",
            "name": "Test Folder",
            "folder_type": "TEST_CASE",
            "project_key": project_key,
        }

        response = self.server.handle_request(
            "POST", "/folders", data=folder_data, headers={"Authorization": f"Bearer {token}"}
        )

        # Verify folder was created
        assert "id" in response
        assert response["name"] == "Test Folder"
        assert response["folder_type"] == "TEST_CASE"
        assert response["project_key"] == project_key

        # Verify folder exists in data store
        assert response["id"] in self.server.data["folders"]

    def test_test_cases_listing(self):
        """Test test cases listing endpoint."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Get a project key from the sample data
        project_key = next(iter(self.server.data["projects"].values()))["key"]

        # Test test cases listing for a project
        response = self.server.handle_request(
            "GET",
            "/testcases",
            params={"projectKey": project_key},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify response format
        assert "values" in response
        assert "maxResults" in response
        assert "startAt" in response
        assert "isLast" in response
        assert "totalCount" in response

        # Verify test cases data
        assert len(response["values"]) > 0
        for test_case in response["values"]:
            assert "id" in test_case
            assert "key" in test_case
            assert test_case["key"].startswith(f"{project_key}-")
            assert "name" in test_case
            assert "steps" in test_case

    def test_test_case_by_key(self):
        """Test getting a test case by key."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Get a test case key from the sample data
        test_case_key = next(iter(self.server.data["test_cases"].values()))["key"]

        # Test getting test case by key
        response = self.server.handle_request(
            "GET", f"/testcases/{test_case_key}", headers={"Authorization": f"Bearer {token}"}
        )

        # Verify test case data
        assert response["key"] == test_case_key
        assert "id" in response
        assert "name" in response
        assert "steps" in response
        assert len(response["steps"]) > 0

    def test_create_test_case(self):
        """Test creating a test case."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Get a project key and folder from the sample data
        project_key = next(iter(self.server.data["projects"].values()))["key"]
        folder = next(
            (
                f
                for f in self.server.data["folders"].values()
                if f["project_key"] == project_key and f["folder_type"] == "TEST_CASE"
            ),
            None,
        )

        # Test creating a test case
        test_case_data = {
            "id": "9999",
            "key": f"{project_key}-T999",
            "name": "Test Case Created in Test",
            "folder": folder["id"],
            "folder_name": folder["name"],
            "steps": [
                {
                    "id": "8001",
                    "index": 1,
                    "description": "Test step 1",
                    "expected_result": "Expected result 1",
                },
                {
                    "id": "8002",
                    "index": 2,
                    "description": "Test step 2",
                    "expected_result": "Expected result 2",
                },
            ],
        }

        response = self.server.handle_request(
            "POST", "/testcases", data=test_case_data, headers={"Authorization": f"Bearer {token}"}
        )

        # Verify test case was created
        assert "id" in response
        assert response["key"] == f"{project_key}-T999"
        assert response["name"] == "Test Case Created in Test"
        assert len(response["steps"]) == 2

        # Verify test case exists in data store
        assert response["id"] in self.server.data["test_cases"]

    def test_test_cycles_listing(self):
        """Test test cycles listing endpoint."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Get a project key from the sample data
        project_key = next(iter(self.server.data["projects"].values()))["key"]

        # Test test cycles listing for a project
        response = self.server.handle_request(
            "GET",
            "/testcycles",
            params={"projectKey": project_key},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify response format
        assert "values" in response
        assert "maxResults" in response
        assert "startAt" in response
        assert "isLast" in response
        assert "totalCount" in response

        # Verify test cycles data
        assert len(response["values"]) > 0
        for test_cycle in response["values"]:
            assert "id" in test_cycle
            assert "key" in test_cycle
            assert "name" in test_cycle
            assert "project_key" in test_cycle
            assert test_cycle["project_key"] == project_key

    def test_test_executions_listing(self):
        """Test test executions listing endpoint."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Get a test cycle ID from the sample data
        test_cycle_id = next(iter(self.server.data["test_cycles"].values()))["id"]

        # Test test executions listing for a test cycle
        response = self.server.handle_request(
            "GET",
            "/testexecutions",
            params={"cycleId": test_cycle_id},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify response format
        assert "values" in response
        assert "maxResults" in response
        assert "startAt" in response
        assert "isLast" in response
        assert "totalCount" in response

        # Verify test executions data
        if len(response["values"]) > 0:
            for test_execution in response["values"]:
                assert "id" in test_execution
                assert "test_case_key" in test_execution
                assert "cycle_id" in test_execution
                assert "status" in test_execution
                assert test_execution["cycle_id"] == test_cycle_id

    def test_create_test_execution(self):
        """Test creating a test execution."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Get a test case and test cycle from the sample data
        test_case = next(iter(self.server.data["test_cases"].values()))
        test_cycle = next(iter(self.server.data["test_cycles"].values()))

        # Test creating a test execution
        test_execution_data = {
            "id": "88888",
            "test_case_key": test_case["key"],
            "cycle_id": test_cycle["id"],
            "cycle_name": test_cycle["name"],
            "status": "Passed",
            "steps": [
                {
                    "id": "7001",
                    "index": 1,
                    "description": "Test step 1",
                    "expected_result": "Expected result 1",
                    "actual_result": "Actual result 1",
                    "status": "Passed",
                }
            ],
        }

        response = self.server.handle_request(
            "POST",
            "/testexecutions",
            data=test_execution_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify test execution was created
        assert "id" in response
        assert response["test_case_key"] == test_case["key"]
        assert response["cycle_id"] == test_cycle["id"]
        assert response["status"] == "Passed"

        # Verify test execution exists in data store
        assert response["id"] in self.server.data["test_executions"]

    def test_attachments_upload(self):
        """Test uploading an attachment."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Get a test case from the sample data
        test_case = next(iter(self.server.data["test_cases"].values()))

        # Test uploading an attachment
        mock_file = ("test.txt", b"Test file content", "text/plain")

        response = self.server.handle_request(
            "POST",
            f"/testcases/{test_case['key']}/attachments",
            files={"file": mock_file},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify attachment was created
        assert "id" in response
        assert "filename" in response
        assert response["filename"] == "test.txt"
        assert "content_type" in response
        assert response["content_type"] == "text/plain"

        # Verify attachment exists in data store
        assert response["id"] in self.server.data["attachments"]

    def test_statuses_listing(self):
        """Test statuses listing endpoint."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Test statuses listing
        response = self.server.handle_request(
            "GET", "/statuses", headers={"Authorization": f"Bearer {token}"}
        )

        # Verify response format
        assert "values" in response
        assert "maxResults" in response
        assert "startAt" in response
        assert "isLast" in response
        assert "totalCount" in response

        # Verify statuses data
        assert len(response["values"]) > 0
        for status in response["values"]:
            assert "id" in status
            assert "name" in status
            assert "type" in status
            assert status["type"] in ["TEST_CASE", "TEST_CYCLE", "TEST_EXECUTION"]

    def test_priorities_listing(self):
        """Test priorities listing endpoint."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Test priorities listing
        response = self.server.handle_request(
            "GET", "/priorities", headers={"Authorization": f"Bearer {token}"}
        )

        # Verify response format
        assert "values" in response
        assert "maxResults" in response
        assert "startAt" in response
        assert "isLast" in response
        assert "totalCount" in response

        # Verify priorities data
        assert len(response["values"]) > 0
        for priority in response["values"]:
            assert "id" in priority
            assert "name" in priority
            assert "rank" in priority
            assert priority["name"] in ["High", "Medium", "Low"]

    def test_environments_listing(self):
        """Test environments listing endpoint."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Test environments listing
        response = self.server.handle_request(
            "GET", "/environments", headers={"Authorization": f"Bearer {token}"}
        )

        # Verify response format
        assert "values" in response
        assert "maxResults" in response
        assert "startAt" in response
        assert "isLast" in response
        assert "totalCount" in response

        # Verify environments data
        assert len(response["values"]) > 0
        for environment in response["values"]:
            assert "id" in environment
            assert "name" in environment
            assert "description" in environment

    def test_custom_fields_listing(self):
        """Test custom fields listing endpoint."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Test custom fields listing
        response = self.server.handle_request(
            "GET",
            "/customfields",
            params={"entityType": "testCase"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify response format
        assert "values" in response
        assert "maxResults" in response
        assert "startAt" in response
        assert "isLast" in response
        assert "totalCount" in response

        # Verify custom fields data
        assert len(response["values"]) > 0
        for custom_field in response["values"]:
            assert "id" in custom_field
            assert "name" in custom_field
            assert "type" in custom_field
            assert "value" in custom_field

    def test_unauthorized_request(self):
        """Test unauthorized request handling."""
        # Make request without authentication
        response = self.server.handle_request("GET", "/projects")

        # Verify unauthorized response
        assert "error" in response
        assert response["error"]["code"] == 401
        assert "Unauthorized" in response["error"]["message"]

    def test_invalid_endpoint(self):
        """Test invalid endpoint handling."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Make request to invalid endpoint
        response = self.server.handle_request(
            "GET", "/invalid-endpoint", headers={"Authorization": f"Bearer {token}"}
        )

        # Verify error response
        assert "error" in response
        assert response["error"]["code"] == 404
        assert "Unsupported endpoint" in response["error"]["message"]

    def test_invalid_method(self):
        """Test invalid method handling."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Make request with invalid method
        response = self.server.handle_request(
            "PUT", "/projects", headers={"Authorization": f"Bearer {token}"}
        )

        # Verify error response
        assert "error" in response
        assert response["error"]["code"] == 400
        assert "Unsupported operation" in response["error"]["message"]

    def test_model_validation(self):
        """Test model validation for create operations."""
        # Authenticate first
        auth_response = self.server.handle_request("POST", "/authorize", data={})
        token = auth_response["access_token"]

        # Test creating a test case with invalid data
        invalid_test_case_data = {
            "name": "Test Case Without Required Key"
            # Missing required fields
        }

        response = self.server.handle_request(
            "POST",
            "/testcases",
            data=invalid_test_case_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify validation error response
        assert "error" in response
        assert response["error"]["code"] == 400
        assert "Invalid test case data" in response["error"]["message"]
