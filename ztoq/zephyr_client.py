"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import functools
import json
import logging
import mimetypes
import os
import random
import time
from pathlib import Path
from typing import Any, Callable, Dict, Generic, Optional, TypeVar, cast, Union
import requests
from requests.exceptions import ConnectionError, HTTPError, RequestException, Timeout
from ztoq.models import (
    Attachment,
    Case,
    CycleInfo,
    Environment,
    Execution,
    Folder,
    PaginatedResponse,
    Plan,
    Priority,
    Project,
    Status,
    ZephyrConfig,
)
from ztoq.openapi_parser import ZephyrApiSpecWrapper, load_openapi_spec

T = TypeVar("T")

# Configure module logger
logger = logging.getLogger("ztoq.zephyr_client")


def configure_logging(level=None):
    """Configure logging for the Zephyr client.

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


class CircuitBreaker:
    """Circuit breaker pattern implementation for API calls.

    Implements a simple circuit breaker that tracks failures and prevents
    calls to failing endpoints for a cooling-off period.

    Attributes:
        failure_threshold: Number of failures before opening circuit
        reset_timeout: Seconds before attempting to close circuit again
        state: Current circuit state (CLOSED, OPEN, HALF_OPEN)
        failure_count: Current count of consecutive failures
        last_failure_time: Timestamp of last failure
        endpoint_circuits: Dictionary tracking circuits for different endpoints
    """

    # Circuit states
    CLOSED = "closed"  # Normal operation - requests pass through
    OPEN = "open"      # Circuit breaker tripped - requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered

    # Class level circuit tracking for different endpoints
    _endpoint_circuits = {}

    def __init__(self, failure_threshold=5, reset_timeout=60):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            reset_timeout: Seconds before attempting to close circuit again
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = self.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0

    def __call__(self, func):
        """Make the class callable as a decorator."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract endpoint from args if present (used for tracking different endpoints)
            endpoint = None
            if len(args) > 2 and isinstance(args[0], ZephyrClient) and isinstance(args[2], str):
                # Extract endpoint from _make_request call: (self, method, endpoint, ...)
                endpoint = args[2]

            # Get or create circuit for this endpoint
            circuit = self._get_circuit(endpoint)

            # Check circuit state
            if circuit.state == self.OPEN:
                # Check if enough time has passed to try again
                if time.time() - circuit.last_failure_time >= circuit.reset_timeout:
                    logger.info(f"Circuit for endpoint {endpoint} switching to HALF_OPEN")
                    circuit.state = self.HALF_OPEN
                else:
                    # Circuit is still open, fail fast
                    error_msg = f"Circuit for endpoint {endpoint} is OPEN - failing fast"
                    logger.error(error_msg)
                    raise RequestException(error_msg)

            try:
                # Call the wrapped function
                result = func(*args, **kwargs)

                # Success - reset circuit if it was half-open
                if circuit.state == self.HALF_OPEN:
                    logger.info(f"Circuit for endpoint {endpoint} reset to CLOSED - service recovered")
                    circuit.state = self.CLOSED
                    circuit.failure_count = 0

                return result

            except (ConnectionError, Timeout, HTTPError) as e:
                # Network or HTTP error - increment failure counter
                circuit.failure_count += 1
                circuit.last_failure_time = time.time()

                # Log the failure
                logger.warning(
                    f"Circuit failure for endpoint {endpoint}: {e} "
                    f"(count: {circuit.failure_count}/{circuit.failure_threshold})"
                )

                # Check if we need to open the circuit
                if circuit.state == self.CLOSED and circuit.failure_count >= circuit.failure_threshold:
                    logger.error(f"Circuit for endpoint {endpoint} OPEN - too many failures")
                    circuit.state = self.OPEN

                # Re-raise the exception
                raise

        return wrapper

    @classmethod
    def _get_circuit(cls, endpoint):
        """Get or create a circuit for an endpoint."""
        if endpoint not in cls._endpoint_circuits:
            cls._endpoint_circuits[endpoint] = CircuitBreaker()
        return cls._endpoint_circuits[endpoint]

    @classmethod
    def reset_all_circuits(cls):
        """Reset all circuits - useful for testing."""
        cls._endpoint_circuits = {}

    @classmethod
    def get_circuit_status(cls):
        """Get status of all tracked circuits."""
        return {
            endpoint: {
                "state": circuit.state,
                "failures": circuit.failure_count,
                "last_failure": circuit.last_failure_time
            }
            for endpoint, circuit in cls._endpoint_circuits.items()
        }


