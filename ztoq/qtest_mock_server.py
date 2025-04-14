"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Mock server for qTest API testing.

This module provides a mock server that simulates the qTest APIs for testing.
"""

import json
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

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

        # Initialize with sample data
        self._initialize_sample_data()

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
                    {"id": 1, "name": "Automation Status", "type": "STRING", "value": "Automated"}
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
                    }
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
                    {"id": 1, "name": "Automation Status", "type": "STRING", "value": "Automated"}
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
                    {"id": 1, "name": "Automation Status", "type": "STRING", "value": "Automated"}
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
            }
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
        rules = [
            {
                "id": str(uuid.uuid4()),
                "name": "JIRA Integration Rule",
                "description": "Update JIRA when test fails",
                "projectId": project_id,
                "enabled": True,
                "conditions": [{"field": "status", "operator": "equals", "value": "FAIL"}],
                "actions": [
                    {
                        "type": "jira",
                        "configuration": {
                            "issueType": "Bug",
                            "summary": "Test Failed: {{testCase.name}}",
                            "description": "Test execution failed: {{testLog.note}}",
                        },
                    }
                ],
            }
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
            }
        ]

        for feature in features:
            self.data["scenario"]["features"][feature["id"]] = feature

    # API route handlers
    def handle_request(
        self,
        api_type: str,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle a request to the mock server."""
        logger.debug(f"Mock server handling {method} {endpoint} to {api_type} API")
        logger.debug(f"Params: {params}")
        logger.debug(f"Data: {data}")

        # Handle authentication
        if endpoint.endswith("/token") or endpoint.endswith("/token-login"):
            return self._handle_auth(api_type)

        # Handle API-specific endpoints based on the path
        if api_type == "manager":
            return self._handle_manager_request(method, endpoint, params, data, files)
        elif api_type == "parameters":
            return self._handle_parameters_request(method, endpoint, params, data)
        elif api_type == "pulse":
            return self._handle_pulse_request(method, endpoint, params, data)
        elif api_type == "scenario":
            return self._handle_scenario_request(method, endpoint, params, data)
        else:
            return {"error": f"Unknown API type: {api_type}"}

    def _handle_auth(self, api_type: str) -> Dict[str, Any]:
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
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle qTest Manager API requests."""
        params = params or {}
        data = data or {}

        # Extract project ID from path if present
        project_id = self._extract_project_id(endpoint)

        # Projects endpoints
        if endpoint.endswith("/projects") and method == "GET":
            return self._handle_get_projects(params)

        # Test cases endpoints
        elif "/test-cases" in endpoint:
            if method == "GET":
                if "/test-cases/" in endpoint and not endpoint.endswith("/test-cases"):
                    # Get single test case
                    test_case_id = int(endpoint.split("/test-cases/")[1].split("/")[0])
                    return self._handle_get_test_case(test_case_id)
                else:
                    # Get multiple test cases
                    return self._handle_get_test_cases(project_id, params)
            elif method == "POST" and endpoint.endswith("/test-cases"):
                # Create test case
                return self._handle_create_test_case(project_id, data)

        # Test cycles endpoints
        elif "/test-cycles" in endpoint:
            if method == "GET":
                if "/test-cycles/" in endpoint and not endpoint.endswith("/test-cycles"):
                    # Get single test cycle
                    test_cycle_id = int(endpoint.split("/test-cycles/")[1].split("/")[0])
                    return self._handle_get_test_cycle(test_cycle_id)
                else:
                    # Get multiple test cycles
                    return self._handle_get_test_cycles(project_id, params)
            elif method == "POST" and endpoint.endswith("/test-cycles"):
                # Create test cycle
                return self._handle_create_test_cycle(project_id, data)

        # Test runs endpoints
        elif "/test-runs" in endpoint:
            if "/test-runs/" in endpoint and "/test-logs" in endpoint:
                test_run_id = int(endpoint.split("/test-runs/")[1].split("/")[0])
                if method == "POST":
                    # Submit test log
                    return self._handle_submit_test_log(test_run_id, data)
                elif method == "GET":
                    # Get test logs
                    return self._handle_get_test_logs(test_run_id)

        # Modules endpoints
        elif "/modules" in endpoint:
            if method == "GET":
                if "/modules/" in endpoint and not endpoint.endswith("/modules"):
                    # Get single module
                    module_id = int(endpoint.split("/modules/")[1].split("/")[0])
                    return self._handle_get_module(module_id)
                else:
                    # Get multiple modules
                    return self._handle_get_modules(project_id, params)
            elif method == "POST" and endpoint.endswith("/modules"):
                # Create module
                return self._handle_create_module(project_id, data)

        # Attachment endpoints
        elif "/blob-handles" in endpoint:
            if method == "POST":
                # Upload attachment
                object_type = endpoint.split(f"/projects/{project_id}/")[1].split("/")[0]
                object_id = int(endpoint.split(f"/{object_type}/")[1].split("/")[0])
                return self._handle_upload_attachment(project_id, object_type, object_id, files)

        # Default response for unimplemented endpoints
        return {"error": f"Unimplemented endpoint: {method} {endpoint}"}

    def _handle_parameters_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle qTest Parameters API requests."""
        params = params or {}
        data = data or {}
        project_id = data.get("projectId")

        # Parameters endpoints
        if "/parameters/" in endpoint:
            if endpoint.endswith("/parameters/query") and method == "POST":
                return self._handle_query_parameters(project_id, data)
            elif endpoint.endswith("/parameters/create") and method == "POST":
                return self._handle_create_parameter(data)
            elif "/parameters/" in endpoint and "/values" in endpoint:
                parameter_id = int(endpoint.split("/parameters/")[1].split("/")[0])
                if method == "POST" and endpoint.endswith("/values"):
                    # Create parameter value
                    return self._handle_create_parameter_value(parameter_id, data)
                elif method == "POST" and endpoint.endswith("/values/query"):
                    # Query parameter values
                    return self._handle_query_parameter_values(parameter_id, data)
            elif "/parameters/" in endpoint and not "/values" in endpoint:
                parameter_id = int(endpoint.split("/parameters/")[1])
                if method == "GET":
                    # Get parameter
                    return self._handle_get_parameter(parameter_id)

        # Datasets endpoints
        elif "/data-sets/" in endpoint:
            if endpoint.endswith("/data-sets/query") and method == "POST":
                return self._handle_query_datasets(project_id, data)
            elif endpoint.endswith("/data-sets/create") and method == "POST":
                return self._handle_create_dataset(data)
            elif "/data-sets/" in endpoint and "/rows" in endpoint:
                dataset_id = int(endpoint.split("/data-sets/")[1].split("/")[0])
                if method == "POST" and endpoint.endswith("/rows"):
                    # Create dataset row
                    return self._handle_create_dataset_row(dataset_id, data)
                elif method == "GET" and endpoint.endswith("/rows"):
                    # Get dataset rows
                    return self._handle_get_dataset_rows(dataset_id)
            elif "/data-sets/" in endpoint and not "/rows" in endpoint:
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
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle qTest Pulse API requests."""
        params = params or {}
        data = data or {}
        project_id = params.get("projectId") or data.get("projectId")

        # Rules endpoints
        if endpoint.startswith("/rules"):
            if method == "GET" and endpoint == "/rules":
                return self._handle_get_rules(project_id)
            elif method == "POST" and endpoint == "/rules":
                return self._handle_create_rule(data)
            elif "/rules/" in endpoint:
                rule_id = endpoint.split("/rules/")[1]
                if method == "GET":
                    return self._handle_get_rule(rule_id)

        # Default response for unimplemented endpoints
        return {"error": f"Unimplemented endpoint: {method} {endpoint}"}

    def _handle_scenario_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle qTest Scenario API requests."""
        params = params or {}
        data = data or {}
        project_id = params.get("projectId") or data.get("projectId")

        # Features endpoints
        if endpoint.startswith("/features"):
            if method == "GET" and endpoint == "/features":
                return self._handle_get_features(project_id)
            elif method == "POST" and endpoint == "/features":
                return self._handle_create_feature(data)

        # Default response for unimplemented endpoints
        return {"error": f"Unimplemented endpoint: {method} {endpoint}"}

    # Helper methods for extracting path components
    def _extract_project_id(self, endpoint: str) -> Optional[int]:
        """Extract project ID from endpoint path."""
        if "/projects/" in endpoint:
            parts = endpoint.split("/projects/")[1].split("/")
            if len(parts) > 0 and parts[0].isdigit():
                return int(parts[0])
        return None

    # Handler methods for specific endpoints
    def _handle_get_projects(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_get_test_cases(self, project_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_get_test_case(self, test_case_id: int) -> Dict[str, Any]:
        """Handle GET /projects/{projectId}/test-cases/{testCaseId} request."""
        if test_case_id in self.data["manager"]["test_cases"]:
            return self.data["manager"]["test_cases"][test_case_id]
        else:
            return {"error": f"Test case not found: {test_case_id}"}

    def _handle_create_test_case(self, project_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle POST /projects/{projectId}/test-cases request."""
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
                    "order": i + 1,
                    "testCaseId": test_case_id,
                }
                self.data["manager"]["test_steps"][step_id] = step
                test_case["steps"].append(step)

        # Store test case
        self.data["manager"]["test_cases"][test_case_id] = test_case

        return test_case

    def _handle_get_modules(self, project_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_get_module(self, module_id: int) -> Dict[str, Any]:
        """Handle GET /projects/{projectId}/modules/{moduleId} request."""
        if module_id in self.data["manager"]["modules"]:
            return self.data["manager"]["modules"][module_id]
        else:
            return {"error": f"Module not found: {module_id}"}

    def _handle_create_module(self, project_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_get_test_cycles(self, project_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_get_test_cycle(self, test_cycle_id: int) -> Dict[str, Any]:
        """Handle GET /projects/{projectId}/test-cycles/{testCycleId} request."""
        if test_cycle_id in self.data["manager"]["test_cycles"]:
            return self.data["manager"]["test_cycles"][test_cycle_id]
        else:
            return {"error": f"Test cycle not found: {test_cycle_id}"}

    def _handle_create_test_cycle(self, project_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_submit_test_log(self, test_run_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle POST /projects/{projectId}/test-runs/{testRunId}/test-logs request."""
        # Verify test run exists
        if test_run_id not in self.data["manager"]["test_runs"]:
            return {"error": f"Test run not found: {test_run_id}"}

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
        }

        # Store test log
        self.data["manager"]["test_logs"][test_log_id] = test_log

        # Update test run status
        self.data["manager"]["test_runs"][test_run_id]["status"] = data.get("status", "")

        return test_log

    def _handle_get_test_logs(self, test_run_id: int) -> Dict[str, Any]:
        """Handle GET /projects/{projectId}/test-runs/{testRunId}/test-logs request."""
        # Filter test logs by test run ID
        test_logs = [
            tl
            for tl in self.data["manager"]["test_logs"].values()
            if tl.get("testRunId") == test_run_id
        ]

        return {"items": test_logs, "total": len(test_logs)}

    def _handle_upload_attachment(
        self, project_id: int, object_type: str, object_id: int, files: Dict[str, Any]
    ) -> Dict[str, Any]:
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

    def _handle_query_parameters(self, project_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_create_parameter(self, data: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_get_parameter(self, parameter_id: int) -> Dict[str, Any]:
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
        else:
            return {"status": "ERROR", "message": f"Parameter not found: {parameter_id}"}

    def _handle_create_parameter_value(
        self, parameter_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        self, parameter_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
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

    def _handle_query_datasets(self, project_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_create_dataset(self, data: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_get_dataset(self, dataset_id: int) -> Dict[str, Any]:
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
        else:
            return {"status": "ERROR", "message": f"Dataset not found: {dataset_id}"}

    def _handle_create_dataset_row(self, dataset_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_get_dataset_rows(self, dataset_id: int) -> Dict[str, Any]:
        """Handle GET /data-sets/{dsId}/rows request."""
        # Filter rows by dataset ID
        rows = [
            r
            for r in self.data["parameters"]["dataset_rows"].values()
            if r.get("datasetId") == dataset_id
        ]

        return {"status": "SUCCESS", "data": rows}

    def _handle_get_rules(self, project_id: int) -> Dict[str, Any]:
        """Handle GET /rules request."""
        # Filter by project ID
        rules = [
            r for r in self.data["pulse"]["rules"].values() if r.get("projectId") == project_id
        ]

        return {"data": rules}

    def _handle_create_rule(self, data: Dict[str, Any]) -> Dict[str, Any]:
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

    def _handle_get_rule(self, rule_id: str) -> Dict[str, Any]:
        """Handle GET /rules/{id} request."""
        if rule_id in self.data["pulse"]["rules"]:
            return {"data": self.data["pulse"]["rules"][rule_id]}
        else:
            return {"error": f"Rule not found: {rule_id}"}

    def _handle_get_features(self, project_id: int) -> Dict[str, Any]:
        """Handle GET /features request."""
        # Filter by project ID
        features = [
            f
            for f in self.data["scenario"]["features"].values()
            if f.get("projectId") == project_id
        ]

        return {"data": features}

    def _handle_create_feature(self, data: Dict[str, Any]) -> Dict[str, Any]:
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
