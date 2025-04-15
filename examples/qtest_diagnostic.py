"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import argparse
import logging
import os
import socket
import sys
import urllib.parse
from pathlib import Path

import requests

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
logger = logging.getLogger("qtest_diagnostic")


def check_environment_variables():
    """Check and report on qTest related environment variables."""
    logger.info("Checking environment variables...")

    # Variables to check
    required_vars = ["qtest_base_url", "qtest_bearer_token"]
    optional_vars = ["qtest_username", "qtest_password", "qtest_project_id"]

    # Check required variables
    missing = []
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing.append(var)
            logger.error(f"❌ Missing required environment variable: {var}")
        # Mask token for logging
        elif "token" in var.lower():
            masked_value = f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}" if len(value) > 8 else "****"
            logger.info(f"✅ Found {var}: {masked_value}")
        else:
            logger.info(f"✅ Found {var}: {value}")

    # Check optional variables
    for var in optional_vars:
        value = os.environ.get(var)
        if value:
            # Mask password for logging
            if "password" in var.lower():
                logger.info(f"✅ Found optional {var}: ********")
            else:
                logger.info(f"✅ Found optional {var}: {value}")

    return len(missing) == 0


def check_dns(hostname):
    """Check DNS resolution for a hostname."""
    logger.info(f"Checking DNS resolution for: {hostname}")

    try:
        ip_address = socket.gethostbyname(hostname)
        logger.info(f"✅ DNS resolution successful: {hostname} -> {ip_address}")
        return True
    except socket.gaierror as e:
        logger.error(f"❌ DNS resolution failed: {e}")
        return False


