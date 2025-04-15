"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Example script to list qTest projects with various authentication methods.

This script provides a simple way to test qTest authentication and retrieve a list
of projects. It supports both environment variables and command line arguments
for authentication details.

Usage examples:
  # Use environment variables (qtest_bearer_token, qtest_base_url):
  python qtest_project_list.py

  # Use token from command line:
  python qtest_project_list.py --base-url https://example.qtestnet.com --token YOUR_TOKEN

  # Use username/password:
  python qtest_project_list.py --base-url https://example.qtestnet.com --username user@example.com --password YourPassword

Environment variables:
  qtest_base_url - Base URL for qTest API (required)
  qtest_bearer_token - Bearer token for token-based auth (required if not using username/password)
  qtest_username - Username for username/password auth
  qtest_password - Password for username/password auth
"""

import argparse
import logging
import os
import sys

from ztoq.qtest_client import QTestClient
from ztoq.qtest_models import QTestConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("qtest_project_list")

def list_projects(client):
    """List all projects the user has access to.

    Args:
        client: An authenticated QTestClient instance

    Returns:
        List of QTestProject objects
    """
    logger.info("Retrieving projects...")

    try:
        # Fetch projects
        projects = client.get_projects()

        if not projects:
            logger.warning("No projects found - check permissions")
            return []

        # Display projects
        print(f"\n{'ID':<10}{'Name':<40}{'Status':<15}")
        print("-" * 65)

        for project in projects:
            status = project.status_name or "Unknown"
            print(f"{project.id:<10}{project.name:<40}{status:<15}")

        logger.info(f"Found {len(projects)} projects")
        return projects

    except Exception as e:
        logger.error(f"Error retrieving projects: {e}")
        return []

def get_client_health(client):
    """Check API health and token status.

    Args:
        client: An authenticated QTestClient instance

    Returns:
        Dict with health and token information
    """
    logger.info("Checking API health...")

    try:
        # Check API health
        health = client.check_api_health()

        # Get token status
        token_status = client.get_token_status()

        # Display health info
        print("\nAPI Health Status:")
        print(f"  Healthy: {health['healthy']}")
        print(f"  Latency: {health['latency_ms']}ms")

        if health.get("error"):
            print(f"  Error: {health['error']}")

        # Display token info if available
        if "error" not in token_status:
            validity_ms = token_status.get("validityInMilliseconds", 0)
            validity_hours = validity_ms / (1000 * 60 * 60)
            print("\nToken Status:")
            print(f"  Valid for: {validity_hours:.1f} hours")

        return {"health": health, "token_status": token_status}

    except Exception as e:
        logger.error(f"Error checking API health: {e}")
        return {"error": str(e)}

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="List qTest projects")

    # Authentication options
    parser.add_argument("--base-url", help="Base URL for qTest API (e.g., https://example.qtestnet.com)")
    parser.add_argument("--token", help="Bearer token for authentication")
    parser.add_argument("--username", help="Username for authentication")
    parser.add_argument("--password", help="Password for authentication")

    # Other options
    parser.add_argument("--project-id", type=int, default=1, help="Default project ID for operations")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--health-check", action="store_true", help="Perform API health check")

    args = parser.parse_args()

    # Enable verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("ztoq.qtest_client").setLevel(logging.DEBUG)

    # Get authentication parameters from args or environment
    base_url = args.base_url or os.environ.get("qtest_base_url")
    token = args.token or os.environ.get("qtest_bearer_token")
    username = args.username or os.environ.get("qtest_username")
    password = args.password or os.environ.get("qtest_password")

    # Validate required parameters
    if not base_url:
        logger.error("Base URL is required. Use --base-url or set the qtest_base_url environment variable.")
        return 1

    if not token and not (username and password):
        logger.error("Authentication credentials required. Provide either token or username/password.")
        return 1

    try:
        # Create config based on available credentials
        config_params = {
            "base_url": base_url,
            "project_id": args.project_id,
        }

        if token:
            config_params["bearer_token"] = token
            auth_method = "bearer token"
        else:
            config_params["username"] = username
            config_params["password"] = password
            auth_method = "username/password"

        # Create configuration and client
        config = QTestConfig(**config_params)
        client = QTestClient(config)

        logger.info(f"Authenticated with {auth_method}")

        # Perform operations
        if args.health_check:
            get_client_health(client)

        projects = list_projects(client)

        if not projects:
            return 1

        return 0

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
