"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
API Mocking Test Harness for ZTOQ.

This module provides a flexible test harness for mocking API responses in tests.
It supports simulating various API responses, error conditions, and edge cases
for both Zephyr Scale and qTest APIs.
"""

import asyncio
import json
import logging
import random
import re
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    cast,
    ContextManager,
    AsyncContextManager,
)
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ztoq.qtest_mock_factory import (
    QTestAttachmentFactory,
    QTestCustomFieldFactory,
    QTestModuleFactory,
    QTestParameterFactory,
    QTestProjectFactory,
    QTestReleaseFactory,
    QTestTestCaseFactory,
    QTestTestCycleFactory,
    QTestTestLogFactory,
    QTestTestRunFactory,
)
from ztoq.qtest_mock_server import QTestMockServer
from ztoq.qtest_models import QTestConfig

logger = logging.getLogger("ztoq.test.api_harness")


class APIHarness:
    """
    Base class for API test harnesses.

    This class provides the foundation for mocking APIs in tests with configurable
    responses, delays, and error conditions.
    """

    def __init__(self, base_url: str = "https://api.mock-server.example.com"):
        """
        Initialize the API harness.

        Args:
            base_url: The base URL for the mock API server
        """
        self.base_url = base_url
        self.reset()

    def reset(self) -> None:
        """Reset the harness state to defaults."""
        # Response configurations
        self.responses: Dict[str, Dict[str, Any]] = {}
        self.default_response: Dict[str, Any] = {"success": True}

        # Error simulation
        self.error_rate = 0.0  # Percentage (0.0 to 1.0) of requests that should fail
        self.error_codes = [400, 401, 403, 404, 429, 500, 503]
        self.error_weights = [2, 1, 1, 2, 3, 2, 1]  # Probability weight for each error code

        # Performance simulation
        self.min_delay = 0.0  # Minimum delay in seconds
        self.max_delay = 0.1  # Maximum delay in seconds

        # Request tracking
        self.request_history: List[Dict[str, Any]] = []
        self.last_request: Optional[Dict[str, Any]] = None

        # Token generation and validation
        self.valid_tokens: List[str] = []
        self.token_expiry: Dict[str, float] = {}

        # Mock server patch
        self._patch = None

    def add_response(
        self, method: str, path: str, response: Dict[str, Any], status_code: int = 200
    ) -> None:
        """
        Configure a specific response for a given API endpoint.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API endpoint path (e.g., "/projects")
            response: Dictionary containing the response data
            status_code: HTTP status code to return
        """
        key = f"{method.upper()}:{path}"
        self.responses[key] = {"data": response, "status_code": status_code}

    def add_error_response(
        self, method: str, path: str, error: str, status_code: int = 400
    ) -> None:
        """
        Configure an error response for a given API endpoint.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API endpoint path
            error: Error message to include in the response
            status_code: HTTP status code to return
        """
        key = f"{method.upper()}:{path}"
        self.responses[key] = {
            "data": {"error": error, "message": error},
            "status_code": status_code,
        }

    def set_error_rate(self, rate: float) -> None:
        """
        Set the rate at which random errors should occur.

        Args:
            rate: Value between 0.0 (no errors) and 1.0 (all requests fail)
        """
        if not 0.0 <= rate <= 1.0:
            raise ValueError("Error rate must be between 0.0 and 1.0")
        self.error_rate = rate

    def set_delay_range(self, min_delay: float, max_delay: float) -> None:
        """
        Set the range of random delays to simulate network latency.

        Args:
            min_delay: Minimum delay in seconds
            max_delay: Maximum delay in seconds
        """
        if min_delay < 0 or max_delay < 0:
            raise ValueError("Delay values must be non-negative")
        if min_delay > max_delay:
            raise ValueError("Minimum delay cannot be greater than maximum delay")

        self.min_delay = min_delay
        self.max_delay = max_delay

    def generate_token(self, ttl: int = 3600) -> str:
        """
        Generate a mock authentication token.

        Args:
            ttl: Time-to-live in seconds for the token

        Returns:
            A mock authentication token
        """
        token = f"mock-token-{random.randint(100000, 999999)}"
        self.valid_tokens.append(token)
        expiry = time.time() + ttl
        self.token_expiry[token] = expiry
        return token

    def validate_token(self, token: str) -> bool:
        """
        Validate a mock authentication token.

        Args:
            token: The token to validate

        Returns:
            True if the token is valid, False otherwise
        """
        if token not in self.valid_tokens:
            return False

        if token in self.token_expiry:
            if time.time() > self.token_expiry[token]:
                # Token has expired
                self.valid_tokens.remove(token)
                del self.token_expiry[token]
                return False

        return True

    def _should_generate_error(self) -> bool:
        """Determine if a request should generate an error based on error rate."""
        return random.random() < self.error_rate

    def _get_random_error(self) -> Tuple[int, str]:
        """
        Generate a random error response.

        Returns:
            Tuple of (status_code, error_message)
        """
        status_code = random.choices(self.error_codes, weights=self.error_weights)[0]

        if status_code == 400:
            error = "Bad Request: Invalid parameters"
        elif status_code == 401:
            error = "Unauthorized: Invalid authentication credentials"
        elif status_code == 403:
            error = "Forbidden: Insufficient permissions"
        elif status_code == 404:
            error = "Not Found: The requested resource does not exist"
        elif status_code == 429:
            error = "Too Many Requests: Rate limit exceeded"
        elif status_code == 500:
            error = "Internal Server Error: An unexpected error occurred"
        elif status_code == 503:
            error = "Service Unavailable: The service is temporarily unavailable"
        else:
            error = "Unknown Error"

        return status_code, error

    def _get_random_delay(self) -> float:
        """
        Generate a random delay within the configured range.

        Returns:
            Delay in seconds
        """
        return random.uniform(self.min_delay, self.max_delay)

    def _track_request(
        self, method: str, path: str, params: Dict[str, Any], data: Dict[str, Any]
    ) -> None:
        """
        Track a request for later inspection.

        Args:
            method: HTTP method
            path: API endpoint path
            params: Query parameters
            data: Request body data
        """
        request = {
            "timestamp": time.time(),
            "method": method,
            "path": path,
            "params": params,
            "data": data,
        }

        self.request_history.append(request)
        self.last_request = request

    def get_requests(
        self, method: Optional[str] = None, path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get a filtered list of tracked requests.

        Args:
            method: Filter by HTTP method
            path: Filter by API endpoint path

        Returns:
            List of matching request dictionaries
        """
        if method is None and path is None:
            return self.request_history

        filtered = self.request_history

        if method is not None:
            filtered = [req for req in filtered if req["method"].upper() == method.upper()]

        if path is not None:
            # Support regex pattern matching for paths
            pattern = re.compile(path)
            filtered = [req for req in filtered if pattern.match(req["path"])]

        return filtered

    def _handle_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Process a request and generate an appropriate response.

        Args:
            method: HTTP method
            path: API endpoint path
            params: Query parameters
            data: Request body data
            headers: Request headers
            files: File uploads

        Returns:
            Tuple of (response_data, status_code)
        """
        params = params or {}
        data = data or {}
        headers = headers or {}

        # Track the request
        self._track_request(method, path, params, data)

        # Apply simulated network delay
        delay = self._get_random_delay()
        if delay > 0:
            time.sleep(delay)

        # Check for authentication if needed
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            if not self.validate_token(token):
                return {"error": "Invalid or expired token"}, 401

        # Check if we should generate a random error
        if self._should_generate_error():
            status_code, error = self._get_random_error()
            return {"error": error}, status_code

        # Look for a specific configured response
        key = f"{method.upper()}:{path}"
        if key in self.responses:
            response = self.responses[key]
            return response["data"], response["status_code"]

        # Return default response if no specific response is configured
        return self.default_response, 200

    def mock_requests(self) -> ContextManager:
        """
        Create a context manager that patches the requests library to use this harness.

        Returns:
            Context manager that patches requests
        """
        return MockRequestsContext(self)

    async def mock_httpx(self) -> AsyncContextManager:
        """
        Create an async context manager that patches the httpx library to use this harness.

        Returns:
            Async context manager that patches httpx
        """
        return MockHttpxContext(self)

    def start_patch(self) -> None:
        """Start patching requests library to use this harness."""
        if self._patch is not None:
            # Already patched
            return

        self._patch = patch("requests.request", side_effect=self._mocked_request)
        self._patch.start()

    def stop_patch(self) -> None:
        """Stop patching requests library."""
        if self._patch is not None:
            self._patch.stop()
            self._patch = None

    def _mocked_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> "MockResponse":
        """
        Mock implementation of requests.request.

        Args:
            method: HTTP method
            url: Full URL
            params: Query parameters
            data: Form data
            headers: Request headers
            files: File uploads
            json: JSON body data
            **kwargs: Additional arguments

        Returns:
            A MockResponse object
        """
        # Extract the path from the URL
        if url.startswith(self.base_url):
            path = url[len(self.base_url) :]
        else:
            path = url

        # Combine json and data
        request_data = {}
        if data:
            if isinstance(data, dict):
                request_data.update(data)
            elif isinstance(data, str):
                try:
                    request_data.update(json.loads(data))
                except json.JSONDecodeError:
                    pass

        if json:
            request_data.update(json)

        # Handle the request
        response_data, status_code = self._handle_request(
            method, path, params, request_data, headers, files
        )

        # Create a mock response
        response = MockResponse(
            content=json.dumps(response_data).encode("utf-8"),
            status_code=status_code,
            url=url,
            headers={"Content-Type": "application/json"},
        )

        return response


class MockResponse:
    """Mock implementation of requests.Response."""

    def __init__(
        self,
        content: bytes,
        status_code: int = 200,
        url: str = "",
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize a mock response.

        Args:
            content: Response content as bytes
            status_code: HTTP status code
            url: URL that was requested
            headers: Response headers
        """
        self.content = content
        self.status_code = status_code
        self.url = url
        self.headers = headers or {}
        self._text = None
        self._json = None

    @property
    def text(self) -> str:
        """Get the response content as text."""
        if self._text is None:
            self._text = self.content.decode("utf-8")
        return self._text

    def json(self) -> Dict[str, Any]:
        """Parse the response content as JSON."""
        if self._json is None:
            self._json = json.loads(self.text)
        return self._json

    def raise_for_status(self) -> None:
        """Raise an exception if the status code indicates an error."""
        if 400 <= self.status_code < 600:
            raise requests.HTTPError(f"HTTP Error {self.status_code}", response=self)


