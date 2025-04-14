"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import os
import sys
import logging
import time
import signal
import requests
from pathlib import Path
from requests.exceptions import Timeout, ConnectionError, RequestException

# Add the project root to the Python path to enable imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig
from ztoq.zephyr_client import ZephyrClient
from ztoq.qtest_client import QTestClient

# Set up logging
# Get log level from environment variable or use INFO
log_level = os.environ.get("ZTOQ_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("verify_api_tokens")

# Enable debug logging for certain modules if DEBUG level is set
if log_level == "DEBUG":
    logging.getLogger("ztoq.qtest_client").setLevel(logging.DEBUG)
    logging.getLogger("ztoq.zephyr_client").setLevel(logging.DEBUG)

# Global timeout handler
def timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutError("Operation timed out")

def verify_zephyr_token(timeout_seconds=15):
    """Verify the Zephyr API token from environment variables.

    Args:
        timeout_seconds: Maximum time to wait for verification in seconds

    Returns:
        bool: True if token is valid, False otherwise
    """
    token = os.environ.get("zephyr_access_token", "")
    if not token:
        logger.error("Zephyr access token not found in environment variables.")
        logger.error("Please set the 'zephyr_access_token' environment variable.")
        return False

    # Mask token for logging
    masked_token = f"{token[:4]}{'*' * (len(token) - 8)}{token[-4:]}" if len(token) > 8 else "****"
    logger.info(f"Found Zephyr access token: {masked_token}")

    try:
        # Set up a timeout using signal
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)

        # Create client config from environment variables
        config = ZephyrConfig.from_env(
            base_url="https://api.zephyrscale.smartbear.com/v2",
            project_key="DEMO"  # Update with your project key
        )

        # Create client with shorter connection timeouts
        client = ZephyrClient(config)

        # Use the client's _make_request method with explicit timeouts
        # This ensures we don't hang indefinitely
        try:
            client._make_request("GET", "/projects", timeout=(5.0, 10.0))
            logger.info("✅ Zephyr API token is valid and working correctly.")
            return True
        except RequestException as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                logger.error("❌ Zephyr API token is expired or invalid.")
            else:
                logger.error(f"❌ Error connecting to Zephyr API: {str(e)}")
            return False

    except TimeoutError:
        logger.error("❌ Zephyr API token verification timed out after %d seconds.", timeout_seconds)
        return False
    except Exception as e:
        logger.error(f"Error verifying Zephyr token: {e}")
        return False
    finally:
        # Reset the alarm
        signal.alarm(0)

def verify_qtest_token(timeout_seconds=15):
    """Verify the qTest API token from environment variables.

    Args:
        timeout_seconds: Maximum time to wait for verification in seconds

    Returns:
        bool: True if token is valid, False otherwise
    """
    token = os.environ.get("qtest_bearer_token", "")
    if not token:
        logger.error("qTest bearer token not found in environment variables.")
        logger.error("Please set the 'qtest_bearer_token' environment variable.")
        return False

    # Clean up token (in case it already has a bearer prefix)
    if token.lower().startswith("bearer "):
        # Extract just the token part, removing "bearer "
        token = token[7:].strip()
        logger.debug("Removed 'bearer' prefix from token")

    # Mask token for logging
    masked_token = f"{token[:4]}{'*' * (len(token) - 8)}{token[-4:]}" if len(token) > 8 else "****"
    logger.info(f"Found qTest bearer token: {masked_token}")

    try:
        # Set up a timeout using signal
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)

        # Get base URL from environment variable
        base_url = os.environ.get("qtest_base_url", "")
        if not base_url:
            logger.error("qTest base URL not found in environment variables.")
            logger.error("Please set the 'qtest_base_url' environment variable.")
            return False

        # Log available environment variables for debugging
        logger.debug("Environment variables:")
        for env_var, value in os.environ.items():
            if 'token' in env_var.lower() or 'qtest' in env_var.lower() or 'zephyr' in env_var.lower():
                masked_value = value[:4] + '***' + value[-4:] if len(value) > 10 else '***'
                logger.debug(f"  {env_var}: {masked_value}")

        # Ensure base URL has proper prefix
        if not base_url.startswith(('http://', 'https://')):
            base_url = f"https://{base_url}"
            logger.debug(f"Added https:// prefix to base URL: {base_url}")

        # Create client config from environment variables
        config = QTestConfig.from_env(
            base_url=base_url,
            project_id=1  # This is just for verification, actual ID doesn't matter
        )

        # Try two methods for verification:
        # 1. Use the QTestClient directly (which is the preferred method)
        # 2. Fall back to direct API request if there's an issue with the client

        try:
            # Method 1: Use the client's verify_api_token method with timeout
            logger.debug("Verifying token using QTestClient")

            # Create client with our token explicitly set
            if not hasattr(config, 'bearer_token') or not config.bearer_token:
                config.bearer_token = token

            # Override default timeout to ensure we don't hang
            client = QTestClient(config)

            # Temporarily replace requests.request with a version that has a timeout
            original_request = requests.request

            def request_with_timeout(*args, **kwargs):
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = (5.0, 10.0)
                return original_request(*args, **kwargs)

            # Monkey patch requests.request temporarily
            requests.request = request_with_timeout

            try:
                # Use the client's built-in verification
                valid = client.verify_api_token()
                if valid:
                    logger.info("✅ qTest API token is valid and working correctly.")
                    return True
                else:
                    logger.error("❌ qTest API token verification failed.")
                    return False
            finally:
                # Restore original request function
                requests.request = original_request

        except Exception as client_error:
            # Method 1 failed, log the error and try direct API request
            logger.debug(f"Client verification failed: {client_error}")
            logger.debug("Falling back to direct API request")

            try:
                # Method 2: Make a direct request with explicit timeout
                endpoint = "/projects"
                url = f"{base_url}/api/v3{endpoint}"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

                logger.debug(f"Verifying qTest token with direct request to: {url}")
                # Mask the token for logging but show authorization type
                safe_headers = headers.copy()
                if 'Authorization' in safe_headers:
                    auth_parts = safe_headers['Authorization'].split()
                    if len(auth_parts) > 1:
                        safe_headers['Authorization'] = f"{auth_parts[0]} {'*' * 8}"
                    else:
                        safe_headers['Authorization'] = "****"
                logger.debug(f"Headers: {safe_headers}")

                response = requests.get(url=url, headers=headers, timeout=(5.0, 10.0))

                if response.status_code == 200:
                    logger.info("✅ qTest API token is valid and working correctly.")
                    return True
                elif response.status_code == 401:
                    logger.error("❌ qTest API token is expired or invalid.")
                    return False
                else:
                    logger.error(f"❌ qTest API returned unexpected status code: {response.status_code}")
                    return False
            except Timeout:
                logger.error("❌ qTest API request timed out.")
                return False
            except ConnectionError:
                logger.error("❌ Could not connect to qTest API.")
                return False
            except RequestException as e:
                if "401" in str(e) or "Unauthorized" in str(e):
                    logger.error("❌ qTest API token is expired or invalid.")
                else:
                    logger.error(f"❌ Error connecting to qTest API: {str(e)}")
                return False

    except TimeoutError:
        logger.error("❌ qTest API token verification timed out after %d seconds.", timeout_seconds)
        return False
    except Exception as e:
        logger.error(f"Error verifying qTest token: {e}")
        return False
    finally:
        # Reset the alarm
        signal.alarm(0)

