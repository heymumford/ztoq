"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path to enable imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig
from ztoq.zephyr_client import ZephyrClient
from ztoq.qtest_client import QTestClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("verify_api_tokens")

def verify_zephyr_token():
    """Verify the Zephyr API token from environment variables."""
    token = os.environ.get("zephyr_access_token", "")
    if not token:
        logger.error("Zephyr access token not found in environment variables.")
        logger.error("Please set the 'zephyr_access_token' environment variable.")
        return False

    logger.info(f"Found Zephyr access token: {token[:4]}{'*' * (len(token) - 8)}{token[-4:]}")

    try:
        # Create client config from environment variables
        config = ZephyrConfig.from_env(
            base_url="https://api.zephyrscale.smartbear.com/v2",
            project_key="DEMO"  # Update with your project key
        )

        # Create client and verify token
        client = ZephyrClient(config)
        is_valid = client.verify_api_token()

        if is_valid:
            logger.info("✅ Zephyr API token is valid and working correctly.")
            return True
        else:
            logger.error("❌ Zephyr API token is invalid or doesn't have proper permissions.")
            return False

    except Exception as e:
        logger.error(f"Error verifying Zephyr token: {e}")
        return False

def verify_qtest_token():
    """Verify the qTest API token from environment variables."""
    token = os.environ.get("qtest_bearer_token", "")
    if not token:
        logger.error("qTest bearer token not found in environment variables.")
        logger.error("Please set the 'qtest_bearer_token' environment variable.")
        return False

    logger.info(f"Found qTest bearer token: {token[:4]}{'*' * (len(token) - 8)}{token[-4:]}")

    try:
        # Create client config from environment variables
        config = QTestConfig.from_env(
            base_url="https://demo.qtestnet.com",  # Update with your qTest instance URL
            project_id=12345  # Update with your project ID
        )

        # Create client and verify token
        client = QTestClient(config)
        is_valid = client.verify_api_token()

        if is_valid:
            logger.info("✅ qTest API token is valid and working correctly.")
            return True
        else:
            logger.error("❌ qTest API token is invalid or doesn't have proper permissions.")
            return False

    except Exception as e:
        logger.error(f"Error verifying qTest token: {e}")
        return False

def main():
    """Main entry point for the script."""
    logger.info("Verifying API tokens...")

    zephyr_valid = verify_zephyr_token()
    qtest_valid = verify_qtest_token()

    if zephyr_valid and qtest_valid:
        logger.info("\n✨ All API tokens are valid! ✨")
        return 0
    else:
        logger.error("\n❌ One or more API tokens are invalid. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