@contextmanager
def MockRequestsContext(harness: APIHarness):
    """
    Context manager for patching the requests library.

    Args:
        harness: The API harness to use for handling requests
    """
    with patch("requests.request", side_effect=harness._mocked_request):
        with patch(
            "requests.get",
            side_effect=lambda url, **kwargs: harness._mocked_request("GET", url, **kwargs),
        ):
            with patch(
                "requests.post",
                side_effect=lambda url, **kwargs: harness._mocked_request("POST", url, **kwargs),
            ):
                with patch(
                    "requests.put",
                    side_effect=lambda url, **kwargs: harness._mocked_request("PUT", url, **kwargs),
                ):
                    with patch(
                        "requests.delete",
                        side_effect=lambda url, **kwargs: harness._mocked_request(
                            "DELETE", url, **kwargs
                        ),
                    ):
                        yield


@asynccontextmanager
async def MockHttpxContext(harness: APIHarness):
    """
    Async context manager for patching the httpx library.

    Args:
        harness: The API harness to use for handling requests
    """
    with patch(
        "httpx.request",
        side_effect=lambda method, url, **kwargs: harness._mocked_request(method, url, **kwargs),
    ):
        with patch(
            "httpx.get",
            side_effect=lambda url, **kwargs: harness._mocked_request("GET", url, **kwargs),
        ):
            with patch(
                "httpx.post",
                side_effect=lambda url, **kwargs: harness._mocked_request("POST", url, **kwargs),
            ):
                with patch(
                    "httpx.put",
                    side_effect=lambda url, **kwargs: harness._mocked_request("PUT", url, **kwargs),
                ):
                    with patch(
                        "httpx.delete",
                        side_effect=lambda url, **kwargs: harness._mocked_request(
                            "DELETE", url, **kwargs
                        ),
                    ):
                        yield