def check_http_connectivity(url, verify_ssl=True):
    """Check HTTP connectivity to a URL."""
    logger.info(f"Checking HTTP connectivity to: {url}")

    if not verify_ssl:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        logger.warning("SSL certificate verification is disabled")

    try:
        response = requests.get(url, timeout=10, verify=verify_ssl)
        logger.info(f"✅ HTTP connection successful: Status {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        return True
    except requests.exceptions.SSLError as e:
        logger.error(f"❌ SSL Error: {e}")
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            logger.error("SSL certificate verification failed. Try using --no-verify-ssl")
        elif "tlsv1 unrecognized name" in str(e).lower():
            logger.error("TLS SNI error: The server name in the URL doesn't match the SSL certificate")
            logger.error("This often happens with incorrect domain formats")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ Connection Error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        logger.error(f"❌ Timeout Error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected Error: {e}")
        return False


def analyze_qtest_url(url):
    """Analyze a qTest URL and suggest alternatives if needed."""
    logger.info(f"Analyzing qTest URL: {url}")

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
        logger.info(f"Added https:// prefix: {url}")

    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc
    domain_parts = domain.split(".")

    logger.info(f"Domain parts: {domain_parts}")

    # Check for common qTest domain patterns
    if len(domain_parts) >= 2:
        if domain_parts[-2].lower() == "qtest" and domain_parts[-1].lower() == "net":
            company = domain_parts[0] if len(domain_parts) > 2 else ""
            logger.warning(f"❌ Found incorrect domain format: '{domain}'")
            logger.warning("The 'qtest.net' domain appears to be incorrect")
            correct_domain = f"{company}.qtestnet.com"
            logger.info(f"✓ Suggested domain: {correct_domain}")
            return [f"https://{correct_domain}"]

        if domain_parts[-2].lower() == "qtestnet" and domain_parts[-1].lower() == "com":
            logger.info(f"✅ Domain appears to be using the correct SaaS format: {domain}")
            return []

    # If we can't determine the format, suggest alternatives
    alternatives = []
    if len(domain_parts) >= 2:
        company = domain_parts[0]
        alternatives.append(f"https://{company}.qtestnet.com")

    if alternatives:
        logger.info("Alternative domains to try:")
        for alt in alternatives:
            logger.info(f"  {alt}")

    return alternatives


def test_qtest_authentication(url, token, verify_ssl=True):
    """Test qTest authentication with token."""
    logger.info(f"Testing qTest authentication with token against: {url}")

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # Clean up token (in case it already has a bearer prefix)
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    # Create headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # Test the projects endpoint
    api_url = f"{url}/api/v3/projects"
    logger.info(f"Making API request to: {api_url}")

    try:
        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        response = requests.get(api_url, headers=headers, timeout=15, verify=verify_ssl)

        if response.status_code == 200:
            projects = response.json().get("items", [])
            logger.info(f"✅ Authentication successful! Found {len(projects)} projects")
            return True, projects
        logger.error(f"❌ API request failed with status code: {response.status_code}")
        logger.error(f"Response body: {response.text}")
        return False, None
    except Exception as e:
        logger.error(f"❌ API request failed with error: {e}")
        return False, None


def test_with_qtest_client(url, token, verify_ssl=True):
    """Test using the QTestClient."""
    logger.info(f"Testing with QTestClient against: {url}")

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        # Create config
        config = QTestConfig(
            base_url=url,
            bearer_token=token,
            project_id=1,  # Dummy value for testing
        )

        # Create client with debug logging
        client = QTestClient(config, log_level="DEBUG")

        # Try to get projects
        logger.info("Attempting to get projects...")
        projects = client.get_projects()

        logger.info(f"✅ QTestClient successful! Found {len(projects)} projects")
        for i, project in enumerate(projects):
            logger.info(f"  Project {i+1}: {project.name} (ID: {project.id})")

        return True, projects
    except Exception as e:
        logger.error(f"❌ QTestClient failed with error: {e}")
        return False, None


def print_projects(projects):
    """Pretty print projects."""
    if not projects:
        logger.info("No projects found")
        return

    logger.info("\n=== Projects ===")
    for i, project in enumerate(projects):
        if isinstance(project, dict):
            logger.info(f"{i+1}. {project.get('name')} (ID: {project.get('id')})")
        else:
            logger.info(f"{i+1}. {project.name} (ID: {project.id})")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="qTest Connectivity Diagnostic Tool")
    parser.add_argument("--url", help="qTest base URL")
    parser.add_argument("--token", help="qTest bearer token")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL verification")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("ztoq.qtest_client").setLevel(logging.DEBUG)

    logger.info("=== qTest Connectivity Diagnostic Tool ===")

    # Get credentials from args or environment
    qtest_url = args.url or os.environ.get("qtest_base_url", "")
    qtest_token = args.token or os.environ.get("qtest_bearer_token", "")
    verify_ssl = not args.no_verify_ssl

    # Check environment variables
    env_ok = check_environment_variables()
    if not env_ok:
        logger.warning("Some required environment variables are missing")

    if not qtest_url:
        logger.error("❌ No qTest URL provided. Use --url or set qtest_base_url environment variable")
        return 1

    if not qtest_token:
        logger.error("❌ No qTest token provided. Use --token or set qtest_bearer_token environment variable")
        return 1

    # Ensure URL has proper prefix
    if not qtest_url.startswith(("http://", "https://")):
        qtest_url = f"https://{qtest_url}"

    # Analyze URL
    alternatives = analyze_qtest_url(qtest_url)

    # Check DNS resolution
    hostname = urllib.parse.urlparse(qtest_url).netloc
    dns_ok = check_dns(hostname)

    if not dns_ok:
        logger.error("❌ DNS resolution failed! This is a critical issue.")
        logger.error("  The domain name cannot be resolved to an IP address.")
        logger.error("  Check that the domain name is correct and that you have network connectivity.")

        # Check alternatives
        for alt_url in alternatives:
            alt_hostname = urllib.parse.urlparse(alt_url).netloc
            logger.info(f"Trying DNS resolution for alternative: {alt_hostname}")
            if check_dns(alt_hostname):
                logger.info(f"✅ DNS resolution successful for {alt_hostname}!")
                logger.info(f"Consider using this URL instead: {alt_url}")
                qtest_url = alt_url
                dns_ok = True
                break

    # Check HTTP connectivity
    if dns_ok:
        http_ok = check_http_connectivity(qtest_url, verify_ssl)

        if not http_ok and alternatives:
            # Try alternatives
            for alt_url in alternatives:
                logger.info(f"Trying HTTP connectivity to alternative: {alt_url}")
                if check_http_connectivity(alt_url, verify_ssl):
                    logger.info(f"✅ HTTP connectivity successful to {alt_url}!")
                    logger.info("Consider using this URL instead")
                    qtest_url = alt_url
                    http_ok = True
                    break
    else:
        logger.warning("Skipping HTTP connectivity check due to DNS resolution failure")
        http_ok = False

    # Test qTest API authentication
    if dns_ok and http_ok:
        logger.info("\n=== Testing qTest API Authentication ===")

        # First try direct API call
        auth_ok, projects = test_qtest_authentication(qtest_url, qtest_token, verify_ssl)

        if auth_ok:
            logger.info("✅ Direct API authentication successful!")
            print_projects(projects)
        else:
            logger.warning("❌ Direct API authentication failed")

            # Try alternatives
            for alt_url in alternatives:
                logger.info(f"Trying authentication with alternative URL: {alt_url}")
                alt_auth_ok, alt_projects = test_qtest_authentication(alt_url, qtest_token, verify_ssl)
                if alt_auth_ok:
                    logger.info(f"✅ Authentication successful with {alt_url}!")
                    print_projects(alt_projects)
                    qtest_url = alt_url
                    auth_ok = True
                    projects = alt_projects
                    break

        # If direct API call didn't work, try QTestClient
        if not auth_ok:
            logger.info("\n=== Testing with QTestClient ===")
            client_ok, client_projects = test_with_qtest_client(qtest_url, qtest_token, verify_ssl)

            if client_ok:
                logger.info("✅ QTestClient authentication successful!")
                print_projects(client_projects)
            else:
                logger.warning("❌ QTestClient authentication failed")

                # Try alternatives with client
                for alt_url in alternatives:
                    logger.info(f"Trying QTestClient with alternative URL: {alt_url}")
                    alt_client_ok, alt_client_projects = test_with_qtest_client(alt_url, qtest_token, verify_ssl)
                    if alt_client_ok:
                        logger.info(f"✅ QTestClient successful with {alt_url}!")
                        print_projects(alt_client_projects)
                        qtest_url = alt_url
                        break

    # Print summary
    logger.info("\n=== Diagnostic Summary ===")
    logger.info(f"URL: {qtest_url}")
    logger.info(f"DNS Resolution: {'✅ Success' if dns_ok else '❌ Failed'}")
    logger.info(f"HTTP Connectivity: {'✅ Success' if http_ok else '❌ Failed'}")
    logger.info(f"API Authentication: {'✅ Success' if auth_ok else '❌ Failed'}")

    if not dns_ok or not http_ok or not auth_ok:
        logger.info("\n=== Recommendations ===")

        if not dns_ok:
            logger.info("1. Check that the domain name is correct")
            logger.info("2. Check your network connectivity")
            logger.info("3. Check if the domain is accessible from your network")
            logger.info("4. SaaS instances use format: company.qtestnet.com (NOT qtest.net)")
            logger.info("5. Try one of the suggested alternative URLs")

        if not http_ok:
            logger.info("1. Check if the qTest server is up and running")
            logger.info("2. Check if your network blocks HTTPS connections")
            logger.info("3. Try using --no-verify-ssl if you have SSL certificate issues")
            logger.info("4. Check if you need to use a proxy to access the internet")

        if not auth_ok:
            logger.info("1. Check that your token is valid and not expired")
            logger.info("2. Make sure you're using the correct URL format")
            logger.info("3. Check if your token has the necessary permissions")
            logger.info("4. Try regenerating a new token in the qTest UI")

    return 0 if dns_ok and http_ok and auth_ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("Diagnostic interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if logger.level <= logging.DEBUG:
            import traceback
            logger.debug(traceback.format_exc())
        sys.exit(1)
