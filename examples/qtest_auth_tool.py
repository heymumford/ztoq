#!/usr/bin/env python3
"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
qTest Authentication Tool

A comprehensive tool for working with qTest authentication:
- Acquire tokens using username/password
- Verify token validity
- Get token status and expiration information
- Export tokens to environment variables
- Test API connectivity

Usage examples:
  # Get a token using username and password:
  python qtest_auth_tool.py get-token --base-url https://example.qtest.com --username user@example.com --password P@ssw0rd

  # Verify an existing token:
  python qtest_auth_tool.py verify-token --base-url https://example.qtest.com --token YOUR_TOKEN

  # Get token status (expiration info):
  python qtest_auth_tool.py token-status --base-url https://example.qtest.com --token YOUR_TOKEN

  # Revoke a token:
  python qtest_auth_tool.py revoke-token --base-url https://example.qtest.com --token YOUR_TOKEN

  # Export as environment variables:
  eval $(python qtest_auth_tool.py get-token --base-url https://example.qtest.com --username user@example.com --password P@ssw0rd --format env)
"""

import os
import sys
import logging
import argparse
import json
import getpass
import base64
import requests
import time
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("qtest_auth_tool")

def get_token(base_url, username, password, api_type="manager"):
    """
    Get a qTest API token using username and password.

    Args:
        base_url: Base URL for qTest API (e.g., https://example.qtest.com)
        username: qTest username
        password: qTest password
        api_type: API type (manager, parameters, pulse, scenario)

    Returns:
        Dict with token information if successful, error message otherwise
    """
    # Validate base URL
    if not base_url.startswith(('http://', 'https://')):
        return {"error": "base_url must start with http:// or https://"}

    # Auth endpoints based on API type
    auth_endpoints = {
        "manager": "/oauth/token",
        "parameters": "/oauth/v1/token-login",
        "pulse": "/oauth/token",
        "scenario": "/oauth/token",
    }

    # Determine endpoint based on API type
    endpoint = auth_endpoints.get(api_type, "/oauth/token")
    url = f"{base_url}{endpoint}"

    # Common headers for token request
    auth_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Cache-Control": "no-cache"
    }

    # Add basic auth header with client name
    client_name_encoded = base64.b64encode(b"ztoq-client:").decode('utf-8')
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

    logger.info(f"Authenticating to {api_type} API at {url}")

    try:
        # Make request
        if api_type == "parameters":
            # Parameters API uses JSON
            response = requests.post(url=url, headers=auth_headers, json=auth_data)
        else:
            # Manager API uses form data
            response = requests.post(url=url, headers=auth_headers, data=auth_data)

        # Log response details if debug logging is enabled
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")

            try:
                response_data = response.json()
                logger.debug(f"Response body: {json.dumps(response_data)}")
            except ValueError:
                logger.debug(f"Response body: {response.text}")

        # Handle different status codes
        response.raise_for_status()

        # Parse response
        token_data = response.json()

        # Extract token info
        token = token_data.get("access_token")
        token_type = token_data.get("token_type", "bearer").lower()
        expires_in = token_data.get("expires_in")
        scope = token_data.get("scope", "")

        if not token:
            return {"error": "No access token in response"}

        # Calculate expiration date
        if expires_in:
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            expiration_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
        else:
            expiration_str = "Unknown"

        logger.info(f"Successfully acquired token (expires in {expires_in} seconds, at {expiration_str})")

        return {
            "token": token,
            "token_type": token_type,
            "expires_in": expires_in,
            "expires_at": expiration_str,
            "scope": scope
        }

    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to acquire token: {str(e)}"
        logger.error(error_msg)

        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            logger.error(f"Response status: {status_code}")

            try:
                error_json = e.response.json()
                logger.error(f"Error details: {error_json}")
                return {"error": error_msg, "status_code": status_code, "details": error_json}
            except:
                logger.error(f"Response text: {e.response.text}")
                return {"error": error_msg, "status_code": status_code, "details": e.response.text}

        return {"error": error_msg}

def verify_token(base_url, token, api_type="manager"):
    """
    Verify a qTest API token by making a simple API call.

    Args:
        base_url: Base URL for qTest API
        token: Bearer token to verify
        api_type: API type (manager, parameters, pulse, scenario)

    Returns:
        Dict with verification result
    """
    # Validate base URL
    if not base_url.startswith(('http://', 'https://')):
        return {"valid": False, "error": "base_url must start with http:// or https://"}

    # API paths based on API type
    api_paths = {
        "manager": "/api/v3",
        "parameters": "/api/v1",
        "pulse": "",
        "scenario": "",
    }

    # Get the appropriate API path
    api_path = api_paths.get(api_type, "/api/v3")

    # Create endpoint for projects list (common across API types)
    endpoint = f"{api_path}/projects"
    url = f"{base_url}{endpoint}"

    # Prepare headers with token
    headers = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    logger.info(f"Verifying token by accessing {url}")

    try:
        # Make request
        response = requests.get(url=url, headers=headers)

        # Handle response
        if response.status_code == 200:
            # Get project count for informational purposes
            try:
                data = response.json()
                if api_type == "manager":
                    project_count = len(data.get("items", []))
                else:
                    project_count = len(data.get("data", []))

                logger.info(f"Token is valid! User has access to {project_count} projects.")

                # Get rate limit info if available
                rate_limit_remaining = response.headers.get("X-RateLimit-Remaining", "Unknown")

                return {
                    "valid": True,
                    "project_count": project_count,
                    "rate_limit_remaining": rate_limit_remaining
                }
            except ValueError:
                logger.info("Token is valid!")
                return {"valid": True}

        elif response.status_code == 401:
            logger.error("Token is invalid or expired.")
            return {"valid": False, "error": "Token is invalid or expired"}

        else:
            logger.error(f"Unexpected status code: {response.status_code}")
            return {"valid": False, "error": f"Unexpected status code: {response.status_code}"}

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return {"valid": False, "error": str(e)}

def get_token_status(base_url, token):
    """
    Get status information for a token.

    Args:
        base_url: Base URL for qTest API
        token: Bearer token to check

    Returns:
        Dict with token status information
    """
    # Validate base URL
    if not base_url.startswith(('http://', 'https://')):
        return {"error": "base_url must start with http:// or https://"}

    # Create endpoint for token status
    url = f"{base_url}/oauth/status"

    # Prepare headers with token
    headers = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    logger.info(f"Getting token status from {url}")

    try:
        # Make request
        response = requests.get(url=url, headers=headers)

        # Handle response
        if response.status_code == 200:
            try:
                data = response.json()

                # Format expiration info
                expiration = data.get("expiration")
                validity_ms = data.get("validityInMilliseconds", 0)

                # Convert to hours/minutes
                validity_hours = validity_ms / (1000 * 60 * 60)
                validity_minutes = (validity_ms % (1000 * 60 * 60)) / (1000 * 60)

                logger.info(f"Token expiration: {expiration}")
                logger.info(f"Token validity: {validity_hours:.1f} hours, {validity_minutes:.0f} minutes")

                # Add human-readable validity
                data["validity_hours"] = validity_hours
                data["validity_minutes"] = validity_minutes

                return data

            except ValueError:
                logger.error("Failed to parse response JSON")
                return {"error": "Failed to parse response JSON", "raw": response.text}

        elif response.status_code == 401:
            logger.error("Token is invalid or expired.")
            return {"error": "Token is invalid or expired"}

        else:
            logger.error(f"Unexpected status code: {response.status_code}")
            return {"error": f"Unexpected status code: {response.status_code}"}

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return {"error": str(e)}

def revoke_token(base_url, token):
    """
    Revoke a token.

    Args:
        base_url: Base URL for qTest API
        token: Bearer token to revoke

    Returns:
        Dict with revocation result
    """
    # Validate base URL
    if not base_url.startswith(('http://', 'https://')):
        return {"success": False, "error": "base_url must start with http:// or https://"}

    # Create endpoint for token revocation
    url = f"{base_url}/oauth/revoke"

    # Prepare headers with token
    headers = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    logger.info(f"Revoking token at {url}")

    try:
        # Make request
        response = requests.post(url=url, headers=headers)

        # Handle response
        if response.status_code in [200, 204]:
            logger.info("Token successfully revoked")
            return {"success": True}

        else:
            logger.error(f"Failed to revoke token. Status code: {response.status_code}")
            return {"success": False, "error": f"Unexpected status code: {response.status_code}"}

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return {"success": False, "error": str(e)}

def main():
    # Create parent parser
    parser = argparse.ArgumentParser(description="qTest Authentication Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Base URL argument common to all commands
    base_url_help = "Base URL for qTest API (e.g., https://example.qtest.com or example.qtestnet.com)"

    # Common debug argument
    debug_help = "Enable debug logging"

    # Common API type argument
    api_type_help = "API type to use (manager, parameters, pulse, scenario)"

    # Create parser for 'get-token' command
    get_token_parser = subparsers.add_parser("get-token", help="Get an access token")
    get_token_parser.add_argument("--base-url", required=True, help=base_url_help)
    get_token_parser.add_argument("--username", help="qTest username")
    get_token_parser.add_argument("--password", help="qTest password")
    get_token_parser.add_argument("--api-type", choices=["manager", "parameters", "pulse", "scenario"],
                               default="manager", help=api_type_help)
    get_token_parser.add_argument("--format", choices=["text", "json", "env", "shell"], default="text",
                              help="Output format")
    get_token_parser.add_argument("--debug", action="store_true", help=debug_help)

    # Create parser for 'verify-token' command
    verify_token_parser = subparsers.add_parser("verify-token", help="Verify a token")
    verify_token_parser.add_argument("--base-url", required=True, help=base_url_help)
    verify_token_parser.add_argument("--token", help="Bearer token to verify")
    verify_token_parser.add_argument("--api-type", choices=["manager", "parameters", "pulse", "scenario"],
                                  default="manager", help=api_type_help)
    verify_token_parser.add_argument("--format", choices=["text", "json"], default="text",
                                 help="Output format")
    verify_token_parser.add_argument("--debug", action="store_true", help=debug_help)

    # Create parser for 'token-status' command
    token_status_parser = subparsers.add_parser("token-status", help="Get token status")
    token_status_parser.add_argument("--base-url", required=True, help=base_url_help)
    token_status_parser.add_argument("--token", help="Bearer token to check")
    token_status_parser.add_argument("--format", choices=["text", "json"], default="text",
                                 help="Output format")
    token_status_parser.add_argument("--debug", action="store_true", help=debug_help)

    # Create parser for 'revoke-token' command
    revoke_token_parser = subparsers.add_parser("revoke-token", help="Revoke a token")
    revoke_token_parser.add_argument("--base-url", required=True, help=base_url_help)
    revoke_token_parser.add_argument("--token", help="Bearer token to revoke")
    revoke_token_parser.add_argument("--format", choices=["text", "json"], default="text",
                                 help="Output format")
    revoke_token_parser.add_argument("--debug", action="store_true", help=debug_help)

    # Parse arguments
    args = parser.parse_args()

    # Set debug logging if requested
    if hasattr(args, 'debug') and args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Normalize base URL
    if hasattr(args, 'base_url'):
        if not args.base_url.startswith(('http://', 'https://')):
            args.base_url = f"https://{args.base_url}"

    # Execute command
    if args.command == "get-token":
        # Get username/password from args, env vars, or prompt
        username = args.username or os.environ.get("qtest_username")
        if not username:
            username = input("Enter qTest username: ")

        password = args.password or os.environ.get("qtest_password")
        if not password:
            password = getpass.getpass("Enter qTest password: ")

        result = get_token(args.base_url, username, password, args.api_type)

        if "error" in result:
            print(f"Error: {result['error']}")
            if args.format == "json":
                print(json.dumps(result, indent=2))
            return 1

        # Output result in requested format
        if args.format == "text":
            print(f"Access Token: {result['token']}")
            print(f"Token Type: {result['token_type']}")
            print(f"Expires In: {result['expires_in']} seconds")
            print(f"Expires At: {result['expires_at']}")
            print(f"Scope: {result['scope']}")

        elif args.format == "json":
            print(json.dumps(result, indent=2))

        elif args.format == "env":
            print(f"export qtest_base_url='{args.base_url}'")
            print(f"export qtest_bearer_token='{result['token']}'")

        elif args.format == "shell":
            print(f"qtest_base_url='{args.base_url}'")
            print(f"qtest_bearer_token='{result['token']}'")

    elif args.command == "verify-token":
        # Get token from args or env vars
        token = args.token or os.environ.get("qtest_bearer_token")
        if not token:
            print("Error: No token provided. Use --token or set qtest_bearer_token environment variable.")
            return 1

        result = verify_token(args.base_url, token, args.api_type)

        # Output result in requested format
        if args.format == "text":
            if result.get("valid"):
                print("✅ Token is valid!")
                print(f"Project count: {result.get('project_count', 'Unknown')}")
                print(f"Rate limit remaining: {result.get('rate_limit_remaining', 'Unknown')}")
            else:
                print(f"❌ Token is invalid: {result.get('error', 'Unknown error')}")

        elif args.format == "json":
            print(json.dumps(result, indent=2))

        return 0 if result.get("valid") else 1

    elif args.command == "token-status":
        # Get token from args or env vars
        token = args.token or os.environ.get("qtest_bearer_token")
        if not token:
            print("Error: No token provided. Use --token or set qtest_bearer_token environment variable.")
            return 1

        result = get_token_status(args.base_url, token)

        # Output result in requested format
        if args.format == "text":
            if "error" not in result:
                print("Token Status:")
                print(f"  Expiration: {result.get('expiration', 'Unknown')}")
                print(f"  Validity: {result.get('validityInMilliseconds')} ms")
                print(f"  Valid for approximately: {result.get('validity_hours', 0):.1f} hours, {result.get('validity_minutes', 0):.0f} minutes")
            else:
                print(f"Error: {result['error']}")

        elif args.format == "json":
            print(json.dumps(result, indent=2))

        return 0 if "error" not in result else 1

    elif args.command == "revoke-token":
        # Get token from args or env vars
        token = args.token or os.environ.get("qtest_bearer_token")
        if not token:
            print("Error: No token provided. Use --token or set qtest_bearer_token environment variable.")
            return 1

        result = revoke_token(args.base_url, token)

        # Output result in requested format
        if args.format == "text":
            if result.get("success"):
                print("✅ Token successfully revoked")
            else:
                print(f"❌ Failed to revoke token: {result.get('error', 'Unknown error')}")

        elif args.format == "json":
            print(json.dumps(result, indent=2))

        return 0 if result.get("success") else 1

    else:
        parser.print_help()
        return 1

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
