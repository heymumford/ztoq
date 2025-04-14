"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
qTest API Client for interacting with qTest Manager, Parameters, Pulse and Scenario.

This module provides a unified client for working with all qTest APIs.
"""

import json
import logging
import os
import time
import base64
from pathlib import Path
from typing import Any, Generic, TypeVar, cast
import requests
from ztoq.qtest_models import (
    QTestAttachment,
        QTestConfig,
        QTestDataset,
        QTestModule,
        QTestPaginatedResponse,
        QTestParameter,
        QTestProject,
        QTestPulseAction,
        QTestPulseConstant,
        QTestPulseRule,
        QTestPulseTrigger,
        QTestTestCase,
        QTestTestCycle,
)

T = TypeVar("T")

# Configure module logger
logger = logging.getLogger("ztoq.qtest_client")


def configure_logging(level=None):
    """Configure logging for the qTest client.

    Args:
        level: The logging level to use. If None, use the level from the ZTOQ_LOG_LEVEL
              environment variable, or INFO as a default.
    """
    # Use specified level, environment variable, or default to INFO
    if level is None:
        level = os.environ.get("ZTOQ_LOG_LEVEL", "INFO").upper()

    # Convert string level to logging constant
    numeric_level = getattr(logging, level, logging.INFO)

    # Configure the logger
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger.setLevel(numeric_level)

    # Only add handler if not already present
    if not logger.handlers:
        logger.addHandler(handler)

    # Log the configuration
    logger.debug(f"Logging configured with level: {level}")


# Initialize logging with default settings
configure_logging()


class QTestPaginatedIterator(Generic[T]):
    """Iterator for paginated API responses."""

    def __init__(
        self,
            client: "QTestClient",
            endpoint: str,
            model_class: type[T],
            params: dict[str, Any] | None = None,
            page_size: int = 50,
        ):
        """Initialize the paginated iterator.

        Args:
            client: The QTestClient instance
            endpoint: API endpoint path
            model_class: Model class for response items
            params: Additional query parameters
            page_size: Number of items per page
        """
        self.client = client
        self.endpoint = endpoint
        self.model_class = model_class
        self.params = params or {}

        # qTest uses different pagination conventions depending on the API
        if client.api_type == "manager":
            self.params["pageSize"] = page_size
            self.page_param = "page"
        else:
            self.params["limit"] = page_size
            self.page_param = "offset"

        self.current_page: QTestPaginatedResponse | None = None
        self.item_index = 0
        self.total_fetched = 0

        logger.debug(
            f"QTestPaginatedIterator initialized for {endpoint} with page size {page_size}, "
            f"model class {model_class.__name__}"
        )

    def __iter__(self):
        return self

    def __next__(self) -> T:
        # Fetch first page if needed
        if not self.current_page:
            logger.debug(f"Fetching first page for {self.endpoint}")
            self._fetch_next_page()

        # Check if we have valid page data
        if self.current_page is None:
            logger.debug(f"No data found for {self.endpoint}")
            raise StopIteration

        # Check if we need to fetch the next page
        if self.item_index >= len(self.current_page.items):
            if self.current_page.is_last:
                logger.debug(
                    f"Reached last page for {self.endpoint}, total items fetched: {self.total_fetched}"
                )
                raise StopIteration

            logger.debug(
                f"Fetching next page for {self.endpoint}, items so far: {self.total_fetched}"
            )
            self._fetch_next_page()

        # Return the next item
        item = cast(T, self.model_class(**self.current_page.items[self.item_index]))
        self.item_index += 1
        self.total_fetched += 1

        # Log every 100th item to show progress
        if self.total_fetched % 100 == 0:
            logger.debug(f"Processed {self.total_fetched} items from {self.endpoint}")

        return item

    def _fetch_next_page(self):
        """Fetch the next page of results."""
        page_number = 0
        if self.current_page:
            if self.client.api_type == "manager":
                page_number = self.current_page.page + 1
                self.params[self.page_param] = page_number
            else:
                offset = self.current_page.offset + len(self.current_page.items)
                self.params[self.page_param] = offset
                page_number = offset // self.params.get("limit", 50)
        else:
            if self.client.api_type == "manager":
                self.params[self.page_param] = 1
            else:
                self.params[self.page_param] = 0

        logger.debug(f"Fetching page {page_number + 1} from {self.endpoint}")

        response = self.client._make_request("GET", self.endpoint, params=self.params)

        # Handle different pagination formats depending on API type
        if self.client.api_type == "manager":
            self.current_page = QTestPaginatedResponse(
                items=response.get("items", []),
                    page=response.get("page", 0),
                    page_size=response.get("pageSize", 0),
                    total=response.get("total", 0),
                    is_last=response.get("page", 0) * response.get("pageSize", 0)
                + len(response.get("items", []))
                >= response.get("total", 0),
                )
        else:
            self.current_page = QTestPaginatedResponse(
                items=response.get("data", []),
                    offset=response.get("offset", 0),
                    limit=response.get("limit", 0),
                    total=response.get("total", 0),
                    is_last=response.get("offset", 0) + len(response.get("data", []))
                >= response.get("total", 0),
                )

        self.item_index = 0

        logger.debug(
            f"Received page {page_number + 1} with {len(self.current_page.items)} items, "
            f"total: {self.current_page.total}, isLast: {self.current_page.is_last}"
        )


class QTestClient:
    """Client for interacting with the qTest APIs."""

    def __init__(self, config: QTestConfig, api_type: str = "manager", log_level=None):
        """Initialize the qTest client with configuration.

        Args:
            config: The qTest API configuration
            api_type: The qTest API type (manager, parameters, pulse, scenario)
            log_level: Optional logging level to use for this client instance
                      (e.g., "DEBUG", "INFO", "WARNING", "ERROR")
        """
        self.config = config
        self.api_type = api_type.lower()
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        self.auth_token = None
        self.rate_limit_remaining = 1000  # Default high value
        self.rate_limit_reset = 0

        # API base endpoints vary by type
        self.api_endpoints = {
            "manager": "api/v3",
                "parameters": "api/v1",
                "pulse": "",  # Pulse uses root path
            "scenario": "",  # Scenario uses root path
        }

        # Configure logging if level specified
        if log_level:
            configure_logging(log_level)

        logger.debug(
            f"QTestClient initialized for project {config.project_id} with base URL {config.base_url}"
        )

        # Authenticate immediately
        self._authenticate()

    def _authenticate(self):
        """Authenticate with qTest API and obtain an access token."""
        # If bearer token is already provided in config, use it directly
        if hasattr(self.config, 'bearer_token') and self.config.bearer_token:
            token = self.config.bearer_token.strip()

            # Handle case where token already includes "bearer" prefix
            if token.lower().startswith("bearer "):
                # Extract just the token part, removing "bearer "
                self.auth_token = token[7:].strip()
                self.headers["Authorization"] = f"bearer {self.auth_token}"
            else:
                # Use token as-is
                self.auth_token = token
                self.headers["Authorization"] = f"bearer {self.auth_token}"

            logger.info(f"Using provided bearer token for {self.api_type} API")
            logger.debug(f"Authorization header: {self.headers['Authorization']}")
            return

        # Otherwise, use username/password to obtain a token
        auth_endpoints = {
            "manager": "/oauth/token",
            "parameters": "/oauth/v1/token-login",
            "pulse": "/oauth/token",
            "scenario": "/oauth/token",
        }

        endpoint = auth_endpoints.get(self.api_type, "/oauth/token")
        url = f"{self.config.base_url}{endpoint}"

        # Common headers for token request
        auth_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache"
        }

        # Add basic auth header with client name (any string)
        client_name_encoded = base64.b64encode(b"ztoq-client:").decode('utf-8')
        auth_headers["Authorization"] = f"Basic {client_name_encoded}"

        # Prepare form data for token request
        auth_data = {
            "grant_type": "password",
            "username": self.config.username,
            "password": self.config.password,
        }

        # For Parameters API which uses a different format
        if self.api_type == "parameters":
            auth_data = {"email": self.config.username, "password": self.config.password}
            auth_headers["Content-Type"] = "application/json"

        logger.debug(f"Authenticating with {self.api_type} API at {url}")

        try:
            if self.api_type == "parameters":
                # Parameters API uses JSON
                response = requests.post(
                    url=url, headers=auth_headers, json=auth_data
                )
            else:
                # Manager API uses form data
                response = requests.post(
                    url=url, headers=auth_headers, data=auth_data
                )

            response.raise_for_status()
            data = response.json()

            # Get token from response
            token_type = data.get("token_type", "bearer").lower()
            self.auth_token = data.get("access_token")
            if not self.auth_token:
                raise ValueError("No access token returned from authentication endpoint")

            # Set authorization header with proper token format
            self.headers["Authorization"] = f"{token_type} {self.auth_token}"

            logger.info(f"Successfully authenticated with {self.api_type} API")
            logger.debug(f"Token type: {token_type}, expires in: {data.get('expires_in', 'unknown')} seconds")

        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise

    def _make_request(
        self,
            method: str,
            endpoint: str,
            params: dict[str, Any] | None = None,
            json_data: dict[str, Any] | None = None,
            files: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
            verify: bool = True,
            timeout: tuple | None = None,
            _retry_count: int = 0,
            _max_retries: int = 3,
        ) -> dict[str, Any]:
        """Make a request to the qTest API.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body
            files: Files to upload (for multipart/form-data requests)
            headers: Optional headers to override default headers
            verify: Whether to verify SSL certificates (default True)
            timeout: Request timeout as (connect_timeout, read_timeout) tuple
            _retry_count: Internal retry counter to prevent infinite loops
            _max_retries: Maximum number of retries for authentication

        Returns:
            API response as dictionary
        """
        # Check retry limit
        if _retry_count >= _max_retries:
            logger.error(f"Maximum retry limit reached ({_max_retries}). Authentication failed.")
            raise ValueError(f"Authentication failed after {_max_retries} attempts. Check your credentials.")

        # Check rate limits
        if self.rate_limit_remaining <= 0:
            wait_time = max(0, self.rate_limit_reset - time.time())
            if wait_time > 0:
                logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)

        # Re-authenticate if token expired (will be determined from 401 response later)
        if not self.auth_token:
            self._authenticate()

        # Add API version to the path if needed
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        # Prepend API version path if needed
        if not any(endpoint.startswith(f"/{x}") for x in ["oauth", "api"]):
            api_version = self.api_endpoints.get(self.api_type, "api/v3")
            if api_version:
                endpoint = f"/{api_version}{endpoint}"

        # Construct URL
        url = f"{self.config.base_url}{endpoint}"

        # Use provided headers or default
        request_headers = headers or self.headers

        # Log request details (careful not to log sensitive data)
        safe_headers = {k: v for k, v in request_headers.items() if k.lower() != "authorization"}
        logger.debug(f"API Request: {method} {url}")
        logger.debug(f"Parameters: {params}")
        logger.debug(f"Headers: {safe_headers}")

        if logger.isEnabledFor(logging.DEBUG) and json_data:
            # Mask any sensitive fields in the debug output
            safe_json = self._mask_sensitive_data(json_data)
            logger.debug(f"Request Body: {json.dumps(safe_json)}")

        # Measure request time for performance monitoring
        start_time = time.time()

        try:
            # Make the request
            response = requests.request(
                method=method,
                    url=url,
                    headers=request_headers,
                    params=params,
                    json=json_data,
                    files=files,
                    verify=verify,
                    timeout=timeout,
                )

            # Calculate request duration
            duration = time.time() - start_time

            # Update rate limits if provided in headers
            if "X-RateLimit-Remaining" in response.headers:
                self.rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])
                logger.debug(f"Rate limit remaining: {self.rate_limit_remaining}")
            if "X-RateLimit-Reset" in response.headers:
                self.rate_limit_reset = int(response.headers["X-RateLimit-Reset"])

            # Log response metadata
            logger.debug(f"Response received in {duration:.2f}s - Status: {response.status_code}")

            # Log headers at trace level (requires DEBUG or lower)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Response Headers: {dict(response.headers)}")

            # Check if token expired and re-authenticate
            if response.status_code == 401:
                if _retry_count < _max_retries:
                    logger.info(f"Authentication failed (attempt {_retry_count + 1}/{_max_retries}). Re-authenticating...")

                    # Increment retry counter
                    _retry_count += 1

                    # Reset token to force re-authentication
                    self.auth_token = None
                    self._authenticate()

                    # Update headers with the new token if custom headers weren't provided
                    if not headers:
                        request_headers = self.headers

                    # Retry the request with new token and incremented retry counter
                    return self._make_request(
                        method, endpoint, params, json_data, files, headers,
                        _retry_count=_retry_count, _max_retries=_max_retries
                    )
                else:
                    # Max retries reached
                    logger.error(f"Authentication failed after {_max_retries} attempts")
                    response.raise_for_status()

            # Handle errors with detailed logging
            response.raise_for_status()

            # Check if response is empty
            if response.status_code == 204 or not response.content:
                return {}

            # Parse JSON response
            response_json = response.json()

            # Log response data at trace level
            if logger.isEnabledFor(logging.DEBUG):
                # Truncate very large responses for logging
                if isinstance(response_json, dict) and (
                    "items" in response_json or "data" in response_json
                ):
                    data_key = "items" if "items" in response_json else "data"
                    values_count = len(response_json[data_key])
                    # Create a truncated version for logging if there are many values
                    if values_count > 10:
                        log_response = response_json.copy()
                        log_response[data_key] = log_response[data_key][:3]
                        log_response[data_key].append("... truncated for logging")
                        logger.debug(f"Response Body (truncated): {json.dumps(log_response)}")
                    else:
                        logger.debug(f"Response Body: {json.dumps(response_json)}")
                else:
                    logger.debug(f"Response Body: {json.dumps(response_json)}")

            return response_json

        except requests.exceptions.HTTPError as e:
            # Enhanced HTTP error logging
            logger.error(f"HTTP Error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_json = e.response.json()
                    logger.error(f"API Error Details: {error_json}")
                except ValueError:
                    logger.error(f"Response text: {e.response.text}")
            raise

        except requests.exceptions.ConnectionError:
            logger.error(f"Connection Error: Could not connect to {url}")
            raise

        except requests.exceptions.Timeout:
            logger.error(f"Timeout Error: Request to {url} timed out")
            raise

        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error: {e}")
            raise

        except ValueError as e:
            logger.error(f"JSON Parsing Error: {e}")
            raise

    def _mask_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Mask sensitive fields in data before logging."""
        if not isinstance(data, dict):
            return data

        # Create a copy to avoid modifying the original
        result = data.copy()

        # Fields to mask
        sensitive_fields = ["password", "token", "secret", "key", "auth", "credential"]

        # Mask sensitive fields
        for key in result:
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                result[key] = "********"
            elif isinstance(result[key], dict):
                result[key] = self._mask_sensitive_data(result[key])

        return result

    # QTest Manager API methods
    def get_projects(self) -> list[QTestProject]:
        """Get all projects.

        Returns:
            List of projects
        """
        endpoint = "/projects"
        response = self._make_request("GET", endpoint)

        projects_data = response.get("items", [])
        return [QTestProject(**project) for project in projects_data]

    def get_current_user_permission(self, project_id: int = None) -> dict[str, Any]:
        """
        Get current user permissions for a project.

        Args:
            project_id: Optional project ID (uses config project_id if not specified)

        Returns:
            Dict containing user permissions for the project
        """
        project_id = project_id or self.config.project_id
        endpoint = f"/projects/{project_id}/user-profiles/current"

        return self._make_request("GET", endpoint)

    def get_test_cases(
        self, module_id: int | None = None
    ) -> QTestPaginatedIterator[QTestTestCase]:
        """Get all test cases for a project or module.

        Args:
            module_id: Optional module ID to filter test cases

        Returns:
            Iterator of test cases
        """
        endpoint = f"/projects/{self.config.project_id}/test-cases"
        params = {}
        if module_id:
            params["parentId"] = module_id

        return QTestPaginatedIterator[QTestTestCase](
            client=self, endpoint=endpoint, model_class=QTestTestCase, params=params
        )

    def get_test_case(self, test_case_id: int) -> QTestTestCase:
        """Get a test case by ID.

        Args:
            test_case_id: ID of the test case

        Returns:
            Test case
        """
        endpoint = f"/projects/{self.config.project_id}/test-cases/{test_case_id}"
        response = self._make_request("GET", endpoint)
        return QTestTestCase(**response)

    def create_test_case(self, test_case: QTestTestCase) -> QTestTestCase:
        """Create a test case.

        Args:
            test_case: Test case to create

        Returns:
            Created test case
        """
        endpoint = f"/projects/{self.config.project_id}/test-cases"
        response = self._make_request(
            "POST", endpoint, json_data=test_case.model_dump(exclude_unset=True)
        )
        return QTestTestCase(**response)

    def get_test_cycles(self) -> QTestPaginatedIterator[QTestTestCycle]:
        """Get all test cycles for a project.

        Returns:
            Iterator of test cycles
        """
        endpoint = f"/projects/{self.config.project_id}/test-cycles"

        return QTestPaginatedIterator[QTestTestCycle](
            client=self, endpoint=endpoint, model_class=QTestTestCycle
        )

    def create_test_cycle(self, test_cycle: QTestTestCycle) -> QTestTestCycle:
        """Create a test cycle.

        Args:
            test_cycle: Test cycle to create

        Returns:
            Created test cycle
        """
        endpoint = f"/projects/{self.config.project_id}/test-cycles"
        response = self._make_request(
            "POST", endpoint, json_data=test_cycle.model_dump(exclude_unset=True)
        )
        return QTestTestCycle(**response)

    def submit_test_log(self, test_run_id: int, test_log: dict[str, Any]) -> dict[str, Any]:
        """Submit a test log for a test run.

        Args:
            test_run_id: ID of the test run
            test_log: Test log data

        Returns:
            Created test log
        """
        endpoint = f"/projects/{self.config.project_id}/test-runs/{test_run_id}/test-logs"
        return self._make_request("POST", endpoint, json_data=test_log)

    def get_modules(self) -> QTestPaginatedIterator[QTestModule]:
        """Get all modules for a project.

        Returns:
            Iterator of modules
        """
        endpoint = f"/projects/{self.config.project_id}/modules"

        return QTestPaginatedIterator[QTestModule](
            client=self, endpoint=endpoint, model_class=QTestModule
        )

    def create_module(self, module: QTestModule) -> QTestModule:
        """Create a module.

        Args:
            module: Module to create

        Returns:
            Created module
        """
        endpoint = f"/projects/{self.config.project_id}/modules"
        response = self._make_request(
            "POST", endpoint, json_data=module.model_dump(exclude_unset=True)
        )
        return QTestModule(**response)

    def upload_attachment(
        self, object_type: str, object_id: int, file_path: str | Path
    ) -> QTestAttachment:
        """Upload a file attachment to an object in qTest.

        Args:
            object_type: Type of object to attach to (test-cases, test-runs, test-logs)
            object_id: ID of the object
            file_path: Path to the file to upload

        Returns:
            Attachment information
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get file info
        filename = file_path.name
        content_type = "application/octet-stream"

        # Read file contents
        file_content = file_path.read_bytes()

        # Prepare the file for upload - qTest uses a different endpoint
        endpoint = f"/projects/{self.config.project_id}/{object_type}/{object_id}/blob-handles"

        # qTest uses multipart/form-data for file uploads
        files = {"file": (filename, file_content, content_type)}

        # Remove Content-Type from headers to let requests set it with boundary
        headers = self.headers.copy()
        headers.pop("Content-Type", None)

        response = self._make_request(
            method="POST", endpoint=endpoint, headers=headers, files=files
        )

        return QTestAttachment(**response)

    # QTest Parameters API methods
    def get_parameters(self) -> QTestPaginatedIterator[QTestParameter]:
        """Get all parameters for a project.

        Returns:
            Iterator of parameters
        """
        endpoint = "/parameters/query"
        query_data = {"projectId": self.config.project_id, "offset": 0, "limit": 50}

        # Parameters API uses POST for queries
        self._make_request("POST", endpoint, json_data=query_data)

        # Parameters API uses a different response format
        return QTestPaginatedIterator[QTestParameter](
            client=self, endpoint=endpoint, model_class=QTestParameter, params=query_data
        )

    def revoke_token(self) -> bool:
        """
        Revoke (logout) the current authentication token.

        Returns:
            bool: True if token was successfully revoked, False otherwise
        """
        logger.info("Revoking qTest API token")

        if not self.auth_token:
            logger.warning("No token to revoke")
            return False

        endpoint = "/oauth/revoke"

        try:
            # Make request to revoke token
            self._make_request("POST", endpoint)
            # Clear the token
            self.auth_token = None
            self.headers.pop("Authorization", None)
            logger.info("Token successfully revoked")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke token: {str(e)}")
            return False

    def verify_api_token(self, verify_ssl: bool = True) -> bool:
        """
        Verify that the API token is valid by making a simple API call.

        This is useful to check if the token retrieved from environment variables
        is valid and has the necessary permissions.

        Args:
            verify_ssl: Whether to verify SSL certificates (default True)

        Returns:
            bool: True if the token is valid, False otherwise
        """
        logger.info("Verifying qTest API token validity")

        try:
            # Make a lightweight request to verify the token
            # Use projects endpoint with explicit verify parameter
            endpoint = "/projects"
            self._make_request("GET", endpoint, verify=verify_ssl, timeout=(5.0, 10.0))
            logger.info("qTest API token verification successful")
            return True
        except Exception as e:
            logger.error(f"qTest API token verification failed: {str(e)}")
            return False

    def get_token_status(self) -> dict[str, Any]:
        """
        Get the status of the current authentication token.

        Returns:
            Dict with token status information:
            - expiration: timestamp when token expires
            - validityInMilliseconds: how long the token will be valid
        """
        logger.info("Getting token status")

        if not self.auth_token:
            logger.warning("No token available")
            return {"error": "No token available"}

        endpoint = "/oauth/status"

        try:
            # Make request to get token status
            response = self._make_request("GET", endpoint)
            logger.info(f"Token status retrieved successfully")
            return response
        except Exception as e:
            logger.error(f"Failed to get token status: {str(e)}")
            return {"error": str(e)}

    def check_api_health(self) -> dict[str, Any]:
        """
        Check the API health and connectivity.

        This method makes a lightweight request to the API to verify connectivity
        and measure latency.

        Returns:
            Dict containing health check results:
            - healthy: True if API is responding
            - latency_ms: Response time in milliseconds
            - error: Error message if health check failed
        """
        logger.debug("Performing API health check")

        # Initialize health info object
        health_info = {
            "healthy": False,
            "latency_ms": 0,
            "rate_limit_remaining": self.rate_limit_remaining,
            "rate_limit_reset": self.rate_limit_reset,
            "error": None
        }

        try:
            # Use a simple endpoint that should always work and is lightweight
            start_time = time.time()
            self.get_projects()

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Update health info
            health_info["healthy"] = True
            health_info["latency_ms"] = latency_ms

        except Exception as e:
            health_info["healthy"] = False
            health_info["error"] = f"{e.__class__.__name__}: {str(e)}"
            logger.warning(f"API health check failed: {health_info['error']}")

        return health_info

    def create_parameter(self, parameter: QTestParameter) -> QTestParameter:
        """Create a parameter.

        Args:
            parameter: Parameter to create

        Returns:
            Created parameter
        """
        endpoint = "/parameters/create"
        param_data = parameter.model_dump(exclude_unset=True)
        param_data["projectId"] = self.config.project_id

        response = self._make_request("POST", endpoint, json_data=param_data)
        return QTestParameter(**response.get("data", {}))

    def get_datasets(self) -> QTestPaginatedIterator[QTestDataset]:
        """Get all datasets for a project.

        Returns:
            Iterator of datasets
        """
        endpoint = "/data-sets/query"
        query_data = {"projectId": self.config.project_id, "offset": 0, "limit": 50}

        # Parameters API uses POST for queries
        self._make_request("POST", endpoint, json_data=query_data)

        # Parameters API uses a different response format
        return QTestPaginatedIterator[QTestDataset](
            client=self, endpoint=endpoint, model_class=QTestDataset, params=query_data
        )

    def create_dataset(self, dataset: QTestDataset) -> QTestDataset:
        """Create a dataset.

        Args:
            dataset: Dataset to create

        Returns:
            Created dataset
        """
        endpoint = "/data-sets/create"
        dataset_data = dataset.model_dump(exclude_unset=True)
        dataset_data["projectId"] = self.config.project_id

        response = self._make_request("POST", endpoint, json_data=dataset_data)
        return QTestDataset(**response.get("data", {}))

    # QTest Pulse API methods
    def get_pulse_rules(self) -> QTestPaginatedIterator[QTestPulseRule]:
        """Get all Pulse rules for a project.

        Returns:
            Iterator of Pulse rules
        """
        endpoint = "/pulse/rules"
        params = {"projectId": self.config.project_id, "offset": 0, "limit": 50}

        # Pulse API uses a different pagination approach
        return QTestPaginatedIterator[QTestPulseRule](
            client=self, endpoint=endpoint, model_class=QTestPulseRule, params=params
        )

    def get_pulse_rule(self, rule_id: int) -> QTestPulseRule:
        """Get a specific Pulse rule.

        Args:
            rule_id: Rule ID

        Returns:
            Pulse rule
        """
        endpoint = f"/pulse/rules/{rule_id}"
        response = self._make_request("GET", endpoint)
        # Handle the response structure where data is wrapped
        data = response.get("data", response)
        # Check if data is a list and take the first item if so
        if isinstance(data, list) and data:
            data = data[0]
        return QTestPulseRule(**data)

    def create_pulse_rule(self, rule: QTestPulseRule) -> QTestPulseRule:
        """Create a Pulse rule.

        Args:
            rule: Pulse rule to create

        Returns:
            Created Pulse rule
        """
        endpoint = "/pulse/rules"
        rule_data = rule.model_dump(exclude_unset=True)

        # Ensure project ID is set
        rule_data["projectId"] = self.config.project_id

        response = self._make_request("POST", endpoint, json_data=rule_data)
        # Handle the response structure where data is wrapped
        data = response.get("data", response)
        return QTestPulseRule(**data)

    def update_pulse_rule(self, rule_id: int, rule: QTestPulseRule) -> QTestPulseRule:
        """Update a Pulse rule.

        Args:
            rule_id: Rule ID to update
            rule: Updated rule data

        Returns:
            Updated Pulse rule
        """
        endpoint = f"/pulse/rules/{rule_id}"
        rule_data = rule.model_dump(exclude_unset=True)

        # Ensure rule ID is not in the payload
        rule_data.pop("id", None)

        response = self._make_request("PUT", endpoint, json_data=rule_data)
        # Handle the response structure where data is wrapped
        data = response.get("data", response)
        return QTestPulseRule(**data)

    def delete_pulse_rule(self, rule_id: int) -> bool:
        """Delete a Pulse rule.

        Args:
            rule_id: Rule ID to delete

        Returns:
            True if deletion was successful
        """
        endpoint = f"/pulse/rules/{rule_id}"
        self._make_request("DELETE", endpoint)
        return True

    def get_pulse_triggers(self) -> QTestPaginatedIterator[QTestPulseTrigger]:
        """Get all Pulse triggers for a project.

        Returns:
            Iterator of Pulse triggers
        """
        endpoint = "/pulse/triggers"
        params = {"projectId": self.config.project_id, "offset": 0, "limit": 50}

        return QTestPaginatedIterator[QTestPulseTrigger](
            client=self, endpoint=endpoint, model_class=QTestPulseTrigger, params=params
        )

    def get_pulse_trigger(self, trigger_id: int) -> QTestPulseTrigger:
        """Get a specific Pulse trigger.

        Args:
            trigger_id: Trigger ID

        Returns:
            Pulse trigger
        """
        endpoint = f"/pulse/triggers/{trigger_id}"
        response = self._make_request("GET", endpoint)
        # Handle the response structure where data is wrapped
        data = response.get("data", response)
        # Check if data is a list and take the first item if so
        if isinstance(data, list) and data:
            data = data[0]
        return QTestPulseTrigger(**data)

    def create_pulse_trigger(self, trigger: QTestPulseTrigger) -> QTestPulseTrigger:
        """Create a Pulse trigger.

        Args:
            trigger: Pulse trigger to create

        Returns:
            Created Pulse trigger
        """
        endpoint = "/pulse/triggers"
        trigger_data = trigger.model_dump(exclude_unset=True)

        # Ensure project ID is set
        trigger_data["projectId"] = self.config.project_id

        response = self._make_request("POST", endpoint, json_data=trigger_data)
        # Handle the response structure where data is wrapped
        data = response.get("data", response)
        return QTestPulseTrigger(**data)

    def update_pulse_trigger(self, trigger_id: int, trigger: QTestPulseTrigger) -> QTestPulseTrigger:
        """Update a Pulse trigger.

        Args:
            trigger_id: Trigger ID to update
            trigger: Updated trigger data

        Returns:
            Updated Pulse trigger
        """
        endpoint = f"/pulse/triggers/{trigger_id}"
        trigger_data = trigger.model_dump(exclude_unset=True)

        # Ensure trigger ID is not in the payload
        trigger_data.pop("id", None)

        response = self._make_request("PUT", endpoint, json_data=trigger_data)
        # Handle the response structure where data is wrapped
        data = response.get("data", response)
        return QTestPulseTrigger(**data)

    def delete_pulse_trigger(self, trigger_id: int) -> bool:
        """Delete a Pulse trigger.

        Args:
            trigger_id: Trigger ID to delete

        Returns:
            True if deletion was successful
        """
        endpoint = f"/pulse/triggers/{trigger_id}"
        self._make_request("DELETE", endpoint)
        return True

    def get_pulse_actions(self) -> QTestPaginatedIterator[QTestPulseAction]:
        """Get all Pulse actions for a project.

        Returns:
            Iterator of Pulse actions
        """
        endpoint = "/pulse/actions"
        params = {"projectId": self.config.project_id, "offset": 0, "limit": 50}

        return QTestPaginatedIterator[QTestPulseAction](
            client=self, endpoint=endpoint, model_class=QTestPulseAction, params=params
        )

    def get_pulse_action(self, action_id: int) -> QTestPulseAction:
        """Get a specific Pulse action.

        Args:
            action_id: Action ID

        Returns:
            Pulse action
        """
        endpoint = f"/pulse/actions/{action_id}"
        response = self._make_request("GET", endpoint)
        # Handle the response structure where data is wrapped
        data = response.get("data", response)
        # Check if data is a list and take the first item if so
        if isinstance(data, list) and data:
            data = data[0]
        return QTestPulseAction(**data)

    def create_pulse_action(self, action: QTestPulseAction) -> QTestPulseAction:
        """Create a Pulse action.

        Args:
            action: Pulse action to create

        Returns:
            Created Pulse action
        """
        endpoint = "/pulse/actions"
        action_data = action.model_dump(exclude_unset=True)

        # Ensure project ID is set
        action_data["projectId"] = self.config.project_id

        response = self._make_request("POST", endpoint, json_data=action_data)
        # Handle the response structure where data is wrapped
        data = response.get("data", response)
        return QTestPulseAction(**data)

    def update_pulse_action(self, action_id: int, action: QTestPulseAction) -> QTestPulseAction:
        """Update a Pulse action.

        Args:
            action_id: Action ID to update
            action: Updated action data

        Returns:
            Updated Pulse action
        """
        endpoint = f"/pulse/actions/{action_id}"
        action_data = action.model_dump(exclude_unset=True)

        # Ensure action ID is not in the payload
        action_data.pop("id", None)

        response = self._make_request("PUT", endpoint, json_data=action_data)
        # Handle the response structure where data is wrapped
        data = response.get("data", response)
        return QTestPulseAction(**data)

    def delete_pulse_action(self, action_id: int) -> bool:
        """Delete a Pulse action.

        Args:
            action_id: Action ID to delete

        Returns:
            True if deletion was successful
        """
        endpoint = f"/pulse/actions/{action_id}"
        self._make_request("DELETE", endpoint)
        return True

    def get_pulse_constants(self) -> QTestPaginatedIterator[QTestPulseConstant]:
        """Get all Pulse constants for a project.

        Returns:
            Iterator of Pulse constants
        """
        endpoint = "/pulse/constants"
        params = {"projectId": self.config.project_id, "offset": 0, "limit": 50}

        return QTestPaginatedIterator[QTestPulseConstant](
            client=self, endpoint=endpoint, model_class=QTestPulseConstant, params=params
        )

    def download_attachment(self, attachment_id: int, file_path: str) -> bool:
        """
        Download an attachment by ID and save it to the specified file path.

        Args:
            attachment_id: ID of the attachment to download
            file_path: Local file path to save the attachment to

        Returns:
            True if download successful, False otherwise
        """
        endpoint = f"/attachments/{attachment_id}"

        logger.info(f"Downloading attachment {attachment_id} to {file_path}")

        try:
            # Make binary request
            response = requests.get(
                url=f"{self.config.base_url}/api/v3{endpoint}",
                headers=self.headers,
                stream=True
            )

            response.raise_for_status()

            # Check content type
            content_type = response.headers.get('Content-Type', 'application/octet-stream')
            logger.debug(f"Attachment content type: {content_type}")

            # Save file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Attachment downloaded successfully to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download attachment: {e}")
            return False

    def get_pulse_constant(self, constant_id: int) -> QTestPulseConstant:
        """Get a specific Pulse constant.

        Args:
            constant_id: Constant ID

        Returns:
            Pulse constant
        """
        endpoint = f"/pulse/constants/{constant_id}"
        response = self._make_request("GET", endpoint)
        # Handle the response structure where data is wrapped
        data = response.get("data", response)
        # Check if data is a list and take the first item if so
        if isinstance(data, list) and data:
            data = data[0]
        return QTestPulseConstant(**data)

    def create_pulse_constant(self, constant: QTestPulseConstant) -> QTestPulseConstant:
        """Create a Pulse constant.

        Args:
            constant: Pulse constant to create

        Returns:
            Created Pulse constant
        """
        endpoint = "/pulse/constants"
        constant_data = constant.model_dump(exclude_unset=True)

        # Ensure project ID is set
        constant_data["projectId"] = self.config.project_id

        response = self._make_request("POST", endpoint, json_data=constant_data)
        # Handle the response structure where data is wrapped
        data = response.get("data", response)
        return QTestPulseConstant(**data)

    def update_pulse_constant(self, constant_id: int, constant: QTestPulseConstant) -> QTestPulseConstant:
        """Update a Pulse constant.

        Args:
            constant_id: Constant ID to update
            constant: Updated constant data

        Returns:
            Updated Pulse constant
        """
        endpoint = f"/pulse/constants/{constant_id}"
        constant_data = constant.model_dump(exclude_unset=True)

        # Ensure constant ID is not in the payload
        constant_data.pop("id", None)

        response = self._make_request("PUT", endpoint, json_data=constant_data)
        # Handle the response structure where data is wrapped
        data = response.get("data", response)
        return QTestPulseConstant(**data)

    def delete_pulse_constant(self, constant_id: int) -> bool:
        """Delete a Pulse constant.

        Args:
            constant_id: Constant ID to delete

        Returns:
            True if deletion was successful
        """
        endpoint = f"/pulse/constants/{constant_id}"
        self._make_request("DELETE", endpoint)
        return True

    def execute_pulse_rule_manually(self, rule_id: int) -> bool:
        """Execute a Pulse rule manually.

        Args:
            rule_id: Rule ID to execute

        Returns:
            True if execution was successful
        """
        endpoint = f"/pulse/rules/{rule_id}/execute"
        self._make_request("POST", endpoint)
        return True
    def get_rules(self) -> list[dict[str, Any]]:
        """Get all rules for a project.

        Returns:
            List of rules
        """
        endpoint = "/rules"
        params = {"projectId": self.config.project_id}

        response = self._make_request("GET", endpoint, params=params)
        return response.get("data", [])

    def create_rule(self, rule_data: dict[str, Any]) -> dict[str, Any]:
        """Create a rule in Pulse.

        Args:
            rule_data: Rule data

        Returns:
            Created rule
        """
        endpoint = "/rules"
        rule_data["projectId"] = self.config.project_id

        response = self._make_request("POST", endpoint, json_data=rule_data)
        return response.get("data", {})

    # QTest Scenario API methods
    def get_features(self) -> list[dict[str, Any]]:
        """Get all features for a project.

        Returns:
            List of features
        """
        endpoint = "/features"
        params = {"projectId": self.config.project_id}

        response = self._make_request("GET", endpoint, params=params)
        return response.get("data", [])

    def create_feature(self, feature_data: dict[str, Any]) -> dict[str, Any]:
        """Create a feature in Scenario.

        Args:
            feature_data: Feature data

        Returns:
            Created feature
        """
        endpoint = "/features"
        feature_data["projectId"] = self.config.project_id

        response = self._make_request("POST", endpoint, json_data=feature_data)
        return response.get("data", {})
