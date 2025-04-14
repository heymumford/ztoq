"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import requests
from typing import Dict, Any, List, Optional, TypeVar, Generic, Type, cast, Union
from pathlib import Path
import time
import mimetypes
import logging
import json
import os

from ztoq.models import (
    ZephyrConfig,
    Project,
    Case,
    CycleInfo,
    Plan,
    Execution,
    Folder,
    Status,
    Priority,
    Environment,
    Attachment,
    PaginatedResponse,
)
from ztoq.openapi_parser import load_openapi_spec

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


class PaginatedIterator(Generic[T]):
    """Iterator for paginated API responses."""

    def __init__(
        self,
        client: "ZephyrClient",
        endpoint: str,
        model_class: Type[T],
        params: Optional[Dict[str, Any]] = None,
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
        self.current_page: Optional[PaginatedResponse] = None
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

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        handle_pagination: bool = False,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        validate: bool = True,
    ) -> Dict[str, Any]:
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
            )

            # Calculate request duration
            duration = time.time() - start_time

            # Update rate limits
            if "X-Rate-Limit-Remaining" in response.headers:
                self.rate_limit_remaining = int(response.headers["X-Rate-Limit-Remaining"])
                logger.debug(f"Rate limit remaining: {self.rate_limit_remaining}")
            if "X-Rate-Limit-Reset" in response.headers:
                self.rate_limit_reset = int(response.headers["X-Rate-Limit-Reset"])

            # Log response metadata
            logger.debug(f"Response received in {duration:.2f}s - Status: {response.status_code}")

            # Log headers at trace level (requires DEBUG or lower)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Response Headers: {dict(response.headers)}")

            # Handle errors with detailed logging
            response.raise_for_status()

            # Parse JSON response
            response_json = response.json()

            # Validate response against OpenAPI spec if available and validation is enabled
            if validate and hasattr(self, "spec_wrapper"):
                status_code = str(response.status_code)
                valid_response, response_error = self.spec_wrapper.validate_response(
                    endpoint, method.lower(), status_code, response_json
                )
                if not valid_response:
                    logger.warning(f"Response validation failed: {response_error}")
                    if logger.isEnabledFor(logging.DEBUG):
                        # Truncate very large responses for logging
                        if isinstance(response_json, dict) and "values" in response_json:
                            values_count = len(response_json["values"])
                            if values_count > 10:
                                log_response = response_json.copy()
                                log_response["values"] = log_response["values"][:3]
                                log_response["values"].append("... truncated for logging")
                                logger.debug(
                                    f"Invalid response body (truncated): {json.dumps(log_response)}"
                                )
                            else:
                                logger.debug(f"Invalid response body: {json.dumps(response_json)}")
                        else:
                            logger.debug(f"Invalid response body: {json.dumps(response_json)}")

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

    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
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

    def get_projects(self) -> List[Project]:
        """Get all projects.

        Returns:
            List of projects
        """
        response = self._make_request("GET", "/projects")
        # Handle response which could be a list or dict with values
        projects_data = response if isinstance(response, list) else response.get("values", [])
        return [Project(**project) for project in projects_data]

    def get_test_cases(self, project_key: Optional[str] = None) -> PaginatedIterator[Case]:
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

    def get_test_cycles(self, project_key: Optional[str] = None) -> PaginatedIterator[CycleInfo]:
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

    def get_test_plans(self, project_key: Optional[str] = None) -> PaginatedIterator[Plan]:
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
        self, cycle_id: Optional[str] = None, project_key: Optional[str] = None
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

    def get_folders(self, project_key: Optional[str] = None) -> List[Folder]:
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

    def get_statuses(self, project_key: Optional[str] = None) -> List[Status]:
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

    def get_priorities(self, project_key: Optional[str] = None) -> List[Priority]:
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

    def get_environments(self, project_key: Optional[str] = None) -> List[Environment]:
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
        self, entity_type: str = "testCase", project_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
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
        file_path: Union[str, Path],
        project_key: Optional[str] = None,
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
        self, entity_type: str, entity_id: str, project_key: Optional[str] = None
    ) -> List[Attachment]:
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

    def download_attachment(self, attachment_id: str) -> bytes:
        """Download an attachment by ID.

        Args:
            attachment_id: ID of the attachment

        Returns:
            Binary content of the attachment
        """
        endpoint = f"/attachments/{attachment_id}/content"

        # Make request with different content type
        url = f"{self.config.base_url}{endpoint}"
        headers = {"Authorization": self.headers["Authorization"]}

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.content

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
        from ztoq.openapi_parser import ZephyrApiSpecWrapper

        client.spec_wrapper = ZephyrApiSpecWrapper(spec)

        logger.info(f"Created ZephyrClient with OpenAPI spec wrapper")
        return client
