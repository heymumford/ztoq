"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Add the project root to the Python path to enable imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ztoq.qtest_models import QTestConfig
from ztoq.qtest_client import QTestClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("qtest_list_projects")


def list_projects(base_url, token, no_verify_ssl=False, debug=False):
    """List all projects from qTest."""
    # Enable debug logging if requested
    if debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("ztoq.qtest_client").setLevel(logging.DEBUG)

    try:
        # Ensure URL has proper prefix
        if not base_url.startswith(('http://', 'https://')):
            base_url = f"https://{base_url}"
            logger.debug(f"Added https:// prefix: {base_url}")

        # Configure SSL verification
        if no_verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.warning("SSL certificate verification is disabled")

        # Create qTest config
        config = QTestConfig(
            base_url=base_url,
            bearer_token=token,
            project_id=1  # Dummy value, not used for listing projects
        )

        # Create qTest client
        logger.info(f"Connecting to qTest at {base_url}")
        client = QTestClient(config)

        # Try to get projects
        logger.info("Retrieving projects...")
        projects = client.get_projects()

        # Display projects
        if projects:
            logger.info(f"Found {len(projects)} projects:")
            for i, project in enumerate(projects):
                logger.info(f"{i+1}. {project.name} (ID: {project.id})")
        else:
            logger.warning("No projects found")

        return projects

    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        if debug:
            import traceback
            logger.debug(traceback.format_exc())
        return []


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="List qTest Projects")
    parser.add_argument("--url", help="qTest base URL (e.g., company.qtestnet.com)")
    parser.add_argument("--token", help="qTest bearer token")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL verification")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Get credentials from args or environment
    qtest_url = args.url or os.environ.get("qtest_base_url", "")
    qtest_token = args.token or os.environ.get("qtest_bearer_token", "")

    if not qtest_url:
        logger.error("qTest URL not provided. Use --url or set qtest_base_url environment variable")
        return 1

    if not qtest_token:
        logger.error("qTest token not provided. Use --token or set qtest_bearer_token environment variable")
        return 1

    # List projects
    projects = list_projects(qtest_url, qtest_token, args.no_verify_ssl, args.debug)

    return 0 if projects else 1


if __name__ == "__main__":
    sys.exit(main())
