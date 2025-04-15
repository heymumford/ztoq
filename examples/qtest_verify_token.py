"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
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
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("qtest_verify_token")


def verify_token(base_url, token, no_verify_ssl=False, debug=False):
    """Verify a qTest API token works correctly."""
    # Enable debug logging if requested
    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("ztoq.qtest_client").setLevel(logging.DEBUG)

    try:
        # Ensure URL has proper prefix
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"
            logger.debug(f"Added https:// prefix: {base_url}")

        # Format the token properly by removing Bearer prefix if it exists
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
            logger.debug("Removed 'Bearer' prefix from token")

        # Create qTest config
        config = QTestConfig(
            base_url=base_url,
            bearer_token=token,
            project_id=1,  # Dummy value, not used for token verification
        )

        # Create qTest client
        logger.info(f"Connecting to qTest at {base_url}")
        client = QTestClient(config)

        # Check authorization header format
        auth_header = client.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.error(f"Invalid Authorization header format: {auth_header}")
            return False
        logger.info("✓ Authorization header has correct 'Bearer' format")

        # Verify the token works by making an API call
        logger.info("Testing API access with token...")
        result = client.verify_api_token(verify_ssl=not no_verify_ssl)

        if result:
            logger.info("✓ Token verification successful")

            # Get token status information
            logger.info("Getting token status...")
            status = client.get_token_status()

            if "error" not in status:
                validity_ms = status.get("validityInMilliseconds", 0)
                validity_hours = validity_ms / (1000 * 60 * 60)
                logger.info(f"Token expiration: {status.get('expiration')}")
                logger.info(f"Token validity: {validity_ms} ms ({validity_hours:.2f} hours)")

            # Get project list for additional verification
            logger.info("Listing projects to verify permissions...")
            # Use direct API request to avoid potential model validation issues
            projects_data = client._make_request("GET", "/projects")

            # Handle different response formats
            projects = []
            if isinstance(projects_data, list):
                projects = projects_data
            else:
                projects = projects_data.get("items", [])

            logger.info(f"Found {len(projects)} projects")
            for i, project in enumerate(projects[:5]):  # Show only first 5 projects
                project_id = project.get("id", "Unknown")
                project_name = project.get("name", "Unnamed")
                logger.info(f"  {i+1}. Project {project_id}: {project_name}")

            if len(projects) > 5:
                logger.info(f"  ... and {len(projects) - 5} more projects")

            return True
        logger.error("✗ Token verification failed - API access denied")
        return False

    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        if debug:
            import traceback
            logger.debug(traceback.format_exc())
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify qTest API Token")
    parser.add_argument("--url", help="qTest base URL (e.g., company.qtestnet.com)")
    parser.add_argument("--token", help="qTest bearer token")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL certificate verification")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Get credentials from args or environment
    qtest_url = args.url or os.environ.get("qtest_base_url", "")
    qtest_token = args.token or os.environ.get("qtest_bearer_token", "")

    # Show environment variables used
    if args.debug:
        logger.debug(f"Using base URL from: {'argument' if args.url else 'environment variable'}")
        logger.debug(f"Using token from: {'argument' if args.token else 'environment variable'}")

    if not qtest_url:
        logger.error("qTest URL not provided. Use --url or set qtest_base_url environment variable")
        return 1

    if not qtest_token:
        logger.error("qTest token not provided. Use --token or set qtest_bearer_token environment variable")
        return 1

    # Verify token
    success = verify_token(qtest_url, qtest_token, args.no_verify_ssl, args.debug)

    if success:
        logger.info("✓ Token verification completed successfully")
        return 0
    logger.error("✗ Token verification failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
