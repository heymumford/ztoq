"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Example for importing test cycles to qTest.

This example demonstrates how to use the QTestCycleImporter to import test cycles
with associated test cases, how to manage hierarchical test cycles, and handle
potential conflicts.
"""

import logging
import os
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path if running from examples dir
if os.path.basename(os.getcwd()) == "examples":
    sys.path.insert(0, os.path.abspath(".."))

from ztoq.qtest_importer import ConflictResolution, ImportConfig, QTestImporter
from ztoq.qtest_models import (
    QTestConfig,
    QTestCustomField,
    QTestTestCase,
    QTestTestCycle,
)


def get_config_from_env() -> QTestConfig:
    """Get QTestConfig from environment variables."""
    try:
        project_id = int(os.environ.get("QTEST_PROJECT_ID", "0"))
        if project_id <= 0:
            raise ValueError("QTEST_PROJECT_ID must be a positive integer")

        # Create config using environment variables
        return QTestConfig.from_env(project_id=project_id)
    except Exception as e:
        logger.error(f"Failed to get config from environment: {e!s}")
        sys.exit(1)


def create_sample_test_cycles() -> list[QTestTestCycle]:
    """Create sample test cycles for the example."""
    # Parent cycle
    parent_cycle = QTestTestCycle(
        name="Sprint 12 Test Cycle",
        description="Test cycle for Sprint 12 release",
        release_id=50,  # This should match a real release ID in your qTest instance
        properties=[
            QTestCustomField(
                field_id=1001,  # This should match a real field ID in your qTest instance
                field_name="Priority",
                field_type="STRING",
                field_value="High",
            ),
        ],
    )

    # Child cycles
    child_cycles = [
        QTestTestCycle(
            name="UI Tests",
            description="User interface tests for Sprint 12",
            parent_id=None,  # Will be set after parent creation
            release_id=50,
            properties=[],
        ),
        QTestTestCycle(
            name="API Tests",
            description="API tests for Sprint 12",
            parent_id=None,  # Will be set after parent creation
            release_id=50,
            properties=[],
        ),
    ]

    return [parent_cycle] + child_cycles


def create_sample_test_cases() -> list[QTestTestCase]:
    """Create sample test cases for the example."""
    return [
        QTestTestCase(
            name="Login Test",
            description="Verify user login functionality",
            module_id=1000,  # This should match a real module ID in your qTest instance
            properties=[
                QTestCustomField(
                    field_id=2001,  # This should match a real field ID in your qTest instance
                    field_name="Automated",
                    field_type="CHECKBOX",
                    field_value=True,
                ),
            ],
        ),
        QTestTestCase(
            name="User Registration Test",
            description="Verify new user registration flow",
            module_id=1000,
            properties=[],
        ),
    ]


def main():
    """Run the test cycle import example."""
    # Get configuration
    logger.info("Getting qTest configuration from environment variables")
    config = get_config_from_env()
    logger.info(f"Using qTest instance: {config.base_url} with project ID: {config.project_id}")

    # Create importer with conflict resolution set to RENAME
    import_config = ImportConfig(
        conflict_resolution=ConflictResolution.RENAME,
        concurrency=2,
        validate=True,
        show_progress=True,
    )
    importer = QTestImporter(config, import_config)

    # Create sample test cycles and test cases
    test_cycles = create_sample_test_cycles()
    test_cases = create_sample_test_cases()

    # First create or get test cases so we have IDs
    logger.info("Importing test cases")
    case_results = importer.import_test_cases(test_cases)
    imported_test_cases = case_results["test_cases"]

    # Import parent test cycle first
    logger.info("Importing parent test cycle")
    parent_cycle = test_cycles[0]
    parent_result = importer.import_test_cycle_with_test_cases(parent_cycle, imported_test_cases)

    # Update child cycles with parent ID
    parent_id = parent_result["cycle"].id
    logger.info(f"Parent cycle created with ID: {parent_id}")

    # Import child cycles
    child_cycles = test_cycles[1:]
    for cycle in child_cycles:
        cycle.parent_id = parent_id

    logger.info("Importing child test cycles")
    child_results = importer.import_test_cycles(child_cycles)

    # Print summary
    logger.info("Import completed")
    logger.info(f"Test Cases: {case_results['total']} total, {case_results['created']} created, "
               f"{case_results['updated']} updated, {case_results['skipped']} skipped")

    logger.info(f"Test Cycles: {parent_result['stats']['cycles_total']} total, "
               f"{parent_result['stats']['cycles_created']} created, "
               f"{parent_result['stats']['cycles_updated']} updated, "
               f"{parent_result['stats']['cycles_skipped']} skipped")

    logger.info(f"Test Runs: {parent_result['stats']['runs_created']} created")


if __name__ == "__main__":
    main()
