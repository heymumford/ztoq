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

# Create a logger with no handlers (we'll add them only if they don't exist)
logger = logging.getLogger("verify_api_tokens")

# Only configure if no handlers exist yet to avoid duplicate logging
if not logger.handlers:
    # Set logging level
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Create handler and formatter
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

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

def verify_qtest_token(timeout_seconds=15, no_verify_ssl=False):
    """Verify the qTest API token from environment variables.

    Args:
        timeout_seconds: Maximum time to wait for verification in seconds
        no_verify_ssl: If True, SSL certificate verification will be disabled

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

        # Handle common qTest domain variations
        # Extract the domain part for normalization
        import urllib.parse
        domain_parts = urllib.parse.urlparse(base_url).netloc.split('.')

        # Check if we need to try alternative domain formats
        try_alternative_domains = False

        # Log the domain analysis for debugging
        logger.debug(f"Analyzing domain: {urllib.parse.urlparse(base_url).netloc}")
        logger.debug(f"Domain parts: {domain_parts}")

        # If domain doesn't contain 'qtest' or doesn't end with recognized TLD formats
        if not any('qtest' in part.lower() for part in domain_parts) and \
           not any(domain_parts[-1].lower() in ['com', 'net', 'org', 'io']) and \
           not any(f"{domain_parts[-2]}.{domain_parts[-1]}".lower() in ['co.uk', 'com.au']):
            try_alternative_domains = True
            logger.debug("Domain format may not be standard, will try alternative formats")

        # Handle the specific qtest.net case (which should be qtestnet.com)
        if len(domain_parts) >= 2 and domain_parts[-2].lower() == 'qtest' and domain_parts[-1].lower() == 'net':
            try_alternative_domains = True
            logger.warning("Found 'qtest.net' domain which is likely incorrect. qTest SaaS typically uses 'qtestnet.com'")
            # Get the company name part
            company_name = '.'.join(domain_parts[:-2]) if len(domain_parts) > 2 else domain_parts[0]
            logger.info(f"Automatically trying {company_name}.qtestnet.com instead")

        # Special handling for company-specific subdomains
        if len(domain_parts) >= 2 and 'qtest' not in domain_parts[0].lower():
            # This might be a company.qtestnet.com format or similar
            try_alternative_domains = True
            logger.debug("Domain may be using company-specific format, will try alternatives")

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

            # If requested, disable SSL verification warnings
            if no_verify_ssl:
                logger.warning("SSL certificate verification is disabled for client verification")
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # Temporarily replace requests.request with a version that has a timeout
            original_request = requests.request

            def request_with_timeout(*args, **kwargs):
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = (5.0, 10.0)
                # Add verify parameter if not already present
                if 'verify' not in kwargs:
                    kwargs['verify'] = not no_verify_ssl
                return original_request(*args, **kwargs)

            # Monkey patch requests.request temporarily
            requests.request = request_with_timeout

            try:
                # Use the client's built-in verification with SSL option
                valid = client.verify_api_token(verify_ssl=not no_verify_ssl)
                if valid:
                    logger.info("✅ qTest API token is valid and working correctly.")
                    return True
                else:
                    # Check the error in the logs to provide more specific messages
                    logger.error("❌ qTest API token verification failed.")
                    # If we need to try alternative domains
                    if try_alternative_domains:
                        # Try alternative domain formats
                        alternative_formats = []
                        domain = urllib.parse.urlparse(base_url).netloc

                        # Handle the specific qtest.net case which should be qtestnet.com
                        if len(domain_parts) >= 2 and domain_parts[-2].lower() == 'qtest' and domain_parts[-1].lower() == 'net':
                            # Get the company name part
                            company_name = '.'.join(domain_parts[:-2]) if len(domain_parts) > 2 else domain_parts[0]
                            # This is likely the correct format for SaaS
                            alt_url = f"https://{company_name}.qtestnet.com"
                            logger.warning(f"The domain '{domain}' appears to be using an incorrect format.")
                            logger.info(f"According to qTest documentation, SaaS instances use the format: <company>.qtestnet.com")
                            logger.info(f"Trying the corrected URL: {alt_url}")
                            alternative_formats.append(alt_url)

                        # If the domain has at least two parts (e.g., company.domain.tld)
                        elif len(domain_parts) >= 2:
                            # For SaaS, the correct format is "company.qtestnet.com"
                            alternative_formats.append(f"https://{domain_parts[0]}.qtestnet.com")

                            # For completeness, also try these alternatives
                            alternative_formats.append(f"https://{domain_parts[0]}.qtest.com")

                            # Try direct qTest domain
                            if 'qtest' not in domain.lower():
                                alternative_formats.append(f"https://qtest.{domain}")

                        logger.info("Attempting alternative domain formats:")
                        for alt_url in alternative_formats:
                            logger.info(f"  Trying alternative URL: {alt_url}")
                            try:
                                alt_config = QTestConfig.from_env(base_url=alt_url, project_id=1)
                                alt_client = QTestClient(alt_config)
                                if alt_client.verify_api_token(verify_ssl=not no_verify_ssl):
                                    logger.info(f"✅ Connection successful with alternative URL: {alt_url}")
                                    logger.info("Consider updating your qtest_base_url environment variable")
                                    return True
                            except Exception as alt_error:
                                logger.debug(f"Alternative URL {alt_url} failed: {alt_error}")

                    logger.info("Try checking:")
                    logger.info("1. Network connectivity to the qTest server")
                    logger.info("2. Correct URL format - according to qTest documentation:")
                    logger.info("   - SaaS instances: https://company.qtestnet.com (NOT qtest.net)")
                    logger.info("   - On-premises instances: Your custom URL as configured")
                    logger.info("3. Check for DNS resolution issues (ping the domain)")
                    logger.info("4. Token validity and permissions")
                    logger.info("5. If SSL errors occur, try the --no-verify-ssl option (use with caution)")
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

                # Check if SSL verification should be disabled
                verify_ssl = not no_verify_ssl
                if not verify_ssl:
                    logger.warning("SSL certificate verification is disabled")
                    # Suppress the InsecureRequestWarning that comes with verify=False
                    import urllib3
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

                # Add diagnostic info
                logger.debug(f"Making direct request to {url}")
                logger.debug(f"SSL verification: {'disabled' if not verify_ssl else 'enabled'}")

                # Try to diagnose DNS issues first
                try:
                    import socket
                    hostname = urllib.parse.urlparse(url).netloc
                    logger.debug(f"Resolving hostname: {hostname}")
                    ip_address = socket.gethostbyname(hostname)
                    logger.debug(f"Successfully resolved {hostname} to {ip_address}")
                except socket.gaierror as dns_error:
                    logger.error(f"DNS resolution failed for {hostname}: {dns_error}")
                    logger.error("This indicates a DNS resolution issue - the domain name cannot be found")
                    logger.error("Check that the domain name is correct and accessible from your network")

                try:
                    response = requests.get(url=url, headers=headers, timeout=(5.0, 10.0), verify=verify_ssl)
                except requests.exceptions.SSLError as ssl_error:
                    logger.error(f"SSL Error: {ssl_error}")
                    if "CERTIFICATE_VERIFY_FAILED" in str(ssl_error):
                        logger.error("SSL certificate verification failed. Try using --no-verify-ssl if appropriate.")
                    elif "tlsv1 unrecognized name" in str(ssl_error).lower():
                        logger.error("TLS SNI error: The server name in the URL doesn't match the SSL certificate.")
                        logger.error("This often happens with incorrect domain formats or internal server misconfiguration.")
                    raise

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
            except ConnectionError as conn_error:
                logger.error("❌ Could not connect to qTest API.")
                logger.error(f"Connection error details: {conn_error}")

                # Check for proxy issues in corporate environments
                if "ProxyError" in str(conn_error) or "Tunnel connection failed" in str(conn_error):
                    logger.error("This appears to be a proxy-related connection error.")
                    logger.error("If you're in a corporate environment:")
                    logger.error("1. Check your network proxy settings")
                    logger.error("2. Try setting HTTP_PROXY and HTTPS_PROXY environment variables")
                    logger.error("3. Ensure the proxy allows connections to the qTest domain")
                elif "NewConnectionError" in str(conn_error) or "Connection refused" in str(conn_error):
                    logger.error("The connection was actively refused or timed out.")
                    logger.error("This could be due to:")
                    logger.error("1. Incorrect domain name")
                    logger.error("2. Firewall blocking the connection")
                    logger.error("3. qTest server might be down or not accessible from your network")

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

def check_domain_connectivity(domain):
    """
    Check connectivity to a domain using ping.

    Args:
        domain: Domain name to check

    Returns:
        Tuple of (success, message)
    """
    import subprocess
    from shutil import which

    # Check if ping command is available
    if not which("ping"):
        return False, "Ping command not available on this system"

    logger.info(f"Testing connectivity to {domain}...")

    try:
        # Run ping command with timeout
        if os.name == 'nt':  # Windows
            ping_cmd = ["ping", "-n", "3", "-w", "1000", domain]
        else:  # Unix/Linux/MacOS
            ping_cmd = ["ping", "-c", "3", "-W", "1", domain]

        result = subprocess.run(
            ping_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return True, "Connectivity test successful"
        else:
            return False, f"Ping failed with return code {result.returncode}: {result.stderr}"

    except subprocess.TimeoutExpired:
        return False, "Ping command timed out"
    except Exception as e:
        return False, f"Error running ping: {str(e)}"

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
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL certificate verification (use with caution)")
    parser.add_argument("--check-connectivity", action="store_true", help="Check basic connectivity to qTest domain")

    args = parser.parse_args()

    # Set debug mode if requested (only if not already in debug mode)
    if args.debug and log_level != "DEBUG":
        logger.setLevel(logging.DEBUG)
        logging.getLogger("ztoq.qtest_client").setLevel(logging.DEBUG)
        logging.getLogger("ztoq.zephyr_client").setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled via command line argument")

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

    # Check connectivity to qTest domain if requested
    if args.check_connectivity and not args.skip_qtest:
        qtest_base_url = os.environ.get("qtest_base_url", "")
        if qtest_base_url:
            # Extract domain from URL
            if not qtest_base_url.startswith(('http://', 'https://')):
                qtest_base_url = f"https://{qtest_base_url}"

            import urllib.parse
            domain = urllib.parse.urlparse(qtest_base_url).netloc

            logger.info(f"Checking basic connectivity to qTest domain: {domain}")
            success, message = check_domain_connectivity(domain)

            if success:
                logger.info(f"✅ Successfully connected to {domain}: {message}")
            else:
                logger.error(f"❌ Could not connect to {domain}: {message}")
                logger.error("This indicates a network connectivity or DNS resolution issue.")
                logger.error("Check that the domain is accessible from your network.")

                # Try alternative domain formats if needed
                if not any('qtest' in part.lower() for part in domain.split('.')):
                    logger.info("Trying alternative domain formats...")

                    # Try common qTest domain variations
                    alt_domains = []
                    domain_parts = domain.split('.')

                    # Handle the specific qtest.net case which should be qtestnet.com
                    if len(domain_parts) >= 2 and domain_parts[-2].lower() == 'qtest' and domain_parts[-1].lower() == 'net':
                        # Get the company name part
                        company_name = '.'.join(domain_parts[:-2]) if len(domain_parts) > 2 else domain_parts[0]
                        logger.warning(f"The domain '{domain}' appears to be using an incorrect format.")
                        logger.info("According to qTest documentation:")
                        logger.info("- SaaS instances use format: <company>.qtestnet.com")
                        logger.info("- On-premises instances use your custom domain")

                        # Add the correct SaaS format
                        alt_domains.append(f"{company_name}.qtestnet.com")
                    elif len(domain_parts) >= 2:
                        # Try company.qtestnet.com format (standard SaaS format)
                        alt_domains.append(f"{domain_parts[0]}.qtestnet.com")
                        # Try company.qtest.com format (alternative format)
                        alt_domains.append(f"{domain_parts[0]}.qtest.com")

                    for alt_domain in alt_domains:
                        logger.info(f"Testing connectivity to alternative domain: {alt_domain}")
                        alt_success, alt_message = check_domain_connectivity(alt_domain)

                        if alt_success:
                            logger.info(f"✅ Successfully connected to alternative domain {alt_domain}")
                            logger.info(f"Consider using https://{alt_domain} as your qTest base URL")
                        else:
                            logger.debug(f"Could not connect to alternative domain {alt_domain}: {alt_message}")
        else:
            logger.warning("qTest base URL not provided, skipping connectivity check")

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
        qtest_valid = verify_qtest_token(
            timeout_seconds=args.timeout,
            no_verify_ssl=args.no_verify_ssl
        )
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