class ZephyrAPIHarness(APIHarness):
    """
    API test harness for Zephyr Scale API.

    This class extends the base APIHarness with Zephyr-specific functionality,
    including realistic responses for various Zephyr API endpoints.
    """

    def __init__(self, base_url: str = "https://api.zephyrscale.example.com/v2"):
        """
        Initialize the Zephyr API harness.

        Args:
            base_url: The base URL for the mock Zephyr API
        """
        super().__init__(base_url)

        # Set up common Zephyr API responses
        self._setup_common_responses()

    def _setup_common_responses(self) -> None:
        """Set up common Zephyr API responses."""
        # Authentication endpoint
        self.add_response(
            "POST",
            "/authorize",
            {"access_token": self.generate_token(), "token_type": "bearer", "expires_in": 3600},
        )

        # Projects endpoint
        self.add_response(
            "GET",
            "/projects",
            {
                "total": 3,
                "startAt": 0,
                "maxResults": 10,
                "values": [
                    {"id": "10001", "key": "PROJ1", "name": "Project One"},
                    {"id": "10002", "key": "PROJ2", "name": "Project Two"},
                    {"id": "10003", "key": "PROJ3", "name": "Project Three"},
                ],
            },
        )

    def configure_project(self, project_key: str, test_cases: int = 10) -> None:
        """
        Configure a mock project with test cases.

        Args:
            project_key: The project key
            test_cases: Number of test cases to generate
        """
        # Generate project data
        project_id = str(random.randint(10000, 99999))
        project = {
            "id": project_id,
            "key": project_key,
            "name": f"Project {project_key}",
            "description": f"Description for project {project_key}",
        }

        # Add project response
        self.add_response("GET", f"/projects/{project_key}", project)

        # Generate test cases
        self._generate_test_cases(project_key, project_id, test_cases)

    def _generate_test_cases(self, project_key: str, project_id: str, count: int) -> None:
        """
        Generate mock test cases for a project.

        Args:
            project_key: The project key
            project_id: The project ID
            count: Number of test cases to generate
        """
        # Generate folders
        folders = [
            {"id": "1001", "name": "Folder 1", "folderType": "TEST_CASE"},
            {"id": "1002", "name": "Folder 2", "folderType": "TEST_CASE"},
            {"id": "1003", "name": "Folder 3", "folderType": "TEST_CASE"},
        ]

        # Add folders response
        self.add_response(
            "GET",
            f"/folders?projectKey={project_key}&folderType=TEST_CASE",
            {"total": len(folders), "startAt": 0, "maxResults": 50, "values": folders},
        )

        # Generate test cases
        test_cases = []
        for i in range(1, count + 1):
            folder = random.choice(folders)
            test_case = {
                "id": str(10000 + i),
                "key": f"{project_key}-T{i}",
                "name": f"Test Case {i}",
                "project": {"id": project_id, "key": project_key},
                "folder": {"id": folder["id"], "name": folder["name"]},
                "status": random.choice(["Draft", "Ready", "Approved"]),
                "priority": random.choice(["High", "Medium", "Low"]),
                "labels": [f"label-{random.randint(1, 5)}" for _ in range(random.randint(0, 3))],
                "steps": self._generate_test_steps(random.randint(1, 5)),
            }
            test_cases.append(test_case)

            # Add individual test case response
            self.add_response("GET", f"/testcases/{test_case['key']}", test_case)

        # Add test cases response
        self.add_response(
            "GET",
            f"/testcases?projectKey={project_key}",
            {"total": len(test_cases), "startAt": 0, "maxResults": 50, "values": test_cases},
        )

    def _generate_test_steps(self, count: int) -> List[Dict[str, Any]]:
        """
        Generate mock test steps.

        Args:
            count: Number of steps to generate

        Returns:
            List of test step dictionaries
        """
        steps = []
        for i in range(1, count + 1):
            step = {
                "id": str(1000 + i),
                "index": i,
                "description": f"Step {i} description",
                "expectedResult": f"Expected result for step {i}",
                "testData": f"Test data for step {i}" if random.random() > 0.5 else "",
            }
            steps.append(step)

        return steps


