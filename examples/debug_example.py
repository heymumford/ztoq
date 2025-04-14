#!/usr/bin/env python3
"""
Example script demonstrating how to use debug logging with ZTOQ.
"""
import sys
from pathlib import Path

# Add parent directory to path if running as script
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

from ztoq.models import ZephyrConfig
from ztoq.zephyr_client import ZephyrClient, configure_logging


def main():
    """Main entry point for example."""
    # You can set log level in three ways:

    # 1. Set environment variable (this would be set before running the script)
    # os.environ["ZTOQ_LOG_LEVEL"] = "DEBUG"

    # 2. Configure global logging level manually
    configure_logging("DEBUG")

    # 3. Set log level when creating client (most flexible)
    config = ZephyrConfig(
        base_url="https://api.zephyrscale.smartbear.com/v2",
        api_token="your-api-token",  # Replace with your actual token
        project_key="PROJ",  # Replace with your project key
    )

    # 3a. Use the project's OpenAPI specification for validation
    # Better debugging if API interactions don't work as expected
    openapi_path = Path("docs/specs/z-openapi.yml")

    # Initialize client with debug logging
    client = ZephyrClient.from_openapi_spec(
        spec_path=openapi_path,
        config=config,
        log_level="DEBUG",  # Override global level if needed
    )

    # Debug log will show API interactions in detail
    try:
        print("Getting projects...")
        projects = client.get_projects()
        print(f"Found {len(projects)} projects")

        if projects:
            project = projects[0]
            print(f"First project: {project.name} (key: {project.key})")

            print(f"Getting test cases for {project.key}...")
            test_cases = client.get_test_cases(project.key)
            case_count = 0

            # Process first few test cases
            for i, case in enumerate(test_cases):
                if i >= 5:  # Limit to 5 for demo
                    break
                print(f"  - {case.key}: {case.name}")
                case_count += 1

            print(f"Processed {case_count} test cases")

    except Exception as e:
        print(f"Error: {e}")
        # The stack trace and detailed error will be in the logs


if __name__ == "__main__":
    main()
