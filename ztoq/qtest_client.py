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

import uuid
import datetime
from pathlib import Path
from typing import Any, Dict, Generic, Optional, TypeVar, cast
from contextvars import ContextVar
import requests

# Temporarily removed: from ztoq.qtest_retry import with_retry, QTestRetryPolicy, QTestCircuitBreaker
from ztoq.qtest_models import (
    QTestAttachment,
    QTestConfig,
    QTestCustomField,
    QTestDataset,
    QTestLink,
    QTestModule,
    QTestPaginatedResponse,
    QTestParameter,
    QTestProject,
    QTestPulseAction,
    QTestPulseConstant,
    QTestPulseRule,
    QTestPulseTrigger,
    QTestStep,
    QTestTestCase,
    QTestTestCycle,
    QTestTestRun,
)

T = TypeVar("T")

# Context variable to track correlation ID throughout async/threaded code
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")

# Configure module logger
logger = logging.getLogger("ztoq.qtest_client")

# Define pagination constants
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000

class CorrelationIDFilter(logging.Filter):
    """
    Logging filter that adds correlation ID to log records.

    This filter enriches log records with the current correlation ID from the context,
    enabling request tracing across asynchronous and threaded operations.
    """

    def filter(self, record):
        # Add correlation_id to the log record
        record.correlation_id = correlation_id.get() or "-"
        return True

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
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - [%(correlation_id)s] - %(levelname)s - %(message)s"
    )

    # Add correlation ID filter
    correlation_filter = CorrelationIDFilter()

    # Clear existing handlers to prevent duplicates when reconfiguring
    if logger.handlers:
        for h in logger.handlers[:]:
            logger.removeHandler(h)

    handler.setFormatter(formatter)
    logger.addFilter(correlation_filter)
    logger.setLevel(numeric_level)
    logger.addHandler(handler)

    # Log the configuration
    logger.debug(f"Logging configured with level: {level}")

def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID for request tracing.

    Returns:
        A unique string identifier in the format: YYYY-MM-DD-HH-MM-SS-uuid
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_id = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID for brevity
    return f"{timestamp}-{unique_id}"

def set_correlation_id(corr_id: Optional[str] = None) -> str:
    """
    Set the current correlation ID for request tracing.

    Args:
        corr_id: Correlation ID to use. If None, generates a new one.

    Returns:
        The correlation ID that was set
    """
    corr_id = corr_id or generate_correlation_id()
    correlation_id.set(corr_id)
    return corr_id

