"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Test script for qTest authentication using environment variables.

This script tests whether the qTest client can authenticate with qTest API
using environment variables for base URL and token.

Environment variables:
- qtest_base_url: Base URL for qTest API (e.g., https://example.qtest.com)
- qtest_bearer_token: Bearer token for qTest authentication
"""

import os
import logging
import argparse
from ztoq.qtest_client import QTestClient
from ztoq.qtest_models import QTestConfig

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("qtest_auth_test")

def test_auth(base_url=None, token=None, project_id=1):
    """
    Test authentication with qTest API.

    Args:
        base_url: Optional base URL override (otherwise uses env var)
        token: Optional token override (otherwise uses env var)
        project_id: Project ID to use for testing (default: 1)

    Returns:
        QTestClient instance if successful, None otherwise
    """
    # Check if environment variables are set or use provided values
    base_url = base_url or os.environ.get("qtest_base_url")
    token = token or os.environ.get("qtest_bearer_token")

    if not base_url:
        logger.error("qtest_base_url environment variable not set and no base_url provided")
        return None

    if not token:
        logger.error("qtest_bearer_token environment variable not set and no token provided")
        return None

    logger.info(f"Using base URL: {base_url}")
    logger.info(f"Using token: {token[:5]}...{token[-5:] if len(token) > 10 else ''}")

    try:
        # Create config with provided values
        config = QTestConfig(
            base_url=base_url,
            bearer_token=token,
            project_id=project_id
        )

        # Create client
        client = QTestClient(config)

        # Test authentication by getting projects
        projects = client.get_projects()

        logger.info(f"Authentication successful! Found {len(projects)} projects")
        for project in projects:
            logger.info(f"- Project {project.id}: {project.name}")

        # Get token status
        token_status = client.get_token_status()
        logger.info(f"Token status: {token_status}")

        # Don't revoke the token by default to allow it to be reused
        return client

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return None

def main():
    """Main function for the test script."""
    parser = argparse.ArgumentParser(description="Test qTest authentication")
    parser.add_argument("--revoke", action="store_true", help="Revoke the token after successful authentication")
    parser.add_argument("--base-url", help="Base URL for qTest API (overrides environment variable)")
    parser.add_argument("--token", help="Bearer token for qTest authentication (overrides environment variable)")
    parser.add_argument("--project-id", type=int, default=1, help="Project ID to use for testing (default: 1)")
    args = parser.parse_args()

    client = test_auth(base_url=args.base_url, token=args.token, project_id=args.project_id)
    if client:
        print("Authentication test passed")

        if args.revoke:
            logger.info("Revoking token...")
            revoked = client.revoke_token()
            if revoked:
                logger.info("Token successfully revoked")
            else:
                logger.error("Failed to revoke token")
                return 1

        return 0
    else:
        print("Authentication test failed")
        return 1

if __name__ == "__main__":
    exit(main())
