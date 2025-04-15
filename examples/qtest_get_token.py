"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Script to acquire a qTest API access token using username/password authentication.

This script demonstrates how to get a qTest access token using username and password,
which can be used in other scripts that need to authenticate with the qTest API.
"""

import argparse
import json
import logging
import os
import sys

import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("qtest_get_token")

def get_token(base_url, username, password):
    """
    Get a qTest API token using username and password.

    Args:
        base_url: Base URL for qTest API (e.g., https://example.qtest.com)
        username: qTest username
        password: qTest password

    Returns:
        Dict with token information if successful, error message otherwise
    """
    # Validate base URL
    if not base_url.startswith(("http://", "https://")):
        return {"error": "base_url must start with http:// or https://"}

    # Prepare auth endpoint
    auth_endpoint = f"{base_url}/oauth/token"

    # Prepare headers
    import base64
    client_name_encoded = base64.b64encode(b"ztoq-client:").decode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cache-Control": "no-cache",
        "Authorization": f"Basic {client_name_encoded}",
    }

    # Prepare body
    data = {
        "grant_type": "password",
        "username": username,
        "password": password,
    }

    logger.info(f"Authenticating to {auth_endpoint}")

    try:
        # Make request
        response = requests.post(auth_endpoint, headers=headers, data=data)
        response.raise_for_status()

        # Parse response
        token_data = response.json()

        # Extract token and expiration
        token = token_data.get("access_token")
        token_type = token_data.get("token_type", "bearer")
        expires_in = token_data.get("expires_in")
        scope = token_data.get("scope", "")

        if not token:
            return {"error": "No access token in response"}

        logger.info(f"Successfully acquired token (expires in {expires_in} seconds)")

        return {
            "token": token,
            "token_type": token_type,
            "expires_in": expires_in,
            "scope": scope,
        }

    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to acquire token: {e!s}"
        logger.error(error_msg)

        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            try:
                error_json = e.response.json()
                logger.error(f"Error details: {error_json}")
            except:
                logger.error(f"Response text: {e.response.text}")

        return {"error": error_msg}

def main():
    """Main function for the token acquisition script."""
    parser = argparse.ArgumentParser(description="Get a qTest API token")
    parser.add_argument("--base-url", help="Base URL for qTest API")
    parser.add_argument("--username", help="qTest username")
    parser.add_argument("--password", help="qTest password")
    parser.add_argument("--save", action="store_true", help="Save token to environment variables")
    parser.add_argument("--output", choices=["text", "json", "env"], default="text",
                        help="Output format (text, json, or env variables)")
    args = parser.parse_args()

    # Get values from arguments or environment or prompt
    base_url = args.base_url or os.environ.get("qtest_base_url")
    if not base_url:
        base_url = input("Enter qTest base URL (e.g., https://example.qtest.com): ")

    username = args.username or os.environ.get("qtest_username")
    if not username:
        username = input("Enter qTest username: ")

    password = args.password or os.environ.get("qtest_password")
    if not password:
        import getpass
        password = getpass.getpass("Enter qTest password: ")

    # Get token
    result = get_token(base_url, username, password)

    # Check for error
    if "error" in result:
        logger.error(result["error"])
        if args.output == "json":
            print(json.dumps(result, indent=2))
        return 1

    # Output based on format
    if args.output == "text":
        print(f"Access Token: {result['token']}")
        print(f"Token Type: {result['token_type']}")
        print(f"Expires In: {result['expires_in']} seconds")
        print(f"Scope: {result['scope']}")

    elif args.output == "json":
        print(json.dumps(result, indent=2))

    elif args.output == "env":
        print(f"export qtest_base_url='{base_url}'")
        print(f"export qtest_bearer_token='{result['token']}'")

    # Save to environment if requested
    if args.save:
        os.environ["qtest_base_url"] = base_url
        os.environ["qtest_bearer_token"] = result["token"]
        logger.info("Saved token to environment variables (for current process only)")

    return 0

if __name__ == "__main__":
    sys.exit(main())