def retry(
    max_retries: int = 3,
    retry_codes: tuple = (429, 500, 502, 503, 504),
    initial_delay: float = 0.1,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
):
    """Retry decorator with exponential backoff for API calls.

    Args:
        max_retries: Maximum number of retry attempts
        retry_codes: HTTP status codes to retry on
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Factor to multiply delay by on each retry
        jitter: Whether to add random jitter to delay

    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay

            while True:
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, Timeout) as e:
                    # Always retry network errors
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded: {e}")
                        raise

                    # Calculate backoff with optional jitter
                    current_delay = min(delay, max_delay)
                    if jitter:
                        # Add 0-25% random jitter
                        current_delay = current_delay * (1 + random.random() * 0.25)

                    logger.warning(
                        f"Network error: {e}. Retrying in {current_delay:.2f}s "
                        f"(attempt {retries}/{max_retries})"
                    )
                    time.sleep(current_delay)
                    delay *= backoff_factor

                except HTTPError as e:
                    # Only retry on specific HTTP error codes
                    if hasattr(e, "response") and e.response is not None:
                        status_code = e.response.status_code

                        if status_code in retry_codes:
                            retries += 1
                            if retries > max_retries:
                                logger.error(f"Max retries ({max_retries}) exceeded: {e}")
                                raise

                            # Calculate backoff with optional jitter
                            current_delay = min(delay, max_delay)
                            if jitter:
                                current_delay = current_delay * (1 + random.random() * 0.25)

                            logger.warning(
                                f"HTTP error {status_code}: Retrying in {current_delay:.2f}s "
                                f"(attempt {retries}/{max_retries})"
                            )
                            time.sleep(current_delay)
                            delay *= backoff_factor
                        else:
                            # Don't retry on other HTTP errors
                            logger.error(f"HTTP error {status_code} not eligible for retry: {e}")
                            raise
                    else:
                        # If response is not available, don't retry
                        logger.error(f"HTTP error without response, not retrying: {e}")
                        raise

                except Exception as e:
                    # Don't retry other exceptions
                    logger.error(f"Unexpected error, not retrying: {e}")
                    raise

        return wrapper
    return decorator


class PaginatedIterator(Generic[T]):
    """Iterator for paginated API responses."""

    def __init__(
        self,
            client: "ZephyrClient",
            endpoint: str,
            model_class: type[T],
            params: dict[str, Any] | None = None,
            page_size: int = 100,
        ):
        """Initialize the paginated iterator.

        Args:
            client: The ZephyrClient instance
            endpoint: API endpoint path
            model_class: Model class for response items
            params: Additional query parameters
            page_size: Number of items per page
        """
        self.client = client
        self.endpoint = endpoint
        self.model_class = model_class
        self.params = params or {}
        self.params["maxResults"] = page_size
        self.current_page: PaginatedResponse | None = None
        self.item_index = 0
        self.total_fetched = 0

        logger.debug(
            f"PaginatedIterator initialized for {endpoint} with page size {page_size}, "
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
        if self.item_index >= len(self.current_page.values):
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
        item = cast(T, self.model_class(**self.current_page.values[self.item_index]))
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
            self.params["startAt"] = self.current_page.start_at + len(self.current_page.values)
            page_number = (self.current_page.start_at // self.params["maxResults"]) + 1
        else:
            self.params["startAt"] = 0

        logger.debug(
            f"Fetching page {page_number + 1} from {self.endpoint} (startAt={self.params['startAt']})"
        )

        response = self.client._make_request("GET", self.endpoint, params=self.params)
        self.current_page = PaginatedResponse(**response)
        self.item_index = 0

        logger.debug(
            f"Received page {page_number + 1} with {len(self.current_page.values)} items, "
            f"total: {self.current_page.total_count}, isLast: {self.current_page.is_last}"
        )


class ZephyrClient:
    """Client for interacting with the Zephyr Scale API."""

    def __init__(self, config: ZephyrConfig, log_level=None):
        """Initialize the Zephyr client with configuration.

        Args:
            config: The Zephyr Scale API configuration
            log_level: Optional logging level to use for this client instance
                      (e.g., "DEBUG", "INFO", "WARNING", "ERROR")
        """
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_token}",
                "Content-Type": "application/json",
            }
        self.rate_limit_remaining = 1000  # Default high value
        self.rate_limit_reset = 0

        # Configure logging if level specified
        if log_level:
            configure_logging(log_level)

        logger.debug(
            f"ZephyrClient initialized for project {config.project_key} with base URL {config.base_url}"
        )

    @CircuitBreaker(failure_threshold=5, reset_timeout=60)
    @retry(max_retries=3, initial_delay=0.5, backoff_factor=2.0, jitter=True)
    def _make_request(
        self,
            method: str,
            endpoint: str,
            params: dict[str, Any] | None = None,
            json_data: dict[str, Any] | None = None,
            handle_pagination: bool = False,
            files: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
            validate: bool = True,
            timeout: tuple[float, float] = (10.0, 30.0),  # Connect timeout, read timeout
        ) -> dict[str, Any]:
        """Make a request to the Zephyr API.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body
            handle_pagination: Whether to handle pagination
            files: Files to upload (for multipart/form-data requests)
            headers: Optional headers to override default headers
            validate: Whether to validate request/response against OpenAPI spec
            timeout: Connection and read timeout in seconds (tuple of connect_timeout, read_timeout)

        Returns:
            API response as dictionary
        """
        # Check rate limits
        if self.rate_limit_remaining <= 0:
            wait_time = max(0, self.rate_limit_reset - time.time())
            if wait_time > 0:
                logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)

        # Construct URL
        url = f"{self.config.base_url}{endpoint}"

        # Add project key if not in params
        if params is None:
            params = {}
        if "projectKey" not in params and not endpoint.startswith("/projects"):
            params["projectKey"] = self.config.project_key

        # Use provided headers or default
        request_headers = headers or self.headers

        # Validate request against OpenAPI spec if available and validation is enabled
        path_params = {}  # Extract path parameters from endpoint if needed
        if validate and hasattr(self, "spec_wrapper"):
            # Extract path parameters from endpoint
            # Basic implementation - can be enhanced to handle more complex path patterns
            endpoint_parts = endpoint.split("/")
            for i, part in enumerate(endpoint_parts):
                if part.startswith("{") and part.endswith("}"):
                    param_name = part[1:-1]
                    # Try to find the value in the actual endpoint path
                    if i < len(endpoint.split("/")):
                        path_params[param_name] = endpoint.split("/")[i]

            # Validate parameters
            valid_params, param_error = self.spec_wrapper.validate_parameters(
                endpoint, method.lower(), params, path_params
            )
            if not valid_params:
                logger.error(f"Parameter validation failed: {param_error}")
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Invalid parameters: {params}")
                    logger.debug(f"Path parameters: {path_params}")

            # Validate request body if present
            if json_data and method.lower() in ["post", "put", "patch"]:
                valid_body, body_error = self.spec_wrapper.validate_request(
                    endpoint, method.lower(), json_data
                )
                if not valid_body:
                    logger.error(f"Request body validation failed: {body_error}")
                    if logger.isEnabledFor(logging.DEBUG):
                        safe_json = self._mask_sensitive_data(json_data)
                        logger.debug(f"Invalid request body: {json.dumps(safe_json)}")

        # Generate a unique request ID for correlation
        request_id = f"{method}_{endpoint.replace('/', '_')}_{int(time.time()*1000)}"

        # Log request details (careful not to log sensitive data)
        safe_headers = {k: v for k, v in request_headers.items() if k.lower() != "authorization"}
        logger.debug(f"API Request [{request_id}]: {method} {url}")
        logger.debug(f"Parameters [{request_id}]: {params}")
        logger.debug(f"Headers [{request_id}]: {safe_headers}")

        if logger.isEnabledFor(logging.DEBUG) and json_data:
            # Mask any sensitive fields in the debug output
            safe_json = self._mask_sensitive_data(json_data)
            logger.debug(f"Request Body [{request_id}]: {json.dumps(safe_json)}")

        # Measure request time for performance monitoring
        start_time = time.time()

        try:
            # Make the request with timeout
            response = requests.request(
                method=method,
                url=url,
                headers=request_headers,
                params=params,
                json=json_data,
                files=files,
                timeout=timeout,
            )

            # Calculate request duration
            duration = time.time() - start_time

            # Update rate limits
            if "X-Rate-Limit-Remaining" in response.headers:
                self.rate_limit_remaining = int(response.headers["X-Rate-Limit-Remaining"])
                logger.debug(f"Rate limit remaining [{request_id}]: {self.rate_limit_remaining}")
            if "X-Rate-Limit-Reset" in response.headers:
                self.rate_limit_reset = int(response.headers["X-Rate-Limit-Reset"])

            # Log response metadata
            logger.debug(
                f"Response [{request_id}] received in {duration:.2f}s - "
                f"Status: {response.status_code}"
            )

            # Log headers at trace level (requires DEBUG or lower)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Response Headers [{request_id}]: {dict(response.headers)}")

            # Check response status - will raise HTTPError for 4xx/5xx responses
            response.raise_for_status()

            try:
                # Parse JSON response
                response_json = response.json()
            except ValueError as e:
                logger.error(f"JSON Parsing Error [{request_id}]: {e}")
                logger.error(f"Response Text [{request_id}]: {response.text[:500]}")
                raise ValueError(f"Could not parse JSON response: {e}. "
                                 f"Response text: {response.text[:100]}...")

            # Validate response against OpenAPI spec if available and validation is enabled
            if validate and hasattr(self, "spec_wrapper"):
                status_code = str(response.status_code)
                valid_response, response_error = self.spec_wrapper.validate_response(
                    endpoint, method.lower(), status_code, response_json
                )
                if not valid_response:
                    logger.warning(f"Response validation failed [{request_id}]: {response_error}")
                    if logger.isEnabledFor(logging.DEBUG):
                        # Truncate very large responses for logging
                        if isinstance(response_json, dict) and "values" in response_json:
                            values_count = len(response_json["values"])
                            if values_count > 10:
                                log_response = response_json.copy()
                                log_response["values"] = log_response["values"][:3]
                                log_response["values"].append("... truncated for logging")
                                logger.debug(
                                    f"Invalid response body [{request_id}] (truncated): "
                                    f"{json.dumps(log_response)}"
                                )
                            else:
                                logger.debug(
                                    f"Invalid response body [{request_id}]: "
                                    f"{json.dumps(response_json)}"
                                )
                        else:
                            logger.debug(
                                f"Invalid response body [{request_id}]: "
                                f"{json.dumps(response_json)}"
                            )

            # Log response data at trace level
            if logger.isEnabledFor(logging.DEBUG):
                # Truncate very large responses for logging
                if isinstance(response_json, dict) and "values" in response_json:
                    values_count = len(response_json["values"])
                    # Create a truncated version for logging if there are many values
                    if values_count > 10:
                        log_response = response_json.copy()
                        log_response["values"] = log_response["values"][:3]
                        log_response["values"].append("... truncated for logging")
                        logger.debug(
                            f"Response Body [{request_id}] (truncated): "
                            f"{json.dumps(log_response)}"
                        )
                    else:
                        logger.debug(
                            f"Response Body [{request_id}]: {json.dumps(response_json)}"
                        )
                else:
                    logger.debug(f"Response Body [{request_id}]: {json.dumps(response_json)}")

            return response_json

        except requests.exceptions.HTTPError as e:
            # Enhanced HTTP error logging
            logger.error(f"HTTP Error [{request_id}]: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_json = e.response.json()
                    logger.error(f"API Error Details [{request_id}]: {error_json}")
                except ValueError:
                    logger.error(f"Response text [{request_id}]: {e.response.text[:500]}")
            raise

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error [{request_id}]: Could not connect to {url}: {e}")
            raise

        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout Error [{request_id}]: Request to {url} timed out after {timeout}s: {e}")
            raise

        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error [{request_id}]: {e}")
            raise

        except Exception as e:
            logger.error(f"Unexpected Error [{request_id}]: {e.__class__.__name__}: {e}")
            raise

    def _mask_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Mask sensitive fields in data before logging."""
        if not isinstance(data, dict):
            return data

        # Create a copy to avoid modifying the original
        result = data.copy()

        # Fields to mask
        sensitive_fields = ["api_token", "password", "token", "secret", "key", "auth"]

        # Mask sensitive fields
        for key in result:
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                result[key] = "********"
            elif isinstance(result[key], dict):
                result[key] = self._mask_sensitive_data(result[key])

        return result

    def get_projects(self) -> list[Project]:
        """Get all projects.

        Returns:
            List of projects
        """
        response = self._make_request("GET", "/projects")
        # Handle response which could be a list or dict with values
        projects_data = response if isinstance(response, list) else response.get("values", [])
        return [Project(**project) for project in projects_data]

    def get_test_cases(self, project_key: str | None = None) -> PaginatedIterator[Case]:
        """Get all test cases for a project.

        Args:
            project_key: JIRA project key (defaults to config's project_key)

        Returns:
            Iterator of test cases
        """
        params = {}
        if project_key:
            params["projectKey"] = project_key

        return PaginatedIterator[Case](
            client=self, endpoint="/testcases", model_class=Case, params=params
        )

    def get_test_cycles(self, project_key: str | None = None) -> PaginatedIterator[CycleInfo]:
        """Get all test cycles for a project.

        Args:
            project_key: JIRA project key (defaults to config's project_key)

        Returns:
            Iterator of test cycles
        """
        params = {}
        if project_key:
            params["projectKey"] = project_key

        return PaginatedIterator[CycleInfo](
            client=self, endpoint="/testcycles", model_class=CycleInfo, params=params
        )

    def get_test_plans(self, project_key: str | None = None) -> PaginatedIterator[Plan]:
        """Get all test plans for a project.

        Args:
            project_key: JIRA project key (defaults to config's project_key)

        Returns:
            Iterator of test plans
        """
        params = {}
        if project_key:
            params["projectKey"] = project_key

        return PaginatedIterator[Plan](
            client=self, endpoint="/testplans", model_class=Plan, params=params
        )

    def get_test_executions(
        self, cycle_id: str | None = None, project_key: str | None = None
    ) -> PaginatedIterator[Execution]:
        """Get all test executions for a test cycle.

        Args:
            cycle_id: ID of the test cycle
            project_key: JIRA project key (defaults to config's project_key)

        Returns:
            Iterator of test executions
        """
        params = {}
        if cycle_id:
            params["cycleId"] = cycle_id
        if project_key:
            params["projectKey"] = project_key

        return PaginatedIterator[Execution](
            client=self, endpoint="/testexecutions", model_class=Execution, params=params
        )

    def get_folders(self, project_key: str | None = None) -> list[Folder]:
        """Get all folders for a project.

        Args:
            project_key: JIRA project key (defaults to config's project_key)

        Returns:
            List of folders
        """
        params = {}
        if project_key:
            params["projectKey"] = project_key

        response = self._make_request("GET", "/folders", params=params)
        return [Folder(**folder) for folder in response.get("values", [])]

    def get_statuses(self, project_key: str | None = None) -> list[Status]:
        """Get all statuses for a project.

        Args:
            project_key: JIRA project key (defaults to config's project_key)

        Returns:
            List of statuses
        """
        params = {}
        if project_key:
            params["projectKey"] = project_key

        response = self._make_request("GET", "/statuses", params=params)
        return [Status(**status) for status in response.get("values", [])]

    def get_priorities(self, project_key: str | None = None) -> list[Priority]:
        """Get all priorities for a project.

        Args:
            project_key: JIRA project key (defaults to config's project_key)

        Returns:
            List of priorities
        """
        params = {}
        if project_key:
            params["projectKey"] = project_key

        response = self._make_request("GET", "/priorities", params=params)
        return [Priority(**priority) for priority in response.get("values", [])]

    def get_environments(self, project_key: str | None = None) -> list[Environment]:
        """Get all environments for a project.

        Args:
            project_key: JIRA project key (defaults to config's project_key)

        Returns:
            List of environments
        """
        params = {}
        if project_key:
            params["projectKey"] = project_key

        response = self._make_request("GET", "/environments", params=params)
        return [Environment(**env) for env in response.get("values", [])]

    def get_custom_fields(
        self, entity_type: str = "testCase", project_key: str | None = None
    ) -> list[dict[str, Any]]:
        """Get available custom fields for a specific entity type.

        Args:
            entity_type: The entity type ("testCase", "testCycle", "testExecution", etc.)
            project_key: JIRA project key (defaults to config's project_key)

        Returns:
            List of custom field definitions
        """
        params = {"entityType": entity_type}
        if project_key:
            params["projectKey"] = project_key

        response = self._make_request("GET", "/customfields", params=params)
        return response.get("values", [])

    def upload_attachment(
        self,
            entity_type: str,
            entity_id: str,
            file_path: str | Path,
            project_key: str | None = None,
        ) -> Attachment:
        """Upload a file attachment to a test case, step, or execution.

        Args:
            entity_type: Type of entity to attach to ("testCase", "testStep", "testExecution")
            entity_id: ID of the entity
            file_path: Path to the file
            project_key: JIRA project key (defaults to config's project_key)

        Returns:
            Attachment model with details
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get file info
        filename = file_path.name
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        # Read file contents
        file_content = file_path.read_bytes()

        # Prepare the file for upload
        files = {"file": (filename, file_content, content_type)}

        # Set up multipart headers (don't use default JSON headers)
        headers = {
            "Authorization": self.headers["Authorization"],
                # Let requests set the correct Content-Type with boundary
        }

        # Build endpoint based on entity type
        endpoint = f"/{entity_type}s/{entity_id}/attachments"

        params = {}
        if project_key:
            params["projectKey"] = project_key

        response = self._make_request(
            method="POST", endpoint=endpoint, params=params, headers=headers, files=files
        )

        return Attachment(**response)

    def get_attachments(
        self, entity_type: str, entity_id: str, project_key: str | None = None
    ) -> list[Attachment]:
        """Get attachments for a test case, test step, or test execution.

        Args:
            entity_type: Type of entity ("testCase", "testStep", "testExecution")
            entity_id: ID of the entity
            project_key: JIRA project key (defaults to config's project_key)

        Returns:
            List of attachments
        """
        params = {}
        if project_key:
            params["projectKey"] = project_key

        endpoint = f"/{entity_type}s/{entity_id}/attachments"
        response = self._make_request("GET", endpoint, params=params)

        return [Attachment(**attachment) for attachment in response.get("values", [])]

    @CircuitBreaker(failure_threshold=3, reset_timeout=60)
    @retry(max_retries=5, initial_delay=1.0, backoff_factor=2.0, jitter=True)
    def download_attachment(
        self,
        attachment_id: str,
        timeout: tuple[float, float] = (10.0, 120.0)
    ) -> bytes:
        """Download an attachment by ID.

        Args:
            attachment_id: ID of the attachment
            timeout: Connection and read timeout in seconds (tuple of connect_timeout, read_timeout)
                     Longer read timeout for large files

        Returns:
            Binary content of the attachment

        Raises:
            HTTPError: If the attachment can't be downloaded
            ConnectionError: If connection to the server fails
            Timeout: If the download times out
            ValueError: If the attachment ID is invalid
        """
        if not attachment_id:
            raise ValueError("Invalid attachment ID: must not be empty")

        endpoint = f"/attachments/{attachment_id}/content"
        url = f"{self.config.base_url}{endpoint}"
        headers = {"Authorization": self.headers["Authorization"]}

        # Generate unique request ID
        request_id = f"download_{attachment_id}_{int(time.time()*1000)}"

        logger.debug(f"Downloading attachment [{request_id}]: {attachment_id} from {url}")
        start_time = time.time()

        try:
            # Use a streaming response for potentially large files
            response = requests.get(url, headers=headers, timeout=timeout, stream=True)
            response.raise_for_status()

            # Get content length if available
            content_length = int(response.headers.get('Content-Length', '0')) or None
            if content_length:
                logger.debug(f"Attachment size [{request_id}]: {content_length/1024:.1f} KB")

            # Read the content
            content = response.content

            # Calculate download speed
            duration = time.time() - start_time
            size_kb = len(content) / 1024

            # Avoid division by zero for extremely fast downloads or time precision issues
            if duration > 0:
                download_speed = size_kb / duration
            else:
                download_speed = size_kb  # Assume 1 second if duration is 0

            logger.debug(
                f"Attachment downloaded [{request_id}] in {duration:.2f}s "
                f"({size_kb:.1f} KB, {download_speed:.1f} KB/s)"
            )

            return content

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error downloading attachment [{request_id}]: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Status code: {e.response.status_code}")
            raise

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error downloading attachment [{request_id}]: {e}")
            raise

        except requests.exceptions.Timeout as e:
            logger.error(
                f"Timeout Error downloading attachment [{request_id}]: "
                f"Download timed out after {timeout[1]}s"
            )
            raise

        except Exception as e:
            logger.error(f"Error downloading attachment [{request_id}]: {e.__class__.__name__}: {e}")
            raise

    def check_api_health(self) -> dict[str, Any]:
        """Check the health of the Zephyr API.

        Performs a simple API call to check if the API is reachable and properly responding.
        Also returns information about current circuit breaker status.

        Returns:
            Dictionary with health check information

        Example:
            {
                "healthy": True,
                "latency_ms": 152,
                "rate_limit_remaining": 950,
                "rate_limit_reset": 1633046400,
                "circuits": {
                    "/projects": {"state": "closed", "failures": 0},
                    "/testcases": {"state": "open", "failures": 5}
                }
            }
        """
        health_info = {
            "healthy": False,
            "latency_ms": 0,
            "rate_limit_remaining": self.rate_limit_remaining,
            "rate_limit_reset": self.rate_limit_reset,
            "circuits": CircuitBreaker.get_circuit_status(),
            "error": None
        }

        try:
            # Use a simple endpoint that should always work and is lightweight
            start_time = time.time()
            self._make_request("GET", "/projects", timeout=(5.0, 10.0))

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Update health info
            health_info["healthy"] = True
            health_info["latency_ms"] = latency_ms
            health_info["rate_limit_remaining"] = self.rate_limit_remaining
            health_info["rate_limit_reset"] = self.rate_limit_reset

        except Exception as e:
            health_info["healthy"] = False
            health_info["error"] = f"{e.__class__.__name__}: {str(e)}"
            logger.warning(f"API health check failed: {health_info['error']}")

        return health_info

    def verify_api_token(self) -> bool:
        """
        Verify that the API token is valid by making a simple API call.

        This is useful to check if the token retrieved from environment variables
        is valid and has the necessary permissions.

        Returns:
            bool: True if the token is valid, False otherwise
        """
        logger.info("Verifying Zephyr API token validity")

        try:
            # Make a lightweight request to verify the token
            self._make_request("GET", "/projects", timeout=(5.0, 10.0))
            logger.info("Zephyr API token verification successful")
            return True
        except Exception as e:
            logger.error(f"Zephyr API token verification failed: {str(e)}")
            return False

    def reset_circuit_breakers(self) -> None:
        """Reset all circuit breakers to their closed state.

        This is useful when you want to force retry of previously failing endpoints,
        for example after fixing connectivity issues.
        """
        CircuitBreaker.reset_all_circuits()
        logger.info("All circuit breakers have been reset")

    @classmethod
    def from_openapi_spec(
        cls, spec_path: Path, config: ZephyrConfig, log_level=None
    ) -> "ZephyrClient":
        """Create a client from an OpenAPI spec file.

        Args:
            spec_path: Path to the OpenAPI spec file
            config: Zephyr configuration
            log_level: Optional logging level (e.g., "DEBUG", "INFO", "WARNING", "ERROR")

        Returns:
            Configured ZephyrClient instance
        """
        logger.info(f"Creating ZephyrClient from OpenAPI spec: {spec_path}")

        # Load the OpenAPI spec
        spec = load_openapi_spec(spec_path)

        # Log spec details in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"OpenAPI spec loaded: {spec.get('info', {}).get('title')}")
            logger.debug(f"OpenAPI spec version: {spec.get('info', {}).get('version')}")

            # Log available endpoints in debug mode
            if "paths" in spec:
                endpoints = list(spec["paths"].keys())
                logger.debug(
                    f"Available endpoints in spec: {', '.join(endpoints[:10])}"
                    + (f" and {len(endpoints) - 10} more..." if len(endpoints) > 10 else "")
                )

        # Create the client instance
        client = cls(config=config, log_level=log_level)

        # Create a spec wrapper that provides validation and utilities
        client.spec_wrapper = ZephyrApiSpecWrapper(spec)

        logger.info("Created ZephyrClient with OpenAPI spec wrapper")
        return client
