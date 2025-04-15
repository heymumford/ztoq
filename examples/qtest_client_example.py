"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Example script demonstrating the use of the QTestClient class.

This script shows how to use the QTestClient with environment variables
for authentication and various API operations.

Environment variables:
- qtest_base_url: Base URL for qTest API (e.g., https://example.qtest.com)
- qtest_bearer_token: Bearer token for qTest authentication
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path to enable imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ztoq.qtest_client import QTestClient
from ztoq.qtest_models import QTestConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("qtest_client_example")

def list_projects(client):
    """List all projects the user has access to."""
    logger.info("Listing projects:")

    # Get projects directly to avoid model validation issues
    endpoint = "/projects"
    projects_data = client._make_request("GET", endpoint)

    # Handle different response formats
    projects = []
    if isinstance(projects_data, list):
        projects = projects_data
    else:
        projects = projects_data.get("items", [])

    for i, project in enumerate(projects):
        project_id = project.get("id", "Unknown")
        project_name = project.get("name", "Unnamed")
        logger.info(f"{i+1}. Project {project_id}: {project_name}")

    return projects

def list_test_cases(client, project_id, limit=10):
    """List test cases from a project."""
    logger.info(f"Listing up to {limit} test cases for project {project_id}:")

    # Create a client with the specified project
    config = QTestConfig(
        base_url=os.environ.get("qtest_base_url", ""),
        bearer_token=os.environ.get("qtest_bearer_token", ""),
        project_id=project_id,
    )
    project_client = QTestClient(config)

    # Get test cases directly with _make_request to avoid validation issues
    endpoint = f"/projects/{project_id}/test-cases"
    test_cases = project_client._make_request("GET", endpoint)

    # Handle the response
    if isinstance(test_cases, list):
        # List response format
        count = 0
        for test_case in test_cases[:limit]:
            logger.info(f"Test Case {test_case['id']}: {test_case['name']}")
            count += 1
    else:
        # Object with items format
        test_cases_items = test_cases.get("items", [])
        count = 0
        for test_case in test_cases_items[:limit]:
            logger.info(f"Test Case {test_case['id']}: {test_case['name']}")
            count += 1

    return count

def get_token_info(client):
    """Get information about the current token."""
    logger.info("Getting token status:")
    status = client.get_token_status()

    if "error" in status:
        logger.error(f"Failed to get token status: {status['error']}")
        return None

    # Calculate validity in human-readable format
    validity_ms = status.get("validityInMilliseconds", 0)
    validity_hours = validity_ms / (1000 * 60 * 60)

    logger.info(f"Token expiration: {status.get('expiration')}")
    logger.info(f"Token validity: {validity_ms} ms ({validity_hours:.2f} hours)")

    return status

def get_user_permissions(client, project_id):
    """Get and display user permissions for a project."""
    logger.info(f"Getting user permissions for project {project_id}:")

    try:
        # Create a client with the specified project
        config = QTestConfig(
            base_url=os.environ.get("qtest_base_url", ""),
            bearer_token=os.environ.get("qtest_bearer_token", ""),
            project_id=project_id,
        )
        project_client = QTestClient(config)

        # Get permissions using direct API call
        endpoint = f"/projects/{project_id}/user-profiles/current"
        permissions = project_client._make_request("GET", endpoint)

        # Display permissions
        logger.info(f"User ID: {permissions.get('user_id')}")
        logger.info(f"Project ID: {permissions.get('project_id')}")

        # Display module permissions
        module_perms = permissions.get("module", {})
        logger.info("Module permissions: " +
                   f"create={module_perms.get('create', False)}, " +
                   f"edit={module_perms.get('edit', False)}, " +
                   f"delete={module_perms.get('delete', False)}, " +
                   f"view={module_perms.get('view', False)}")

        # Display test case permissions
        tc_perms = permissions.get("test_case", {})
        logger.info("Test Case permissions: " +
                   f"create={tc_perms.get('create', False)}, " +
                   f"edit={tc_perms.get('edit', False)}, " +
                   f"delete={tc_perms.get('delete', False)}, " +
                   f"view={tc_perms.get('view', False)}, " +
                   f"approve={tc_perms.get('approve', False)}, " +
                   f"export={tc_perms.get('export', False)}, " +
                   f"import={tc_perms.get('import', False)}")

        return permissions

    except Exception as e:
        logger.error(f"Failed to get user permissions: {e}")
        return None

def main():
    """Main function for the example script."""
    parser = argparse.ArgumentParser(description="qTest Client Example")
    parser.add_argument("--project-id", type=int, help="Project ID to use for examples")
    parser.add_argument("--check-token", action="store_true", help="Check token status")
    parser.add_argument("--list-projects", action="store_true", help="List all projects")
    parser.add_argument("--list-test-cases", action="store_true", help="List test cases for the project")
    parser.add_argument("--get-permissions", action="store_true", help="Get user permissions for a project")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of items to list")
    parser.add_argument("--base-url", help="Base URL for qTest API (overrides environment variable)")
    parser.add_argument("--token", help="Bearer token for qTest authentication (overrides environment variable)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("ztoq.qtest_client").setLevel(logging.DEBUG)
        # Add console handler if needed
        if not logging.getLogger().handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logging.getLogger().addHandler(handler)

    # Check if URL and token are provided as arguments or in environment variables
    base_url = args.base_url or os.environ.get("qtest_base_url")
    token = args.token or os.environ.get("qtest_bearer_token")

    # Make sure base URL has proper https:// prefix
    if base_url and not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url
        logger.info(f"Added https:// prefix to base URL: {base_url}")

    if not base_url:
        logger.error("qTest base URL not provided. Use --base-url or set qtest_base_url environment variable")
        return 1

    if not token:
        logger.error("qTest token not provided. Use --token or set qtest_bearer_token environment variable")
        return 1

    # Create client for listing projects (uses project_id=1 but it doesn't matter for listing)
    config = QTestConfig(base_url=base_url, bearer_token=token, project_id=1)
    client = QTestClient(config)

    # Execute requested operations
    if args.check_token:
        get_token_info(client)

    if args.list_projects:
        projects = list_projects(client)

    # Determine project ID for operations that need it
    project_id = args.project_id
    if (args.list_test_cases or args.get_permissions) and not project_id:
        if args.list_projects:
            # Projects were already listed
            project_id = int(input("Enter project ID: "))
        else:
            # List projects first
            projects = list_projects(client)
            project_id = int(input("Enter project ID: "))

    # Perform project-specific operations
    if args.list_test_cases and project_id:
        list_test_cases(client, project_id, args.limit)

    if args.get_permissions and project_id:
        get_user_permissions(client, project_id)

    return 0

if __name__ == "__main__":
    sys.exit(main())
