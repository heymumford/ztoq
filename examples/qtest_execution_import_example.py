"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Example script showing how to use the QTestExecutionImporter.

This example demonstrates importing test executions into qTest,
including handling test steps, attachments, and validation.
"""

import logging
import os
from datetime import datetime
from typing import Any

from ztoq.qtest_importer import ConflictResolution, ImportConfig, QTestImporter
from ztoq.qtest_models import QTestConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("qtest_execution_import_example")


def create_test_executions() -> list[dict[str, Any]]:
    """
    Create sample test executions for the import example.

    Returns:
        List of test execution dictionaries
    """
    # Base execution
    base_execution = {
        "testCaseKey": "DEMO-TC-1001",
        "cycleId": "DEMO-CY-2001",
        "status": "PASS",
        "executedBy": "testuser",
        "executedOn": datetime.now(),
        "comment": "Test executed successfully through QTestExecutionImporter",
        "environment": "Production",
    }

    # Add test steps
    base_execution["steps"] = [
        {
            "id": "step-1",
            "index": 1,
            "description": "Login to the application",
            "expected_result": "Login successful",
            "actual_result": "Login was successful with test user credentials",
            "status": "PASS",
        },
        {
            "id": "step-2",
            "index": 2,
            "description": "Navigate to dashboard",
            "expected_result": "Dashboard displayed with widgets",
            "actual_result": "Dashboard displayed correctly with all expected widgets",
            "status": "PASS",
        },
        {
            "id": "step-3",
            "index": 3,
            "description": "Check reports section",
            "expected_result": "Reports available",
            "actual_result": "All reports were accessible",
            "status": "PASS",
        },
    ]

    # Add custom fields
    base_execution["customFields"] = [
        {
            "name": "Browser",
            "type": "TEXT",
            "value": "Chrome",
        },
        {
            "name": "Build",
            "type": "TEXT",
            "value": "v2.3.1",
        },
    ]

    # Create variations for multiple executions
    executions = [
        # First execution (passed)
        base_execution,

        # Second execution (failed)
        {
            **base_execution,
            "testCaseKey": "DEMO-TC-1002",
            "cycleId": "DEMO-CY-2001",
            "status": "FAIL",
            "comment": "Test failed due to timeout",
            "steps": [
                {
                    "id": "step-1",
                    "index": 1,
                    "description": "Login to the application",
                    "expected_result": "Login successful",
                    "actual_result": "Login was successful",
                    "status": "PASS",
                },
                {
                    "id": "step-2",
                    "index": 2,
                    "description": "Navigate to dashboard",
                    "expected_result": "Dashboard displayed with widgets",
                    "actual_result": "Dashboard failed to load within timeout period",
                    "status": "FAIL",
                },
            ],
        },

        # Third execution (blocked)
        {
            **base_execution,
            "testCaseKey": "DEMO-TC-1003",
            "cycleId": "DEMO-CY-2002",
            "status": "BLOCKED",
            "comment": "Test blocked due to environment issue",
            "steps": [
                {
                    "id": "step-1",
                    "index": 1,
                    "description": "Login to the application",
                    "expected_result": "Login successful",
                    "actual_result": "Unable to connect to authentication service",
                    "status": "BLOCKED",
                },
            ],
        },
    ]

    return executions


def main():
    """Run the example script."""
    # Get qTest connection details from environment or use defaults for example
    qtest_url = os.environ.get("QTEST_URL", "https://example.qtest.com")
    qtest_token = os.environ.get("QTEST_TOKEN", "example-token")
    project_id = int(os.environ.get("QTEST_PROJECT_ID", "12345"))

    # Configure qTest client
    config = QTestConfig(
        base_url=qtest_url,
        bearer_token=qtest_token,
        project_id=project_id,
    )

    # Create import configuration
    import_config = ImportConfig(
        conflict_resolution=ConflictResolution.UPDATE,
        concurrency=2,
        show_progress=True,
        validate=True,
    )

    # Create qTest importer
    importer = QTestImporter(config, import_config)

    # Create sample test executions
    executions = create_test_executions()

    # Import test executions
    logger.info(f"Importing {len(executions)} test executions...")

    try:
        # Import a single test execution
        single_result = importer.import_test_execution(executions[0])

        if single_result["success"]:
            test_run = single_result["test_run"]
            test_log = single_result["test_log"]
            logger.info(f"Successfully imported execution for {executions[0]['testCaseKey']}")
            logger.info(f"Test Run ID: {test_run.id}")
            logger.info(f"Test Log ID: {test_log.id}")

            # Log any warnings
            if single_result["warnings"]:
                logger.warning("Warnings during import:")
                for warning in single_result["warnings"]:
                    logger.warning(f"  - {warning}")
        else:
            logger.error(f"Failed to import execution: {single_result['errors']}")

        # Import multiple test executions in parallel
        logger.info("\nImporting multiple test executions...")
        batch_result = importer.import_test_executions(executions)

        # Log summary of batch import
        logger.info("Batch import completed:")
        logger.info(f"  Total: {batch_result['total']}")
        logger.info(f"  Successful: {batch_result['successful']}")
        logger.info(f"  Failed: {batch_result['failed']}")
        logger.info(f"  Test Runs Created: {batch_result['stats']['runs_created']}")
        logger.info(f"  Test Runs Updated: {batch_result['stats']['runs_updated']}")
        logger.info(f"  Test Logs Created: {batch_result['stats']['logs_created']}")

        # Check for any errors in the batch
        if batch_result["failed"] > 0:
            logger.warning("Some executions failed to import:")
            for result in batch_result["executions"]:
                if not result["success"]:
                    logger.warning(f"  - Errors: {result['errors']}")

    except Exception as e:
        logger.error(f"Error during import: {e!s}", exc_info=True)


if __name__ == "__main__":
    main()