def get_correlation_id() -> str:
    """
    Get the current correlation ID.

    Returns:
        The current correlation ID, or empty string if none is set.
    """
    return correlation_id.get()

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

        # Handle different response formats - either a dict with pagination or a direct list
        if isinstance(response, list):
            # Direct list of items
            self.current_page = QTestPaginatedResponse(
                items=response,
                page=0,
                page_size=len(response),
                total=len(response),
                is_last=True,  # Assume this is the only page when the response is a list
            )
        # Handle different pagination formats depending on API type
        elif self.client.api_type == "manager" and isinstance(response, dict):
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

    def __init__(
        self,
        config: QTestConfig,
        api_type: str = "manager",
        log_level=None,
        correlation_id: Optional[str] = None,
    ):
        """Initialize the qTest client with configuration.

        Args:
            config: The qTest API configuration
            api_type: The qTest API type (manager, parameters, pulse, scenario)
            log_level: Optional logging level to use for this client instance
                      (e.g., "DEBUG", "INFO", "WARNING", "ERROR")
            correlation_id: Optional correlation ID for request tracing
        """
        # Set correlation ID for this client instance
        self.correlation_id = set_correlation_id(correlation_id)

        self.config = config
        self.api_type = api_type.lower()
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        self.auth_token = None
        self.rate_limit_remaining = 1000  # Default high value
        self.rate_limit_reset = 0

        # Request metrics for logging and monitoring
        self.request_count = 0
        self.error_count = 0
        self.last_request_time = 0
        self.total_request_time = 0

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

        logger.info(
            f"QTestClient initialized: project={config.project_id}, "
            f"url={config.base_url}, api_type={api_type}"
        )

        # Authenticate immediately
        self._authenticate()

    def _authenticate(self):
        """Authenticate with qTest API and obtain an access token."""
        # If bearer token is already provided in config, use it directly
        if hasattr(self.config, "bearer_token") and self.config.bearer_token:
            token = self.config.bearer_token.strip()

            # Handle case where token already includes "bearer" prefix
            if token.lower().startswith("bearer "):
                # Extract just the token part, removing "bearer "
                self.auth_token = token[7:].strip()
                self.headers["Authorization"] = f"Bearer {self.auth_token}"
            else:
                # Use token as-is but add Bearer prefix
                self.auth_token = token
                self.headers["Authorization"] = f"Bearer {self.auth_token}"

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
            "Cache-Control": "no-cache",
        }

        # Add basic auth header with client name (any string)
        client_name_encoded = base64.b64encode(b"ztoq-client:").decode("utf-8")
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
                response = requests.post(url=url, headers=auth_headers, json=auth_data)
            else:
                # Manager API uses form data
                response = requests.post(url=url, headers=auth_headers, data=auth_data)

            response.raise_for_status()
            data = response.json()

            # Get token from response
            token_type = data.get("token_type", "bearer").lower()
            self.auth_token = data.get("access_token")
            if not self.auth_token:
                raise ValueError("No access token returned from authentication endpoint")

            # Set authorization header with proper token format, always using "Bearer" with proper capitalization
            self.headers["Authorization"] = f"Bearer {self.auth_token}"

            logger.info(f"Successfully authenticated with {self.api_type} API")
            logger.debug(
                f"Token type: {token_type}, expires in: {data.get('expires_in', 'unknown')} seconds"
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise

    # Temporarily removed: @QTestCircuitBreaker(failure_threshold=5, reset_timeout=60)
    # Temporarily removed: retry mechanism
    # Previous config:
    # max_retries=3,
    # retry_delay=0.5,
    # backoff_factor=2.0,
    # jitter=True,
    # retry_on_codes={401, 429, 500, 502, 503, 504}
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
        _request_id: Optional[str] = None,
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
            _retry_count: Internal counter for token refresh attempts
            _max_retries: Maximum token refresh attempts
            _request_id: Internal request ID for correlation

        Returns:
            API response as dictionary
        """
        # Generate a request-specific ID for correlation if not provided
        # This allows tracing individual requests even when retried
        request_id = _request_id or f"req-{generate_correlation_id()}"

        # Set request-specific correlation ID that inherits client correlation ID
        set_correlation_id(f"{self.correlation_id}:{request_id}")

        # Update request metrics
        self.request_count += 1
        request_number = self.request_count

        # Check rate limits - this happens before we even attempt the request
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
        request_headers = headers or self.headers.copy()

        # Add correlation ID header for tracing through systems
        request_headers["X-Correlation-ID"] = get_correlation_id()

        # Log request details (careful not to log sensitive data)
        safe_headers = {k: v for k, v in request_headers.items() if k.lower() != "authorization"}
        logger.info(
            f"API Request #{request_number}: {method} {endpoint} "
            + f"(retry {_retry_count}/{_max_retries})"
        )
        logger.debug(f"Full URL: {url}")
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

            # Update request metrics
            self.last_request_time = duration
            self.total_request_time += duration

            # Update rate limits if provided in headers
            if "X-RateLimit-Remaining" in response.headers:
                self.rate_limit_remaining = int(response.headers["X-RateLimit-Remaining"])
                logger.debug(f"Rate limit remaining: {self.rate_limit_remaining}")
            if "X-RateLimit-Reset" in response.headers:
                self.rate_limit_reset = int(response.headers["X-RateLimit-Reset"])

            # Extract correlation ID from response if present
            response_correlation_id = response.headers.get("X-Correlation-ID", "")
            if response_correlation_id and response_correlation_id != get_correlation_id():
                logger.debug(f"Server correlation ID: {response_correlation_id}")

            # Log response metadata
            logger.info(
                f"Response #{request_number} received in {duration:.2f}s - "
                + f"Status: {response.status_code} - {method} {endpoint}"
            )

            # Log headers at trace level
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Response Headers: {dict(response.headers)}")

            # Special handling for 401 Unauthorized - likely token expiration
            # This is outside the retry decorator to handle token refresh specially
            if response.status_code == 401:
                if _retry_count < _max_retries:
                    logger.info(
                        f"Authentication failed (attempt {_retry_count + 1}/{_max_retries}). Re-authenticating..."
                    )

                    # Increment retry counter
                    _retry_count += 1

                    # Reset token to force re-authentication
                    self.auth_token = None
                    self._authenticate()

                    # Update headers with the new token if custom headers weren't provided
                    if not headers:
                        request_headers = self.headers.copy()
                        # Preserve correlation ID
                        request_headers["X-Correlation-ID"] = get_correlation_id()

                    # Retry the request with new token and incremented retry counter
                    # Note: This will bypass the retry decorator since we're handling this case specially
                    return self._make_request(
                        method,
                        endpoint,
                        params,
                        json_data,
                        files,
                        headers,
                        verify,
                        timeout,
                        _retry_count=_retry_count,
                        _max_retries=_max_retries,
                        _request_id=request_id,
                    )
                else:
                    # Max auth retries reached - this is terminal
                    logger.error(f"Authentication failed after {_max_retries} attempts")
                    self.error_count += 1
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
            self.error_count += 1
            logger.error(
                f"HTTP Error #{request_number}: {e} - "
                + f"{method} {endpoint} - Duration: {time.time() - start_time:.2f}s"
            )
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_json = e.response.json()
                    logger.error(f"API Error Details: {error_json}")
                except ValueError:
                    logger.error(f"Response text: {e.response.text}")
            raise

        except requests.exceptions.ConnectionError:
            self.error_count += 1
            logger.error(
                f"Connection Error #{request_number}: Could not connect to {url} - "
                + f"{method} {endpoint} - Duration: {time.time() - start_time:.2f}s"
            )
            raise

        except requests.exceptions.Timeout:
            self.error_count += 1
            logger.error(
                f"Timeout Error #{request_number}: Request to {url} timed out - "
                + f"{method} {endpoint} - Duration: {time.time() - start_time:.2f}s"
            )
            raise

        except requests.exceptions.RequestException as e:
            self.error_count += 1
            logger.error(
                f"Request Error #{request_number}: {e} - "
                + f"{method} {endpoint} - Duration: {time.time() - start_time:.2f}s"
            )
            raise

        except ValueError as e:
            self.error_count += 1
            logger.error(
                f"JSON Parsing Error #{request_number}: {e} - "
                + f"{method} {endpoint} - Duration: {time.time() - start_time:.2f}s"
            )
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

        # Handle both response formats - either a list of projects directly or an object with "items" property
        if isinstance(response, list):
            projects_data = response
        else:
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

    def get_test_cases(self, module_id: int | None = None) -> QTestPaginatedIterator[QTestTestCase]:
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

    def update_test_case(self, test_case_id: int, test_case: QTestTestCase) -> QTestTestCase:
        """Update an existing test case.

        Args:
            test_case_id: ID of the test case to update
            test_case: Updated test case data

        Returns:
            Updated test case
        """
        endpoint = f"/projects/{self.config.project_id}/test-cases/{test_case_id}"

        # Create a copy of the test case data, excluding the ID to avoid conflicts
        update_data = test_case.model_dump(exclude_unset=True)
        update_data.pop("id", None)  # Remove ID if present

        response = self._make_request("PUT", endpoint, json_data=update_data)
        return QTestTestCase(**response)

    def delete_test_case(self, test_case_id: int) -> bool:
        """Delete a test case.

        Args:
            test_case_id: ID of the test case to delete

        Returns:
            True if deletion was successful
        """
        endpoint = f"/projects/{self.config.project_id}/test-cases/{test_case_id}"
        self._make_request("DELETE", endpoint)
        return True

    def get_attachments(self, object_type: str, object_id: int) -> list[QTestAttachment]:
        """Get all attachments for an object in qTest.

        Args:
            object_type: Type of object to get attachments for (test-cases, test-runs, test-logs, requirements, defects)
            object_id: ID of the object

        Returns:
            List of attachments as QTestAttachment objects

        Raises:
            ValueError: If object_type is invalid
        """
        # Validate object type
        valid_object_types = [
            "test-cases",
            "test-runs",
            "test-logs",
            "requirements",
            "defects",
            "test-steps",
        ]
        if object_type not in valid_object_types:
            raise ValueError(
                f"Invalid object type: {object_type}. Must be one of: {', '.join(valid_object_types)}"
            )

        endpoint = f"/projects/{self.config.project_id}/{object_type}/{object_id}/attachments"

        try:
            response = self._make_request("GET", endpoint)

            # Handle different response formats
            if isinstance(response, list):
                attachments_data = response
            else:
                attachments_data = response.get("items", [])

            attachments = [QTestAttachment(**attachment) for attachment in attachments_data]

            # Log the number of attachments found
            logger.debug(f"Found {len(attachments)} attachments for {object_type}/{object_id}")

            return attachments
        except Exception as e:
            logger.error(f"Failed to get attachments for {object_type}/{object_id}: {str(e)}")
            raise

    def get_test_case_attachments(self, test_case_id: int) -> list[QTestAttachment]:
        """Get all attachments for a test case.

        Args:
            test_case_id: ID of the test case

        Returns:
            List of attachments
        """
        return self.get_attachments("test-cases", test_case_id)

    def get_test_run_attachments(self, test_run_id: int) -> list[QTestAttachment]:
        """Get all attachments for a test run.

        Args:
            test_run_id: Test run ID

        Returns:
            List of attachments
        """
        return self.get_attachments("test-runs", test_run_id)

    def get_test_log_attachments(self, test_log_id: int) -> list[QTestAttachment]:
        """Get all attachments for a test log.

        Args:
            test_log_id: Test log ID

        Returns:
            List of attachments
        """
        return self.get_attachments("test-logs", test_log_id)

    def delete_attachment(self, attachment_id: int) -> bool:
        """Delete an attachment by ID.

        Args:
            attachment_id: ID of the attachment to delete

        Returns:
            True if deletion was successful
        """
        endpoint = f"/attachments/{attachment_id}"

        try:
            self._make_request("DELETE", endpoint)
            logger.info(f"Successfully deleted attachment with ID {attachment_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete attachment {attachment_id}: {str(e)}")
            return False

    def get_attachment_info(self, attachment_id: int) -> QTestAttachment:
        """Get information about a specific attachment by ID.

        Args:
            attachment_id: ID of the attachment to get information for

        Returns:
            QTestAttachment object with metadata about the attachment
        """
        endpoint = f"/attachments/{attachment_id}"

        try:
            response = self._make_request("GET", endpoint)

            # Handle response structure where data is sometimes wrapped
            if isinstance(response, dict) and "id" not in response and "data" in response:
                response = response["data"]

            return QTestAttachment(**response)
        except Exception as e:
            logger.error(f"Failed to get attachment info for ID {attachment_id}: {str(e)}")
            raise

    def upload_multiple_attachments(
        self,
        object_type: str,
        object_id: int,
        file_paths: list[str | Path],
        verify: bool = True,
        timeout: tuple[float, float] = None,
        continue_on_error: bool = True,
    ) -> list[QTestAttachment]:
        """Upload multiple files as attachments to an object in qTest.

        Args:
            object_type: Type of object to attach to
            object_id: ID of the object
            file_paths: List of file paths to upload
            verify: Whether to verify SSL certificates
            timeout: Request timeout as (connect_timeout, read_timeout) tuple
            continue_on_error: Whether to continue uploading if an individual file upload fails

        Returns:
            List of QTestAttachment objects for the uploaded files

        Note:
            Files are uploaded sequentially, not in parallel. For parallel uploads,
            use the upload_attachments_parallel method.
        """
        # Validate object type
        valid_object_types = [
            "test-cases",
            "test-runs",
            "test-logs",
            "requirements",
            "defects",
            "test-steps",
        ]
        if object_type not in valid_object_types:
            raise ValueError(
                f"Invalid object type: {object_type}. Must be one of: {', '.join(valid_object_types)}"
            )

        if not file_paths:
            return []

        logger.info(f"Uploading {len(file_paths)} files to {object_type}/{object_id}")

        attachments = []
        for file_path in file_paths:
            try:
                attachment = self.upload_attachment(
                    object_type=object_type,
                    object_id=object_id,
                    file_path=file_path,
                    verify=verify,
                    timeout=timeout,
                )
                attachments.append(attachment)
            except Exception as e:
                logger.error(f"Failed to upload {file_path}: {str(e)}")
                if not continue_on_error:
                    raise

        logger.info(f"Successfully uploaded {len(attachments)} of {len(file_paths)} files")
        return attachments

    def upload_attachments_parallel(
        self,
        object_type: str,
        object_id: int,
        file_paths: list[str | Path],
        max_workers: int = 5,
        verify: bool = True,
        timeout: tuple[float, float] = None,
    ) -> list[QTestAttachment]:
        """Upload multiple files as attachments to an object in qTest using parallel processing.

        This method uses concurrent.futures to upload multiple files in parallel, which
        can significantly improve performance for large numbers of attachments.

        Args:
            object_type: Type of object to attach to
            object_id: ID of the object
            file_paths: List of file paths to upload
            max_workers: Maximum number of concurrent uploads (default: 5)
            verify: Whether to verify SSL certificates
            timeout: Request timeout as (connect_timeout, read_timeout) tuple

        Returns:
            List of QTestAttachment objects for the uploaded files

        Note:
            Too many concurrent uploads may trigger rate limits or connection issues.
            The default max_workers of 5 is a reasonable balance for most API environments.
        """
        import concurrent.futures

        # Validate object type
        valid_object_types = [
            "test-cases",
            "test-runs",
            "test-logs",
            "requirements",
            "defects",
            "test-steps",
        ]
        if object_type not in valid_object_types:
            raise ValueError(
                f"Invalid object type: {object_type}. Must be one of: {', '.join(valid_object_types)}"
            )

        if not file_paths:
            return []

        logger.info(
            f"Parallel uploading {len(file_paths)} files to {object_type}/{object_id} with {max_workers} workers"
        )

        # Define the worker function that will be executed in parallel
        def upload_worker(file_path):
            try:
                return self.upload_attachment(
                    object_type=object_type,
                    object_id=object_id,
                    file_path=file_path,
                    verify=verify,
                    timeout=timeout,
                    report_progress=False,  # Disable progress reporting in parallel mode to avoid log clutter
                )
            except Exception as e:
                logger.error(f"Failed to upload {file_path}: {str(e)}")
                return None

        # Execute uploads in parallel
        successful_attachments = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(upload_worker, file_path): file_path for file_path in file_paths
            }

            completed = 0
            for future in concurrent.futures.as_completed(future_to_file):
                file_path = future_to_file[future]
                completed += 1

                # Log progress every 10% or for every file if there are few files
                if len(file_paths) <= 10 or completed % max(1, len(file_paths) // 10) == 0:
                    logger.info(
                        f"Progress: {completed}/{len(file_paths)} files processed ({completed/len(file_paths)*100:.1f}%)"
                    )

                try:
                    attachment = future.result()
                    if attachment:
                        successful_attachments.append(attachment)
                except Exception as e:
                    logger.error(
                        f"Exception occurred during parallel upload of {file_path}: {str(e)}"
                    )

        logger.info(
            f"Parallel upload complete. Successfully uploaded {len(successful_attachments)} of {len(file_paths)} files"
        )
        return successful_attachments

    def bulk_create_test_cases(self, test_cases: list[QTestTestCase]) -> list[QTestTestCase]:
        """Create multiple test cases in a single batch request.

        Args:
            test_cases: List of test cases to create

        Returns:
            List of created test cases
        """
        endpoint = f"/projects/{self.config.project_id}/test-cases/bulk"

        # Convert test cases to dicts, excluding unset fields
        test_case_data = [tc.model_dump(exclude_unset=True) for tc in test_cases]

        response = self._make_request("POST", endpoint, json_data=test_case_data)

        # Return list of QTestTestCase objects
        return [QTestTestCase(**tc_data) for tc_data in response]

    def get_test_case_links(self, test_case_id: int) -> list[QTestLink]:
        """Get all links for a test case.

        Args:
            test_case_id: ID of the test case

        Returns:
            List of links
        """
        endpoint = f"/projects/{self.config.project_id}/test-cases/{test_case_id}/links"
        response = self._make_request("GET", endpoint)

        # Handle different response formats
        if isinstance(response, list):
            links_data = response
        else:
            links_data = response.get("items", [])

        return [QTestLink(**link) for link in links_data]

    def add_link_to_test_case(self, test_case_id: int, link: QTestLink) -> QTestLink:
        """Add a link to a test case.

        Args:
            test_case_id: ID of the test case
            link: Link to add

        Returns:
            Created link
        """
        endpoint = f"/projects/{self.config.project_id}/test-cases/{test_case_id}/links"

        # Convert link to dict, excluding unset fields and ID
        link_data = link.model_dump(exclude_unset=True)
        link_data.pop("id", None)  # Remove ID if present

        response = self._make_request("POST", endpoint, json_data=link_data)
        return QTestLink(**response)

    def search_test_cases(self, search_criteria: dict[str, Any]) -> list[QTestTestCase]:
        """Search for test cases with specific criteria.

        Args:
            search_criteria: Dictionary containing search parameters
                Possible keys include:
                - name: String to search in test case names
                - properties: List of property objects to match
                - module_ids: List of module IDs to search in
                - created_from: ISO-8601 datetime string for creation date range start
                - created_to: ISO-8601 datetime string for creation date range end

        Returns:
            List of matching test cases
        """
        endpoint = f"/projects/{self.config.project_id}/test-cases/search"

        response = self._make_request("POST", endpoint, json_data=search_criteria)

        # Handle different response formats
        if isinstance(response, list):
            test_cases_data = response
        else:
            test_cases_data = response.get("items", [])

        # Convert property format to match model expectations
        for tc in test_cases_data:
            if "properties" in tc and isinstance(tc["properties"], list):
                for prop in tc["properties"]:
                    # Convert field_* properties to standard names if needed
                    if "field_id" in prop and "id" not in prop:
                        prop["id"] = prop.pop("field_id")
                    if "field_name" in prop and "name" not in prop:
                        prop["name"] = prop.pop("field_name")
                    if "field_value" in prop and "value" not in prop:
                        prop["value"] = prop.pop("field_value")
                    if "field_type" in prop and "type" not in prop:
                        prop["type"] = prop.pop("field_type")

        return [QTestTestCase(**tc) for tc in test_cases_data]

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

    def get_test_cycle(self, test_cycle_id: int) -> QTestTestCycle:
        """Get a test cycle by ID.

        Args:
            test_cycle_id: ID of the test cycle

        Returns:
            Test cycle
        """
        endpoint = f"/projects/{self.config.project_id}/test-cycles/{test_cycle_id}"
        response = self._make_request("GET", endpoint)
        return QTestTestCycle(**response)

    def update_test_cycle(self, test_cycle_id: int, test_cycle: QTestTestCycle) -> QTestTestCycle:
        """Update an existing test cycle.

        Args:
            test_cycle_id: ID of the test cycle to update
            test_cycle: Updated test cycle data

        Returns:
            Updated test cycle
        """
        endpoint = f"/projects/{self.config.project_id}/test-cycles/{test_cycle_id}"

        # Create a copy of the test cycle data, excluding the ID to avoid conflicts
        update_data = test_cycle.model_dump(exclude_unset=True)
        update_data.pop("id", None)  # Remove ID if present

        response = self._make_request("PUT", endpoint, json_data=update_data)
        return QTestTestCycle(**response)

    def delete_test_cycle(self, test_cycle_id: int) -> bool:
        """Delete a test cycle.

        Args:
            test_cycle_id: ID of the test cycle to delete

        Returns:
            True if deletion was successful
        """
        endpoint = f"/projects/{self.config.project_id}/test-cycles/{test_cycle_id}"
        self._make_request("DELETE", endpoint)
        return True

    def get_test_runs_for_cycle(
        self, test_cycle_id: int, params: dict[str, Any] | None = None
    ) -> QTestPaginatedIterator:
        """Get all test runs for a specific test cycle.

        Args:
            test_cycle_id: ID of the test cycle
            params: Additional query parameters

        Returns:
            Iterator of test runs
        """
        endpoint = f"/projects/{self.config.project_id}/test-runs"
        query_params = params or {}
        query_params["parentId"] = test_cycle_id

        # Use the QTestTestRun model imported at the top of the file

        return QTestPaginatedIterator[QTestTestRun](
            client=self, endpoint=endpoint, model_class=QTestTestRun, params=query_params
        )

    def get_child_test_cycles(self, parent_id: int) -> QTestPaginatedIterator[QTestTestCycle]:
        """Get all child test cycles for a parent cycle.

        Args:
            parent_id: ID of the parent test cycle

        Returns:
            Iterator of child test cycles
        """
        endpoint = f"/projects/{self.config.project_id}/test-cycles"
        params = {"parentId": parent_id}

        return QTestPaginatedIterator[QTestTestCycle](
            client=self, endpoint=endpoint, model_class=QTestTestCycle, params=params
        )

    def add_test_cases_to_cycle(
        self, test_cycle_id: int, test_case_ids: list[int]
    ) -> dict[str, Any]:
        """Add test cases to a test cycle, creating test runs.

        Args:
            test_cycle_id: ID of the test cycle
            test_case_ids: List of test case IDs to add

        Returns:
            Dictionary containing information about the operation:
            - total: Total number of test cases
            - created: Number of test runs created
            - failed: Number of failures
            - ids: List of created test run IDs
        """
        endpoint = f"/projects/{self.config.project_id}/test-cycles/{test_cycle_id}/test-runs"
        request_data = {"testCaseIds": test_case_ids}
        return self._make_request("POST", endpoint, json_data=request_data)

    def search_test_cycles(self, search_criteria: dict[str, Any]) -> list[QTestTestCycle]:
        """Search for test cycles with specific criteria.

        Args:
            search_criteria: Dictionary containing search parameters
                Possible keys include:
                - name: String to search in test cycle names
                - parentId: ID of the parent test cycle
                - releaseId: ID of the release the cycles belong to
                - properties: List of property objects to match
                - created_from: ISO-8601 datetime string for creation date range start
                - created_to: ISO-8601 datetime string for creation date range end

        Returns:
            List of matching test cycles
        """
        endpoint = f"/projects/{self.config.project_id}/test-cycles/search"

        # If search is by simple parameters, use GET method with query params
        if set(search_criteria.keys()).issubset({"name", "parentId", "releaseId"}):
            # Convert to snake_case to camelCase if needed
            params = {}
            for key, value in search_criteria.items():
                if key == "parent_id":
                    params["parentId"] = value
                elif key == "release_id":
                    params["releaseId"] = value
                else:
                    params[key] = value

            response = self._make_request(
                "GET", f"/projects/{self.config.project_id}/test-cycles", params=params
            )

            # Handle paginated response
            if isinstance(response, dict) and "items" in response:
                test_cycles_data = response.get("items", [])
            else:
                test_cycles_data = response
        else:
            # For more complex search, use POST with JSON body
            response = self._make_request("POST", endpoint, json_data=search_criteria)

            # Handle different response formats
            if isinstance(response, list):
                test_cycles_data = response
            else:
                test_cycles_data = response.get("items", [])

        # Convert property format to match model expectations if needed
        for tc in test_cycles_data:
            if "properties" in tc and isinstance(tc["properties"], list):
                for prop in tc["properties"]:
                    # Convert field_* properties to standard names if needed
                    if "field_id" in prop and "id" not in prop:
                        prop["id"] = prop.pop("field_id")
                    if "field_name" in prop and "name" not in prop:
                        prop["name"] = prop.pop("field_name")
                    if "field_value" in prop and "value" not in prop:
                        prop["value"] = prop.pop("field_value")
                    if "field_type" in prop and "type" not in prop:
                        prop["type"] = prop.pop("field_type")

        return [QTestTestCycle(**tc) for tc in test_cycles_data]

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
        self,
        object_type: str,
        object_id: int,
        file_path: str | Path,
        custom_filename: str = None,
        content_type: str = None,
        verify: bool = True,
        timeout: tuple[float, float] = None,
        report_progress: bool = True,
    ) -> QTestAttachment:
        """Upload a file attachment to an object in qTest.

        Args:
            object_type: Type of object to attach to (test-cases, test-runs, test-logs, requirements, defects)
            object_id: ID of the object
            file_path: Path to the file to upload
            custom_filename: Optional custom filename to use instead of the original filename
            content_type: Optional MIME type override (auto-detected if not provided)
            verify: Whether to verify SSL certificates
            timeout: Request timeout as (connect_timeout, read_timeout) tuple
            report_progress: Whether to log progress for large uploads

        Returns:
            Attachment information as a QTestAttachment object

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the object_type is invalid
            RequestException: For connection errors, timeouts, etc.
        """
        # Validate object type
        valid_object_types = [
            "test-cases",
            "test-runs",
            "test-logs",
            "requirements",
            "defects",
            "test-steps",
        ]
        if object_type not in valid_object_types:
            raise ValueError(
                f"Invalid object type: {object_type}. Must be one of: {', '.join(valid_object_types)}"
            )

        # Convert string path to Path object
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get file info
        filename = custom_filename or file_path.name
        file_size = file_path.stat().st_size

        # Detect content type if not provided
        if content_type is None:
            import mimetypes

            content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            logger.debug(f"Auto-detected content type: {content_type}")

        # Read file contents and calculate checksum
        file_content = file_path.read_bytes()
        file_checksum = QTestAttachment.calculate_checksum(file_content)
        logger.debug(f"File size: {file_size} bytes, MD5 checksum: {file_checksum}")

        # Prepare the file for upload
        endpoint = f"/projects/{self.config.project_id}/{object_type}/{object_id}/blob-handles"

        # qTest uses multipart/form-data for file uploads
        files = {"file": (filename, file_content, content_type)}

        # Remove Content-Type from headers to let requests set it with boundary
        headers = self.headers.copy()
        headers.pop("Content-Type", None)

        try:
            # Log upload start
            if report_progress and file_size > 1024 * 1024:  # Only for files > 1MB
                logger.info(
                    f"Uploading file {filename} ({file_size} bytes) to {object_type}/{object_id}"
                )

            # Make the request with optional timeout and SSL verification
            response = self._make_request(
                method="POST",
                endpoint=endpoint,
                headers=headers,
                files=files,
                verify=verify,
                timeout=timeout,
            )

            # Create attachment object with checksum
            attachment = QTestAttachment(**response)

            # Log successful upload
            if report_progress and file_size > 1024 * 1024:
                logger.info(f"Upload completed successfully. Attachment ID: {attachment.id}")

            return attachment

        except Exception as e:
            logger.error(f"Failed to upload attachment {filename}: {str(e)}")
            raise

    def upload_binary_attachment(
        self,
        object_type: str,
        object_id: int,
        binary_data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        verify: bool = True,
        timeout: tuple[float, float] = None,
    ) -> QTestAttachment:
        """Upload binary data as an attachment to an object in qTest.

        This method allows directly uploading binary data without needing to save it to a file first.

        Args:
            object_type: Type of object to attach to (test-cases, test-runs, test-logs, requirements, defects)
            object_id: ID of the object
            binary_data: Binary content to upload
            filename: Name to give the uploaded file
            content_type: MIME type of the content (defaults to application/octet-stream)
            verify: Whether to verify SSL certificates
            timeout: Request timeout as (connect_timeout, read_timeout) tuple

        Returns:
            Attachment information as a QTestAttachment object

        Raises:
            ValueError: If object_type is invalid or binary_data is empty
            RequestException: For connection errors, timeouts, etc.
        """
        # Validate object type
        valid_object_types = [
            "test-cases",
            "test-runs",
            "test-logs",
            "requirements",
            "defects",
            "test-steps",
        ]
        if object_type not in valid_object_types:
            raise ValueError(
                f"Invalid object type: {object_type}. Must be one of: {', '.join(valid_object_types)}"
            )

        # Validate binary data
        if not binary_data:
            raise ValueError("Binary data cannot be empty")

        # Validate filename
        if not filename or not filename.strip():
            raise ValueError("Filename cannot be empty")

        # Calculate size and checksum
        file_size = len(binary_data)
        file_checksum = QTestAttachment.calculate_checksum(binary_data)
        logger.debug(f"Binary attachment size: {file_size} bytes, MD5 checksum: {file_checksum}")

        # Prepare the file for upload
        endpoint = f"/projects/{self.config.project_id}/{object_type}/{object_id}/blob-handles"

        # qTest uses multipart/form-data for file uploads
        files = {"file": (filename, binary_data, content_type)}

        # Remove Content-Type from headers to let requests set it with boundary
        headers = self.headers.copy()
        headers.pop("Content-Type", None)

        try:
            # Log upload start for large content
            if file_size > 1024 * 1024:
                logger.info(
                    f"Uploading binary data as {filename} ({file_size} bytes) to {object_type}/{object_id}"
                )

            # Make the request with optional timeout and SSL verification
            response = self._make_request(
                method="POST",
                endpoint=endpoint,
                headers=headers,
                files=files,
                verify=verify,
                timeout=timeout,
            )

            # Create attachment object
            attachment = QTestAttachment(**response)

            # Log successful upload for large content
            if file_size > 1024 * 1024:
                logger.info(f"Binary upload completed successfully. Attachment ID: {attachment.id}")

            return attachment

        except Exception as e:
            logger.error(f"Failed to upload binary attachment {filename}: {str(e)}")
            raise

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
            "error": None,
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

    def update_pulse_trigger(
        self, trigger_id: int, trigger: QTestPulseTrigger
    ) -> QTestPulseTrigger:
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

    def download_attachment(
        self,
        attachment_id: int,
        file_path: str | Path,
        verify: bool = True,
        timeout: tuple[float, float] | None = None,
        chunk_size: int = 8192,
    ) -> bool:
        """
        Download an attachment by ID and save it to the specified file path.

        Args:
            attachment_id: ID of the attachment to download
            file_path: Local file path to save the attachment to
            verify: Whether to verify SSL certificates (default True)
            timeout: Request timeout as (connect_timeout, read_timeout) tuple
            chunk_size: Size of chunks for streaming download (in bytes)

        Returns:
            True if download successful, False otherwise
        """
        # Ensure the endpoint follows standards
        endpoint = f"/attachments/{attachment_id}"

        # Use API version path if needed
        api_version = self.api_endpoints.get(self.api_type, "api/v3")
        if api_version:
            endpoint = f"/{api_version}{endpoint}"

        # Construct URL
        url = f"{self.config.base_url}{endpoint}"

        # Convert string path to Path object for consistency
        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Ensure the parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading attachment {attachment_id} to {file_path}")

        try:
            # Make binary request with streaming
            # Use requests directly for streaming support, but apply all our auth/headers
            response = requests.get(
                url=url, headers=self.headers, stream=True, verify=verify, timeout=timeout
            )

            # Check for auth failures and retry if needed
            if response.status_code == 401:
                logger.info("Authentication failed during download. Re-authenticating...")
                self.auth_token = None
                self._authenticate()

                # Retry with new token
                response = requests.get(
                    url=url, headers=self.headers, stream=True, verify=verify, timeout=timeout
                )

            # Handle errors with detailed logging
            response.raise_for_status()

            # Get file info from headers
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            content_length = int(response.headers.get("Content-Length", "0"))

            logger.debug(f"Attachment content type: {content_type}, size: {content_length} bytes")

            # Track progress for large files
            bytes_downloaded = 0
            last_log_percent = 0

            # Save file
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        bytes_downloaded += len(chunk)

                        # Log progress for large files (>1MB) at 10% intervals
                        if content_length > 1024 * 1024:
                            percent_complete = int((bytes_downloaded / content_length) * 100)
                            if percent_complete >= last_log_percent + 10:
                                logger.info(
                                    f"Download progress: {percent_complete}% ({bytes_downloaded}/{content_length} bytes)"
                                )
                                last_log_percent = percent_complete

            logger.info(f"Attachment downloaded successfully to {file_path}")
            return True

        except requests.exceptions.HTTPError as e:
            # Enhanced HTTP error logging
            logger.error(f"HTTP Error during attachment download: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_json = e.response.json()
                    logger.error(f"API Error Details: {error_json}")
                except ValueError:
                    logger.error(f"Response text: {e.response.text}")
            return False

        except requests.exceptions.ConnectionError:
            logger.error(f"Connection Error: Could not connect to {url}")
            return False

        except requests.exceptions.Timeout:
            logger.error(f"Timeout Error: Request to {url} timed out")
            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error during attachment download: {e}")
            return False

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

    def update_pulse_constant(
        self, constant_id: int, constant: QTestPulseConstant
    ) -> QTestPulseConstant:
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

    def get_circuit_breaker_status(self) -> dict[str, dict[str, Any]]:
        """
        Get the current status of all circuit breakers.

        This method is useful for debugging and monitoring the health of API endpoints.

        Returns:
            Dictionary mapping endpoints to their circuit breaker status, including:
            - state: Current state (closed, open, half_open)
            - failures: Number of consecutive failures
            - last_failure: Timestamp of last failure
        """
        # Temporarily removed: return QTestCircuitBreaker.get_circuit_status()
        return {"state": "CLOSED", "failures": 0, "total_requests": 0}  # Default return

    def reset_circuit_breakers(self) -> None:
        """
        Reset all circuit breakers to their initial state.

        This method is useful when you want to force-reset all circuit breakers
        after resolving connectivity issues or during testing.
        """
        logger.info("Resetting all circuit breakers")
        # Temporarily removed: QTestCircuitBreaker.reset_all_circuits()
        pass  # Placeholder

    def get_client_metrics(self) -> dict[str, Any]:
        """
        Get performance and reliability metrics for this client instance.

        Returns:
            Dictionary containing client metrics:
            - request_count: Total number of requests made
            - error_count: Number of failed requests
            - error_rate: Percentage of requests that failed
            - avg_request_time: Average time per request in seconds
            - last_request_time: Duration of the last request in seconds
            - total_request_time: Total time spent in requests
            - rate_limit_remaining: Current rate limit remaining
            - correlation_id: Client's correlation ID for tracing
        """
        # Calculate error rate and average request time
        error_rate = 0
        avg_request_time = 0

        if self.request_count > 0:
            error_rate = (self.error_count / self.request_count) * 100
            avg_request_time = self.total_request_time / self.request_count

        # Get circuit breaker status
        circuit_status = self.get_circuit_breaker_status()
        open_circuits = {
            endpoint: status
            for endpoint, status in circuit_status.items()
            # Temporarily removed: if status["state"] == QTestCircuitBreaker.OPEN
            if status["state"] == "OPEN"
        }

        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": error_rate,
            "avg_request_time": avg_request_time,
            "last_request_time": self.last_request_time,
            "total_request_time": self.total_request_time,
            "rate_limit_remaining": self.rate_limit_remaining,
            "correlation_id": self.correlation_id,
            "circuit_breakers": {
                "total": len(circuit_status),
                "open": len(open_circuits),
                "open_circuits": open_circuits,
            },
        }

    def with_correlation_id(self, correlation_id: str):
        """
        Create a context for operations with a specific correlation ID.

        This is useful when you want to trace a specific business operation
        across multiple API requests.

        Args:
            correlation_id: Correlation ID to use for the context

        Returns:
            A context manager that sets/resets the correlation ID
        """
        # Save the original ID
        original_id = get_correlation_id()

        class CorrelationContext:
            def __enter__(self):
                # Set the new ID
                set_correlation_id(correlation_id)
                logger.debug(f"Set correlation ID: {correlation_id}")
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                # Restore the original ID
                set_correlation_id(original_id)
                logger.debug(f"Restored correlation ID: {original_id}")

        return CorrelationContext()
