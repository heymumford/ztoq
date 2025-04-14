"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Mock server for Zephyr Scale API testing.

This module provides a mock server that simulates the Zephyr Scale API for testing.
The mock server supports the main Zephyr API endpoints including projects, test cases,
test cycles, folders, and executions.
"""

import copy
import json
import logging
import random
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import ValidationError

from ztoq.models import (
    Attachment,
    Case,
    CaseStep,
    CustomField,
    CycleInfo,
    Environment,
    Execution,
    Folder,
    Link,
    Plan,
    PaginatedResponse,
    Priority,
    Project,
    Status,
    ZephyrConfig
)

from ztoq.zephyr_mock_factory import (
    AttachmentFactory,
    CaseFactory,
    CaseStepFactory,
    CustomFieldFactory,
    CycleInfoFactory,
    EnvironmentFactory,
    ExecutionFactory,
    FolderFactory,
    LinkFactory,
    PaginatedResponseFactory,
    PlanFactory,
    PriorityFactory,
    ProjectFactory,
    StatusFactory
)

logger = logging.getLogger("ztoq.zephyr_mock_server")


class ZephyrMockServer:
    """Mock server for Zephyr Scale API."""

    def __init__(self):
        """Initialize the mock server with empty data stores."""
        # Initialize the data stores
        self.data = {
            "projects": {},
            "folders": {},
            "test_cases": {},
            "test_cycles": {},
            "test_plans": {},
            "test_executions": {},
            "attachments": {},
            "statuses": {},
            "priorities": {},
            "environments": {},
            "custom_fields": {},
        }

        # Track request history for debugging
        self.request_history = []

        # API response configuration
        self.error_rate = 0.0  # Percentage of requests that should fail with errors
        self.response_delay = 0.0  # Delay in seconds before responding
        self.validation_mode = True  # Whether to validate request data against models

        # Authentication tokens
        self.valid_tokens = []

        # Initialize with sample data
        self._initialize_sample_data()

    def _validate_model(self, data: dict, model_class, exclude_none: bool = True) -> Tuple[bool, Optional[dict], Optional[str]]:
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
            # For create operations, if id is not provided, generate one
            if "id" not in data and hasattr(model_class, "id"):
                data["id"] = str(random.randint(10000, 99999))

            # Create model instance and validate
            model = model_class(**data)

            # Convert to dict for response
            validated_data = model.model_dump(exclude_none=exclude_none)

            return True, validated_data, None
        except ValidationError as e:
            logger.warning(f"Validation error: {str(e)}")
            return False, None, str(e)
        except Exception as e:
            logger.error(f"Unexpected error during validation: {str(e)}")
            return False, None, f"Internal server error: {str(e)}"

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
                "timestamp": datetime.now().isoformat()
            }
        }

    def _initialize_sample_data(self):
        """Initialize the server with sample data."""
        # Create sample projects
        for i in range(1, 4):
            project = ProjectFactory.create(
                id=str(i),
                key=f"PROJ{i}",
                name=f"Project {i}",
                description=f"Description for Project {i}"
            ).model_dump()
            self.data["projects"][project["id"]] = project

        # Create sample statuses
        status_types = ["TEST_CASE", "TEST_CYCLE", "TEST_EXECUTION"]
        status_names = {
            "TEST_CASE": ["Active", "Draft", "Deprecated"],
            "TEST_CYCLE": ["Active", "Draft", "Completed"],
            "TEST_EXECUTION": ["Passed", "Failed", "Blocked", "Not Run"]
        }

        status_id = 1
        for status_type in status_types:
            for status_name in status_names[status_type]:
                status = StatusFactory.create(
                    id=str(status_id),
                    name=status_name,
                    type=status_type,
                    description=f"{status_name} status for {status_type}"
                ).model_dump()
                self.data["statuses"][status["id"]] = status
                status_id += 1

        # Create sample priorities
        priority_names = ["High", "Medium", "Low"]
        for i, name in enumerate(priority_names, 1):
            priority = PriorityFactory.create(
                id=str(i),
                name=name,
                rank=i,
                description=f"{name} priority"
            ).model_dump()
            self.data["priorities"][priority["id"]] = priority

        # Create sample environments
        env_names = ["Development", "Testing", "Production"]
        for i, name in enumerate(env_names, 1):
            env = EnvironmentFactory.create(
                id=str(i),
                name=name,
                description=f"{name} environment"
            ).model_dump()
            self.data["environments"][env["id"]] = env

        # Create sample folders for each project
        for project_id, project in self.data["projects"].items():
            project_key = project["key"]

            # Create root folders
            root_folders = {
                "TEST_CASE": FolderFactory.create(
                    id=f"{project_id}01",
                    name="Test Cases Root",
                    folder_type="TEST_CASE",
                    project_key=project_key
                ).model_dump(),
                "TEST_CYCLE": FolderFactory.create(
                    id=f"{project_id}02",
                    name="Test Cycles Root",
                    folder_type="TEST_CYCLE",
                    project_key=project_key
                ).model_dump()
            }

            for folder in root_folders.values():
                self.data["folders"][folder["id"]] = folder

            # Create subfolders
            subfolder_names = ["UI Tests", "API Tests", "Performance Tests"]
            for i, name in enumerate(subfolder_names, 1):
                # Test case subfolders
                tc_folder = FolderFactory.create(
                    id=f"{project_id}1{i}",
                    name=name,
                    folder_type="TEST_CASE",
                    parent_id=root_folders["TEST_CASE"]["id"],
                    project_key=project_key
                ).model_dump()
                self.data["folders"][tc_folder["id"]] = tc_folder

                # Test cycle subfolders
                cycle_folder = FolderFactory.create(
                    id=f"{project_id}2{i}",
                    name=name,
                    folder_type="TEST_CYCLE",
                    parent_id=root_folders["TEST_CYCLE"]["id"],
                    project_key=project_key
                ).model_dump()
                self.data["folders"][cycle_folder["id"]] = cycle_folder

            # Create sample test cases for each project
            self._add_sample_test_cases(project_id, project_key)

            # Create sample test cycles for each project
            self._add_sample_test_cycles(project_id, project_key)

            # Create sample test executions for each project
            self._add_sample_test_executions(project_id, project_key)

    def _add_sample_test_cases(self, project_id: str, project_key: str):
        """Add sample test cases for a project."""
        # Find folders for this project
        project_folders = [f for f in self.data["folders"].values()
                          if f["project_key"] == project_key and f["folder_type"] == "TEST_CASE"]

        # Create test cases in each folder
        test_case_count = 1
        for folder in project_folders:
            folder_id = folder["id"]
            # Skip root folders
            if folder["name"] == "Test Cases Root":
                continue

            # Create 2-3 test cases per folder
            for i in range(1, random.randint(3, 4)):
                test_case = CaseFactory.create_with_steps(
                    id=f"{project_id}{test_case_count}",
                    key=f"{project_key}-T{test_case_count}",
                    name=f"{folder['name']} Test Case {i}",
                    folder=folder_id,
                    folder_name=folder["name"],
                    project_key=project_key,
                    priority=PriorityFactory.create(
                        id=str(random.randint(1, 3)),
                        name=random.choice(["High", "Medium", "Low"])
                    ),
                    status=random.choice(["Active", "Draft", "Deprecated"]),
                    step_count=random.randint(2, 5)
                ).model_dump()

                self.data["test_cases"][test_case["id"]] = test_case
                test_case_count += 1

    def _add_sample_test_cycles(self, project_id: str, project_key: str):
        """Add sample test cycles for a project."""
        # Find folders for this project
        project_folders = [f for f in self.data["folders"].values()
                          if f["project_key"] == project_key and f["folder_type"] == "TEST_CYCLE"]

        # Create test cycles in each folder
        test_cycle_count = 1
        for folder in project_folders:
            folder_id = folder["id"]
            # Skip root folders
            if folder["name"] == "Test Cycles Root":
                continue

            # Create 1-2 test cycles per folder
            for i in range(1, random.randint(2, 3)):
                test_cycle = CycleInfoFactory.create(
                    id=f"{project_id}{test_cycle_count}",
                    key=f"{project_key}-C{test_cycle_count}",
                    name=f"{folder['name']} Test Cycle {i}",
                    folder=folder_id,
                    folder_name=folder["name"],
                    project_key=project_key,
                    status=random.choice(["Active", "Draft", "Completed"]),
                ).model_dump()

                self.data["test_cycles"][test_cycle["id"]] = test_cycle
                test_cycle_count += 1

    def _add_sample_test_executions(self, project_id: str, project_key: str):
        """Add sample test executions for a project."""
        # Get test cases and test cycles for this project
        project_test_cases = [tc for tc in self.data["test_cases"].values()
                             if tc["key"].startswith(f"{project_key}-")]
        project_test_cycles = [tc for tc in self.data["test_cycles"].values()
                              if tc["project_key"] == project_key]

        if not project_test_cases or not project_test_cycles:
            return

        # Create test executions
        execution_count = 1
        for test_cycle in project_test_cycles:
            # Assign 2-3 random test cases to each cycle
            for i in range(random.randint(2, 3)):
                if not project_test_cases:
                    break

                test_case = random.choice(project_test_cases)

                execution = ExecutionFactory.create(
                    id=f"{project_id}{execution_count}",
                    test_case_key=test_case["key"],
                    cycle_id=test_cycle["id"],
                    cycle_name=test_cycle["name"],
                    status=random.choice(["Passed", "Failed", "Blocked", "Not Run"]),
                    environment=random.choice(["1", "2", "3"]),
                    environment_name=random.choice(["Development", "Testing", "Production"])
                ).model_dump()

                self.data["test_executions"][execution["id"]] = execution
                execution_count += 1

    def _generate_token(self) -> str:
        """Generate a new authentication token."""
        token = f"zephyr-token-{random.randint(10000, 99999)}"
        self.valid_tokens.append(token)
        return token

    def _is_valid_token(self, token: str) -> bool:
        """Check if a token is valid."""
        return token in self.valid_tokens

    def handle_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None,
                      data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None,
                      files: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle a mock API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            headers: Request headers
            files: File uploads

        Returns:
            API response data
        """
        # Set defaults
        if params is None:
            params = {}
        if data is None:
            data = {}
        if headers is None:
            headers = {}

        # Simulate API delay
        if self.response_delay > 0:
            time.sleep(self.response_delay)

        # Track request
        self.request_history.append({
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "endpoint": endpoint,
            "params": params,
            "data": data,
            "headers": headers,
            "files": files is not None,
        })

        # Randomly generate errors based on error rate
        if random.random() < self.error_rate:
            error_codes = [400, 401, 403, 404, 429, 500, 503]
            error_code = random.choice(error_codes)
            error_message = f"Simulated {error_code} error"
            return self._format_error_response(error_message, error_code)

        # Special case for authentication
        if endpoint == "/authorize":
            return self._handle_auth(method, data)

        # Check authentication except for authentication endpoints
        if not endpoint.startswith("/authorize"):
            token = self._extract_token_from_headers(headers)
            if not token or not self._is_valid_token(token):
                return self._format_error_response("Unauthorized: Invalid or missing token", 401)

        # Check for attachments endpoint first since it has a special pattern
        entity_attachment_match = re.match(r"^/(\w+)s/([A-Za-z0-9\-]+)/attachments$", endpoint)
        if entity_attachment_match and (method == "GET" or method == "POST"):
            return self._handle_attachments(method, endpoint, params, data, files)

        # Route to appropriate handler based on endpoint
        if endpoint.startswith("/projects"):
            return self._handle_projects(method, endpoint, params, data)
        elif endpoint.startswith("/folders"):
            return self._handle_folders(method, endpoint, params, data)
        elif endpoint.startswith("/testcases"):
            return self._handle_test_cases(method, endpoint, params, data)
        elif endpoint.startswith("/testcycles"):
            return self._handle_test_cycles(method, endpoint, params, data)
        elif endpoint.startswith("/testplans"):
            return self._handle_test_plans(method, endpoint, params, data)
        elif endpoint.startswith("/testexecutions"):
            return self._handle_test_executions(method, endpoint, params, data)
        elif endpoint.startswith("/attachments"):
            return self._handle_attachments(method, endpoint, params, data, files)
        elif endpoint.startswith("/statuses"):
            return self._handle_statuses(method, endpoint, params, data)
        elif endpoint.startswith("/priorities"):
            return self._handle_priorities(method, endpoint, params, data)
        elif endpoint.startswith("/environments"):
            return self._handle_environments(method, endpoint, params, data)
        elif endpoint.startswith("/customfields"):
            return self._handle_custom_fields(method, endpoint, params, data)
        else:
            return self._format_error_response(f"Unsupported endpoint: {endpoint}", 404)

    def _extract_token_from_headers(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract the bearer token from request headers."""
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        return None

    def _handle_auth(self, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle authentication requests."""
        if method != "POST":
            return self._format_error_response("Method not allowed", 405)

        # For mock server, we don't validate actual credentials
        token = self._generate_token()

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 3600
        }

    def _handle_projects(self, method: str, endpoint: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle projects endpoint requests."""
        # List projects
        if endpoint == "/projects" and method == "GET":
            projects = list(self.data["projects"].values())

            # Pagination parameters
            start_at = int(params.get("startAt", 0))
            max_results = int(params.get("maxResults", 50))

            # Apply pagination
            paginated_projects = projects[start_at:start_at + max_results]

            return {
                "values": paginated_projects,
                "maxResults": max_results,
                "startAt": start_at,
                "isLast": (start_at + max_results) >= len(projects),
                "totalCount": len(projects)
            }

        # Get project by key
        project_key_match = re.match(r"^/projects/([A-Za-z0-9]+)$", endpoint)
        if project_key_match and method == "GET":
            project_key = project_key_match.group(1)
            project = next((p for p in self.data["projects"].values() if p["key"] == project_key), None)

            if project:
                return project
            else:
                return self._format_error_response(f"Project not found with key: {project_key}", 404)

        # Create project
        if endpoint == "/projects" and method == "POST":
            if not data:
                return self._format_error_response("Missing request body", 400)

            # Validate project data
            valid, validated_data, error = self._validate_model(data, Project)
            if not valid:
                return self._format_error_response(f"Invalid project data: {error}", 400)

            # Generate an ID if not provided
            if "id" not in validated_data:
                validated_data["id"] = str(len(self.data["projects"]) + 1)

            # Store the project
            self.data["projects"][validated_data["id"]] = validated_data

            return validated_data

        return self._format_error_response(f"Unsupported operation for projects: {method} {endpoint}", 400)

    def _handle_folders(self, method: str, endpoint: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle folders endpoint requests."""
        # List folders
        if endpoint == "/folders" and method == "GET":
            project_key = params.get("projectKey")
            folder_type = params.get("folderType")

            # Filter by project key and folder type if provided
            folders = self.data["folders"].values()
            if project_key:
                folders = [f for f in folders if f["project_key"] == project_key]
            if folder_type:
                folders = [f for f in folders if f["folder_type"] == folder_type]

            # Pagination parameters
            start_at = int(params.get("startAt", 0))
            max_results = int(params.get("maxResults", 50))

            # Apply pagination
            paginated_folders = list(folders)[start_at:start_at + max_results]

            return {
                "values": paginated_folders,
                "maxResults": max_results,
                "startAt": start_at,
                "isLast": (start_at + max_results) >= len(folders),
                "totalCount": len(folders)
            }

        # Get folder by ID
        folder_id_match = re.match(r"^/folders/([A-Za-z0-9]+)$", endpoint)
        if folder_id_match and method == "GET":
            folder_id = folder_id_match.group(1)

            if folder_id in self.data["folders"]:
                return self.data["folders"][folder_id]
            else:
                return self._format_error_response(f"Folder not found with ID: {folder_id}", 404)

        # Create folder
        if endpoint == "/folders" and method == "POST":
            if not data:
                return self._format_error_response("Missing request body", 400)

            # Validate folder data
            valid, validated_data, error = self._validate_model(data, Folder)
            if not valid:
                return self._format_error_response(f"Invalid folder data: {error}", 400)

            # Generate an ID if not provided
            if "id" not in validated_data:
                validated_data["id"] = str(len(self.data["folders"]) + 1)

            # Store the folder
            self.data["folders"][validated_data["id"]] = validated_data

            return validated_data

        return self._format_error_response(f"Unsupported operation for folders: {method} {endpoint}", 400)

    def _handle_test_cases(self, method: str, endpoint: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle test cases endpoint requests."""
        # List test cases
        if endpoint == "/testcases" and method == "GET":
            project_key = params.get("projectKey")

            # Filter by project key if provided
            test_cases = self.data["test_cases"].values()
            if project_key:
                test_cases = [tc for tc in test_cases if tc["key"].startswith(f"{project_key}-")]

            # Pagination parameters
            start_at = int(params.get("startAt", 0))
            max_results = int(params.get("maxResults", 50))

            # Apply pagination
            paginated_test_cases = list(test_cases)[start_at:start_at + max_results]

            return {
                "values": paginated_test_cases,
                "maxResults": max_results,
                "startAt": start_at,
                "isLast": (start_at + max_results) >= len(test_cases),
                "totalCount": len(test_cases)
            }

        # Get test case by key
        test_case_key_match = re.match(r"^/testcases/([A-Za-z0-9\-]+)$", endpoint)
        if test_case_key_match and method == "GET":
            test_case_key = test_case_key_match.group(1)
            test_case = next((tc for tc in self.data["test_cases"].values() if tc["key"] == test_case_key), None)

            if test_case:
                return test_case
            else:
                return self._format_error_response(f"Test case not found with key: {test_case_key}", 404)

        # Create test case
        if endpoint == "/testcases" and method == "POST":
            if not data:
                return self._format_error_response("Missing request body", 400)

            # Validate test case data
            valid, validated_data, error = self._validate_model(data, Case)
            if not valid:
                return self._format_error_response(f"Invalid test case data: {error}", 400)

            # Generate an ID if not provided
            if "id" not in validated_data:
                validated_data["id"] = str(len(self.data["test_cases"]) + 1)

            # Store the test case
            self.data["test_cases"][validated_data["id"]] = validated_data

            return validated_data

        return self._format_error_response(f"Unsupported operation for test cases: {method} {endpoint}", 400)

    def _handle_test_cycles(self, method: str, endpoint: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle test cycles endpoint requests."""
        # List test cycles
        if endpoint == "/testcycles" and method == "GET":
            project_key = params.get("projectKey")

            # Filter by project key if provided
            test_cycles = self.data["test_cycles"].values()
            if project_key:
                test_cycles = [tc for tc in test_cycles if tc["project_key"] == project_key]

            # Pagination parameters
            start_at = int(params.get("startAt", 0))
            max_results = int(params.get("maxResults", 50))

            # Apply pagination
            paginated_test_cycles = list(test_cycles)[start_at:start_at + max_results]

            return {
                "values": paginated_test_cycles,
                "maxResults": max_results,
                "startAt": start_at,
                "isLast": (start_at + max_results) >= len(test_cycles),
                "totalCount": len(test_cycles)
            }

        # Get test cycle by key
        test_cycle_key_match = re.match(r"^/testcycles/([A-Za-z0-9\-]+)$", endpoint)
        if test_cycle_key_match and method == "GET":
            test_cycle_key = test_cycle_key_match.group(1)
            test_cycle = next((tc for tc in self.data["test_cycles"].values() if tc["key"] == test_cycle_key), None)

            if test_cycle:
                return test_cycle
            else:
                return self._format_error_response(f"Test cycle not found with key: {test_cycle_key}", 404)

        # Create test cycle
        if endpoint == "/testcycles" and method == "POST":
            if not data:
                return self._format_error_response("Missing request body", 400)

            # Validate test cycle data
            valid, validated_data, error = self._validate_model(data, CycleInfo)
            if not valid:
                return self._format_error_response(f"Invalid test cycle data: {error}", 400)

            # Generate an ID if not provided
            if "id" not in validated_data:
                validated_data["id"] = str(len(self.data["test_cycles"]) + 1)

            # Store the test cycle
            self.data["test_cycles"][validated_data["id"]] = validated_data

            return validated_data

        return self._format_error_response(f"Unsupported operation for test cycles: {method} {endpoint}", 400)

    def _handle_test_plans(self, method: str, endpoint: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle test plans endpoint requests."""
        # List test plans
        if endpoint == "/testplans" and method == "GET":
            project_key = params.get("projectKey")

            # Filter by project key if provided
            test_plans = self.data["test_plans"].values()
            if project_key:
                test_plans = [tp for tp in test_plans if tp["project_key"] == project_key]

            # Pagination parameters
            start_at = int(params.get("startAt", 0))
            max_results = int(params.get("maxResults", 50))

            # Apply pagination
            paginated_test_plans = list(test_plans)[start_at:start_at + max_results]

            return {
                "values": paginated_test_plans,
                "maxResults": max_results,
                "startAt": start_at,
                "isLast": (start_at + max_results) >= len(test_plans),
                "totalCount": len(test_plans)
            }

        # Get test plan by key
        test_plan_key_match = re.match(r"^/testplans/([A-Za-z0-9\-]+)$", endpoint)
        if test_plan_key_match and method == "GET":
            test_plan_key = test_plan_key_match.group(1)
            test_plan = next((tp for tp in self.data["test_plans"].values() if tp["key"] == test_plan_key), None)

            if test_plan:
                return test_plan
            else:
                return self._format_error_response(f"Test plan not found with key: {test_plan_key}", 404)

        # Create test plan
        if endpoint == "/testplans" and method == "POST":
            if not data:
                return self._format_error_response("Missing request body", 400)

            # Validate test plan data
            valid, validated_data, error = self._validate_model(data, Plan)
            if not valid:
                return self._format_error_response(f"Invalid test plan data: {error}", 400)

            # Generate an ID if not provided
            if "id" not in validated_data:
                validated_data["id"] = str(len(self.data["test_plans"]) + 1)

            # Store the test plan
            self.data["test_plans"][validated_data["id"]] = validated_data

            return validated_data

        return self._format_error_response(f"Unsupported operation for test plans: {method} {endpoint}", 400)

    def _handle_test_executions(self, method: str, endpoint: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle test executions endpoint requests."""
        # List test executions
        if endpoint == "/testexecutions" and method == "GET":
            project_key = params.get("projectKey")
            cycle_id = params.get("cycleId")

            # Filter by project key and cycle ID if provided
            test_executions = self.data["test_executions"].values()
            if project_key:
                # For executions, we'd need to look up the case to get project key
                test_case_keys = [tc["key"] for tc in self.data["test_cases"].values()
                                 if tc["key"].startswith(f"{project_key}-")]
                test_executions = [te for te in test_executions if te["test_case_key"] in test_case_keys]

            if cycle_id:
                test_executions = [te for te in test_executions if te["cycle_id"] == cycle_id]

            # Pagination parameters
            start_at = int(params.get("startAt", 0))
            max_results = int(params.get("maxResults", 50))

            # Apply pagination
            paginated_test_executions = list(test_executions)[start_at:start_at + max_results]

            return {
                "values": paginated_test_executions,
                "maxResults": max_results,
                "startAt": start_at,
                "isLast": (start_at + max_results) >= len(test_executions),
                "totalCount": len(test_executions)
            }

        # Get test execution by ID
        test_execution_id_match = re.match(r"^/testexecutions/([A-Za-z0-9]+)$", endpoint)
        if test_execution_id_match and method == "GET":
            test_execution_id = test_execution_id_match.group(1)

            if test_execution_id in self.data["test_executions"]:
                return self.data["test_executions"][test_execution_id]
            else:
                return self._format_error_response(f"Test execution not found with ID: {test_execution_id}", 404)

        # Create test execution
        if endpoint == "/testexecutions" and method == "POST":
            if not data:
                return self._format_error_response("Missing request body", 400)

            # Validate test execution data
            valid, validated_data, error = self._validate_model(data, Execution)
            if not valid:
                return self._format_error_response(f"Invalid test execution data: {error}", 400)

            # Generate an ID if not provided
            if "id" not in validated_data:
                validated_data["id"] = str(len(self.data["test_executions"]) + 1)

            # Store the test execution
            self.data["test_executions"][validated_data["id"]] = validated_data

            return validated_data

        return self._format_error_response(f"Unsupported operation for test executions: {method} {endpoint}", 400)

    def _handle_attachments(self, method: str, endpoint: str, params: Dict[str, Any],
                           data: Dict[str, Any], files: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle attachments endpoint requests."""
        # Upload attachment
        entity_attachment_match = re.match(r"^/(\w+)s/([A-Za-z0-9\-]+)/attachments$", endpoint)
        if entity_attachment_match and method == "POST":
            entity_type = entity_attachment_match.group(1)
            entity_id = entity_attachment_match.group(2)

            if not files:
                return self._format_error_response("No file provided", 400)

            # Create a mock attachment
            attachment_id = str(len(self.data["attachments"]) + 1)

            # Mock file details
            file_data = list(files.values())[0]
            if isinstance(file_data, tuple):
                filename, content = file_data[0], file_data[1]
                content_type = file_data[2] if len(file_data) > 2 else "application/octet-stream"
            else:
                # Handle other file formats
                filename = "mock_file.txt"
                content = b"Mock file content"
                content_type = "text/plain"

            # Create attachment
            attachment = AttachmentFactory.create(
                id=attachment_id,
                filename=filename,
                content_type=content_type,
                size=len(content) if content else 0,
                created_on=datetime.now(),
                created_by="mock_user"
            ).model_dump()

            self.data["attachments"][attachment_id] = attachment

            return attachment

        # Get attachments for entity
        if entity_attachment_match and method == "GET":
            entity_type = entity_attachment_match.group(1)
            entity_id = entity_attachment_match.group(2)

            # In a real server, we'd filter by entity type and ID
            # For mock, we'll just return a few random attachments
            attachments = list(self.data["attachments"].values())[:3]

            return {
                "values": attachments,
                "maxResults": 50,
                "startAt": 0,
                "isLast": True,
                "totalCount": len(attachments)
            }

        # Get attachment content
        attachment_content_match = re.match(r"^/attachments/([A-Za-z0-9]+)/content$", endpoint)
        if attachment_content_match and method == "GET":
            attachment_id = attachment_content_match.group(1)

            if attachment_id in self.data["attachments"]:
                # For mock, we'd normally return the binary content
                # But for testing, we'll return a mock response
                return b"Mock attachment content"
            else:
                return self._format_error_response(f"Attachment not found with ID: {attachment_id}", 404)

        return self._format_error_response(f"Unsupported operation for attachments: {method} {endpoint}", 400)

    def _handle_statuses(self, method: str, endpoint: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle statuses endpoint requests."""
        # List statuses
        if endpoint == "/statuses" and method == "GET":
            project_key = params.get("projectKey")
            entity_type = params.get("entityType")

            # Filter statuses
            statuses = self.data["statuses"].values()
            if entity_type:
                statuses = [s for s in statuses if s["type"] == entity_type]

            # Pagination parameters
            start_at = int(params.get("startAt", 0))
            max_results = int(params.get("maxResults", 50))

            # Apply pagination
            paginated_statuses = list(statuses)[start_at:start_at + max_results]

            return {
                "values": paginated_statuses,
                "maxResults": max_results,
                "startAt": start_at,
                "isLast": (start_at + max_results) >= len(statuses),
                "totalCount": len(statuses)
            }

        return self._format_error_response(f"Unsupported operation for statuses: {method} {endpoint}", 400)

    def _handle_priorities(self, method: str, endpoint: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle priorities endpoint requests."""
        # List priorities
        if endpoint == "/priorities" and method == "GET":
            project_key = params.get("projectKey")

            # Get all priorities
            priorities = self.data["priorities"].values()

            # Pagination parameters
            start_at = int(params.get("startAt", 0))
            max_results = int(params.get("maxResults", 50))

            # Apply pagination
            paginated_priorities = list(priorities)[start_at:start_at + max_results]

            return {
                "values": paginated_priorities,
                "maxResults": max_results,
                "startAt": start_at,
                "isLast": (start_at + max_results) >= len(priorities),
                "totalCount": len(priorities)
            }

        return self._format_error_response(f"Unsupported operation for priorities: {method} {endpoint}", 400)

    def _handle_environments(self, method: str, endpoint: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle environments endpoint requests."""
        # List environments
        if endpoint == "/environments" and method == "GET":
            project_key = params.get("projectKey")

            # Get all environments
            environments = self.data["environments"].values()

            # Pagination parameters
            start_at = int(params.get("startAt", 0))
            max_results = int(params.get("maxResults", 50))

            # Apply pagination
            paginated_environments = list(environments)[start_at:start_at + max_results]

            return {
                "values": paginated_environments,
                "maxResults": max_results,
                "startAt": start_at,
                "isLast": (start_at + max_results) >= len(environments),
                "totalCount": len(environments)
            }

        return self._format_error_response(f"Unsupported operation for environments: {method} {endpoint}", 400)

    def _handle_custom_fields(self, method: str, endpoint: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle custom fields endpoint requests."""
        # List custom fields
        if endpoint == "/customfields" and method == "GET":
            project_key = params.get("projectKey")
            entity_type = params.get("entityType")

            # In a real server, we'd filter by project key and entity type
            # For mock, we'll just create a few custom fields on the fly
            custom_fields = []
            for i in range(3):
                field_type = random.choice(["TEXT", "PARAGRAPH", "CHECKBOX", "NUMERIC", "DATE"])
                custom_field = CustomFieldFactory.create(
                    id=str(i + 1),
                    name=f"Custom Field {i + 1}",
                    type=field_type
                ).model_dump()
                custom_fields.append(custom_field)

            return {
                "values": custom_fields,
                "maxResults": 50,
                "startAt": 0,
                "isLast": True,
                "totalCount": len(custom_fields)
            }

        return self._format_error_response(f"Unsupported operation for custom fields: {method} {endpoint}", 400)
