"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import os
import sys
import json
import logging
import argparse
import requests
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("qtest_direct_api_check")


def check_qtest_api(base_url, token, no_verify_ssl=False, debug=False):
    """Check qTest API directly using requests."""
    if debug:
        logger.setLevel(logging.DEBUG)

    # Ensure URL has proper prefix
    if not base_url.startswith(('http://', 'https://')):
        base_url = f"https://{base_url}"
        logger.debug(f"Added https:// prefix: {base_url}")

    # Clean up token (remove bearer prefix if present)
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
        logger.debug("Removed 'bearer' prefix from token")

    # Configure SSL verification
    verify_ssl = not no_verify_ssl
    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logger.warning("SSL certificate verification is disabled")

    # Create headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Log request details (without sensitive data)
    safe_headers = headers.copy()
    safe_headers["Authorization"] = "Bearer ********"
    logger.debug(f"Headers: {safe_headers}")

    # Endpoint for projects
    endpoint = "/api/v3/projects"
    url = f"{base_url}{endpoint}"

    logger.info(f"Making direct API request to: {url}")

    try:
        # Make the request
        response = requests.get(
            url=url,
            headers=headers,
            timeout=30,
            verify=verify_ssl
        )

        # Log response details
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")

        # Handle response
        if response.status_code == 200:
            try:
                data = response.json()
                projects = data.get("items", [])

                logger.info(f"✅ API request successful! Found {len(projects)} projects:")
                for i, project in enumerate(projects):
                    logger.info(f"{i+1}. {project.get('name')} (ID: {project.get('id')})")

                if debug:
                    logger.debug(f"Raw response: {json.dumps(data, indent=2)}")

                return True
            except ValueError:
                logger.error(f"❌ API returned invalid JSON: {response.text}")
                return False
        else:
            logger.error(f"❌ API request failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")

            # Handle common error codes
            if response.status_code == 401:
                logger.error("Authentication failed: Invalid or expired token")
            elif response.status_code == 403:
                logger.error("Authorization failed: Insufficient permissions")
            elif response.status_code == 404:
                logger.error("Resource not found: Check URL is correct")
            elif response.status_code >= 500:
                logger.error("Server error: The qTest server encountered an error")

            return False

    except requests.exceptions.SSLError as e:
        logger.error(f"❌ SSL Error: {e}")
        logger.error("Try running with --no-verify-ssl if appropriate")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ Connection Error: {e}")
        logger.error("Check that the URL is correct and accessible from your network")
        return False
    except requests.exceptions.Timeout as e:
        logger.error(f"❌ Timeout Error: {e}")
        logger.error("The request took too long to complete")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected Error: {e}")
        if debug:
            import traceback
            logger.debug(traceback.format_exc())
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Direct qTest API Check")
    parser.add_argument("--url", help="qTest base URL (e.g., company.qtestnet.com)")
    parser.add_argument("--token", help="qTest bearer token")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL verification")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--try-alternatives", action="store_true", help="Try alternative domain formats")

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

    # Check API
    success = check_qtest_api(qtest_url, qtest_token, args.no_verify_ssl, args.debug)

    # If failed and try-alternatives is enabled, try alternative domain formats
    if not success and args.try_alternatives:
        logger.info("Original request failed. Trying alternative domain formats...")

        # Parse domain
        domain_parts = qtest_url.split('.')
        if 'http' in domain_parts[0]:
            # Extract domain from URL
            if '://' in qtest_url:
                domain_parts = qtest_url.split('://')[1].split('.')
            else:
                domain_parts = qtest_url.split('.')

        alternatives = []

        # Handle qtest.net case
        if len(domain_parts) >= 2 and domain_parts[-2].lower() == 'qtest' and domain_parts[-1].lower() == 'net':
            company = domain_parts[0]
            alternatives.append(f"{company}.qtestnet.com")
        else:
            # Generic alternatives
            if len(domain_parts) >= 1:
                company = domain_parts[0]
                alternatives.append(f"{company}.qtestnet.com")
                alternatives.append(f"{company}.qtest.com")

        # Try each alternative
        for alt_domain in alternatives:
            logger.info(f"Trying alternative domain: {alt_domain}")
            if check_qtest_api(alt_domain, qtest_token, args.no_verify_ssl, args.debug):
                logger.info(f"✅ Success with alternative domain: {alt_domain}")
                logger.info(f"UPDATE YOUR ENVIRONMENT VARIABLE: qtest_base_url={alt_domain}")
                success = True
                break

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
