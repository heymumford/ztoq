"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Integration tests using the API mocking harness.

This module demonstrates using the API mocking harness in integration tests
to test the ZTOQ migration workflow between Zephyr Scale and qTest.
"""

import json
import pytest
from typing import Dict, List, Any, Tuple
from unittest.mock import patch

from ztoq.qtest_client import QTestClient
from ztoq.qtest_models import QTestConfig, QTestProject, QTestTestCase, QTestModule
from ztoq.zephyr_client import ZephyrClient
from ztoq.models import ZephyrConfig, Project, Case, Folder

# Import the test migration function
# (In a real scenario, this would be imported from a real module)
from tests.fixtures.mocks.test_api_harness_examples import migrate_test_case

from tests.fixtures.mocks.api_harness import (
    ZephyrAPIHarness,
    QTestAPIHarness,
    MockAPITestBase,
)


@pytest.mark.integration
class TestMigrationWorkflow(MockAPITestBase):
    """
    Integration tests for the migration workflow.

    These tests use the API harnesses to test the complete migration
    workflow between Zephyr Scale and qTest.
    """

    def setup_zephyr_data(self, harness: ZephyrAPIHarness) -> None:
        """Set up mock Zephyr Scale data."""
        # Configure the project
        harness.add_response(
            "GET", "/projects", {"values": [{"id": "1001", "key": "DEMO", "name": "Demo Project"}]}
        )

        # Configure folders
        harness.add_response(
            "GET",
            "/folders",
            {
                "total": 2,
                "startAt": 0,
                "maxResults": 50,
                "isLast": True,
                "values": [
                    {"id": "f1", "name": "Login Tests", "folderType": "TEST_CASE"},
                    {"id": "f2", "name": "Registration Tests", "folderType": "TEST_CASE"},
                ],
            },
        )

        # Configure test cases
        test_cases = [
            {
                "id": "tc1",
                "key": "DEMO-T1",
                "name": "Login with valid credentials",
                "folder": {"id": "f1", "name": "Login Tests"},
                "status": "Approved",
                "priority": "High",
                "description": "Test login with valid credentials",
                "steps": [
                    {
                        "id": "s1",
                        "index": 1,
                        "description": "Navigate to login page",
                        "expectedResult": "Login page is displayed",
                    },
                    {
                        "id": "s2",
                        "index": 2,
                        "description": "Enter valid credentials",
                        "expectedResult": "User is logged in successfully",
                    },
                ],
            },
            {
                "id": "tc2",
                "key": "DEMO-T2",
                "name": "Login with invalid credentials",
                "folder": {"id": "f1", "name": "Login Tests"},
                "status": "Approved",
                "priority": "High",
                "description": "Test login with invalid credentials",
                "steps": [
                    {
                        "id": "s3",
                        "index": 1,
                        "description": "Navigate to login page",
                        "expectedResult": "Login page is displayed",
                    },
                    {
                        "id": "s4",
                        "index": 2,
                        "description": "Enter invalid credentials",
                        "expectedResult": "Error message is displayed",
                    },
                ],
            },
            {
                "id": "tc3",
                "key": "DEMO-T3",
                "name": "Register new user",
                "folder": {"id": "f2", "name": "Registration Tests"},
                "status": "Draft",
                "priority": "Medium",
                "description": "Test user registration",
                "steps": [
                    {
                        "id": "s5",
                        "index": 1,
                        "description": "Navigate to registration page",
                        "expectedResult": "Registration page is displayed",
                    },
                    {
                        "id": "s6",
                        "index": 2,
                        "description": "Fill in registration form",
                        "expectedResult": "Form is completed",
                    },
                    {
                        "id": "s7",
                        "index": 3,
                        "description": "Submit form",
                        "expectedResult": "Registration confirmation is displayed",
                    },
                ],
            },
        ]

        # Add response for all test cases
        harness.add_response(
            "GET",
            "/testcases",
            {
                "total": len(test_cases),
                "startAt": 0,
                "maxResults": 50,
                "isLast": True,
                "values": test_cases,
            },
        )

        # Add responses for individual test cases
        for test_case in test_cases:
            harness.add_response("GET", f"/testcases/{test_case['key']}", test_case)

    def setup_qtest_data(self, harness: QTestAPIHarness) -> None:
        """Set up mock qTest data."""
        # Configure authentication
        harness.add_response(
            "POST",
            "/oauth/token",
            {"access_token": "mock-qtest-token", "token_type": "bearer", "expires_in": 3600},
        )

        # Configure project
        harness.add_response(
            "GET",
            "/api/v3/projects",
            {
                "total": 1,
                "page": 1,
                "pageSize": 100,
                "items": [{"id": 1, "name": "qTest Demo Project"}],
            },
        )

        # Configure modules (folders)
        harness.add_response(
            "GET",
            "/api/v3/projects/1/modules",
            {
                "total": 2,
                "page": 1,
                "pageSize": 100,
                "items": [
                    {"id": 101, "name": "Login Tests", "parentId": None, "pid": "MD-1"},
                    {"id": 102, "name": "Registration Tests", "parentId": None, "pid": "MD-2"},
                ],
            },
        )

        # Configure responses for creating test cases
        for i, tc_name in enumerate(
            ["Login with valid credentials", "Login with invalid credentials", "Register new user"],
            start=1,
        ):
            harness.add_response(
                "POST",
                "/api/v3/projects/1/test-cases",
                {
                    "id": 1000 + i,
                    "name": tc_name,
                    "pid": f"TC-{i}",
                    "parentId": 101
                    if i <= 2
                    else 102,  # First 2 in Login Tests, last in Registration Tests
                },
            )

    def test_migrate_all_test_cases(self, mock_both_apis):
        """Test migrating all test cases from Zephyr to qTest."""
        # Destructure the tuple from the fixture
        zephyr_harness, qtest_harness = mock_both_apis

        # Set up test data
        self.setup_zephyr_data(zephyr_harness)
        self.setup_qtest_data(qtest_harness)

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

        # Migrate each test case
        migrated_ids = []
        zephyr_test_cases = list(zephyr_client.get_test_cases())

        for test_case in zephyr_test_cases:
            qtest_case_id = migrate_test_case(zephyr_client, qtest_client, test_case.key)
            migrated_ids.append(qtest_case_id)

        # Verify results
        assert len(migrated_ids) == 3
        assert all(id >= 1001 for id in migrated_ids)

        # Verify correct number of API calls were made
        zephyr_test_case_requests = zephyr_harness.get_requests(method="GET", path="/testcases")
        assert len(zephyr_test_case_requests) == 4  # 1 for listing + 3 for individual lookups

        qtest_create_requests = qtest_harness.get_requests(
            method="POST", path="/api/v3/projects/1/test-cases"
        )
        assert len(qtest_create_requests) == 3  # 3 test cases created

    def test_migration_with_error_handling(self, mock_both_apis):
        """Test migration with error handling."""
        # Destructure the tuple from the fixture
        zephyr_harness, qtest_harness = mock_both_apis

        # Set up Zephyr test data
        self.setup_zephyr_data(zephyr_harness)

        # Set up qTest with an error for one test case
        self.setup_qtest_data(qtest_harness)

        # Add an error for one specific test case
        qtest_harness.add_error_response(
            "POST", "/api/v3/projects/1/test-cases", "Duplicate test case name", status_code=400
        )

        # Create a handler to return the error only for the second test case
        original_handler = qtest_harness._handle_request

        def conditional_error_handler(method, path, params, data, headers, files):
            if method == "POST" and path == "/api/v3/projects/1/test-cases":
                # Check if this is the second test case create request
                create_requests = qtest_harness.get_requests(
                    method="POST", path="/api/v3/projects/1/test-cases"
                )
                if len(create_requests) == 1 and "Login with invalid credentials" in json.dumps(
                    data
                ):
                    return {"error": "Duplicate test case name"}, 400

            # Use the original handler for other requests
            return original_handler(method, path, params, data, headers, files)

        # Replace the handler
        qtest_harness._handle_request = conditional_error_handler

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

        # Migrate each test case with error handling
        successful_migrations = []
        failed_migrations = []

        zephyr_test_cases = list(zephyr_client.get_test_cases())

        for test_case in zephyr_test_cases:
            try:
                qtest_case_id = migrate_test_case(zephyr_client, qtest_client, test_case.key)
                successful_migrations.append((test_case.key, qtest_case_id))
            except Exception as e:
                failed_migrations.append((test_case.key, str(e)))

        # Verify results
        assert len(successful_migrations) == 2  # 2 successful migrations
        assert len(failed_migrations) == 1  # 1 failed migration

        # Verify the second test case failed
        assert failed_migrations[0][0] == "DEMO-T2"
        assert "400" in failed_migrations[0][1] or "Duplicate" in failed_migrations[0][1]

        # Verify API calls
        qtest_create_requests = qtest_harness.get_requests(
            method="POST", path="/api/v3/projects/1/test-cases"
        )
        assert len(qtest_create_requests) == 3  # 3 attempts (even though one failed)


@pytest.mark.integration
class TestFolderStructureMigration:
    """Test migrating folder structure from Zephyr to qTest."""

    @pytest.fixture
    def mock_clients(self, mock_both_apis):
        """Set up mock clients and test data."""
        zephyr_harness, qtest_harness = mock_both_apis

        # Configure Zephyr folders (nested structure)
        zephyr_folders = [
            {"id": "f1", "name": "System Tests", "folderType": "TEST_CASE"},
            {"id": "f2", "name": "Frontend", "folderType": "TEST_CASE"},
            {"id": "f3", "name": "Backend", "folderType": "TEST_CASE"},
            {"id": "f4", "name": "Login", "folderType": "TEST_CASE"},
            {"id": "f5", "name": "Registration", "folderType": "TEST_CASE"},
        ]

        # Add response for folders
        zephyr_harness.add_response(
            "GET",
            "/folders",
            {
                "total": len(zephyr_folders),
                "startAt": 0,
                "maxResults": 50,
                "isLast": True,
                "values": zephyr_folders,
            },
        )

        # Configure qTest authentication
        qtest_harness.add_response(
            "POST",
            "/oauth/token",
            {"access_token": "mock-qtest-token", "token_type": "bearer", "expires_in": 3600},
        )

        # Configure qTest project
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

        # Configure responses for creating modules
        for i, folder_name in enumerate(
            ["System Tests", "Frontend", "Backend", "Login", "Registration"], start=1
        ):
            qtest_harness.add_response(
                "POST",
                "/api/v3/projects/1/modules",
                {"id": 100 + i, "name": folder_name, "pid": f"MD-{i}", "parentId": None},
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

        return zephyr_client, qtest_client, zephyr_harness, qtest_harness

    def test_migrate_folders(self, mock_clients):
        """Test migrating folder structure."""
        zephyr_client, qtest_client, zephyr_harness, qtest_harness = mock_clients

        # Define a function to migrate folders
        def migrate_folders(zephyr_client, qtest_client):
            # Get Zephyr folders
            zephyr_folders_response = zephyr_client._make_request("GET", "/folders")
            zephyr_folders = [
                Folder(**folder) for folder in zephyr_folders_response.get("values", [])
            ]

            # Create qTest modules for each folder
            folder_mapping = {}
            for folder in zephyr_folders:
                # Create module with parent if needed
                module = QTestModule(
                    name=folder.name, description=f"Migrated from Zephyr folder {folder.id}"
                )

                # Create in qTest
                created_module = qtest_client.create_module(module)
                folder_mapping[folder.id] = created_module.id

            return folder_mapping

        # Migrate folders
        folder_mapping = migrate_folders(zephyr_client, qtest_client)

        # Verify results
        assert len(folder_mapping) == 5
        assert all(isinstance(folder_id, str) for folder_id in folder_mapping.keys())
        assert all(isinstance(module_id, int) for module_id in folder_mapping.values())

        # Verify API calls
        zephyr_folder_requests = zephyr_harness.get_requests(method="GET", path="/folders")
        assert len(zephyr_folder_requests) == 1

        qtest_module_requests = qtest_harness.get_requests(
            method="POST", path="/api/v3/projects/1/modules"
        )
        assert len(qtest_module_requests) == 5  # 5 modules created


@pytest.mark.integration
class TestMigrationWithCustomFields:
    """Test migrating custom fields from Zephyr to qTest."""

    @pytest.fixture
    def mock_apis_with_custom_fields(self, mock_both_apis):
        """Set up mock APIs with custom fields configuration."""
        zephyr_harness, qtest_harness = mock_both_apis

        # Configure Zephyr custom fields
        zephyr_harness.add_response(
            "GET",
            "/customfields",
            {
                "total": 3,
                "startAt": 0,
                "maxResults": 50,
                "isLast": True,
                "values": [
                    {
                        "id": "cf1",
                        "name": "Component",
                        "type": "SINGLE_SELECT",
                        "options": ["UI", "API", "Database"],
                    },
                    {"id": "cf2", "name": "Reviewer", "type": "TEXT"},
                    {"id": "cf3", "name": "Automated", "type": "CHECKBOX"},
                ],
            },
        )

        # Configure a test case with custom fields
        zephyr_harness.add_response(
            "GET",
            "/testcases/DEMO-T1",
            {
                "id": "tc1",
                "key": "DEMO-T1",
                "name": "Login Test",
                "description": "Test login functionality",
                "customFields": [
                    {"id": "cf1", "name": "Component", "value": "UI"},
                    {"id": "cf2", "name": "Reviewer", "value": "John Doe"},
                    {"id": "cf3", "name": "Automated", "value": True},
                ],
            },
        )

        # Configure qTest custom fields
        qtest_harness.add_response(
            "POST",
            "/oauth/token",
            {"access_token": "mock-qtest-token", "token_type": "bearer", "expires_in": 3600},
        )

        qtest_harness.add_response(
            "GET",
            "/api/v3/projects/1/settings/test-cases/custom-fields",
            {
                "total": 3,
                "items": [
                    {
                        "id": 101,
                        "label": "Component",
                        "required": False,
                        "allowed_values": ["UI", "API", "Database"],
                        "type": "SINGLE_SELECT",
                    },
                    {"id": 102, "label": "Reviewer", "required": False, "type": "TEXT"},
                    {"id": 103, "label": "Automated", "required": False, "type": "CHECKBOX"},
                ],
            },
        )

        # Configure response for creating test case with custom fields
        qtest_harness.add_response(
            "POST",
            "/api/v3/projects/1/test-cases",
            {
                "id": 1001,
                "name": "Login Test",
                "description": "Test login functionality",
                "properties": [
                    {"field_id": 101, "field_value": "UI"},
                    {"field_id": 102, "field_value": "John Doe"},
                    {"field_id": 103, "field_value": True},
                ],
            },
        )

        return zephyr_harness, qtest_harness

    def test_migrate_with_custom_fields(self, mock_apis_with_custom_fields):
        """Test migrating a test case with custom fields."""
        zephyr_harness, qtest_harness = mock_apis_with_custom_fields

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

        # Define a function to migrate custom fields
        def migrate_test_case_with_custom_fields(zephyr_key, qtest_client, zephyr_client):
            # Get Zephyr custom fields mapping
            zephyr_custom_fields_response = zephyr_client._make_request("GET", "/customfields")
            zephyr_custom_fields = {
                cf["id"]: cf["name"] for cf in zephyr_custom_fields_response.get("values", [])
            }

            # Get qTest custom fields mapping
            qtest_custom_fields_response = qtest_client._make_request(
                "GET",
                f"/api/v3/projects/{qtest_client.config.project_id}/settings/test-cases/custom-fields",
            )
            qtest_custom_fields = {
                cf["label"]: cf["id"] for cf in qtest_custom_fields_response.get("items", [])
            }

            # Get Zephyr test case
            zephyr_test_case_response = zephyr_client._make_request(
                "GET", f"/testcases/{zephyr_key}"
            )

            # Extract custom field values
            custom_fields = {}
            for cf in zephyr_test_case_response.get("customFields", []):
                field_name = cf["name"]
                field_value = cf["value"]
                custom_fields[field_name] = field_value

            # Create qTest test case with custom fields
            properties = []
            for field_name, field_value in custom_fields.items():
                if field_name in qtest_custom_fields:
                    properties.append(
                        {"field_id": qtest_custom_fields[field_name], "field_value": field_value}
                    )

            # Create test case data
            qtest_case_data = {
                "name": zephyr_test_case_response["name"],
                "description": zephyr_test_case_response.get("description", ""),
                "properties": properties,
            }

            # Create test case in qTest
            response = qtest_client._make_request(
                "POST",
                f"/api/v3/projects/{qtest_client.config.project_id}/test-cases",
                json_data=qtest_case_data,
            )

            return response["id"]

        # Migrate test case with custom fields
        qtest_case_id = migrate_test_case_with_custom_fields("DEMO-T1", qtest_client, zephyr_client)

        # Verify results
        assert qtest_case_id == 1001

        # Verify API calls
        zephyr_custom_fields_request = zephyr_harness.get_requests(
            method="GET", path="/customfields"
        )
        assert len(zephyr_custom_fields_request) == 1

        qtest_custom_fields_request = qtest_harness.get_requests(
            method="GET", path="/api/v3/projects/1/settings/test-cases/custom-fields"
        )
        assert len(qtest_custom_fields_request) == 1

        zephyr_test_case_request = zephyr_harness.get_requests(
            method="GET", path="/testcases/DEMO-T1"
        )
        assert len(zephyr_test_case_request) == 1

        qtest_create_request = qtest_harness.get_requests(
            method="POST", path="/api/v3/projects/1/test-cases"
        )
        assert len(qtest_create_request) == 1

        # Verify custom fields were included in the qTest request
        request_data = qtest_create_request[0]["data"]
        assert "properties" in request_data
        assert len(request_data["properties"]) == 3

        # Verify specific field values
        component_field = next(
            (p for p in request_data["properties"] if p["field_id"] == 101), None
        )
        assert component_field is not None
        assert component_field["field_value"] == "UI"

        reviewer_field = next((p for p in request_data["properties"] if p["field_id"] == 102), None)
        assert reviewer_field is not None
        assert reviewer_field["field_value"] == "John Doe"

        automated_field = next(
            (p for p in request_data["properties"] if p["field_id"] == 103), None
        )
        assert automated_field is not None
        assert automated_field["field_value"] is True
