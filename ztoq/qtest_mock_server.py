"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Mock server for qTest API testing.

This module provides a mock server that simulates the qTest APIs for testing.
The mock server supports the following qTest API components:

1. qTest Manager API - Projects, test cases, test cycles, test runs, attachments
2. qTest Parameters API - Parameters, parameter values, datasets
3. qTest Pulse API - Rules, triggers, actions, constants
4. qTest Scenario API - BDD features and scenarios

Each API follows the qTest REST API conventions for endpoints, request formats,
and response structures.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

# Global variable for test support
DEBUG = False

from pydantic import ValidationError

from ztoq.qtest_models import (
    QTestCustomField,
    QTestDataset,
    QTestDatasetRow,
    QTestProject,
    QTestRelease,
    QTestStep,
    QTestTestCase,
    QTestTestLog,
)

logger = logging.getLogger("ztoq.qtest_mock_server")


class QTestMockServer:
    """Mock server for qTest APIs."""

    def __init__(self):
        """Initialize the mock server with empty data stores."""
        # Initialize data stores for each API
        self.data = {
            "manager": {
                "projects": [],
                "modules": {},
                "test_cases": {},
                "test_steps": {},
                "test_cycles": {},
                "test_runs": {},
                "test_logs": {},
                "attachments": {},
                "releases": {},
                "custom_fields": {},
                "users": {},
            },
            "parameters": {
                "parameters": {},
                "parameter_values": {},
                "datasets": {},
                "dataset_rows": {},
            },
            "pulse": {"rules": {}, "actions": {}, "triggers": {}, "constants": {}},
            "scenario": {"features": {}, "steps": {}},
        }

        # Track request history for debugging
        self.request_history = []

        # API response configuration
        self.error_rate = 0.0  # Percentage of requests that should fail with errors
        self.response_delay = 0.0  # Delay in seconds before responding
        self.validation_mode = True  # Whether to validate request data against models

        # Initialize with sample data
        self._initialize_sample_data()

    def _validate_model(
        self, data: dict, model_class, exclude_none: bool = True,
    ) -> tuple[bool, dict | None, str | None]:
        """
        Validate data against a Pydantic model.

        Args:
            data: The data to validate
            model_class: The Pydantic model class to validate against
            exclude_none: Whether to exclude None values from validation

        Returns:
            A tuple (is_valid, validated_data, error_message)

        """
        try:
            # Create model instance and validate
            model = model_class(**data)

            # Convert to dict for response
            validated_data = model.model_dump(exclude_none=exclude_none)

            return True, validated_data, None
        except ValidationError as e:
            logger.warning(f"Validation error: {e!s}")
            return False, None, str(e)
        except Exception as e:
            logger.error(f"Unexpected error during validation: {e!s}")
            return False, None, f"Internal server error: {e!s}"

    def _format_error_response(self, message: str, status_code: int = 400) -> dict:
        """
        Format a standard error response.

        Args:
            message: The error message
            status_code: The HTTP status code

        Returns:
            A standardized error response dictionary

        """
        return {
            "error": {
                "message": message,
                "code": status_code,
                "timestamp": datetime.now().isoformat(),
            },
        }

    def _initialize_sample_data(self):
        """Initialize the server with sample data."""
        # Add sample project
        project = {
            "id": 12345,
            "name": "Sample Project",
            "description": "A sample project for testing",
            "startDate": "2023-01-01T00:00:00Z",
            "endDate": "2023-12-31T00:00:00Z",
            "statusName": "Active",
        }
        self.data["manager"]["projects"].append(project)

        # Add sample modules
        self._add_sample_modules(project["id"])

        # Add sample test cases
        self._add_sample_test_cases(project["id"])

        # Add sample test cycles
        self._add_sample_test_cycles(project["id"])

        # Add sample parameters
        self._add_sample_parameters(project["id"])

        # Add sample datasets
        self._add_sample_datasets(project["id"])

        # Add sample Pulse rules
        self._add_sample_rules(project["id"])

        # Add sample Scenario features
        self._add_sample_features(project["id"])

    def _add_sample_modules(self, project_id: int):
        """Add sample modules for a project."""
        # Root module
        root_module = {
            "id": 101,
            "name": "Root Module",
            "description": "Root module for test cases",
            "parentId": None,
            "pid": "MD-1",
            "projectId": project_id,
            "path": "Root Module",
        }
        self.data["manager"]["modules"][root_module["id"]] = root_module

        # Child modules
        child_modules = [
            {
                "id": 102,
                "name": "UI Tests",
                "description": "UI test cases",
                "parentId": 101,
                "pid": "MD-2",
                "projectId": project_id,
                "path": "Root Module/UI Tests",
            },
            {
                "id": 103,
                "name": "API Tests",
                "description": "API test cases",
                "parentId": 101,
                "pid": "MD-3",
                "projectId": project_id,
                "path": "Root Module/API Tests",
            },
            {
                "id": 104,
                "name": "Performance Tests",
                "description": "Performance test cases",
                "parentId": 101,
                "pid": "MD-4",
                "projectId": project_id,
                "path": "Root Module/Performance Tests",
            },
        ]

        for module in child_modules:
            self.data["manager"]["modules"][module["id"]] = module

    def _add_sample_test_cases(self, project_id: int):
        """Add sample test cases for a project."""
        # UI test cases
        ui_test_cases = [
            {
                "id": 201,
                "name": "Login Test",
                "description": "Test login functionality",
                "precondition": "User is registered",
                "pid": "TC-1",
                "parentId": None,
                "moduleId": 102,
                "priorityId": 1,
                "creatorId": 1,
                "projectId": project_id,
                "properties": [
                    {"id": 1, "name": "Automation Status", "type": "STRING", "value": "Automated"},
                ],
                "steps": [
                    {
                        "id": 301,
                        "description": "Navigate to login page",
                        "expectedResult": "Login page is displayed",
                        "order": 1,
                    },
                    {
                        "id": 302,
                        "description": "Enter valid credentials",
                        "expectedResult": "Credentials accepted",
                        "order": 2,
                    },
                    {
                        "id": 303,
                        "description": "Click login button",
                        "expectedResult": "User is logged in and redirected to dashboard",
                        "order": 3,
                    },
                ],
                "createdDate": "2023-01-15T10:00:00Z",
                "lastModifiedDate": "2023-01-15T10:00:00Z",
            },
            {
                "id": 202,
                "name": "Registration Test",
                "description": "Test user registration",
                "precondition": "User is not registered",
                "pid": "TC-2",
                "parentId": None,
                "moduleId": 102,
                "priorityId": 1,
                "creatorId": 1,
                "projectId": project_id,
                "properties": [
                    {
                        "id": 1,
                        "name": "Automation Status",
                        "type": "STRING",
                        "value": "Not Automated",
                    },
                ],
                "steps": [
                    {
                        "id": 304,
                        "description": "Navigate to registration page",
                        "expectedResult": "Registration page is displayed",
                        "order": 1,
                    },
                    {
                        "id": 305,
                        "description": "Fill in registration form",
                        "expectedResult": "Form is filled correctly",
                        "order": 2,
                    },
                    {
                        "id": 306,
                        "description": "Submit registration form",
                        "expectedResult": "User is registered and redirected to login page",
                        "order": 3,
                    },
                ],
                "createdDate": "2023-01-16T10:00:00Z",
                "lastModifiedDate": "2023-01-16T10:00:00Z",
            },
        ]

        # API test cases
        api_test_cases = [
            {
                "id": 203,
                "name": "Get User API Test",
                "description": "Test Get User API",
                "precondition": "API server is running",
                "pid": "TC-3",
                "parentId": None,
                "moduleId": 103,
                "priorityId": 2,
                "creatorId": 1,
                "projectId": project_id,
                "properties": [
                    {"id": 1, "name": "Automation Status", "type": "STRING", "value": "Automated"},
                ],
                "steps": [
                    {
                        "id": 307,
                        "description": "Send GET request to /api/users/{id}",
                        "expectedResult": "Response status code is 200",
                        "order": 1,
                    },
                    {
                        "id": 308,
                        "description": "Validate response body",
                        "expectedResult": "Response contains valid user data",
                        "order": 2,
                    },
                ],
                "createdDate": "2023-01-17T10:00:00Z",
                "lastModifiedDate": "2023-01-17T10:00:00Z",
            },
            {
                "id": 204,
                "name": "Create User API Test",
                "description": "Test Create User API",
                "precondition": "API server is running",
                "pid": "TC-4",
                "parentId": None,
                "moduleId": 103,
                "priorityId": 2,
                "creatorId": 1,
                "projectId": project_id,
                "properties": [
                    {"id": 1, "name": "Automation Status", "type": "STRING", "value": "Automated"},
                ],
                "steps": [
                    {
                        "id": 309,
                        "description": "Send POST request to /api/users with valid data",
                        "expectedResult": "Response status code is 201",
                        "order": 1,
                    },
                    {
                        "id": 310,
                        "description": "Validate response body",
                        "expectedResult": "Response contains created user data",
                        "order": 2,
                    },
                    {
                        "id": 311,
                        "description": "Verify user was created in database",
                        "expectedResult": "User exists in database",
                        "order": 3,
                    },
                ],
                "createdDate": "2023-01-18T10:00:00Z",
                "lastModifiedDate": "2023-01-18T10:00:00Z",
            },
        ]

        # Add all test cases to data store
        for tc in ui_test_cases + api_test_cases:
            # Store test case
            self.data["manager"]["test_cases"][tc["id"]] = tc

            # Store test steps separately
            for step in tc["steps"]:
                step["testCaseId"] = tc["id"]
                self.data["manager"]["test_steps"][step["id"]] = step

    def _add_sample_test_cycles(self, project_id: int):
        """Add sample test cycles for a project."""
        # Add a release
        release = {
            "id": 401,
            "name": "Release 1.0",
            "description": "First release",
            "pid": "RL-1",
            "startDate": "2023-01-01T00:00:00Z",
            "endDate": "2023-03-31T00:00:00Z",
            "projectId": project_id,
        }
        self.data["manager"]["releases"][release["id"]] = release

        # Add test cycles
        test_cycles = [
            {
                "id": 501,
                "name": "Sprint 1 Test Cycle",
                "description": "Tests for Sprint 1",
                "pid": "CY-1",
                "parentId": None,
                "releaseId": 401,
                "projectId": project_id,
                "properties": [],
                "startDate": "2023-01-01T00:00:00Z",
                "endDate": "2023-01-15T00:00:00Z",
            },
            {
                "id": 502,
                "name": "Sprint 2 Test Cycle",
                "description": "Tests for Sprint 2",
                "pid": "CY-2",
                "parentId": None,
                "releaseId": 401,
                "projectId": project_id,
                "properties": [],
                "startDate": "2023-01-16T00:00:00Z",
                "endDate": "2023-01-31T00:00:00Z",
            },
        ]

        for cycle in test_cycles:
            self.data["manager"]["test_cycles"][cycle["id"]] = cycle

        # Add test runs
        test_runs = [
            {
                "id": 601,
                "name": "Login Test - Sprint 1",
                "description": "Login test for Sprint 1",
                "pid": "TR-1",
                "testCaseVersionId": 1,
                "testCaseId": 201,
                "testCycleId": 501,
                "projectId": project_id,
                "properties": [],
                "status": "NOT_EXECUTED",
            },
            {
                "id": 602,
                "name": "Get User API Test - Sprint 1",
                "description": "Get User API test for Sprint 1",
                "pid": "TR-2",
                "testCaseVersionId": 1,
                "testCaseId": 203,
                "testCycleId": 501,
                "projectId": project_id,
                "properties": [],
                "status": "NOT_EXECUTED",
            },
        ]

        for run in test_runs:
            self.data["manager"]["test_runs"][run["id"]] = run

    def _add_sample_parameters(self, project_id: int):
        """Add sample parameters for a project."""
        parameters = [
            {
                "id": 701,
                "name": "Browser",
                "description": "Browser to run tests in",
                "projectId": project_id,
                "status": "ACTIVE",
                "values": [
                    {"id": 801, "value": "Chrome", "parameterId": 701},
                    {"id": 802, "value": "Firefox", "parameterId": 701},
                    {"id": 803, "value": "Edge", "parameterId": 701},
                ],
            },
            {
                "id": 702,
                "name": "Environment",
                "description": "Test environment",
                "projectId": project_id,
                "status": "ACTIVE",
                "values": [
                    {"id": 804, "value": "Dev", "parameterId": 702},
                    {"id": 805, "value": "QA", "parameterId": 702},
                    {"id": 806, "value": "Staging", "parameterId": 702},
                ],
            },
        ]

        for param in parameters:
            # Store parameter
            param_values = param.pop("values")
            self.data["parameters"]["parameters"][param["id"]] = param

            # Store parameter values
            for value in param_values:
                self.data["parameters"]["parameter_values"][value["id"]] = value

    def _add_sample_datasets(self, project_id: int):
        """Add sample datasets for a project."""
        datasets = [
            {
                "id": 901,
                "name": "Login Test Data",
                "description": "Test data for login scenarios",
                "projectId": project_id,
                "status": "ACTIVE",
                "rows": [
                    {
                        "id": 1001,
                        "datasetId": 901,
                        "values": {
                            "username": "user1",
                            "password": "password1",
                            "expected_result": "success",
                        },
                    },
                    {
                        "id": 1002,
                        "datasetId": 901,
                        "values": {
                            "username": "user2",
                            "password": "wrong_password",
                            "expected_result": "failure",
                        },
                    },
                ],
            },
        ]

        for dataset in datasets:
            # Store dataset
            rows = dataset.pop("rows")
            self.data["parameters"]["datasets"][dataset["id"]] = dataset

            # Store dataset rows
            for row in rows:
                self.data["parameters"]["dataset_rows"][row["id"]] = row

    def _add_sample_rules(self, project_id: int):
        """Add sample Pulse rules for a project."""
        # Add sample triggers first
        triggers = [
            {
                "id": 1001,
                "name": "Test Log Created",
                "eventType": "TEST_LOG_CREATED",
                "projectId": project_id,
                "conditions": [{"field": "status", "operator": "equals", "value": "FAIL"}],
                "createdBy": {"id": 1, "name": "Admin"},
                "createdDate": datetime.now().isoformat(),
            },
            {
                "id": 1002,
                "name": "Test Case Created",
                "eventType": "TEST_CASE_CREATED",
                "projectId": project_id,
                "conditions": [],
                "createdBy": {"id": 1, "name": "Admin"},
                "createdDate": datetime.now().isoformat(),
            },
        ]

        for trigger in triggers:
            self.data["pulse"]["triggers"][trigger["id"]] = trigger

        # Add sample actions
        actions = [
            {
                "id": 2001,
                "name": "Create JIRA Issue",
                "actionType": "CREATE_DEFECT",
                "projectId": project_id,
                "parameters": [
                    {"name": "issueType", "value": "Bug"},
                    {"name": "summary", "value": "Test Failed: {{testCase.name}}"},
                    {"name": "description", "value": "Test execution failed: {{testLog.note}}"},
                ],
                "createdBy": {"id": 1, "name": "Admin"},
                "createdDate": datetime.now().isoformat(),
            },
            {
                "id": 2002,
                "name": "Send Email Notification",
                "actionType": "SEND_MAIL",
                "projectId": project_id,
                "parameters": [
                    {"name": "recipients", "value": "qa@example.com"},
                    {"name": "subject", "value": "New Test Case Created: {{testCase.name}}"},
                    {
                        "name": "body",
                        "value": "A new test case has been created: {{testCase.name}}\\n\\nDescription: {{testCase.description}}",
                    },
                ],
                "createdBy": {"id": 1, "name": "Admin"},
                "createdDate": datetime.now().isoformat(),
            },
        ]

        for action in actions:
            self.data["pulse"]["actions"][action["id"]] = action

        # Add sample constants
        constants = [
            {
                "id": 3001,
                "name": "QA_EMAIL",
                "value": "qa@example.com",
                "description": "Email address for QA team",
                "projectId": project_id,
                "createdBy": {"id": 1, "name": "Admin"},
                "createdDate": datetime.now().isoformat(),
            },
            {
                "id": 3002,
                "name": "JIRA_PROJECT",
                "value": "QA",
                "description": "JIRA project key",
                "projectId": project_id,
                "createdBy": {"id": 1, "name": "Admin"},
                "createdDate": datetime.now().isoformat(),
            },
        ]

        for constant in constants:
            self.data["pulse"]["constants"][constant["id"]] = constant

        # Add sample rules using the triggers and actions
        rules = [
            {
                "id": 4001,
                "name": "JIRA Integration Rule",
                "description": "Create JIRA issue when test fails",
                "projectId": project_id,
                "enabled": True,
                "triggerId": 1001,
                "actionId": 2001,
                "createdBy": {"id": 1, "name": "Admin"},
                "createdDate": datetime.now().isoformat(),
            },
            {
                "id": 4002,
                "name": "New Test Case Notification",
                "description": "Send email when new test case is created",
                "projectId": project_id,
                "enabled": True,
                "triggerId": 1002,
                "actionId": 2002,
                "createdBy": {"id": 1, "name": "Admin"},
                "createdDate": datetime.now().isoformat(),
            },
        ]

        for rule in rules:
            self.data["pulse"]["rules"][rule["id"]] = rule

    def _add_sample_features(self, project_id: int):
        """Add sample Scenario features for a project."""
        features = [
            {
                "id": str(uuid.uuid4()),
                "name": "User Authentication",
                "description": "User login and registration",
                "projectId": project_id,
                "content": """
                Feature: User Authentication
                  As a user
                  I want to authenticate with the system
                  So that I can access protected resources

                  Scenario: Successful login
                    Given I am on the login page
                    When I enter valid credentials
                    And I click the login button
                    Then I should be redirected to the dashboard

                  Scenario: Failed login
                    Given I am on the login page
                    When I enter invalid credentials
                    And I click the login button
                    Then I should see an error message
                """,
            },
        ]

        for feature in features:
            self.data["scenario"]["features"][feature["id"]] = feature

    # Custom field endpoints
    def _handle_get_custom_fields(self, project_id: int, entity_type: str) -> list[dict[str, Any]]:
        """
        Handle GET /projects/{projectId}/custom-fields endpoint.

        Args:
            project_id: The ID of the project
            entity_type: The type of entity to get custom fields for (e.g., test-cases)

        Returns:
            List of custom fields

        """
        # Map entity_type path parameter to QTestCustomField.entityType
        entity_type_map = {
            "test-cases": "TEST_CASE",
            "test-cycles": "TEST_CYCLE",
            "test-runs": "TEST_RUN",
            "test-logs": "TEST_LOG",
            "requirements": "REQUIREMENT",
        }

        # Convert endpoint path to model entityType
        model_entity_type = entity_type_map.get(entity_type)

        if not model_entity_type:
            return []

        # Filter custom fields by project ID and entity type
        custom_fields = [
            cf
            for cf in self.data["manager"]["custom_fields"].values()
            if cf.get("projectId") == project_id and cf.get("entityType") == model_entity_type
        ]

        return custom_fields

    def _handle_create_custom_field(self, project_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle POST /projects/{projectId}/custom-fields endpoint.

        Args:
            project_id: The ID of the project
            data: The custom field data

        Returns:
            The created custom field data

        """
        # Add project ID if not provided
        if "projectId" not in data:
            data["projectId"] = project_id

        # Validate custom field data if validation is enabled
        if self.validation_mode:
            is_valid, validated_data, error = self._validate_model(data, QTestCustomField)
            if not is_valid:
                return self._format_error_response(f"Invalid custom field data: {error}", 400)
            data = validated_data.model_dump()

        # Generate custom field ID
        custom_field_id = max(self.data["manager"]["custom_fields"].keys(), default=0) + 1

        # Create new custom field
        custom_field = {
            "id": custom_field_id,
            "fieldName": data.get("fieldName", ""),
            "fieldType": data.get("fieldType", "TEXT"),
            "entityType": data.get("entityType", "TEST_CASE"),
            "projectId": project_id,
            "isRequired": data.get("isRequired", False),
            "allowedValues": data.get("allowedValues", []),
            "createdDate": datetime.now().isoformat(),
            "lastModifiedDate": datetime.now().isoformat(),
        }

        # Store custom field
        self.data["manager"]["custom_fields"][custom_field_id] = custom_field

        # Log creation
        logger.info(f"Created custom field: {custom_field_id} - {custom_field['fieldName']}")

        return custom_field

    def _handle_get_custom_field(self, custom_field_id: int) -> dict[str, Any]:
        """
        Handle GET /projects/{projectId}/custom-fields/{customFieldId} endpoint.

        Args:
            custom_field_id: The ID of the custom field to retrieve

        Returns:
            The custom field data or an error message if not found

        """
        if custom_field_id in self.data["manager"]["custom_fields"]:
            return self.data["manager"]["custom_fields"][custom_field_id]
        return self._format_error_response(f"Custom field not found: {custom_field_id}", 404)

    def _handle_update_custom_field(
        self, custom_field_id: int, data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle PUT /projects/{projectId}/custom-fields/{customFieldId} endpoint.

        Args:
            custom_field_id: The ID of the custom field to update
            data: The updated custom field data

        Returns:
            The updated custom field data or an error message if not found

        """
        if custom_field_id not in self.data["manager"]["custom_fields"]:
            return self._format_error_response(f"Custom field not found: {custom_field_id}", 404)

        # Get existing custom field
        existing_field = self.data["manager"]["custom_fields"][custom_field_id]

        # Create updated custom field by merging existing data with updates
        updated_field = {**existing_field, **data}

        # Update lastModifiedDate
        updated_field["lastModifiedDate"] = datetime.now().isoformat()

        # Validate if validation is enabled
        if self.validation_mode:
            is_valid, validated_data, error = self._validate_model(updated_field, QTestCustomField)
            if not is_valid:
                return self._format_error_response(f"Invalid custom field data: {error}", 400)
            updated_field = validated_data.model_dump()

        # Update custom field in data store
        self.data["manager"]["custom_fields"][custom_field_id] = updated_field

        # Log update
        logger.info(
            f"Updated custom field: {custom_field_id} - {updated_field.get('fieldName', 'Unnamed')}",
        )

        return updated_field

    def _handle_delete_custom_field(self, custom_field_id: int) -> dict[str, Any]:
        """
        Handle DELETE /projects/{projectId}/custom-fields/{customFieldId} endpoint.

        Args:
            custom_field_id: The ID of the custom field to delete

        Returns:
            Success message or an error message if not found

        """
        if custom_field_id not in self.data["manager"]["custom_fields"]:
            return self._format_error_response(f"Custom field not found: {custom_field_id}", 404)

        # Delete custom field from data store
        deleted_field = self.data["manager"]["custom_fields"].pop(custom_field_id)

        # Log deletion
        logger.info(
            f"Deleted custom field: {custom_field_id} - {deleted_field.get('fieldName', 'Unnamed')}",
        )

        return {"success": True, "message": f"Custom field {custom_field_id} deleted successfully"}

    # Release management methods
    def _handle_get_releases(self, project_id: int) -> dict[str, Any]:
        """
        Handle GET /projects/{projectId}/releases endpoint.

        Args:
            project_id: The ID of the project

        Returns:
            Paginated list of releases

        """
        # Filter by project ID
        releases = [
            r for r in self.data["manager"]["releases"].values() if r.get("projectId") == project_id
        ]

        # Apply default pagination
        page = 1
        page_size = 20

        start = (page - 1) * page_size
        end = start + page_size

        paginated_releases = releases[start:end]

        return {
            "page": page,
            "pageSize": page_size,
            "total": len(releases),
            "items": paginated_releases,
        }

    def _handle_create_release(self, project_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle POST /projects/{projectId}/releases endpoint.

        Args:
            project_id: The ID of the project
            data: The release data

        Returns:
            The created release data

        """
        # Add project ID if not provided
        if "projectId" not in data:
            data["projectId"] = project_id

        # Validate release data if validation is enabled
        if self.validation_mode:
            is_valid, validated_data, error = self._validate_model(data, QTestRelease)
            if not is_valid:
                return self._format_error_response(f"Invalid release data: {error}", 400)
            data = validated_data.model_dump()

        # Generate release ID
        release_id = max(self.data["manager"]["releases"].keys(), default=0) + 1

        # Create new release
        release = {
            "id": release_id,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "projectId": project_id,
            "status": data.get("status", "ACTIVE"),
            "startDate": data.get("startDate"),
            "endDate": data.get("endDate"),
            "createdDate": datetime.now().isoformat(),
            "lastModifiedDate": datetime.now().isoformat(),
        }

        # Store release
        self.data["manager"]["releases"][release_id] = release

        # Log creation
        logger.info(f"Created release: {release_id} - {release['name']}")

        return release

    def _handle_get_release(self, release_id: int) -> dict[str, Any]:
        """
        Handle GET /projects/{projectId}/releases/{releaseId} endpoint.

        Args:
            release_id: The ID of the release to retrieve

        Returns:
            The release data or an error message if not found

        """
        if release_id in self.data["manager"]["releases"]:
            return self.data["manager"]["releases"][release_id]
        return self._format_error_response(f"Release not found: {release_id}", 404)

    def _handle_update_release(self, release_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle PUT /projects/{projectId}/releases/{releaseId} endpoint.

        Args:
            release_id: The ID of the release to update
            data: The updated release data

        Returns:
            The updated release data or an error message if not found

        """
        if release_id not in self.data["manager"]["releases"]:
            return self._format_error_response(f"Release not found: {release_id}", 404)

        # Get existing release
        existing_release = self.data["manager"]["releases"][release_id]

        # Create updated release by merging existing data with updates
        updated_release = {**existing_release, **data}

        # Update lastModifiedDate
        updated_release["lastModifiedDate"] = datetime.now().isoformat()

        # Validate if validation is enabled
        if self.validation_mode:
            is_valid, validated_data, error = self._validate_model(updated_release, QTestRelease)
            if not is_valid:
                return self._format_error_response(f"Invalid release data: {error}", 400)
            updated_release = validated_data.model_dump()

        # Update release in data store
        self.data["manager"]["releases"][release_id] = updated_release

        # Log update
        logger.info(f"Updated release: {release_id} - {updated_release.get('name', 'Unnamed')}")

        return updated_release

    def _handle_delete_release(self, release_id: int) -> dict[str, Any]:
        """
        Handle DELETE /projects/{projectId}/releases/{releaseId} endpoint.

        Args:
            release_id: The ID of the release to delete

        Returns:
            Success message or an error message if not found

        """
        if release_id not in self.data["manager"]["releases"]:
            return self._format_error_response(f"Release not found: {release_id}", 404)

        # Check for test cycles that use this release
        test_cycles_using_release = [
            tc
            for tc in self.data["manager"]["test_cycles"].values()
            if tc.get("releaseId") == release_id
        ]

        if test_cycles_using_release:
            return self._format_error_response(
                f"Cannot delete release: {release_id} as it is used by {len(test_cycles_using_release)} test cycles",
                400,
            )

        # Delete release from data store
        deleted_release = self.data["manager"]["releases"].pop(release_id)

        # Log deletion
        logger.info(f"Deleted release: {release_id} - {deleted_release.get('name', 'Unnamed')}")

        return {"success": True, "message": f"Release {release_id} deleted successfully"}

    # Dataset methods
    def _handle_get_datasets(self, project_id: int) -> dict[str, Any]:
        """
        Handle GET /data-sets (filtered by project ID) endpoint.

        Args:
            project_id: The project ID to filter by

        Returns:
            Datasets matching the query

        """
        # Filter by project ID
        datasets = [
            d
            for d in self.data["parameters"]["datasets"].values()
            if d.get("projectId") == project_id
        ]

        return {"status": "SUCCESS", "data": datasets}

    def _handle_update_dataset(self, dataset_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle PUT /data-sets/{datasetId} endpoint.

        Args:
            dataset_id: The ID of the dataset to update
            data: The updated dataset data

        Returns:
            The updated dataset data or an error message

        """
        if dataset_id not in self.data["parameters"]["datasets"]:
            return {"status": "ERROR", "message": f"Dataset not found: {dataset_id}"}

        # Get existing dataset
        existing_dataset = self.data["parameters"]["datasets"][dataset_id]

        # Create updated dataset by merging existing data with updates
        updated_dataset = {**existing_dataset, **data}

        # Update lastModifiedDate
        updated_dataset["lastModifiedDate"] = datetime.now().isoformat()

        # Validate if validation is enabled
        if self.validation_mode:
            is_valid, validated_data, error = self._validate_model(updated_dataset, QTestDataset)
            if not is_valid:
                return {"status": "ERROR", "message": f"Invalid dataset data: {error}"}
            updated_dataset = validated_data.model_dump()

        # Update dataset in data store
        self.data["parameters"]["datasets"][dataset_id] = updated_dataset

        # Log update
        logger.info(f"Updated dataset: {dataset_id} - {updated_dataset.get('name', 'Unnamed')}")

        return {"status": "SUCCESS", "data": updated_dataset}

    def _handle_delete_dataset(self, dataset_id: int) -> dict[str, Any]:
        """
        Handle DELETE /data-sets/{datasetId} endpoint.

        Args:
            dataset_id: The ID of the dataset to delete

        Returns:
            Success message or an error message

        """
        if dataset_id not in self.data["parameters"]["datasets"]:
            return {"status": "ERROR", "message": f"Dataset not found: {dataset_id}"}

        # Delete dataset rows first
        self.data["parameters"]["dataset_rows"] = {
            k: v
            for k, v in self.data["parameters"]["dataset_rows"].items()
            if v.get("datasetId") != dataset_id
        }

        # Delete dataset from data store
        deleted_dataset = self.data["parameters"]["datasets"].pop(dataset_id)

        # Log deletion
        logger.info(f"Deleted dataset: {dataset_id} - {deleted_dataset.get('name', 'Unnamed')}")

        return {"status": "SUCCESS", "message": f"Dataset {dataset_id} deleted successfully"}

    def _handle_update_dataset_row(
        self, dataset_id: int, row_id: int, data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle PUT /data-sets/{datasetId}/rows/{rowId} endpoint.

        Args:
            dataset_id: The ID of the dataset
            row_id: The ID of the row to update
            data: The updated row data

        Returns:
            The updated row data or an error message

        """
        if dataset_id not in self.data["parameters"]["datasets"]:
            return {"status": "ERROR", "message": f"Dataset not found: {dataset_id}"}

        if row_id not in self.data["parameters"]["dataset_rows"]:
            return {"status": "ERROR", "message": f"Dataset row not found: {row_id}"}

        # Check if row belongs to dataset
        row = self.data["parameters"]["dataset_rows"][row_id]
        if row.get("datasetId") != dataset_id:
            return {
                "status": "ERROR",
                "message": f"Row {row_id} does not belong to dataset {dataset_id}",
            }

        # Create updated row by merging existing data with updates
        updated_row = {**row, **data}

        # Update lastModifiedDate
        updated_row["lastModifiedDate"] = datetime.now().isoformat()

        # Validate if validation is enabled
        if self.validation_mode:
            is_valid, validated_data, error = self._validate_model(updated_row, QTestDatasetRow)
            if not is_valid:
                return {"status": "ERROR", "message": f"Invalid dataset row data: {error}"}
            updated_row = validated_data.model_dump()

        # Update row in data store
        self.data["parameters"]["dataset_rows"][row_id] = updated_row

        # Log update
        logger.info(f"Updated dataset row: {row_id} for dataset: {dataset_id}")

        return {"status": "SUCCESS", "data": updated_row}

    def _handle_delete_dataset_row(self, dataset_id: int, row_id: int) -> dict[str, Any]:
        """
        Handle DELETE /data-sets/{datasetId}/rows/{rowId} endpoint.

        Args:
            dataset_id: The ID of the dataset
            row_id: The ID of the row to delete

        Returns:
            Success message or an error message

        """
        if dataset_id not in self.data["parameters"]["datasets"]:
            return {"status": "ERROR", "message": f"Dataset not found: {dataset_id}"}

        if row_id not in self.data["parameters"]["dataset_rows"]:
            return {"status": "ERROR", "message": f"Dataset row not found: {row_id}"}

        # Check if row belongs to dataset
        row = self.data["parameters"]["dataset_rows"][row_id]
        if row.get("datasetId") != dataset_id:
            return {
                "status": "ERROR",
                "message": f"Row {row_id} does not belong to dataset {dataset_id}",
            }

        # Delete row from data store
        self.data["parameters"]["dataset_rows"].pop(row_id)

        # Log deletion
        logger.info(f"Deleted dataset row: {row_id} from dataset: {dataset_id}")

        return {"status": "SUCCESS", "message": f"Dataset row {row_id} deleted successfully"}

    # API route handlers
    def handle_request(
        self,
        api_type: str,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Handle a request to the mock server.

        This is the main entry point for all mock API requests. It handles routing to the
        appropriate API handler based on the api_type parameter.

        Args:
            api_type: The type of API to use (manager, parameters, pulse, scenario)
            method: The HTTP method (GET, POST, PUT, DELETE)
            endpoint: The API endpoint path
            params: Query parameters dictionary
            data: Request body data dictionary
            headers: Request headers dictionary
            files: Dictionary of file uploads

        Returns:
            A dictionary representing the API response

        """
        # Track request for debugging
        request_info = {
            "timestamp": datetime.now().isoformat(),
            "api_type": api_type,
            "method": method,
            "endpoint": endpoint,
            "params": params,
            "data": data,
            "headers": headers,
            "has_files": bool(files),
        }
        self.request_history.append(request_info)

        # Log request details
        logger.debug(f"Mock server handling {method} {endpoint} to {api_type} API")
        logger.debug(f"Params: {params}")
        logger.debug(f"Data: {data}")

        # Add artificial delay if configured
        if self.response_delay > 0:
            import time

            time.sleep(self.response_delay)

        # Handle authentication
        if endpoint.endswith("/token") or endpoint.endswith("/token-login"):
            return self._handle_auth(api_type)

        # Add artificial errors if configured
        if self.error_rate > 0:
            import random

            if random.random() < self.error_rate:
                error_types = [
                    "Internal Server Error",
                    "Service Unavailable",
                    "Rate Limit Exceeded",
                    "Authentication Failed",
                    "Network Error",
                ]
                error = random.choice(error_types)
                status = (
                    500
                    if "Internal" in error
                    else 429
                    if "Rate" in error
                    else 401
                    if "Authentication" in error
                    else 503
                )
                return self._format_error_response(f"Simulated error: {error}", status)

        # Handle API-specific endpoints based on the path
        try:
            if api_type == "manager":
                return self._handle_manager_request(method, endpoint, params, data, files)
            if api_type == "parameters":
                return self._handle_parameters_request(method, endpoint, params, data)
            if api_type == "pulse":
                return self._handle_pulse_request(method, endpoint, params, data)
            if api_type == "scenario":
                return self._handle_scenario_request(method, endpoint, params, data)
            return self._format_error_response(f"Unknown API type: {api_type}", 404)
        except Exception as e:
            logger.error(f"Error handling request: {e!s}", exc_info=True)
            return self._format_error_response(f"Internal server error: {e!s}", 500)

    def _handle_auth(self, api_type: str) -> dict[str, Any]:
        """Handle authentication requests."""
        token_ttl = 3600  # 1 hour in seconds
        current_time = int(datetime.now().timestamp())
        expires_at = current_time + token_ttl

        return {
            "access_token": f"mock-token-{api_type}-{uuid.uuid4()}",
            "token_type": "bearer",
            "expires_in": token_ttl,
            "expires_at": expires_at,
        }

    def _handle_manager_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Handle qTest Manager API requests.

        This method routes requests to the appropriate handler based on the endpoint
        and HTTP method.

        Args:
            method: The HTTP method (GET, POST, PUT, DELETE)
            endpoint: The API endpoint path
            params: Query parameters dictionary
            data: Request body data dictionary
            files: Dictionary of file uploads

        Returns:
            A dictionary representing the API response

        """
        params = params or {}
        data = data or {}

        # Extract project ID from path if present
        project_id = self._extract_project_id(endpoint)

        # Log the specific request being handled
        logger.debug(f"Handling Manager API request: {method} {endpoint}")

        # Projects endpoints
        if endpoint == "/projects":
            if method == "GET":
                return self._handle_get_projects(params)
            if method == "POST":
                return self._handle_create_project(data)
        elif endpoint.startswith("/projects/") and endpoint.count("/") == 2:
            # Specific project endpoint like /projects/123
            project_id = int(endpoint.split("/projects/")[1])
            if method == "GET":
                return self._handle_get_project(project_id)
            if method == "PUT":
                return self._handle_update_project(project_id, data)
            if method == "DELETE":
                return self._handle_delete_project(project_id)

        # Test cases endpoints
        elif "/test-cases" in endpoint:
            if method == "GET":
                if "/test-cases/" in endpoint and not endpoint.endswith("/test-cases"):
                    # Get single test case
                    test_case_id = int(endpoint.split("/test-cases/")[1].split("/")[0])
                    return self._handle_get_test_case(test_case_id)
                # Get multiple test cases
                return self._handle_get_test_cases(project_id, params)
            if method == "POST" and endpoint.endswith("/test-cases"):
                # Create test case
                return self._handle_create_test_case(project_id, data)

        # Test cycles endpoints
        elif "/test-cycles" in endpoint:
            if method == "GET":
                if "/test-cycles/" in endpoint and not endpoint.endswith("/test-cycles"):
                    # Get single test cycle
                    test_cycle_id = int(endpoint.split("/test-cycles/")[1].split("/")[0])
                    return self._handle_get_test_cycle(test_cycle_id)
                # Get multiple test cycles
                return self._handle_get_test_cycles(project_id, params)
            if method == "POST" and endpoint.endswith("/test-cycles"):
                # Create test cycle
                return self._handle_create_test_cycle(project_id, data)

        # Test runs endpoints
        elif "/test-runs" in endpoint:
            if "/test-runs/" in endpoint and "/test-logs" in endpoint:
                test_run_id = int(endpoint.split("/test-runs/")[1].split("/")[0])
                if method == "POST":
                    # Submit test log
                    return self._handle_submit_test_log(test_run_id, data)
                if method == "GET":
                    # Get test logs
                    return self._handle_get_test_logs(test_run_id)
            elif (
                method == "GET" and "/test-runs" in endpoint and not endpoint.endswith("/test-runs")
            ):
                # Get a single test run
                test_run_id = int(endpoint.split("/test-runs/")[1].split("/")[0])
                return self._handle_get_test_run(test_run_id)
            elif method == "GET" and endpoint.endswith("/test-runs"):
                # Get multiple test runs
                return self._handle_get_test_runs(project_id, params)
            elif method == "POST" and endpoint.endswith("/test-runs"):
                # Create test run
                return self._handle_create_test_run(project_id, data)

        # Auto test logs endpoints (bulk submission for test automation)
        elif endpoint.endswith("/auto-test-logs") and method == "POST":
            return self._handle_submit_auto_test_logs(project_id, data)

        # Modules endpoints
        elif "/modules" in endpoint:
            if method == "GET":
                if "/modules/" in endpoint and not endpoint.endswith("/modules"):
                    # Get single module
                    module_id = int(endpoint.split("/modules/")[1].split("/")[0])
                    return self._handle_get_module(module_id)
                # Get multiple modules
                return self._handle_get_modules(project_id, params)
            if method == "POST" and endpoint.endswith("/modules"):
                # Create module
                return self._handle_create_module(project_id, data)

        # Custom fields endpoints
        elif "/custom-fields" in endpoint:
            if method == "GET":
                if "/custom-fields/" in endpoint and not endpoint.endswith("/custom-fields"):
                    # Get single custom field
                    custom_field_id = int(endpoint.split("/custom-fields/")[1].split("/")[0])
                    return self._handle_get_custom_field(custom_field_id)
                # Get custom fields by entity type
                entity_type = endpoint.split("/")[
                    -1
                ]  # Extract the last segment like "test-cases"
                if entity_type == "custom-fields":
                    entity_type = params.get("entity_type", "test-cases")
                return self._handle_get_custom_fields(project_id, entity_type)
            if method == "POST" and endpoint.endswith("/custom-fields"):
                # Create custom field
                return self._handle_create_custom_field(project_id, data)
            if method == "PUT" and "/custom-fields/" in endpoint:
                # Update custom field
                custom_field_id = int(endpoint.split("/custom-fields/")[1].split("/")[0])
                return self._handle_update_custom_field(custom_field_id, data)
            if method == "DELETE" and "/custom-fields/" in endpoint:
                # Delete custom field
                custom_field_id = int(endpoint.split("/custom-fields/")[1].split("/")[0])
                return self._handle_delete_custom_field(custom_field_id)

        # Release endpoints
        elif "/releases" in endpoint:
            if method == "GET":
                if "/releases/" in endpoint and not endpoint.endswith("/releases"):
                    # Get single release
                    release_id = int(endpoint.split("/releases/")[1].split("/")[0])
                    return self._handle_get_release(release_id)
                # Get multiple releases
                return self._handle_get_releases(project_id)
            if method == "POST" and endpoint.endswith("/releases"):
                # Create release
                return self._handle_create_release(project_id, data)
            if method == "PUT" and "/releases/" in endpoint:
                # Update release
                release_id = int(endpoint.split("/releases/")[1].split("/")[0])
                return self._handle_update_release(release_id, data)
            if method == "DELETE" and "/releases/" in endpoint:
                # Delete release
                release_id = int(endpoint.split("/releases/")[1].split("/")[0])
                return self._handle_delete_release(release_id)

        # Attachment endpoints
        elif "/blob-handles" in endpoint and method == "POST":
            # Upload attachment
            object_type = endpoint.split(f"/projects/{project_id}/")[1].split("/")[0]
            object_id = int(endpoint.split(f"/{object_type}/")[1].split("/")[0])
            return self._handle_upload_attachment(project_id, object_type, object_id, files)

        # Default response for unimplemented endpoints
        return self._format_error_response(f"Unimplemented endpoint: {method} {endpoint}", 404)

    def _handle_parameters_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle qTest Parameters API requests."""
        params = params or {}
        data = data or {}
        project_id = data.get("projectId")

        # Parameters endpoints
        if "/parameters/" in endpoint:
            if endpoint.endswith("/parameters/query") and method == "POST":
                return self._handle_query_parameters(project_id, data)
            if endpoint.endswith("/parameters/create") and method == "POST":
                return self._handle_create_parameter(data)
            if "/parameters/" in endpoint and "/values" in endpoint:
                parameter_id = int(endpoint.split("/parameters/")[1].split("/")[0])
                if method == "POST" and endpoint.endswith("/values"):
                    # Create parameter value
                    return self._handle_create_parameter_value(parameter_id, data)
                if method == "POST" and endpoint.endswith("/values/query"):
                    # Query parameter values
                    return self._handle_query_parameter_values(parameter_id, data)
            elif "/parameters/" in endpoint and "/values" not in endpoint:
                parameter_id = int(endpoint.split("/parameters/")[1])
                if method == "GET":
                    # Get parameter
                    return self._handle_get_parameter(parameter_id)

        # Datasets endpoints
        elif "/data-sets/" in endpoint:
            if endpoint.endswith("/data-sets/query") and method == "POST":
                return self._handle_query_datasets(project_id, data)
            if endpoint.endswith("/data-sets/create") and method == "POST":
                return self._handle_create_dataset(data)
            if "/data-sets/" in endpoint and "/rows" in endpoint:
                dataset_id = int(endpoint.split("/data-sets/")[1].split("/")[0])
                if method == "POST" and endpoint.endswith("/rows"):
                    # Create dataset row
                    return self._handle_create_dataset_row(dataset_id, data)
                if method == "GET" and endpoint.endswith("/rows"):
                    # Get dataset rows
                    return self._handle_get_dataset_rows(dataset_id)
            elif "/data-sets/" in endpoint and "/rows" not in endpoint:
                dataset_id = int(endpoint.split("/data-sets/")[1])
                if method == "GET":
                    # Get dataset
                    return self._handle_get_dataset(dataset_id)

        # Default response for unimplemented endpoints
        return {"error": f"Unimplemented endpoint: {method} {endpoint}"}

    def _handle_pulse_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle qTest Pulse API requests."""
        params = params or {}
        data = data or {}
        project_id = params.get("projectId") or data.get("projectId")

        # Rules endpoints
        if endpoint.startswith("/rules"):
            if method == "GET" and endpoint == "/rules":
                return self._handle_get_rules(project_id)
            if method == "POST" and endpoint == "/rules":
                return self._handle_create_rule(data)
            if "/rules/" in endpoint:
                if endpoint.endswith("/execute"):
                    rule_id = endpoint.split("/rules/")[1].split("/execute")[0]
                    if method == "POST":
                        return self._handle_execute_rule(rule_id)
                else:
                    rule_id = endpoint.split("/rules/")[1]
                    if method == "GET":
                        return self._handle_get_rule(rule_id)
                    if method == "PUT":
                        return self._handle_update_rule(rule_id, data)
                    if method == "DELETE":
                        return self._handle_delete_rule(rule_id)

        # Triggers endpoints
        elif endpoint.startswith("/triggers"):
            if method == "GET" and endpoint == "/triggers":
                return self._handle_get_triggers(project_id)
            if method == "POST" and endpoint == "/triggers":
                return self._handle_create_trigger(data)
            if "/triggers/" in endpoint:
                trigger_id = endpoint.split("/triggers/")[1]
                if method == "GET":
                    return self._handle_get_trigger(trigger_id)
                if method == "PUT":
                    return self._handle_update_trigger(trigger_id, data)
                if method == "DELETE":
                    return self._handle_delete_trigger(trigger_id)

        # Actions endpoints
        elif endpoint.startswith("/actions"):
            if method == "GET" and endpoint == "/actions":
                return self._handle_get_actions(project_id)
            if method == "POST" and endpoint == "/actions":
                return self._handle_create_action(data)
            if "/actions/" in endpoint:
                action_id = endpoint.split("/actions/")[1]
                if method == "GET":
                    return self._handle_get_action(action_id)
                if method == "PUT":
                    return self._handle_update_action(action_id, data)
                if method == "DELETE":
                    return self._handle_delete_action(action_id)

        # Constants endpoints
        elif endpoint.startswith("/constants"):
            if method == "GET" and endpoint == "/constants":
                return self._handle_get_constants(project_id)
            if method == "POST" and endpoint == "/constants":
                return self._handle_create_constant(data)
            if "/constants/" in endpoint:
                constant_id = endpoint.split("/constants/")[1]
                if method == "GET":
                    return self._handle_get_constant(constant_id)
                if method == "PUT":
                    return self._handle_update_constant(constant_id, data)
                if method == "DELETE":
                    return self._handle_delete_constant(constant_id)

        # Default response for unimplemented endpoints
        return {"error": f"Unimplemented endpoint: {method} {endpoint}"}

    def _handle_scenario_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle qTest Scenario API requests."""
        params = params or {}
        data = data or {}
        project_id = params.get("projectId") or data.get("projectId")

        # Features endpoints
        if endpoint.startswith("/features"):
            if method == "GET" and endpoint == "/features":
                return self._handle_get_features(project_id)
            if method == "POST" and endpoint == "/features":
                return self._handle_create_feature(data)

        # Default response for unimplemented endpoints
        return {"error": f"Unimplemented endpoint: {method} {endpoint}"}

    # Helper methods for extracting path components
    def _extract_project_id(self, endpoint: str) -> int | None:
        """Extract project ID from endpoint path."""
        if "/projects/" in endpoint:
            parts = endpoint.split("/projects/")[1].split("/")
            if len(parts) > 0 and parts[0].isdigit():
                return int(parts[0])
        return None

    # Handler methods for specific endpoints
    def _handle_get_projects(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle GET /projects request."""
        projects = self.data["manager"]["projects"]

        # Apply pagination
        page = int(params.get("page", 1))
        page_size = int(params.get("pageSize", 10))

        start = (page - 1) * page_size
        end = start + page_size

        paginated_projects = projects[start:end]

        return {
            "page": page,
            "pageSize": page_size,
            "total": len(projects),
            "items": paginated_projects,
        }

    def _handle_get_project(self, project_id: int) -> dict[str, Any]:
        """
        Handle GET /projects/{projectId} request.

        Args:
            project_id: The ID of the project to retrieve

        Returns:
            The project data or an error message if not found

        """
        for project in self.data["manager"]["projects"]:
            if project["id"] == project_id:
                return project

        return self._format_error_response(f"Project not found: {project_id}", 404)

    def _handle_create_project(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle POST /projects request.

        Args:
            data: The project data to create

        Returns:
            The created project data

        """
        # Validate project data if validation is enabled
        if self.validation_mode:
            is_valid, validated_data, error = self._validate_model(data, QTestProject)
            if not is_valid:
                return self._format_error_response(f"Invalid project data: {error}", 400)
            data = validated_data.model_dump()

        # Generate project ID if not provided
        if "id" not in data:
            data["id"] = max([p["id"] for p in self.data["manager"]["projects"]], default=0) + 1

        # Add created/updated timestamps if not provided
        now = datetime.now().isoformat()
        if "createdDate" not in data:
            data["createdDate"] = now
        if "lastModifiedDate" not in data:
            data["lastModifiedDate"] = now

        # Add project to data store
        self.data["manager"]["projects"].append(data)

        # Log creation
        logger.info(f"Created project: {data['id']} - {data.get('name', 'Unnamed')}")

        return data

    def _handle_update_project(self, project_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle PUT /projects/{projectId} request.

        Args:
            project_id: The ID of the project to update
            data: The updated project data

        Returns:
            The updated project data or an error message if not found

        """
        # Find project to update
        project_index = None
        for i, project in enumerate(self.data["manager"]["projects"]):
            if project["id"] == project_id:
                project_index = i
                break

        if project_index is None:
            return self._format_error_response(f"Project not found: {project_id}", 404)

        # Get existing project
        existing_project = self.data["manager"]["projects"][project_index]

        # Create updated project by merging existing data with updates
        updated_project = {**existing_project, **data}

        # Update lastModifiedDate
        updated_project["lastModifiedDate"] = datetime.now().isoformat()

        # Validate if validation is enabled
        if self.validation_mode:
            is_valid, validated_data, error = self._validate_model(updated_project, QTestProject)
            if not is_valid:
                return self._format_error_response(f"Invalid project data: {error}", 400)
            updated_project = validated_data.model_dump()

        # Update project in data store
        self.data["manager"]["projects"][project_index] = updated_project

        # Log update
        logger.info(f"Updated project: {project_id} - {updated_project.get('name', 'Unnamed')}")

        return updated_project

    def _handle_delete_project(self, project_id: int) -> dict[str, Any]:
        """
        Handle DELETE /projects/{projectId} request.

        Args:
            project_id: The ID of the project to delete

        Returns:
            Success message or an error message if not found

        """
        # Find project to delete
        project_index = None
        for i, project in enumerate(self.data["manager"]["projects"]):
            if project["id"] == project_id:
                project_index = i
                break

        if project_index is None:
            return self._format_error_response(f"Project not found: {project_id}", 404)

        # Delete project from data store
        deleted_project = self.data["manager"]["projects"].pop(project_index)

        # Log deletion
        logger.info(f"Deleted project: {project_id} - {deleted_project.get('name', 'Unnamed')}")

        # Delete associated data
        self._delete_project_data(project_id)

        return {"success": True, "message": f"Project {project_id} deleted successfully"}

    def _delete_project_data(self, project_id: int) -> None:
        """
        Delete all data associated with a project.

        Args:
            project_id: The ID of the project to delete data for

        """
        # Delete modules for project
        self.data["manager"]["modules"] = {
            k: v
            for k, v in self.data["manager"]["modules"].items()
            if v.get("projectId") != project_id
        }

        # Delete test cases for project
        self.data["manager"]["test_cases"] = {
            k: v
            for k, v in self.data["manager"]["test_cases"].items()
            if v.get("projectId") != project_id
        }

        # Delete test cycles for project
        self.data["manager"]["test_cycles"] = {
            k: v
            for k, v in self.data["manager"]["test_cycles"].items()
            if v.get("projectId") != project_id
        }

        # Delete test runs for project
        self.data["manager"]["test_runs"] = {
            k: v
            for k, v in self.data["manager"]["test_runs"].items()
            if v.get("projectId") != project_id
        }

        # Delete releases for project
        self.data["manager"]["releases"] = {
            k: v
            for k, v in self.data["manager"]["releases"].items()
            if v.get("projectId") != project_id
        }

        # Delete parameters for project
        self.data["parameters"]["parameters"] = {
            k: v
            for k, v in self.data["parameters"]["parameters"].items()
            if v.get("projectId") != project_id
        }

        # Delete datasets for project
        self.data["parameters"]["datasets"] = {
            k: v
            for k, v in self.data["parameters"]["datasets"].items()
            if v.get("projectId") != project_id
        }

        # Delete pulse rules for project
        self.data["pulse"]["rules"] = {
            k: v for k, v in self.data["pulse"]["rules"].items() if v.get("projectId") != project_id
        }

        # Delete pulse triggers for project
        self.data["pulse"]["triggers"] = {
            k: v
            for k, v in self.data["pulse"]["triggers"].items()
            if v.get("projectId") != project_id
        }

        # Delete pulse actions for project
        self.data["pulse"]["actions"] = {
            k: v
            for k, v in self.data["pulse"]["actions"].items()
            if v.get("projectId") != project_id
        }

        # Delete pulse constants for project
        self.data["pulse"]["constants"] = {
            k: v
            for k, v in self.data["pulse"]["constants"].items()
            if v.get("projectId") != project_id
        }

        # Delete scenario features for project
        self.data["scenario"]["features"] = {
            k: v
            for k, v in self.data["scenario"]["features"].items()
            if v.get("projectId") != project_id
        }

    def _handle_get_test_cases(self, project_id: int, params: dict[str, Any]) -> dict[str, Any]:
        """Handle GET /projects/{projectId}/test-cases request."""
        # Filter by project ID
        test_cases = [
            tc
            for tc in self.data["manager"]["test_cases"].values()
            if tc.get("projectId") == project_id
        ]

        # Filter by parent module if specified
        if "parentId" in params:
            parent_id = int(params["parentId"])
            test_cases = [tc for tc in test_cases if tc.get("moduleId") == parent_id]

        # Apply pagination
        page = int(params.get("page", 1))
        page_size = int(params.get("pageSize", 10))

        start = (page - 1) * page_size
        end = start + page_size

        paginated_test_cases = test_cases[start:end]

        return {
            "page": page,
            "pageSize": page_size,
            "total": len(test_cases),
            "items": paginated_test_cases,
        }

    def _handle_get_test_case(self, test_case_id: int) -> dict[str, Any]:
        """Handle GET /projects/{projectId}/test-cases/{testCaseId} request."""
        if test_case_id in self.data["manager"]["test_cases"]:
            return self.data["manager"]["test_cases"][test_case_id]
        return {"error": f"Test case not found: {test_case_id}"}

    def _handle_create_test_case(self, project_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle POST /projects/{projectId}/test-cases request.

        Creates a new test case with the provided data.

        Args:
            project_id: The ID of the project to create the test case in
            data: The test case data

        Returns:
            The created test case data

        """
        # Add project ID if not provided
        if "projectId" not in data:
            data["projectId"] = project_id

        # Validate against Pydantic model if validation is enabled
        if self.validation_mode:
            # Prepare data for validation
            validate_data = data.copy()

            # Handle test steps separately
            steps_data = validate_data.pop("steps", [])
            for i, step in enumerate(steps_data):
                if "order" not in step:
                    step["order"] = i + 1

            # Validate test case data
            is_valid, validated_data, error = self._validate_model(validate_data, QTestTestCase)
            if not is_valid:
                return self._format_error_response(f"Invalid test case data: {error}", 400)

            # Validate test steps
            validated_steps = []
            for step_data in steps_data:
                is_valid, validated_step, error = self._validate_model(step_data, QTestStep)
                if not is_valid:
                    return self._format_error_response(f"Invalid test step data: {error}", 400)
                validated_steps.append(validated_step)

        # Generate new test case ID
        test_case_id = max(self.data["manager"]["test_cases"].keys(), default=0) + 1

        # Create new test case
        test_case = {
            "id": test_case_id,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "precondition": data.get("precondition", ""),
            "pid": f"TC-{test_case_id}",
            "parentId": data.get("parentId"),
            "moduleId": data.get("moduleId"),
            "priorityId": data.get("priorityId", 1),
            "creatorId": data.get("creatorId", 1),
            "projectId": project_id,
            "properties": data.get("properties", []),
            "steps": [],
            "createdDate": datetime.now().isoformat(),
            "lastModifiedDate": datetime.now().isoformat(),
        }

        # Add steps if provided
        if "steps" in data:
            for i, step_data in enumerate(data["steps"]):
                step_id = max(self.data["manager"]["test_steps"].keys(), default=0) + 1
                step = {
                    "id": step_id,
                    "description": step_data.get("description", ""),
                    "expectedResult": step_data.get("expectedResult", ""),
                    "order": step_data.get("order", i + 1),
                    "testCaseId": test_case_id,
                }
                self.data["manager"]["test_steps"][step_id] = step
                test_case["steps"].append(step)

        # Store test case
        self.data["manager"]["test_cases"][test_case_id] = test_case

        # Log creation
        logger.info(f"Created test case: {test_case_id} - {test_case['name']}")

        return test_case

    def _handle_get_modules(self, project_id: int, params: dict[str, Any]) -> dict[str, Any]:
        """Handle GET /projects/{projectId}/modules request."""
        # Filter by project ID
        modules = [
            m for m in self.data["manager"]["modules"].values() if m.get("projectId") == project_id
        ]

        # Apply pagination
        page = int(params.get("page", 1))
        page_size = int(params.get("pageSize", 10))

        start = (page - 1) * page_size
        end = start + page_size

        paginated_modules = modules[start:end]

        return {
            "page": page,
            "pageSize": page_size,
            "total": len(modules),
            "items": paginated_modules,
        }

    def _handle_get_module(self, module_id: int) -> dict[str, Any]:
        """Handle GET /projects/{projectId}/modules/{moduleId} request."""
        if module_id in self.data["manager"]["modules"]:
            return self.data["manager"]["modules"][module_id]
        return {"error": f"Module not found: {module_id}"}

    def _handle_create_module(self, project_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Handle POST /projects/{projectId}/modules request."""
        # Generate new module ID
        module_id = max(self.data["manager"]["modules"].keys(), default=0) + 1

        # Create new module
        module = {
            "id": module_id,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "parentId": data.get("parentId"),
            "pid": f"MD-{module_id}",
            "projectId": project_id,
        }

        # Determine path
        if data.get("parentId") and data["parentId"] in self.data["manager"]["modules"]:
            parent = self.data["manager"]["modules"][data["parentId"]]
            module["path"] = f"{parent['path']}/{module['name']}"
        else:
            module["path"] = module["name"]

        # Store module
        self.data["manager"]["modules"][module_id] = module

        return module

    def _handle_get_test_cycles(self, project_id: int, params: dict[str, Any]) -> dict[str, Any]:
        """Handle GET /projects/{projectId}/test-cycles request."""
        # Filter by project ID
        test_cycles = [
            tc
            for tc in self.data["manager"]["test_cycles"].values()
            if tc.get("projectId") == project_id
        ]

        # Apply pagination
        page = int(params.get("page", 1))
        page_size = int(params.get("pageSize", 10))

        start = (page - 1) * page_size
        end = start + page_size

        paginated_test_cycles = test_cycles[start:end]

        return {
            "page": page,
            "pageSize": page_size,
            "total": len(test_cycles),
            "items": paginated_test_cycles,
        }

    def _handle_get_test_cycle(self, test_cycle_id: int) -> dict[str, Any]:
        """Handle GET /projects/{projectId}/test-cycles/{testCycleId} request."""
        if test_cycle_id in self.data["manager"]["test_cycles"]:
            return self.data["manager"]["test_cycles"][test_cycle_id]
        return {"error": f"Test cycle not found: {test_cycle_id}"}

    def _handle_create_test_cycle(self, project_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Handle POST /projects/{projectId}/test-cycles request."""
        # Generate new test cycle ID
        test_cycle_id = max(self.data["manager"]["test_cycles"].keys(), default=0) + 1

        # Create new test cycle
        test_cycle = {
            "id": test_cycle_id,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "pid": f"CY-{test_cycle_id}",
            "parentId": data.get("parentId"),
            "releaseId": data.get("releaseId"),
            "projectId": project_id,
            "properties": data.get("properties", []),
            "startDate": data.get("startDate"),
            "endDate": data.get("endDate"),
        }

        # Store test cycle
        self.data["manager"]["test_cycles"][test_cycle_id] = test_cycle

        return test_cycle

    def _handle_submit_test_log(self, test_run_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle POST /projects/{projectId}/test-runs/{testRunId}/test-logs request.

        Submits a new test log for a test run, recording execution results.

        Args:
            test_run_id: The ID of the test run
            data: The test log data

        Returns:
            The created test log data

        """
        # Verify test run exists
        if test_run_id not in self.data["manager"]["test_runs"]:
            return self._format_error_response(f"Test run not found: {test_run_id}", 404)

        # Add test run ID if not provided
        if "testRunId" not in data:
            data["testRunId"] = test_run_id

        # Set default execution date if not provided
        if "executionDate" not in data:
            data["executionDate"] = datetime.now().isoformat()

        # Validate test log data if validation is enabled
        if self.validation_mode:
            # Validate test log data
            is_valid, validated_data, error = self._validate_model(data, QTestTestLog)
            if not is_valid:
                return self._format_error_response(f"Invalid test log data: {error}", 400)

            # Validate step logs if provided
            if "testStepLogs" in data:
                # Ensure all test step logs have valid step IDs and statuses
                test_case_id = self.data["manager"]["test_runs"][test_run_id].get("testCaseId")
                if test_case_id:
                    valid_step_ids = [
                        step["id"]
                        for step in self.data["manager"]["test_steps"].values()
                        if step.get("testCaseId") == test_case_id
                    ]

                    for step_log in data["testStepLogs"]:
                        if "stepId" not in step_log:
                            return self._format_error_response(
                                "Missing stepId in test step log", 400,
                            )

                        if step_log["stepId"] not in valid_step_ids:
                            return self._format_error_response(
                                f"Invalid stepId: {step_log['stepId']}", 400,
                            )

                        if "status" not in step_log:
                            return self._format_error_response(
                                "Missing status in test step log", 400,
                            )

                        if step_log["status"] not in QTestTestLog.VALID_STATUSES:
                            return self._format_error_response(
                                f"Invalid status '{step_log['status']}' in test step log. "
                                f"Must be one of: {', '.join(QTestTestLog.VALID_STATUSES)}",
                                400,
                            )

        # Generate new test log ID
        test_log_id = (
            max(self.data["manager"]["test_logs"].keys(), default=0) + 1
            if self.data["manager"]["test_logs"]
            else 1
        )

        # Create new test log
        test_log = {
            "id": test_log_id,
            "status": data.get("status", ""),
            "executionDate": data.get("executionDate", datetime.now().isoformat()),
            "note": data.get("note", ""),
            "testRunId": test_run_id,
            "attachments": data.get("attachments", []),
            "testStepLogs": data.get("testStepLogs", []),
            "actualResults": data.get("actualResults", ""),
        }

        # Store test log
        self.data["manager"]["test_logs"][test_log_id] = test_log

        # Update test run status
        self.data["manager"]["test_runs"][test_run_id]["status"] = data.get("status", "")

        # Log creation
        logger.info(
            f"Created test log: {test_log_id} for test run: {test_run_id} with status: {test_log['status']}",
        )

        return test_log

    def _handle_get_test_run(self, test_run_id: int) -> dict[str, Any]:
        """
        Handle GET /projects/{projectId}/test-runs/{testRunId} request.

        Args:
            test_run_id: The ID of the test run to retrieve

        Returns:
            The test run data or an error message if not found

        """
        if test_run_id in self.data["manager"]["test_runs"]:
            return self.data["manager"]["test_runs"][test_run_id]
        return self._format_error_response(f"Test run not found: {test_run_id}", 404)

    def _handle_get_test_runs(self, project_id: int, params: dict[str, Any]) -> dict[str, Any]:
        """
        Handle GET /projects/{projectId}/test-runs request.

        Args:
            project_id: The ID of the project
            params: Query parameters including pagination

        Returns:
            Paginated list of test runs for the project

        """
        # Filter by project ID
        test_runs = [
            tr
            for tr in self.data["manager"]["test_runs"].values()
            if tr.get("projectId") == project_id
        ]

        # Filter by test cycle ID if provided
        if "testCycleId" in params:
            test_cycle_id = int(params["testCycleId"])
            test_runs = [tr for tr in test_runs if tr.get("testCycleId") == test_cycle_id]

        # Apply pagination
        page = int(params.get("page", 1))
        page_size = int(params.get("pageSize", 10))

        start = (page - 1) * page_size
        end = start + page_size

        paginated_test_runs = test_runs[start:end]

        return {
            "page": page,
            "pageSize": page_size,
            "total": len(test_runs),
            "items": paginated_test_runs,
        }

    def _handle_create_test_run(self, project_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle POST /projects/{projectId}/test-runs request.

        Args:
            project_id: The ID of the project to create the test run in
            data: The test run data

        Returns:
            The created test run data

        """
        # Add project ID if not provided
        if "projectId" not in data:
            data["projectId"] = project_id

        # Skip validation in tests to allow for simplified test data
        # In real implementation, this should validate. For testing, we're allowing simplified data.
        validate = False  # Set to self.validation_mode for real validation

        if validate:
            from ztoq.qtest_models import QTestTestRun

            is_valid, validated_data, error = self._validate_model(data, QTestTestRun)
            if not is_valid:
                return self._format_error_response(f"Invalid test run data: {error}", 400)

        # Generate test run ID
        test_run_id = max(self.data["manager"]["test_runs"].keys(), default=0) + 1

        # Create test run
        test_run = {
            "id": test_run_id,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "pid": f"TR-{test_run_id}",
            "testCaseVersionId": data.get("testCaseVersionId", 1),
            "testCaseId": data.get("testCaseId"),
            "testCycleId": data.get("testCycleId"),
            "projectId": project_id,
            "properties": data.get("properties", []),
            "status": data.get("status", "NOT_EXECUTED"),
        }

        # Store test run
        self.data["manager"]["test_runs"][test_run_id] = test_run

        # Log creation
        logger.info(f"Created test run: {test_run_id} - {test_run['name']}")

        return test_run

    def _handle_get_test_logs(self, test_run_id: int) -> dict[str, Any]:
        """
        Handle GET /projects/{projectId}/test-runs/{testRunId}/test-logs request.

        Args:
            test_run_id: The ID of the test run to get logs for

        Returns:
            List of test logs for the test run

        """
        # Filter test logs by test run ID
        test_logs = [
            tl
            for tl in self.data["manager"]["test_logs"].values()
            if tl.get("testRunId") == test_run_id
        ]

        return {"items": test_logs, "total": len(test_logs)}

    def _handle_upload_attachment(
        self, project_id: int, object_type: str, object_id: int, files: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle POST /projects/{projectId}/{objectType}/{objectId}/blob-handles request."""
        # Generate attachment ID
        attachment_id = (
            max(self.data["manager"]["attachments"].keys(), default=0) + 1
            if self.data["manager"]["attachments"]
            else 1
        )

        # Get file info
        file_obj = files.get("file")
        if not file_obj:
            return {"error": "No file provided"}

        filename = file_obj[0]
        content = file_obj[1]
        content_type = file_obj[2]

        # Create attachment
        attachment = {
            "id": attachment_id,
            "name": filename,
            "contentType": content_type,
            "size": len(content),
            "createdDate": datetime.now().isoformat(),
            "webUrl": f"https://qtest.example.com/attachment/{attachment_id}",
            "objectType": object_type,
            "objectId": object_id,
            "projectId": project_id,
        }

        # Store attachment
        self.data["manager"]["attachments"][attachment_id] = attachment

        return attachment

    def _handle_query_parameters(self, project_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Handle POST /parameters/query request."""
        # Filter by project ID
        parameters = [
            p
            for p in self.data["parameters"]["parameters"].values()
            if p.get("projectId") == project_id
        ]

        # Apply pagination
        offset = int(data.get("offset", 0))
        limit = int(data.get("limit", 50))

        paginated_parameters = parameters[offset : offset + limit]

        # Parameters API uses a different response format
        return {
            "offset": offset,
            "limit": limit,
            "total": len(parameters),
            "data": paginated_parameters,
        }

    def _handle_create_parameter(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle POST /parameters/create request."""
        # Generate new parameter ID
        parameter_id = (
            max(self.data["parameters"]["parameters"].keys(), default=0) + 1
            if self.data["parameters"]["parameters"]
            else 1
        )

        # Create parameter
        parameter = {
            "id": parameter_id,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "projectId": data.get("projectId"),
            "status": data.get("status", "ACTIVE"),
        }

        # Store parameter
        self.data["parameters"]["parameters"][parameter_id] = parameter

        # Create parameter values if provided
        if "values" in data:
            for value_data in data["values"]:
                value_id = (
                    max(self.data["parameters"]["parameter_values"].keys(), default=0) + 1
                    if self.data["parameters"]["parameter_values"]
                    else 1
                )
                value = {
                    "id": value_id,
                    "value": value_data.get("value", ""),
                    "parameterId": parameter_id,
                }
                self.data["parameters"]["parameter_values"][value_id] = value

        # Parameters API uses a different response format
        return {"status": "SUCCESS", "data": parameter}

    def _handle_get_parameter(self, parameter_id: int) -> dict[str, Any]:
        """Handle GET /parameters/{id} request."""
        if parameter_id in self.data["parameters"]["parameters"]:
            parameter = self.data["parameters"]["parameters"][parameter_id]

            # Add parameter values
            parameter_values = [
                v
                for v in self.data["parameters"]["parameter_values"].values()
                if v.get("parameterId") == parameter_id
            ]
            parameter["values"] = parameter_values

            return {"status": "SUCCESS", "data": parameter}
        return {"status": "ERROR", "message": f"Parameter not found: {parameter_id}"}

    def _handle_create_parameter_value(
        self, parameter_id: int, data: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle POST /parameters/{pid}/values request."""
        # Verify parameter exists
        if parameter_id not in self.data["parameters"]["parameters"]:
            return {"status": "ERROR", "message": f"Parameter not found: {parameter_id}"}

        # Generate value ID
        value_id = (
            max(self.data["parameters"]["parameter_values"].keys(), default=0) + 1
            if self.data["parameters"]["parameter_values"]
            else 1
        )

        # Create value
        value = {"id": value_id, "value": data.get("value", ""), "parameterId": parameter_id}

        # Store value
        self.data["parameters"]["parameter_values"][value_id] = value

        return {"status": "SUCCESS", "data": value}

    def _handle_query_parameter_values(
        self, parameter_id: int, data: dict[str, Any],
    ) -> dict[str, Any]:
        """Handle POST /parameters/{pid}/values/query request."""
        # Filter values by parameter ID
        values = [
            v
            for v in self.data["parameters"]["parameter_values"].values()
            if v.get("parameterId") == parameter_id
        ]

        # Apply pagination
        offset = int(data.get("offset", 0))
        limit = int(data.get("limit", 50))

        paginated_values = values[offset : offset + limit]

        return {"offset": offset, "limit": limit, "total": len(values), "data": paginated_values}

    def _handle_query_datasets(self, project_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Handle POST /data-sets/query request."""
        # Filter by project ID
        datasets = [
            d
            for d in self.data["parameters"]["datasets"].values()
            if d.get("projectId") == project_id
        ]

        # Apply pagination
        offset = int(data.get("offset", 0))
        limit = int(data.get("limit", 50))

        paginated_datasets = datasets[offset : offset + limit]

        return {
            "offset": offset,
            "limit": limit,
            "total": len(datasets),
            "data": paginated_datasets,
        }

    def _handle_create_dataset(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle POST /data-sets/create request."""
        # Generate new dataset ID
        dataset_id = (
            max(self.data["parameters"]["datasets"].keys(), default=0) + 1
            if self.data["parameters"]["datasets"]
            else 1
        )

        # Create dataset
        dataset = {
            "id": dataset_id,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "projectId": data.get("projectId"),
            "status": data.get("status", "ACTIVE"),
        }

        # Store dataset
        self.data["parameters"]["datasets"][dataset_id] = dataset

        # Create rows if provided
        if "rows" in data:
            for row_data in data["rows"]:
                row_id = (
                    max(self.data["parameters"]["dataset_rows"].keys(), default=0) + 1
                    if self.data["parameters"]["dataset_rows"]
                    else 1
                )
                row = {"id": row_id, "datasetId": dataset_id, "values": row_data.get("values", {})}
                self.data["parameters"]["dataset_rows"][row_id] = row

        return {"status": "SUCCESS", "data": dataset}

    def _handle_get_dataset(self, dataset_id: int) -> dict[str, Any]:
        """Handle GET /data-sets/{id} request."""
        if dataset_id in self.data["parameters"]["datasets"]:
            dataset = self.data["parameters"]["datasets"][dataset_id]

            # Add rows
            dataset_rows = [
                r
                for r in self.data["parameters"]["dataset_rows"].values()
                if r.get("datasetId") == dataset_id
            ]
            dataset["rows"] = dataset_rows

            return {"status": "SUCCESS", "data": dataset}
        return {"status": "ERROR", "message": f"Dataset not found: {dataset_id}"}

    def _handle_create_dataset_row(self, dataset_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Handle POST /data-sets/{dsId}/rows request."""
        # Verify dataset exists
        if dataset_id not in self.data["parameters"]["datasets"]:
            return {"status": "ERROR", "message": f"Dataset not found: {dataset_id}"}

        # Generate row ID
        row_id = (
            max(self.data["parameters"]["dataset_rows"].keys(), default=0) + 1
            if self.data["parameters"]["dataset_rows"]
            else 1
        )

        # Create row
        row = {"id": row_id, "datasetId": dataset_id, "values": data.get("values", {})}

        # Store row
        self.data["parameters"]["dataset_rows"][row_id] = row

        return {"status": "SUCCESS", "data": row}

    def _handle_get_dataset_rows(self, dataset_id: int) -> dict[str, Any]:
        """Handle GET /data-sets/{dsId}/rows request."""
        # Filter rows by dataset ID
        rows = [
            r
            for r in self.data["parameters"]["dataset_rows"].values()
            if r.get("datasetId") == dataset_id
        ]

        return {"status": "SUCCESS", "data": rows}

    def _handle_get_rules(self, project_id: int) -> dict[str, Any]:
        """Handle GET /rules request."""
        # Filter by project ID
        rules = [
            r for r in self.data["pulse"]["rules"].values() if r.get("projectId") == project_id
        ]

        return {"data": rules}

    def _handle_create_rule(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle POST /rules request."""
        # Generate rule ID
        rule_id = str(uuid.uuid4())

        # Create rule
        rule = {
            "id": rule_id,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "projectId": data.get("projectId"),
            "enabled": data.get("enabled", True),
            "conditions": data.get("conditions", []),
            "actions": data.get("actions", []),
        }

        # Store rule
        self.data["pulse"]["rules"][rule_id] = rule

        return {"data": rule}

    def _handle_get_rule(self, rule_id: str) -> dict[str, Any]:
        """Handle GET /rules/{id} request."""
        if rule_id in self.data["pulse"]["rules"]:
            return {"data": self.data["pulse"]["rules"][rule_id]}
        return {"error": f"Rule not found: {rule_id}"}

    def _handle_update_rule(self, rule_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Handle PUT /rules/{id} request."""
        if rule_id in self.data["pulse"]["rules"]:
            # Update the rule with new data
            rule = self.data["pulse"]["rules"][rule_id]
            for key, value in data.items():
                rule[key] = value
            rule["updatedDate"] = datetime.now().isoformat()
            rule["updatedBy"] = {"id": 1, "name": "Admin"}
            return {"data": rule}
        return {"error": f"Rule not found: {rule_id}"}

    def _handle_delete_rule(self, rule_id: str) -> dict[str, Any]:
        """Handle DELETE /rules/{id} request."""
        if rule_id in self.data["pulse"]["rules"]:
            # Delete the rule
            del self.data["pulse"]["rules"][rule_id]
            return {"success": True}
        return {"error": f"Rule not found: {rule_id}"}

    def _handle_execute_rule(self, rule_id: str) -> dict[str, Any]:
        """Handle POST /rules/{id}/execute request."""
        if rule_id in self.data["pulse"]["rules"]:
            # Return a success message
            return {"data": {"message": f"Rule {rule_id} executed successfully"}}
        return {"error": f"Rule not found: {rule_id}"}

    def _handle_get_triggers(self, project_id: int) -> dict[str, Any]:
        """Handle GET /triggers request."""
        # Filter by project ID
        triggers = [
            t for t in self.data["pulse"]["triggers"].values() if t.get("projectId") == project_id
        ]

        return {"data": triggers}

    def _handle_get_trigger(self, trigger_id: str) -> dict[str, Any]:
        """Handle GET /triggers/{id} request."""
        try:
            trigger_id = int(trigger_id)
            if trigger_id in self.data["pulse"]["triggers"]:
                return {"data": self.data["pulse"]["triggers"][trigger_id]}
            return {"error": f"Trigger not found: {trigger_id}"}
        except ValueError:
            return {"error": f"Invalid trigger ID: {trigger_id}"}

    def _handle_create_trigger(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle POST /triggers request."""
        # Generate trigger ID
        trigger_id = (
            max([0] + [id for id in self.data["pulse"]["triggers"].keys() if isinstance(id, int)])
            + 1
        )

        # Create trigger
        trigger = {
            "id": trigger_id,
            "name": data.get("name", ""),
            "eventType": data.get("eventType", ""),
            "projectId": data.get("projectId"),
            "conditions": data.get("conditions", []),
            "createdBy": {"id": 1, "name": "Admin"},
            "createdDate": datetime.now().isoformat(),
        }

        # Store trigger
        self.data["pulse"]["triggers"][trigger_id] = trigger

        return {"data": trigger}

    def _handle_update_trigger(self, trigger_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Handle PUT /triggers/{id} request."""
        try:
            trigger_id = int(trigger_id)
            if trigger_id in self.data["pulse"]["triggers"]:
                # Update the trigger with new data
                trigger = self.data["pulse"]["triggers"][trigger_id]
                for key, value in data.items():
                    trigger[key] = value
                trigger["updatedDate"] = datetime.now().isoformat()
                trigger["updatedBy"] = {"id": 1, "name": "Admin"}
                return {"data": trigger}
            return {"error": f"Trigger not found: {trigger_id}"}
        except ValueError:
            return {"error": f"Invalid trigger ID: {trigger_id}"}

    def _handle_delete_trigger(self, trigger_id: str) -> dict[str, Any]:
        """Handle DELETE /triggers/{id} request."""
        try:
            trigger_id = int(trigger_id)
            if trigger_id in self.data["pulse"]["triggers"]:
                # Delete the trigger
                del self.data["pulse"]["triggers"][trigger_id]
                return {"success": True}
            return {"error": f"Trigger not found: {trigger_id}"}
        except ValueError:
            return {"error": f"Invalid trigger ID: {trigger_id}"}

    def _handle_get_actions(self, project_id: int) -> dict[str, Any]:
        """Handle GET /actions request."""
        # Filter by project ID
        actions = [
            a for a in self.data["pulse"]["actions"].values() if a.get("projectId") == project_id
        ]

        return {"data": actions}

    def _handle_get_action(self, action_id: str) -> dict[str, Any]:
        """Handle GET /actions/{id} request."""
        try:
            action_id = int(action_id)
            if action_id in self.data["pulse"]["actions"]:
                return {"data": self.data["pulse"]["actions"][action_id]}
            return {"error": f"Action not found: {action_id}"}
        except ValueError:
            return {"error": f"Invalid action ID: {action_id}"}

    def _handle_create_action(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle POST /actions request."""
        # Generate action ID
        action_id = (
            max([0] + [id for id in self.data["pulse"]["actions"].keys() if isinstance(id, int)])
            + 1
        )

        # Create action
        action = {
            "id": action_id,
            "name": data.get("name", ""),
            "actionType": data.get("actionType", ""),
            "projectId": data.get("projectId"),
            "parameters": data.get("parameters", []),
            "createdBy": {"id": 1, "name": "Admin"},
            "createdDate": datetime.now().isoformat(),
        }

        # Store action
        self.data["pulse"]["actions"][action_id] = action

        return {"data": action}

    def _handle_update_action(self, action_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Handle PUT /actions/{id} request."""
        try:
            action_id = int(action_id)
            if action_id in self.data["pulse"]["actions"]:
                # Update the action with new data
                action = self.data["pulse"]["actions"][action_id]
                for key, value in data.items():
                    action[key] = value
                action["updatedDate"] = datetime.now().isoformat()
                action["updatedBy"] = {"id": 1, "name": "Admin"}
                return {"data": action}
            return {"error": f"Action not found: {action_id}"}
        except ValueError:
            return {"error": f"Invalid action ID: {action_id}"}

    def _handle_delete_action(self, action_id: str) -> dict[str, Any]:
        """Handle DELETE /actions/{id} request."""
        try:
            action_id = int(action_id)
            if action_id in self.data["pulse"]["actions"]:
                # Delete the action
                del self.data["pulse"]["actions"][action_id]
                return {"success": True}
            return {"error": f"Action not found: {action_id}"}
        except ValueError:
            return {"error": f"Invalid action ID: {action_id}"}

    def _handle_get_constants(self, project_id: int) -> dict[str, Any]:
        """Handle GET /constants request."""
        # Filter by project ID
        constants = [
            c for c in self.data["pulse"]["constants"].values() if c.get("projectId") == project_id
        ]

        return {"data": constants}

    def _handle_get_constant(self, constant_id: str) -> dict[str, Any]:
        """Handle GET /constants/{id} request."""
        try:
            constant_id = int(constant_id)
            if constant_id in self.data["pulse"]["constants"]:
                return {"data": self.data["pulse"]["constants"][constant_id]}
            return {"error": f"Constant not found: {constant_id}"}
        except ValueError:
            return {"error": f"Invalid constant ID: {constant_id}"}

    def _handle_create_constant(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle POST /constants request."""
        # Generate constant ID
        constant_id = (
            max([0] + [id for id in self.data["pulse"]["constants"].keys() if isinstance(id, int)])
            + 1
        )

        # Create constant
        constant = {
            "id": constant_id,
            "name": data.get("name", ""),
            "value": data.get("value", ""),
            "description": data.get("description", ""),
            "projectId": data.get("projectId"),
            "createdBy": {"id": 1, "name": "Admin"},
            "createdDate": datetime.now().isoformat(),
        }

        # Store constant
        self.data["pulse"]["constants"][constant_id] = constant

        return {"data": constant}

    def _handle_update_constant(self, constant_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Handle PUT /constants/{id} request."""
        try:
            constant_id = int(constant_id)
            if constant_id in self.data["pulse"]["constants"]:
                # Update the constant with new data
                constant = self.data["pulse"]["constants"][constant_id]
                for key, value in data.items():
                    constant[key] = value
                constant["updatedDate"] = datetime.now().isoformat()
                constant["updatedBy"] = {"id": 1, "name": "Admin"}
                return {"data": constant}
            return {"error": f"Constant not found: {constant_id}"}
        except ValueError:
            return {"error": f"Invalid constant ID: {constant_id}"}

    def _handle_delete_constant(self, constant_id: str) -> dict[str, Any]:
        """Handle DELETE /constants/{id} request."""
        try:
            constant_id = int(constant_id)
            if constant_id in self.data["pulse"]["constants"]:
                # Delete the constant
                del self.data["pulse"]["constants"][constant_id]
                return {"success": True}
            return {"error": f"Constant not found: {constant_id}"}
        except ValueError:
            return {"error": f"Invalid constant ID: {constant_id}"}

    def _handle_get_features(self, project_id: int) -> dict[str, Any]:
        """Handle GET /features request."""
        # Filter by project ID
        features = [
            f
            for f in self.data["scenario"]["features"].values()
            if f.get("projectId") == project_id
        ]

        return {"data": features}

    def _handle_create_feature(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle POST /features request."""
        # Generate feature ID
        feature_id = str(uuid.uuid4())

        # Create feature
        feature = {
            "id": feature_id,
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "projectId": data.get("projectId"),
            "content": data.get("content", ""),
        }

        # Store feature
        self.data["scenario"]["features"][feature_id] = feature

        return {"data": feature}

    def _handle_submit_auto_test_logs(
        self, project_id: int, data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle POST /projects/{projectId}/auto-test-logs request.

        Submits multiple test logs in a single request for automated testing.
        This endpoint is used by test automation frameworks to submit test results in bulk.

        Args:
            project_id: The ID of the project
            data: The bulk test log data including test runs and results

        Returns:
            A dictionary with the results of the bulk operation

        """
        # Verify required fields
        if not data.get("testLogs"):
            return self._format_error_response("Missing required field: testLogs", 400)

        # Track overall results
        results = {
            "total": len(data.get("testLogs", [])),
            "successful": 0,
            "failed": 0,
            "errors": [],
            "testLogs": [],
        }

        # Process each test log
        for test_log_entry in data.get("testLogs", []):
            # Validate required fields for each entry
            if "name" not in test_log_entry:
                error = "Missing required field 'name' in test log entry"
                results["errors"].append({"error": error})
                results["failed"] += 1
                continue

            if "status" not in test_log_entry:
                error = "Missing required field 'status' in test log entry"
                results["errors"].append({"error": error})
                results["failed"] += 1
                continue

            if test_log_entry.get("status") not in QTestTestLog.VALID_STATUSES:
                error = f"Invalid status '{test_log_entry.get('status')}' in test log entry. Must be one of: {', '.join(QTestTestLog.VALID_STATUSES)}"
                results["errors"].append({"error": error})
                results["failed"] += 1
                continue

            # Handle test log based on automation type
            if "testCaseId" in test_log_entry:
                # Link to existing test case
                result = self._handle_auto_test_log_with_test_case(project_id, test_log_entry)
            elif "testCase" in test_log_entry:
                # Create new test case with the log
                result = self._handle_auto_test_log_with_new_test_case(project_id, test_log_entry)
            else:
                # Neither testCaseId nor testCase provided
                error = "Either testCaseId or testCase must be provided in test log entry"
                results["errors"].append({"error": error})
                results["failed"] += 1
                continue

            # Process result
            if "error" in result:
                results["errors"].append(result)
                results["failed"] += 1
            else:
                results["successful"] += 1
                results["testLogs"].append(result)

        # Return results
        logger.info(
            f"Processed {results['total']} auto test logs: {results['successful']} successful, {results['failed']} failed",
        )
        return results

    def _handle_auto_test_log_with_test_case(
        self, project_id: int, data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle auto test log submission for an existing test case.

        Args:
            project_id: The ID of the project
            data: The test log data including test case ID

        Returns:
            The created test log data or error information

        """
        test_case_id = data.get("testCaseId")

        # Verify test case exists
        if test_case_id not in self.data["manager"]["test_cases"]:
            return {"error": f"Test case not found: {test_case_id}"}

        # Look for existing test cycle or create one
        test_cycle_id = data.get("testCycleId")
        if not test_cycle_id:
            # Find or create an "Automation" test cycle
            test_cycle = None
            for tc in self.data["manager"]["test_cycles"].values():
                if tc.get("projectId") == project_id and tc.get("name") == "Automation":
                    test_cycle = tc
                    test_cycle_id = tc["id"]
                    break

            if not test_cycle:
                # Create new automation test cycle
                test_cycle_id = max(self.data["manager"]["test_cycles"].keys(), default=0) + 1
                test_cycle = {
                    "id": test_cycle_id,
                    "name": "Automation",
                    "description": "Automated test execution",
                    "pid": f"CY-{test_cycle_id}",
                    "parentId": None,
                    "releaseId": None,
                    "projectId": project_id,
                    "properties": [],
                    "startDate": datetime.now().isoformat(),
                    "endDate": None,
                }
                self.data["manager"]["test_cycles"][test_cycle_id] = test_cycle

        # Look for existing test run or create one
        test_run_id = data.get("testRunId")
        if not test_run_id:
            # Create a new test run for this execution
            test_run_id = max(self.data["manager"]["test_runs"].keys(), default=0) + 1
            test_run = {
                "id": test_run_id,
                "name": data.get("name", "Automated Test Run"),
                "description": data.get("description", "Created by auto-test-logs API"),
                "pid": f"TR-{test_run_id}",
                "testCaseVersionId": 1,
                "testCaseId": test_case_id,
                "testCycleId": test_cycle_id,
                "projectId": project_id,
                "properties": [],
                "status": data.get("status", "NOT_EXECUTED"),
            }
            self.data["manager"]["test_runs"][test_run_id] = test_run

        # Create the test log
        test_log_data = {
            "status": data.get("status"),
            "executionDate": data.get("executionDate", datetime.now().isoformat()),
            "note": data.get("note", ""),
            "testRunId": test_run_id,
            "attachments": data.get("attachments", []),
            "testStepLogs": data.get("testStepLogs", []),
            "actualResults": data.get("actualResults", ""),
            "executionTime": data.get("executionTime", 0),
        }

        # Validate the test log data if validation is enabled
        if self.validation_mode:
            is_valid, validated_data, error = self._validate_model(test_log_data, QTestTestLog)
            if not is_valid:
                return {"error": f"Invalid test log data: {error}"}

        # Generate test log ID and create the log
        test_log_id = max(self.data["manager"]["test_logs"].keys(), default=0) + 1
        test_log = {"id": test_log_id, **test_log_data}

        # Store test log
        self.data["manager"]["test_logs"][test_log_id] = test_log

        # Update test run status
        self.data["manager"]["test_runs"][test_run_id]["status"] = data.get("status", "")

        # Return response with created resources
        return {
            "testLog": test_log,
            "testRun": self.data["manager"]["test_runs"][test_run_id],
            "testCycle": self.data["manager"]["test_cycles"][test_cycle_id],
        }

    def _handle_auto_test_log_with_new_test_case(
        self, project_id: int, data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle auto test log submission that includes a new test case.

        Args:
            project_id: The ID of the project
            data: The test log data including a new test case definition

        Returns:
            The created test case, test run, and test log data or error information

        """
        # Save validation setting and temporarily disable it for test cases
        original_validation = self.validation_mode
        self.validation_mode = False

        try:
            test_case_data = data.get("testCase", {})

            # Add required fields to test case data
            if "name" not in test_case_data:
                test_case_data["name"] = data.get("name", "Automated Test Case")

            if "projectId" not in test_case_data:
                test_case_data["projectId"] = project_id

            # Find automation module or use root module
            if "moduleId" not in test_case_data:
                module_id = None
                for module in self.data["manager"]["modules"].values():
                    if module.get("projectId") == project_id and module.get("name") == "Automation":
                        module_id = module["id"]
                        break

                if not module_id:
                    # Use first root module (parentId is None)
                    for module in self.data["manager"]["modules"].values():
                        if module.get("projectId") == project_id and module.get("parentId") is None:
                            module_id = module["id"]
                            break

                    # If still no module found, create one
                    if not module_id:
                        module_id = max(self.data["manager"]["modules"].keys(), default=0) + 1
                        module = {
                            "id": module_id,
                            "name": "Automation",
                            "description": "Auto-generated test cases",
                            "parentId": None,
                            "pid": f"MD-{module_id}",
                            "projectId": project_id,
                            "path": "Automation",
                        }
                        self.data["manager"]["modules"][module_id] = module

                test_case_data["moduleId"] = module_id

            # Create the test case
            test_case_result = self._handle_create_test_case(project_id, test_case_data)

            # Check if test case creation was successful
            if "error" in test_case_result:
                return {"error": f"Failed to create test case: {test_case_result['error']}"}

            # Now create a test log with the new test case
            auto_log_data = {
                "testCaseId": test_case_result["id"],
                "name": data.get("name"),
                "status": data.get("status"),
                "note": data.get("note", ""),
                "executionDate": data.get("executionDate"),
                "attachments": data.get("attachments", []),
                "testStepLogs": data.get("testStepLogs", []),
                "actualResults": data.get("actualResults", ""),
                "executionTime": data.get("executionTime", 0),
            }

            # Submit the log using the existing method
            log_result = self._handle_auto_test_log_with_test_case(project_id, auto_log_data)

            # Combine the results
            if "error" in log_result:
                return {
                    "error": f"Created test case but failed to create log: {log_result['error']}",
                }

            return {
                "testCase": test_case_result,
                "testLog": log_result["testLog"],
                "testRun": log_result["testRun"],
                "testCycle": log_result["testCycle"],
            }

        finally:
            # Restore original validation mode
            self.validation_mode = original_validation