class QTestAPIHarness(APIHarness):
    """
    API test harness for qTest API.

    This class extends the base APIHarness with qTest-specific functionality,
    including realistic responses for various qTest API endpoints.
    """

    def __init__(self, base_url: str = "https://api.qtest.example.com"):
        """
        Initialize the qTest API harness.

        Args:
            base_url: The base URL for the mock qTest API
        """
        super().__init__(base_url)
        self.mock_server = QTestMockServer()

        # Set up common qTest API responses
        self._setup_common_responses()

    def _setup_common_responses(self) -> None:
        """Set up common qTest API responses."""
        # Authentication endpoint
        self.add_response(
            "POST",
            "/oauth/token",
            {"access_token": self.generate_token(), "token_type": "bearer", "expires_in": 3600},
        )

        # Projects endpoint
        projects = [QTestProjectFactory.create().model_dump() for _ in range(3)]
        self.add_response(
            "GET",
            "/api/v3/projects",
            {"total": len(projects), "page": 1, "pageSize": 20, "items": projects},
        )

    def configure_project(self, project_id: int, test_cases: int = 10) -> None:
        """
        Configure a mock project with test cases, cycles, and other entities.

        Args:
            project_id: The project ID
            test_cases: Number of test cases to generate
        """
        # Generate project data
        project = QTestProjectFactory.create(id=project_id).model_dump()

        # Add project response
        self.add_response("GET", f"/api/v3/projects/{project_id}", project)

        # Generate modules (folders)
        modules = [QTestModuleFactory.create(project_id=project_id).model_dump() for _ in range(3)]
        self.add_response(
            "GET",
            f"/api/v3/projects/{project_id}/modules",
            {"total": len(modules), "page": 1, "pageSize": 20, "items": modules},
        )

        # Generate test cases
        self._generate_test_cases(project_id, modules, test_cases)

        # Generate releases and test cycles
        self._generate_test_cycles(project_id)

    def _generate_test_cases(
        self, project_id: int, modules: List[Dict[str, Any]], count: int
    ) -> None:
        """
        Generate mock test cases for a project.

        Args:
            project_id: The project ID
            modules: List of module dictionaries
            count: Number of test cases to generate
        """
        test_cases = []
        for i in range(count):
            module = random.choice(modules)
            test_case = QTestTestCaseFactory.create(
                project_id=project_id, module_id=module["id"]
            ).model_dump()
            test_cases.append(test_case)

            # Add individual test case response
            self.add_response(
                "GET", f"/api/v3/projects/{project_id}/test-cases/{test_case['id']}", test_case
            )

        # Add test cases response
        self.add_response(
            "GET",
            f"/api/v3/projects/{project_id}/test-cases",
            {"total": len(test_cases), "page": 1, "pageSize": 20, "items": test_cases},
        )

    def _generate_test_cycles(self, project_id: int) -> None:
        """
        Generate mock releases and test cycles for a project.

        Args:
            project_id: The project ID
        """
        # Generate releases
        releases = [
            QTestReleaseFactory.create(project_id=project_id).model_dump() for _ in range(2)
        ]
        self.add_response(
            "GET",
            f"/api/v3/projects/{project_id}/releases",
            {"total": len(releases), "page": 1, "pageSize": 20, "items": releases},
        )

        # Generate test cycles for each release
        all_cycles = []
        for release in releases:
            cycles = [
                QTestTestCycleFactory.create(
                    project_id=project_id, release_id=release["id"]
                ).model_dump()
                for _ in range(2)
            ]
            all_cycles.extend(cycles)

        # Add test cycles response
        self.add_response(
            "GET",
            f"/api/v3/projects/{project_id}/test-cycles",
            {"total": len(all_cycles), "page": 1, "pageSize": 20, "items": all_cycles},
        )

    def create_test_run(
        self, project_id: int, test_case_id: int, test_cycle_id: int
    ) -> Dict[str, Any]:
        """
        Create a mock test run and configure the appropriate response.

        Args:
            project_id: The project ID
            test_case_id: The test case ID
            test_cycle_id: The test cycle ID

        Returns:
            The created test run dictionary
        """
        test_run = QTestTestRunFactory.create(
            project_id=project_id, test_case_id=test_case_id, test_cycle_id=test_cycle_id
        ).model_dump()

        # Add test run response
        self.add_response(
            "GET", f"/api/v3/projects/{project_id}/test-runs/{test_run['id']}", test_run
        )

        return test_run

    def submit_test_log(self, project_id: int, test_run_id: int, status: str) -> Dict[str, Any]:
        """
        Submit a mock test log and configure the appropriate response.

        Args:
            project_id: The project ID
            test_run_id: The test run ID
            status: The test execution status

        Returns:
            The created test log dictionary
        """
        test_log = QTestTestLogFactory.create(test_run_id=test_run_id, status=status).model_dump()

        # Add test log response
        self.add_response(
            "POST", f"/api/v3/projects/{project_id}/test-runs/{test_run_id}/test-logs", test_log
        )

        return test_log

    def handle_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Handle a request using the QTestMockServer.

        This method provides a bridge to the existing QTestMockServer implementation.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            headers: Request headers
            files: File uploads

        Returns:
            Tuple of (response_data, status_code)
        """
        # Check if we have a specific configured response
        key = f"{method.upper()}:{endpoint}"
        if key in self.responses:
            response = self.responses[key]
            return response["data"], response["status_code"]

        # Extract API type from endpoint
        api_type = "manager"  # Default
        if endpoint.startswith("/parameters") or endpoint.startswith("/data-sets"):
            api_type = "parameters"
        elif (
            endpoint.startswith("/rules")
            or endpoint.startswith("/triggers")
            or endpoint.startswith("/actions")
        ):
            api_type = "pulse"
        elif endpoint.startswith("/features"):
            api_type = "scenario"

        # Use the QTestMockServer to handle the request
        try:
            response = self.mock_server.handle_request(
                api_type, method, endpoint, params, data, headers, files
            )
            return response, 200
        except Exception as e:
            return {"error": str(e)}, 500


class MockAPITestBase:
    """
    Base class for tests that use the API harnesses.

    This class provides utility methods for setting up and using the API harnesses
    in tests. It can be used as a base class for pytest test classes.
    """

    def setup_method(self) -> None:
        """Set up test method by creating API harnesses."""
        self.zephyr_harness = ZephyrAPIHarness()
        self.qtest_harness = QTestAPIHarness()

    def teardown_method(self) -> None:
        """Clean up by stopping any patches."""
        self.zephyr_harness.stop_patch()
        self.qtest_harness.stop_patch()

    @pytest.fixture
    def mock_zephyr_api(self) -> ZephyrAPIHarness:
        """Fixture for a ZephyrAPIHarness with requests patching."""
        self.zephyr_harness.start_patch()
        yield self.zephyr_harness
        self.zephyr_harness.stop_patch()

    @pytest.fixture
    def mock_qtest_api(self) -> QTestAPIHarness:
        """Fixture for a QTestAPIHarness with requests patching."""
        self.qtest_harness.start_patch()
        yield self.qtest_harness
        self.qtest_harness.stop_patch()

    @pytest.fixture
    def mock_both_apis(self) -> Tuple[ZephyrAPIHarness, QTestAPIHarness]:
        """Fixture for both API harnesses with requests patching."""
        # Use context managers to ensure proper cleanup
        with self.zephyr_harness.mock_requests():
            with self.qtest_harness.mock_requests():
                yield self.zephyr_harness, self.qtest_harness


class FastAPIHarness:
    """
    FastAPI-based test harness for mocking APIs with an actual server.

    This class provides a more realistic API mocking experience by launching an actual
    FastAPI server that simulates both Zephyr and qTest APIs. It's ideal for integration
    tests and scenarios where a higher-fidelity API simulation is needed.
    """

    def __init__(self, host: str = "localhost", port: int = 8000):
        """
        Initialize the FastAPI harness.

        Args:
            host: Hostname to bind the server to
            port: Port to bind the server to
        """
        self.host = host
        self.port = port
        self.app = FastAPI(title="API Simulation Server")
        self.server_thread = None

        # Add routes to the app
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up API routes in the FastAPI app."""
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Health check
        @self.app.get("/health")
        def health_check():
            """Health check endpoint."""
            return {"status": "ok"}

        # Authentication routes
        @self.app.post("/oauth/token")
        def qtest_auth():
            """qTest authentication endpoint."""
            return {
                "access_token": f"qtest-token-{random.randint(1000, 9999)}",
                "token_type": "bearer",
                "expires_in": 3600,
            }

        @self.app.post("/authorize")
        def zephyr_auth():
            """Zephyr authentication endpoint."""
            return {
                "access_token": f"zephyr-token-{random.randint(1000, 9999)}",
                "token_type": "bearer",
                "expires_in": 3600,
            }

        # Generic route handler for any other path
        @self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
        async def catch_all(request: Request, path: str):
            """
            Catch-all route handler.

            Args:
                request: The FastAPI request object
                path: The API path

            Returns:
                JSON response
            """
            # Log the request
            logger.info(f"Request: {request.method} /{path}")

            try:
                # Parse body if present
                body = {}
                if request.method in ["POST", "PUT"]:
                    body_bytes = await request.body()
                    if body_bytes:
                        try:
                            body = json.loads(body_bytes)
                        except json.JSONDecodeError:
                            pass

                # Determine API type and generate mock response
                if path.startswith("api/v3") or path.startswith("oauth"):
                    # qTest API
                    return self._handle_qtest_request(
                        request.method, path, dict(request.query_params), body
                    )
                elif path.startswith("v2"):
                    # Zephyr API
                    return self._handle_zephyr_request(
                        request.method, path, dict(request.query_params), body
                    )
                else:
                    # Unknown API
                    return JSONResponse(
                        status_code=404, content={"error": f"Unknown API path: {path}"}
                    )
            except Exception as e:
                logger.exception(f"Error handling request: {e}")
                return JSONResponse(status_code=500, content={"error": f"Server error: {str(e)}"})

    def _handle_qtest_request(
        self, method: str, path: str, params: Dict[str, Any], data: Dict[str, Any]
    ) -> JSONResponse:
        """
        Handle a qTest API request.

        Args:
            method: HTTP method
            path: API path
            params: Query parameters
            data: Request body

        Returns:
            JSON response
        """
        # TODO: Implement more sophisticated qTest API simulation logic
        if "projects" in path:
            if path.endswith("projects"):
                # List projects
                projects = [QTestProjectFactory.create().model_dump() for _ in range(3)]
                return JSONResponse(
                    content={"total": len(projects), "page": 1, "pageSize": 20, "items": projects}
                )
            else:
                # Single project - Extract project ID
                project_id_match = re.search(r"projects/(\d+)", path)
                if project_id_match:
                    project_id = int(project_id_match.group(1))
                    project = QTestProjectFactory.create(id=project_id).model_dump()
                    return JSONResponse(content=project)

        # Default response
        return JSONResponse(content={"message": f"Unimplemented qTest endpoint: {method} {path}"})

    def _handle_zephyr_request(
        self, method: str, path: str, params: Dict[str, Any], data: Dict[str, Any]
    ) -> JSONResponse:
        """
        Handle a Zephyr API request.

        Args:
            method: HTTP method
            path: API path
            params: Query parameters
            data: Request body

        Returns:
            JSON response
        """
        # TODO: Implement more sophisticated Zephyr API simulation logic
        if "projects" in path:
            if path.endswith("projects"):
                # List projects
                return JSONResponse(
                    content={
                        "total": 3,
                        "startAt": 0,
                        "maxResults": 10,
                        "values": [
                            {"id": "10001", "key": "PROJ1", "name": "Project One"},
                            {"id": "10002", "key": "PROJ2", "name": "Project Two"},
                            {"id": "10003", "key": "PROJ3", "name": "Project Three"},
                        ],
                    }
                )
            else:
                # Single project - Extract project key
                project_key_match = re.search(r"projects/([A-Z0-9]+)", path)
                if project_key_match:
                    project_key = project_key_match.group(1)
                    return JSONResponse(
                        content={
                            "id": f"1000{random.randint(1, 5)}",
                            "key": project_key,
                            "name": f"Project {project_key}",
                            "description": f"Description for project {project_key}",
                        }
                    )

        # Default response
        return JSONResponse(content={"message": f"Unimplemented Zephyr endpoint: {method} {path}"})

    def start_server(self) -> None:
        """Start the FastAPI server in a separate thread."""
        if self.server_thread is not None:
            # Server already running
            return

        def run_server():
            """Run the FastAPI server using uvicorn."""
            import uvicorn

            uvicorn.run(self.app, host=self.host, port=self.port)

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # Wait for the server to start
        time.sleep(1)

    def stop_server(self) -> None:
        """Stop the FastAPI server."""
        # FastAPI doesn't have a clean way to stop the server programmatically
        # The daemon thread will be terminated when the main thread exits
        self.server_thread = None

    @property
    def base_url(self) -> str:
        """Get the base URL of the server."""
        return f"http://{self.host}:{self.port}"

    @property
    def zephyr_url(self) -> str:
        """Get the Zephyr API URL."""
        return f"{self.base_url}/v2"

    @property
    def qtest_url(self) -> str:
        """Get the qTest API URL."""
        return f"{self.base_url}/api/v3"

    @contextmanager
    def server_context(self):
        """Context manager for running the server."""
        self.start_server()
        try:
            yield self
        finally:
            self.stop_server()


# Fixtures for use in pytest tests


@pytest.fixture
def mock_zephyr_api() -> ZephyrAPIHarness:
    """Fixture that provides a ZephyrAPIHarness with requests patching."""
    harness = ZephyrAPIHarness()
    with harness.mock_requests():
        yield harness


@pytest.fixture
def mock_qtest_api() -> QTestAPIHarness:
    """Fixture that provides a QTestAPIHarness with requests patching."""
    harness = QTestAPIHarness()
    with harness.mock_requests():
        yield harness


@pytest.fixture
def mock_both_apis() -> Tuple[ZephyrAPIHarness, QTestAPIHarness]:
    """Fixture that provides both API harnesses with requests patching."""
    zephyr_harness = ZephyrAPIHarness()
    qtest_harness = QTestAPIHarness()

    with zephyr_harness.mock_requests():
        with qtest_harness.mock_requests():
            yield zephyr_harness, qtest_harness


@pytest.fixture
def api_server() -> FastAPIHarness:
    """Fixture that provides a running FastAPI harness server."""
    harness = FastAPIHarness()
    with harness.server_context():
        yield harness
