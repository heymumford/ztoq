"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Example demonstrating recovery mechanisms in QTestExecutionImporter.

This script shows how to:
1. Configure checkpointing for test execution import
2. Resume from a checkpoint after a failure
3. Implement batch recovery
"""

import logging
import os
import random
import tempfile
import time
from datetime import datetime
from typing import Any

from ztoq.qtest_client import QTestClient
from ztoq.qtest_importer import ConflictResolution, ImportConfig, QTestImporter
from ztoq.qtest_models import QTestConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_executions(count: int = 20) -> list[dict[str, Any]]:
    """
    Create sample test executions for the import example.

    Args:
        count: Number of executions to create

    Returns:
        List of test execution dictionaries
    """
    now = datetime.now()

    executions = []
    for i in range(count):
        # Generate random status for variety
        status_options = ["PASS", "FAIL", "BLOCKED", "NOT_RUN"]
        status = random.choice(status_options)

        execution = {
            "id": f"exec-{10000+i}",
            "testCaseKey": f"DEMO-TC-{1000+i}",
            "cycleId": f"cycle-{2000+(i//5)}",  # Group every 5 executions in the same cycle
            "status": status,
            "executedBy": "testuser",
            "executedOn": now,
            "comment": f"Test execution {i+1}",
            "environment": "Production",
            "steps": [
                {
                    "id": f"step-{i}-1",
                    "index": 1,
                    "description": "Login to the application",
                    "expected_result": "Login successful",
                    "actual_result": "Login was successful with test user credentials",
                    "status": status,
                },
                {
                    "id": f"step-{i}-2",
                    "index": 2,
                    "description": "Navigate to dashboard",
                    "expected_result": "Dashboard displayed",
                    "actual_result": "Dashboard displayed with all widgets",
                    "status": status,
                },
            ],
        }
        executions.append(execution)

    return executions


def simulate_import_with_failure(executions: list[dict[str, Any]], checkpoint_dir: str) -> dict[str, Any]:
    """
    Simulate an import process that fails partway through.

    Args:
        executions: List of test executions to import
        checkpoint_dir: Directory to store checkpoints

    Returns:
        Result of the import operation
    """
    # Create QTest configuration (in real case, use actual credentials)
    config = QTestConfig(
        base_url="https://example.qtest.com",
        bearer_token="sample_token",
        project_id=12345,
    )

    # Create import configuration with checkpointing
    import_config = ImportConfig(
        conflict_resolution=ConflictResolution.SKIP,
        concurrency=2,  # Use parallel processing
        validate=True,
        show_progress=True,
        max_retries=3,
        checkpoint_frequency=5,  # Create checkpoint every 5 operations
        checkpoint_dir=checkpoint_dir,
    )

    # Create the QTest client and importer
    # In this example, we'll mock the client's behavior
    client = QTestClient(config)

    # Monkey patch the client methods to simulate success/failure
    def mock_get_entity_mapping(*args, **kwargs):
        # Simulate successful entity mapping lookup
        return {"target_id": 101}

    def mock_search_test_runs(*args, **kwargs):
        # Simulate no existing test runs
        return []

    def mock_create_test_run(*args, **kwargs):
        # Simulate successful test run creation
        from ztoq.qtest_models import QTestTestRun
        return QTestTestRun(
            id=random.randint(1000, 9999),
            name="Test Run",
            test_case_id=101,
            test_cycle_id=201,
            status="Not Run",
        )

    def mock_create_test_log(*args, **kwargs):
        # Simulate test log creation with random failure
        from ztoq.qtest_models import QTestTestLog

        # Simulate a random failure after processing ~60% of executions
        processed_count = client._processed_count if hasattr(client, "_processed_count") else 0
        client._processed_count = processed_count + 1

        if processed_count > len(executions) * 0.6:
            if random.random() < 0.5:  # 50% chance of failure after 60% progress
                raise ConnectionError("Network connection lost during import")

        return QTestTestLog(
            id=random.randint(2000, 9999),
            test_run_id=101,
            status="Passed",
            execution_date=datetime.now(),
        )

    # Set up the mock methods
    client.get_entity_mapping = mock_get_entity_mapping
    client.search_test_runs = mock_search_test_runs
    client.create_test_run = mock_create_test_run
    client.create_test_log = mock_create_test_log
    client._processed_count = 0

    # Create the importer with our mocked client
    importer = QTestImporter(config, import_config)

    # Attempt to import executions (will likely fail partway through)
    try:
        logger.info(f"Starting import of {len(executions)} test executions with checkpointing")
        result = importer.import_test_executions(executions)
        logger.info(f"Import completed successfully: {result['successful']} successful, {result['failed']} failed")
        return result
    except Exception as e:
        logger.error(f"Import failed: {e!s}")
        logger.info("A checkpoint should have been created before failure")
        return {"success": False, "error": str(e)}


def resume_import_after_failure(executions: list[dict[str, Any]], checkpoint_dir: str) -> dict[str, Any]:
    """
    Resume the import process from checkpoint after failure.

    Args:
        executions: List of all test executions (same as original import)
        checkpoint_dir: Directory containing checkpoints

    Returns:
        Result of the resumed import operation
    """
    # Create QTest configuration (same as in original import)
    config = QTestConfig(
        base_url="https://example.qtest.com",
        bearer_token="sample_token",
        project_id=12345,
    )

    # Create import configuration with recovery mode enabled
    import_config = ImportConfig(
        conflict_resolution=ConflictResolution.SKIP,
        concurrency=2,
        validate=True,
        show_progress=True,
        max_retries=3,
        checkpoint_frequency=5,
        checkpoint_dir=checkpoint_dir,
        recovery_mode=True,  # Enable recovery mode
    )

    # Create the QTest client and importer
    # In this example, we'll mock the client's behavior again but without the failures
    client = QTestClient(config)

    # Monkey patch the client methods to simulate success
    def mock_get_entity_mapping(*args, **kwargs):
        return {"target_id": 101}

    def mock_search_test_runs(*args, **kwargs):
        return []

    def mock_create_test_run(*args, **kwargs):
        from ztoq.qtest_models import QTestTestRun
        return QTestTestRun(
            id=random.randint(1000, 9999),
            name="Test Run",
            test_case_id=101,
            test_cycle_id=201,
            status="Not Run",
        )

    def mock_create_test_log(*args, **kwargs):
        from ztoq.qtest_models import QTestTestLog
        return QTestTestLog(
            id=random.randint(2000, 9999),
            test_run_id=101,
            status="Passed",
            execution_date=datetime.now(),
        )

    # Set up the mock methods (without failures this time)
    client.get_entity_mapping = mock_get_entity_mapping
    client.search_test_runs = mock_search_test_runs
    client.create_test_run = mock_create_test_run
    client.create_test_log = mock_create_test_log

    # Create the importer with our mocked client
    importer = QTestImporter(config, import_config)

    # Resume import from where it left off
    logger.info("Resuming import from checkpoint")
    result = importer.resume_test_execution_import(executions)

    logger.info(f"Resume completed: {result['successful']} newly processed, "
               f"{result['stats']['recovered']} recovered from checkpoint")

    return result


def main():
    """Run the recovery example."""
    # Create a temporary directory for checkpoint files
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"Using checkpoint directory: {temp_dir}")

        # Create sample test executions
        executions = create_test_executions(20)
        logger.info(f"Created {len(executions)} sample test executions")

        # Attempt initial import (will likely fail)
        logger.info("Attempting initial import (with simulated failure)...")
        initial_result = simulate_import_with_failure(executions, temp_dir)

        # Pause to make the example clearer
        logger.info("Simulating system recovery after failure...")
        time.sleep(2)

        # Resume import from checkpoint
        logger.info("Resuming import from checkpoint...")
        resume_result = resume_import_after_failure(executions, temp_dir)

        # Show final results
        logger.info("Import recovery process completed")
        logger.info(f"Total executions: {len(executions)}")
        logger.info(f"Successfully imported: {resume_result['stats']['runs_created'] + resume_result['stats']['recovered']}")
        logger.info(f"Failed: {resume_result['stats']['failed']}")

        # List checkpoint files
        checkpoint_files = [f for f in os.listdir(temp_dir) if f.startswith("qtest_execution_checkpoint")]
        logger.info(f"Checkpoint files created ({len(checkpoint_files)}):")
        for checkpoint_file in sorted(checkpoint_files):
            logger.info(f"  - {checkpoint_file}")


if __name__ == "__main__":
    main()
