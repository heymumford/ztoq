"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import os
import sys
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
logger = logging.getLogger("qtest_check_connection")


def check_domain_format(domain, token, no_verify_ssl=False):
    """
    Check if the domain is in the correct format for qTest access.
    Tries various domain formats and reports which one works.
    """
    # Strip any protocol prefixes
    if "://" in domain:
        domain = domain.split("://")[1]

    # Remove trailing slashes
    domain = domain.rstrip("/")

    # Generate potential domain formats to try
    formats_to_try = [
        domain,  # Original format
        f"https://{domain}",  # Ensure https:// prefix
    ]

    # Extract company name (first part of domain) and try common qTest domain patterns
    parts = domain.split(".")
    company = parts[0]

    # Add common qTest domain formats if not already in the list
    additional_formats = [
        f"https://{company}.qtestnet.com",  # Common qTest domain format
        f"https://{company}.qtest.com",     # Alternative qTest domain format
        f"https://{company}.qtest.net",     # Another possible format
    ]

    # Add formats that aren't already in the list
    for fmt in additional_formats:
        if fmt not in formats_to_try:
            formats_to_try.append(fmt)

    # Configure SSL verification
    verify_ssl = not no_verify_ssl
    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logger.warning("SSL certificate verification is disabled")

    # Create headers with proper Bearer format
    # Strip Bearer prefix if present in token
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Try each domain format
    working_formats = []

    for i, fmt in enumerate(formats_to_try):
        if not fmt.startswith(('http://', 'https://')):
            fmt = f"https://{fmt}"

        logger.info(f"Trying format {i+1}/{len(formats_to_try)}: {fmt}")

        # Endpoint for projects
        endpoint = "/api/v3/projects"
        url = f"{fmt}{endpoint}"

        try:
            # Make the request
            response = requests.get(
                url=url,
                headers=headers,
                timeout=10,
                verify=verify_ssl
            )

            # If success, add to working formats
            if response.status_code == 200:
                logger.info(f"✅ Success! Domain format works: {fmt}")
                working_formats.append(fmt)

                # Try to get project list as additional verification
                try:
                    data = response.json()
                    projects = data.get("items", [])
                    logger.info(f"   Found {len(projects)} projects")
                    for j, project in enumerate(projects[:3]):
                        logger.info(f"   Project {j+1}: {project.get('name', 'Unknown')} (ID: {project.get('id', 'Unknown')})")
                    if len(projects) > 3:
                        logger.info(f"   ... and {len(projects) - 3} more projects")
                except Exception as e:
                    logger.warning(f"   Could not parse project data: {e}")
            else:
                logger.info(f"❌ Failed with status code: {response.status_code}")

                # Log common error messages
                if response.status_code == 401:
                    logger.info("   Authentication failed: Invalid or expired token")
                elif response.status_code == 403:
                    logger.info("   Authorization failed: Insufficient permissions")
                elif response.status_code == 404:
                    logger.info("   Resource not found: Check URL path")

        except requests.exceptions.ConnectionError:
            logger.info(f"❌ Could not connect to {fmt}")
        except requests.exceptions.Timeout:
            logger.info(f"❌ Connection timed out for {fmt}")
        except Exception as e:
            logger.info(f"❌ Error: {str(e)}")

    return working_formats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check qTest Domain Formats")
    parser.add_argument("--url", help="qTest base URL or domain")
    parser.add_argument("--token", help="qTest bearer token")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL verification")

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

    # Check domain formats
    logger.info(f"Checking domain formats for: {qtest_url}")
    working_formats = check_domain_format(qtest_url, qtest_token, args.no_verify_ssl)

    if working_formats:
        logger.info("\n✅ Working domain formats found:")
        for i, fmt in enumerate(working_formats):
            logger.info(f"{i+1}. {fmt}")

        # Provide environment variable commands for the first working format
        if working_formats:
            recommended = working_formats[0]
            logger.info("\nRecommended configuration:")
            logger.info(f"export qtest_base_url=\"{recommended}\"")
            logger.info(f"export qtest_bearer_token=\"{qtest_token}\"")

        return 0
    else:
        logger.error("\n❌ No working domain formats found")
        logger.error("Please verify:")
        logger.error("1. The qTest domain is correct")
        logger.error("2. The bearer token is valid and not expired")
        logger.error("3. Your network allows connections to the qTest server")
        return 1


if __name__ == "__main__":
    sys.exit(main())
