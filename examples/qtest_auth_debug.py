"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Debug script for qTest authentication using multiple methods.

This script tests qTest authentication via both bearer token and username/password,
and provides detailed logging to identify any issues.
"""

import argparse
import base64
import json
import logging
import os
import sys
from pathlib import Path

import requests

# Add the project root to the Python path to enable imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ztoq.qtest_client import QTestClient
from ztoq.qtest_models import QTestConfig

# Configure logging with more detailed output
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("qtest_auth_debug")


def test_direct_auth(base_url, username, password, api_type="manager"):
    """
    Test direct authentication with username/password without using the client.

    Args:
        base_url: Base URL for qTest API
        username: qTest username
        password: qTest password
        api_type: API type (manager, parameters, pulse, scenario)

    Returns:
        dict with token data if successful, error dict otherwise
    """
    logger.info(f"Testing direct authentication to {api_type} API with username/password...")

    # Determine endpoint based on API type
    auth_endpoints = {
        "manager": "/oauth/token",
        "parameters": "/oauth/v1/token-login",
        "pulse": "/oauth/token",
        "scenario": "/oauth/token",
    }

    endpoint = auth_endpoints.get(api_type, "/oauth/token")
    url = f"{base_url}{endpoint}"

    # Common headers for token request
    auth_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cache-Control": "no-cache",
    }

    # Add basic auth header with client name
    client_name_encoded = base64.b64encode(b"ztoq-client:").decode("utf-8")
    auth_headers["Authorization"] = f"Basic {client_name_encoded}"

    # Prepare form data for token request
    auth_data = {
        "grant_type": "password",
        "username": username,
        "password": password,
    }

    # For Parameters API which uses a different format
    if api_type == "parameters":
        auth_data = {"email": username, "password": password}
        auth_headers["Content-Type"] = "application/json"

    logger.debug(f"Auth URL: {url}")
    logger.debug(f"Auth headers: {auth_headers}")
    logger.debug(f"Auth data type: {type(auth_data)}")

    try:
        if api_type == "parameters":
            # Parameters API uses JSON
            response = requests.post(url=url, headers=auth_headers, json=auth_data)
        else:
            # Manager API uses form data
            response = requests.post(url=url, headers=auth_headers, data=auth_data)

        # Log full response details
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")

        try:
            response_data = response.json()
            logger.debug(f"Response JSON: {json.dumps(response_data, indent=2)}")
        except ValueError:
            logger.debug(f"Response text: {response.text}")
            response_data = {}

        # Handle response based on status code
        if response.status_code == 200:
            token = response_data.get("access_token")
            if token:
                logger.info(f"✅ Successfully obtained token from {api_type} API")
                return {
                    "success": True,
                    "token": token,
                    "token_type": response_data.get("token_type", "bearer"),
                    "expires_in": response_data.get("expires_in"),
                }
            logger.error(f"❌ No access token in success response from {api_type} API")
            return {"success": False, "error": "No access token in response", "data": response_data}
        logger.error(f"❌ Authentication failed with status {response.status_code}")
        return {"success": False, "error": f"Status code {response.status_code}", "data": response_data}

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request exception: {e}")
        return {"success": False, "error": str(e)}


def test_client_auth_with_token(base_url, token, project_id=1, api_type="manager"):
    """
    Test authentication with qTest API via bearer token using the client.

    Args:
        base_url: Base URL for qTest API
        token: Bearer token
        project_id: Project ID for testing
        api_type: API type (manager, parameters, pulse, scenario)

    Returns:
        QTestClient instance if successful, None otherwise
    """
    logger.info(f"Testing {api_type} API authentication with bearer token...")

    try:
        # Create config with provided token
        config = QTestConfig(
            base_url=base_url,
            bearer_token=token,
            project_id=project_id,
        )

        # Create client
        client = QTestClient(config, api_type=api_type, log_level="DEBUG")

        # Test authentication by getting projects
        logger.info("Fetching projects to verify token...")
        projects = client.get_projects()

        logger.info(f"✅ Authentication successful! Found {len(projects)} projects")
        for project in projects:
            logger.info(f"- Project {project.id}: {project.name}")

        # Get token status
        token_status = client.get_token_status()
        logger.info(f"Token status: {token_status}")

        return client

    except Exception as e:
        logger.error(f"❌ Authentication with token failed: {e}")
        return None


def test_client_auth_with_credentials(base_url, username, password, project_id=1, api_type="manager"):
    """
    Test authentication with qTest API via username/password using the client.

    Args:
        base_url: Base URL for qTest API
        username: qTest username
        password: qTest password
        project_id: Project ID for testing
        api_type: API type (manager, parameters, pulse, scenario)

    Returns:
        QTestClient instance if successful, None otherwise
    """
    logger.info(f"Testing {api_type} API authentication with username/password...")

    try:
        # Create config with username/password
        config = QTestConfig(
            base_url=base_url,
            username=username,
            password=password,
            project_id=project_id,
        )

        # Create client
        client = QTestClient(config, api_type=api_type, log_level="DEBUG")

        # Test authentication by getting projects
        logger.info("Fetching projects to verify credentials...")
        projects = client.get_projects()

        logger.info(f"✅ Authentication successful! Found {len(projects)} projects")
        for project in projects:
            logger.info(f"- Project {project.id}: {project.name}")

        # Get token status
        token_status = client.get_token_status()
        logger.info(f"Token status: {token_status}")

        return client

    except Exception as e:
        logger.error(f"❌ Authentication with username/password failed: {e}")
        return None


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Debug qTest authentication")
    parser.add_argument("--base-url", help="Base URL for qTest API")
    parser.add_argument("--username", help="qTest username")
    parser.add_argument("--password", help="qTest password")
    parser.add_argument("--token", help="Bearer token")
    parser.add_argument("--project-id", type=int, default=1, help="Project ID for testing")
    parser.add_argument("--api-type", choices=["manager", "parameters", "pulse", "scenario"],
                        default="manager", help="API type to test")
    parser.add_argument("--skip-direct", action="store_true", help="Skip direct auth test")
    parser.add_argument("--skip-token", action="store_true", help="Skip token client test")
    parser.add_argument("--skip-credentials", action="store_true", help="Skip credentials client test")
    args = parser.parse_args()

    # Get values from args or environment variables
    base_url = args.base_url or os.environ.get("qtest_base_url")
    username = args.username or os.environ.get("qtest_username")
    password = args.password or os.environ.get("qtest_password")
    token = args.token or os.environ.get("qtest_bearer_token")
    project_id = args.project_id
    api_type = args.api_type

    if not base_url:
        logger.error("Base URL not provided. Use --base-url or set qtest_base_url env variable.")
        return 1

    # Check if we have enough credentials for testing
    if not token and not (username and password):
        logger.error("Either token or username/password is required.")
        return 1

    # Display detected auth methods
    logger.info(f"Testing qTest authentication to {base_url}")
    logger.info(f"API type: {api_type}")
    logger.info(f"Project ID: {project_id}")

    if username:
        logger.info(f"Username available: {username}")
    if password:
        logger.info("Password available: [MASKED]")
    if token:
        masked_token = f"{token[:5]}...{token[-5:]}" if len(token) > 10 else "[MASKED]"
        logger.info(f"Bearer token available: {masked_token}")

    # Test direct authentication with username/password
    if username and password and not args.skip_direct:
        direct_auth_result = test_direct_auth(base_url, username, password, api_type)
        if direct_auth_result.get("success"):
            # Save token for future use if not already provided
            if not token:
                token = direct_auth_result.get("token")
                logger.info("Using token from direct auth for subsequent tests")

    # Test client authentication with token
    if token and not args.skip_token:
        token_client = test_client_auth_with_token(base_url, token, project_id, api_type)

    # Test client authentication with username/password
    if username and password and not args.skip_credentials:
        cred_client = test_client_auth_with_credentials(base_url, username, password,
                                                      project_id, api_type)

    logger.info("Authentication debugging complete")
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Script interrupted by user.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
