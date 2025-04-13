import requests
from typing import Dict, Any, List, Optional, TypeVar, Generic, Type, cast, Union
from pathlib import Path
import time
import mimetypes

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
    PaginatedResponse
)
from ztoq.openapi_parser import load_openapi_spec

T = TypeVar("T")


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

    def __iter__(self):
        return self

    def __next__(self) -> T:
        # Fetch first page if needed
        if not self.current_page:
            self._fetch_next_page()

        # Check if we have valid page data
        if self.current_page is None:
            raise StopIteration

        # Check if we need to fetch the next page
        if self.item_index >= len(self.current_page.values):
            if self.current_page.is_last:
                raise StopIteration

            self._fetch_next_page()

        # Return the next item
        item = cast(T, self.model_class(**self.current_page.values[self.item_index]))
        self.item_index += 1
        self.total_fetched += 1
        return item

    def _fetch_next_page(self):
        """Fetch the next page of results."""
        if self.current_page:
            self.params["startAt"] = self.current_page.start_at + len(self.current_page.values)
        else:
            self.params["startAt"] = 0

        response = self.client._make_request("GET", self.endpoint, params=self.params)
        self.current_page = PaginatedResponse(**response)
        self.item_index = 0


class ZephyrClient:
    """Client for interacting with the Zephyr Scale API."""

    def __init__(self, config: ZephyrConfig):
        """Initialize the Zephyr client with configuration."""
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.api_token}",
            "Content-Type": "application/json",
        }
        self.rate_limit_remaining = 1000  # Default high value
        self.rate_limit_reset = 0

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        handle_pagination: bool = False,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
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

        Returns:
            API response as dictionary
        """
        # Check rate limits
        if self.rate_limit_remaining <= 0:
            wait_time = max(0, self.rate_limit_reset - time.time())
            if wait_time > 0:
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

        # Make the request
        response = requests.request(
            method=method, 
            url=url, 
            headers=request_headers, 
            params=params, 
            json=json_data,
            files=files
        )

        # Update rate limits
        if "X-Rate-Limit-Remaining" in response.headers:
            self.rate_limit_remaining = int(response.headers["X-Rate-Limit-Remaining"])
        if "X-Rate-Limit-Reset" in response.headers:
            self.rate_limit_reset = int(response.headers["X-Rate-Limit-Reset"])

        # Handle errors
        response.raise_for_status()

        # Return the response
        return response.json()

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

    def get_test_cycles(
        self, project_key: Optional[str] = None
    ) -> PaginatedIterator[CycleInfo]:
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
        self, 
        entity_type: str = "testCase", 
        project_key: Optional[str] = None
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
        project_key: Optional[str] = None
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
        files = {
            "file": (filename, file_content, content_type)
        }
        
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
            method="POST",
            endpoint=endpoint,
            params=params,
            headers=headers,
            files=files
        )
        
        return Attachment(**response)
        
    def get_attachments(
        self,
        entity_type: str,
        entity_id: str,
        project_key: Optional[str] = None
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
    def from_openapi_spec(cls, spec_path: Path, config: ZephyrConfig) -> "ZephyrClient":
        """Create a client from an OpenAPI spec file.

        Args:
            spec_path: Path to the OpenAPI spec file
            config: Zephyr configuration

        Returns:
            Configured ZephyrClient instance
        """
        # Load the OpenAPI spec to validate and get details if needed
        # Currently we're not using the spec for anything, but in the future
        # we could use it to dynamically configure the client
        load_openapi_spec(spec_path)

        return cls(config=config)
