"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Example for creating hierarchical test cycles in qTest.

This example demonstrates how to use the QTestImporter to create a hierarchy of
test cycles, associate test cases with them, and handle conflict resolution.
"""

import os
import sys
import logging
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path if running from examples dir
if os.path.basename(os.getcwd()) == "examples":
    sys.path.insert(0, os.path.abspath(".."))

from ztoq.qtest_client import QTestClient
from ztoq.qtest_models import (
    QTestConfig, QTestTestCycle, QTestTestCase, QTestCustomField
)
from ztoq.qtest_importer import QTestImporter, ImportConfig, ConflictResolution


def get_config_from_env() -> QTestConfig:
    """Get QTestConfig from environment variables."""
    try:
        project_id = int(os.environ.get("QTEST_PROJECT_ID", "0"))
        if project_id <= 0:
            raise ValueError("QTEST_PROJECT_ID must be a positive integer")

        # Create config using environment variables
        return QTestConfig.from_env(project_id=project_id)
    except Exception as e:
        logger.error(f"Failed to get config from environment: {str(e)}")
        sys.exit(1)


def create_hierarchical_test_cycles(release_id: int) -> Dict[str, Any]:
    """
    Create a hierarchical structure of test cycles.

    Args:
        release_id: ID of the release to associate with the cycles

    Returns:
        Dictionary containing parent and child cycles
    """
    # Create parent/root test cycle
    parent_cycle = QTestTestCycle(
        name="Sprint 15 Test Plan",
        description="Comprehensive testing for Sprint 15 release",
        release_id=release_id,
        properties=[
            QTestCustomField(
                field_id=1001,  # This should match a real field ID in your qTest instance
                field_name="Priority",
                field_type="STRING",
                field_value="High"
            )
        ]
    )

    # Create child test cycles for different test types
    child_cycles = [
        QTestTestCycle(
            name="Regression Tests",
            description="Tests to verify existing functionality",
            # parent_id will be set after parent creation
            release_id=release_id,
            properties=[]
        ),
        QTestTestCycle(
            name="New Feature Tests",
            description="Tests for new features in Sprint 15",
            # parent_id will be set after parent creation
            release_id=release_id,
            properties=[]
        ),
        QTestTestCycle(
            name="Performance Tests",
            description="Tests to verify performance benchmarks",
            # parent_id will be set after parent creation
            release_id=release_id,
            properties=[]
        )
    ]

    # Create grandchild cycles for the first child (Regression Tests)
    grandchild_cycles = [
        QTestTestCycle(
            name="UI Regression",
            description="Regression tests for the user interface",
            # parent_id will be set after child creation
            release_id=release_id,
            properties=[]
        ),
        QTestTestCycle(
            name="API Regression",
            description="Regression tests for the API endpoints",
            # parent_id will be set after child creation
            release_id=release_id,
            properties=[]
        )
    ]

    return {
        "parent": parent_cycle,
        "children": child_cycles,
        "grandchildren": grandchild_cycles
    }


def create_sample_test_cases(module_id: int) -> List[QTestTestCase]:
    """
    Create sample test cases to associate with test cycles.

    Args:
        module_id: ID of the module to associate with the test cases

    Returns:
        List of test cases
    """
    return [
        QTestTestCase(
            name="Login Authentication Test",
            description="Verify user login with valid credentials",
            module_id=module_id,
            properties=[
                QTestCustomField(
                    field_id=2001,  # This should match a real field ID in your qTest instance
                    field_name="Automated",
                    field_type="CHECKBOX",
                    field_value=True
                ),
                QTestCustomField(
                    field_id=2002,  # This should match a real field ID in your qTest instance
                    field_name="Component",
                    field_type="STRING",
                    field_value="Authentication"
                )
            ]
        ),
        QTestTestCase(
            name="User Profile Update Test",
            description="Verify user can update their profile information",
            module_id=module_id,
            properties=[
                QTestCustomField(
                    field_id=2001,
                    field_name="Automated",
                    field_type="CHECKBOX",
                    field_value=True
                ),
                QTestCustomField(
                    field_id=2002,
                    field_name="Component",
                    field_type="STRING",
                    field_value="User Management"
                )
            ]
        ),
        QTestTestCase(
            name="API Response Time Test",
            description="Verify API endpoints respond within performance thresholds",
            module_id=module_id,
            properties=[
                QTestCustomField(
                    field_id=2001,
                    field_name="Automated",
                    field_type="CHECKBOX",
                    field_value=True
                ),
                QTestCustomField(
                    field_id=2002,
                    field_name="Component",
                    field_type="STRING",
                    field_value="API"
                ),
                QTestCustomField(
                    field_id=2003,
                    field_name="Performance",
                    field_type="CHECKBOX",
                    field_value=True
                )
            ]
        )
    ]


def main():
    """Run the hierarchical test cycle example."""
    # Get configuration
    logger.info("Getting qTest configuration from environment variables")
    config = get_config_from_env()
    logger.info(f"Using qTest instance: {config.base_url} with project ID: {config.project_id}")

    # You would typically get these IDs from user input or from the qTest API
    release_id = int(os.environ.get("QTEST_RELEASE_ID", "0"))
    module_id = int(os.environ.get("QTEST_MODULE_ID", "0"))

    if release_id <= 0 or module_id <= 0:
        logger.error("Please set QTEST_RELEASE_ID and QTEST_MODULE_ID environment variables")
        sys.exit(1)

    # Create test cycles for our hierarchy
    test_cycles = create_hierarchical_test_cycles(release_id)

    # Create test cases to associate with cycles
    test_cases = create_sample_test_cases(module_id)

    # Create importer with RENAME conflict resolution to avoid errors
    import_config = ImportConfig(
        conflict_resolution=ConflictResolution.RENAME,
        concurrency=2,
        validate=True,
        show_progress=True
    )
    importer = QTestImporter(config, import_config)

    # First, create/get test cases so we have IDs
    logger.info("Importing test cases")
    case_results = importer.import_test_cases(test_cases)
    imported_test_cases = case_results["test_cases"]

    # Import parent cycle first and associate all test cases with it
    logger.info("Importing parent test cycle")
    parent_cycle = test_cycles["parent"]
    parent_result = importer.import_test_cycle_with_test_cases(parent_cycle, imported_test_cases)
    parent_id = parent_result["cycle"]["id"]
    logger.info(f"Parent cycle created with ID: {parent_id}")

    # Update child cycles with parent ID
    child_cycles = test_cycles["children"]
    for cycle in child_cycles:
        cycle.parent_id = parent_id

    # Import child cycles
    logger.info("Importing child test cycles")
    child_results = importer.import_test_cycles(child_cycles)

    # Get the IDs from the results
    child_cycle_ids = [cycle["id"] for cycle in child_results["cycles"]]
    logger.info(f"Child cycle IDs: {child_cycle_ids}")

    # Update grandchild cycles with first child's ID (Regression Tests)
    grandchild_cycles = test_cycles["grandchildren"]
    for cycle in grandchild_cycles:
        cycle.parent_id = child_cycle_ids[0]  # First child ID (Regression Tests)

    # Import grandchild cycles
    logger.info("Importing grandchild test cycles")
    grandchild_results = importer.import_test_cycles(grandchild_cycles)

    # Separate test cases by component for specific cycle association
    ui_test_cases = [tc for tc in imported_test_cases
                     if any(prop.field_name == "Component" and "User" in str(prop.field_value)
                            for prop in tc.properties)]
    api_test_cases = [tc for tc in imported_test_cases
                     if any(prop.field_name == "Component" and "API" in str(prop.field_value)
                            for prop in tc.properties)]

    # Associate UI test cases with the UI Regression cycle (first grandchild)
    if ui_test_cases:
        logger.info("Associating UI test cases with UI Regression cycle")
        ui_cycle_id = grandchild_results["cycles"][0]["id"]
        # Create a custom TestCycle object with just the ID to use for association
        ui_cycle = QTestTestCycle(id=ui_cycle_id, name="UI Regression", release_id=release_id)
        ui_result = importer.import_test_cycle_with_test_cases(ui_cycle, ui_test_cases)
        logger.info(f"Associated {ui_result['associated_test_cases']} UI test cases")

    # Associate API test cases with the API Regression cycle (second grandchild)
    if api_test_cases:
        logger.info("Associating API test cases with API Regression cycle")
        api_cycle_id = grandchild_results["cycles"][1]["id"]
        # Create a custom TestCycle object with just the ID to use for association
        api_cycle = QTestTestCycle(id=api_cycle_id, name="API Regression", release_id=release_id)
        api_result = importer.import_test_cycle_with_test_cases(api_cycle, api_test_cases)
        logger.info(f"Associated {api_result['associated_test_cases']} API test cases")

    # Print full hierarchy summary
    logger.info("---------------------------------------")
    logger.info("TEST CYCLE HIERARCHY CREATED:")
    logger.info(f"Parent Cycle: {parent_cycle.name} (ID: {parent_id})")
    for i, cycle_id in enumerate(child_cycle_ids):
        logger.info(f"  Child Cycle: {child_cycles[i].name} (ID: {cycle_id})")
        if i == 0:  # If this is the Regression Tests cycle
            for j, grandchild in enumerate(grandchild_results["cycles"]):
                logger.info(f"    Grandchild Cycle: {grandchild_cycles[j].name} (ID: {grandchild['id']})")
    logger.info("---------------------------------------")

    logger.info("Hierarchy creation complete!")


if __name__ == "__main__":
    main()
