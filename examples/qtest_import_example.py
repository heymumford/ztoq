"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Example script demonstrating how to use QTestImporter to import test cases into qTest.

This script shows how to:
1. Initialize QTestImporter with appropriate configuration
2. Prepare test cases to import
3. Import test cases with conflict resolution
4. Handle attachments during the import process

Usage:
    python qtest_import_example.py
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any

from ztoq.qtest_models import QTestConfig, QTestTestCase, QTestStep, QTestCustomField
from ztoq.qtest_importer import QTestImporter, ImportConfig, ConflictResolution

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_sample_test_cases() -> List[QTestTestCase]:
    """Create a list of sample test cases for the example."""
    return [
        QTestTestCase(
            name="Login Functionality Test",
            description="Verify that users can log in with valid credentials",
            precondition="User has a valid account",
            test_steps=[
                QTestStep(
                    description="Navigate to login page",
                    expected_result="Login page is displayed",
                    order=1
                ),
                QTestStep(
                    description="Enter valid username and password",
                    expected_result="Credentials are accepted",
                    order=2
                ),
                QTestStep(
                    description="Click login button",
                    expected_result="User is successfully logged in and redirected to dashboard",
                    order=3
                )
            ],
            properties=[
                QTestCustomField(
                    field_id=1,
                    field_name="Priority",
                    field_type="STRING",
                    field_value="High"
                ),
                QTestCustomField(
                    field_id=2,
                    field_name="Automated",
                    field_type="CHECKBOX",
                    field_value=True
                )
            ]
        ),
        QTestTestCase(
            name="Password Reset Test",
            description="Verify that users can reset their password",
            precondition="User has a valid account",
            test_steps=[
                QTestStep(
                    description="Navigate to login page",
                    expected_result="Login page is displayed",
                    order=1
                ),
                QTestStep(
                    description="Click 'Forgot Password' link",
                    expected_result="Password reset page is displayed",
                    order=2
                ),
                QTestStep(
                    description="Enter registered email address",
                    expected_result="Email field accepts input",
                    order=3
                ),
                QTestStep(
                    description="Click 'Reset Password' button",
                    expected_result="Confirmation message is displayed",
                    order=4
                )
            ],
            properties=[
                QTestCustomField(
                    field_id=1,
                    field_name="Priority",
                    field_type="STRING",
                    field_value="Medium"
                ),
                QTestCustomField(
                    field_id=2,
                    field_name="Automated",
                    field_type="CHECKBOX",
                    field_value=False
                )
            ]
        )
    ]


def main():
    """Execute the qTest import example."""
    logger.info("Starting qTest import example")

    # Get qTest configuration from environment variables
    base_url = os.environ.get("QTEST_URL", "https://example.qtest.com")
    api_token = os.environ.get("QTEST_TOKEN")
    project_id = os.environ.get("QTEST_PROJECT_ID")

    if not api_token or not project_id:
        logger.error("Missing required environment variables: QTEST_TOKEN and QTEST_PROJECT_ID")
        logger.info("Please set the following environment variables:")
        logger.info("  QTEST_URL - qTest base URL (default: https://example.qtest.com)")
        logger.info("  QTEST_TOKEN - API token for qTest authentication")
        logger.info("  QTEST_PROJECT_ID - Project ID to import test cases to")
        return 1

    try:
        # Convert project_id to int
        project_id = int(project_id)
    except ValueError:
        logger.error(f"Invalid project ID: {project_id}. Must be an integer.")
        return 1

    # Create qTest configuration
    qtest_config = QTestConfig(
        base_url=base_url,
        bearer_token=api_token,
        project_id=project_id
    )

    # Create import configuration
    import_config = ImportConfig(
        module_id=None,  # Will be set after listing modules
        conflict_resolution=ConflictResolution.SKIP,
        concurrency=2,
        batch_size=10,
        validate=True,
        show_progress=True
    )

    # Initialize the importer
    importer = QTestImporter(qtest_config, import_config)

    # List available modules
    logger.info("Fetching available modules...")
    modules = importer.get_modules()

    if not modules:
        logger.error("No modules found in the project. Please create at least one module.")
        return 1

    # Print available modules
    logger.info(f"Found {len(modules)} modules:")
    for i, module in enumerate(modules):
        logger.info(f"  {i+1}. {module.name} (ID: {module.id})")

    # For this example, use the first module
    selected_module = modules[0]
    logger.info(f"Selected module: {selected_module.name} (ID: {selected_module.id})")

    # Update import configuration with selected module ID
    import_config.module_id = selected_module.id

    # Create sample test cases
    test_cases = create_sample_test_cases()
    logger.info(f"Created {len(test_cases)} sample test cases")

    # Import test cases
    logger.info("Importing test cases...")
    result = importer.import_test_cases(test_cases)

    # Print import results
    logger.info("Import completed with the following results:")
    logger.info(f"  Total: {result['total']}")
    logger.info(f"  Created: {result['created']}")
    logger.info(f"  Updated: {result.get('updated', 0)}")
    logger.info(f"  Skipped: {result.get('skipped', 0)}")
    logger.info(f"  Failed: {result.get('failed', 0)}")

    # Example of importing a test case with attachments
    if test_cases and result['test_cases']:
        # Use the first test case
        test_case = test_cases[0]

        # Prepare attachment paths (these don't exist in this example)
        attachment_paths = [
            "examples/attachments/screenshot.png",
            "examples/attachments/test_data.csv"
        ]

        # For demonstration purposes, create temporary files
        Path("examples/attachments").mkdir(parents=True, exist_ok=True)

        for path in attachment_paths:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(f"Sample content for {path}")

        logger.info(f"Created temporary attachment files: {attachment_paths}")

        # Import test case with attachments
        logger.info(f"Importing test case '{test_case.name}' with attachments...")

        attachment_result = importer.case_importer.import_test_case_with_attachments(
            test_case, attachment_paths
        )

        # Print attachment results
        logger.info(f"Attachment import completed with {len(attachment_result['attachments'])} attachments:")
        for i, attachment in enumerate(attachment_result['attachments']):
            logger.info(f"  {i+1}. {attachment.name} (ID: {attachment.id})")

        # Clean up temporary files
        for path in attachment_paths:
            if Path(path).exists():
                Path(path).unlink()

        logger.info("Cleaned up temporary attachment files")

    logger.info("Import example completed successfully")
    return 0


if __name__ == "__main__":
    exit(main())