def main():
    """Main entry point for the script."""
    import argparse

    # Set up command line arguments
    parser = argparse.ArgumentParser(description="Verify API tokens for ZTOQ")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--qtest-base-url", help="qTest base URL")
    parser.add_argument("--qtest-token", help="qTest bearer token")
    parser.add_argument("--zephyr-token", help="Zephyr access token")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds for each verification")
    parser.add_argument("--skip-zephyr", action="store_true", help="Skip Zephyr token verification")
    parser.add_argument("--skip-qtest", action="store_true", help="Skip qTest token verification")

    args = parser.parse_args()

    # Set debug mode if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("ztoq.qtest_client").setLevel(logging.DEBUG)
        logging.getLogger("ztoq.zephyr_client").setLevel(logging.DEBUG)

    # Set environment variables from command line arguments if provided
    if args.qtest_base_url:
        os.environ["qtest_base_url"] = args.qtest_base_url
        logger.debug(f"Setting qtest_base_url from command line: {args.qtest_base_url}")

    if args.qtest_token:
        os.environ["qtest_bearer_token"] = args.qtest_token
        logger.debug("Setting qtest_bearer_token from command line")

    if args.zephyr_token:
        os.environ["zephyr_access_token"] = args.zephyr_token
        logger.debug("Setting zephyr_access_token from command line")

    logger.info("Verifying API tokens...")

    # Set a global timeout for the entire script
    max_execution_time = args.timeout  # seconds
    start_time = time.time()

    # Track verification results
    zephyr_valid = True  # Default to True if we skip
    qtest_valid = True   # Default to True if we skip

    # Verify Zephyr token if not skipped
    if not args.skip_zephyr:
        zephyr_valid = verify_zephyr_token(timeout_seconds=args.timeout)
    else:
        logger.info("⏩ Skipping Zephyr token verification")

    # Check if we still have time to verify qTest token
    elapsed_time = time.time() - start_time
    remaining_time = max_execution_time - elapsed_time

    if remaining_time <= 0 and not args.skip_qtest:
        logger.error("❌ Script timed out before verifying qTest token.")
        return 1

    # Verify qTest token if not skipped
    if not args.skip_qtest:
        qtest_valid = verify_qtest_token(timeout_seconds=args.timeout)
    else:
        logger.info("⏩ Skipping qTest token verification")

    # Report results
    if zephyr_valid and qtest_valid:
        logger.info("\n✨ All API tokens are valid! ✨")
        return 0
    else:
        logger.error("\n❌ One or more API tokens are invalid. Please check the errors above.")
        return 1

if __name__ == "__main__":
    try:
        # Parse arguments first to get timeout value
        import argparse
        parser = argparse.ArgumentParser(description="Verify API tokens for ZTOQ", add_help=False)
        parser.add_argument("--timeout", type=int, default=45)
        args, _ = parser.parse_known_args()

        # Set an overall timeout for the script
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(args.timeout + 15)  # Add 15 seconds margin to timeout

        exit_code = main()

        # Disable alarm
        signal.alarm(0)
        sys.exit(exit_code)

    except TimeoutError:
        logger.error("❌ Script timed out during execution.")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Script interrupted by user.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if log_level == "DEBUG":
            import traceback
            logger.debug(traceback.format_exc())
        sys.exit(1)
