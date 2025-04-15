"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Migration module for transforming and migrating test data from Zephyr Scale to qTest.

This module implements the ETL (Extract, Transform, Load) workflow for migrating
test data between the two systems, as described in ADR-013.
"""

import json
import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from ztoq.custom_field_mapping import get_default_field_mapper
from ztoq.models import ZephyrConfig
from ztoq.qtest_client import QTestClient
from ztoq.qtest_models import (
    QTestConfig,
    QTestModule,
    QTestProject,
    QTestStep,
    QTestTestCase,
    QTestTestCycle,
    QTestTestLog,
    QTestTestRun,
)
from ztoq.validation_integration import get_enhanced_migration
from ztoq.zephyr_client import ZephyrClient

logger = logging.getLogger("ztoq.migration")


class MigrationState:
    """Class for tracking the state and progress of the migration."""

    def __init__(self, project_key: str, database: Any):
        """
        Initialize migration state tracker.

        Args:
            project_key: The Zephyr project key
            database: The database manager instance

        """
        self.project_key = project_key
        self.db = database
        self.extraction_status = "not_started"
        self.transformation_status = "not_started"
        self.loading_status = "not_started"
        self.rollback_status = "not_started"
        self.error_message = None
        self.is_incremental = False
        self._load_state()

    def _load_state(self):
        """Load the current migration state from the database."""
        state = self.db.get_migration_state(self.project_key)
        if state:
            self.extraction_status = state.get("extraction_status", "not_started")
            self.transformation_status = state.get("transformation_status", "not_started")
            self.loading_status = state.get("loading_status", "not_started")
            self.rollback_status = state.get("rollback_status", "not_started")
            self.error_message = state.get("error_message")
            self.is_incremental = state.get("is_incremental", False)
            self.meta_data = state.get("meta_data")

    @property
    def metadata_dict(self) -> dict:
        """
        Get metadata as a dictionary.

        Returns:
            Dict containing parsed metadata or empty dict if no metadata.

        """
        if not hasattr(self, "meta_data") or not self.meta_data:
            return {}

        try:
            return json.loads(self.meta_data)
        except (json.JSONDecodeError, TypeError):
            # Handle invalid JSON
            return {}

    def update_extraction_status(self, status: str, error: str | None = None):
        """
        Update the extraction phase status.

        Args:
            status: The new status
            error: Optional error message

        """
        self.extraction_status = status
        if error:
            self.error_message = error
        self.db.update_migration_state(
            self.project_key, extraction_status=status, error_message=error,
        )

    def update_transformation_status(self, status: str, error: str | None = None):
        """
        Update the transformation phase status.

        Args:
            status: The new status
            error: Optional error message

        """
        self.transformation_status = status
        if error:
            self.error_message = error
        self.db.update_migration_state(
            self.project_key, transformation_status=status, error_message=error,
        )

    def update_loading_status(self, status: str, error: str | None = None):
        """
        Update the loading phase status.

        Args:
            status: The new status
            error: Optional error message

        """
        self.loading_status = status
        if error:
            self.error_message = error
        self.db.update_migration_state(self.project_key, loading_status=status, error_message=error)

    def update_rollback_status(self, status: str, error: str | None = None):
        """
        Update the rollback phase status.

        Args:
            status: The new status
            error: Optional error message

        """
        self.rollback_status = status
        if error:
            self.error_message = error
        self.db.update_migration_state(
            self.project_key, rollback_status=status, error_message=error,
        )

    def update_loading_status(self, status: str, error: str | None = None):
        """
        Update the loading phase status.

        Args:
            status: The new status
            error: Optional error message

        """
        self.loading_status = status
        if error:
            self.error_message = error
        self.db.update_migration_state(self.project_key, loading_status=status, error_message=error)

    def can_extract(self) -> bool:
        """
        Check if extraction can proceed.

        Returns:
            True if extraction can proceed, False otherwise

        """
        return self.extraction_status in ["not_started", "in_progress", "failed"]

    def can_transform(self) -> bool:
        """
        Check if transformation can proceed.

        Returns:
            True if transformation can proceed, False otherwise

        """
        return self.extraction_status == "completed" and self.transformation_status in [
            "not_started",
            "in_progress",
            "failed",
        ]

    def can_load(self) -> bool:
        """
        Check if loading can proceed.

        Returns:
            True if loading can proceed, False otherwise

        """
        return self.transformation_status == "completed" and self.loading_status in [
            "not_started",
            "in_progress",
            "failed",
        ]

    def can_rollback(self) -> bool:
        """
        Check if rollback can proceed.

        Returns:
            True if rollback can proceed, False otherwise

        """
        # We can rollback if there's anything to roll back (any completed phase)
        return (
            self.extraction_status == "completed"
            or self.transformation_status == "completed"
            or self.loading_status == "completed"
        )


class EntityBatchTracker:
    """Tracks and manages batches of entities during migration."""

    def __init__(self, project_key: str, entity_type: str, database: Any):
        """
        Initialize batch tracker.

        Args:
            project_key: The Zephyr project key
            entity_type: The type of entity being tracked
            database: The database manager instance

        """
        self.project_key = project_key
        self.entity_type = entity_type
        self.db = database

    def initialize_batches(self, total_items: int, batch_size: int = 50):
        """
        Initialize batch tracking for a set of entities.

        Args:
            total_items: Total number of items to process
            batch_size: Number of items per batch

        """
        total_batches = (total_items + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_items)
            items_count = end_idx - start_idx

            self.db.create_entity_batch(
                self.project_key, self.entity_type, batch_num, total_batches, items_count,
            )

    def update_batch_status(
        self, batch_num: int, processed_count: int, status: str, error: str | None = None,
    ):
        """
        Update the status of a batch.

        Args:
            batch_num: The batch number
            processed_count: Number of items processed
            status: Current status of the batch
            error: Optional error message

        """
        self.db.update_entity_batch(
            self.project_key, self.entity_type, batch_num, processed_count, status, error,
        )

    def get_pending_batches(self) -> list[dict[str, Any]]:
        """
        Get batches that are pending processing.

        Returns:
            List of pending batch information

        """
        return self.db.get_pending_entity_batches(self.project_key, self.entity_type)


class ZephyrToQTestMigration:
    """
    Main class for migrating data from Zephyr Scale to qTest.

    This class implements the ETL (Extract, Transform, Load) operations for migrating
    test data from Zephyr Scale to qTest. It supports both standard and batch-based
    transformation methods, with intelligent batching strategies for optimal performance.
    """

    def __init__(
        self,
        zephyr_config: ZephyrConfig,
        qtest_config: QTestConfig,
        database_manager: Any,
        batch_size: int = 50,
        max_workers: int = 5,
        attachments_dir: Path | None = None,
        enable_validation: bool = True,
    ):
        """
        Initialize the migration manager.

        Args:
            zephyr_config: The Zephyr API configuration
            qtest_config: The qTest API configuration
            database_manager: The database manager for storing migration data
            batch_size: Number of items to process in a batch
            max_workers: Maximum number of concurrent workers
            attachments_dir: Optional directory for attachment storage
            enable_validation: Whether to enable enhanced validation (default: True)

        """
        self.zephyr_config = zephyr_config
        self.qtest_config = qtest_config
        self.db = database_manager
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.attachments_dir = attachments_dir
        self.enable_validation = enable_validation

        # Initialize API clients
        self.zephyr_client = ZephyrClient(zephyr_config)
        self.qtest_client = QTestClient(qtest_config)

        # Initialize state tracker
        self.state = MigrationState(zephyr_config.project_key, self.db)

        # Initialize field mapper
        self.field_mapper = get_default_field_mapper()

        # Initialize mapping tables for created entities
        self.entity_mappings = {
            "folders": {},  # Zephyr folder ID -> qTest module ID
            "test_cases": {},  # Zephyr test case ID -> qTest test case ID
            "test_cycles": {},  # Zephyr test cycle ID -> qTest test cycle ID
            "test_executions": {},  # Zephyr execution ID -> qTest test run ID
        }

        # Load existing mappings from database if available
        self._load_entity_mappings()

    def _load_entity_mappings(self):
        """Load existing entity mappings from the database."""
        # Load folder mappings
        folder_mappings = self.db.get_entity_mappings(
            self.zephyr_config.project_key, "folder_to_module",
        )
        for mapping in folder_mappings:
            self.entity_mappings["folders"][mapping["source_id"]] = mapping["target_id"]

        # Load test case mappings
        testcase_mappings = self.db.get_entity_mappings(
            self.zephyr_config.project_key, "testcase_to_testcase",
        )
        for mapping in testcase_mappings:
            self.entity_mappings["test_cases"][mapping["source_id"]] = mapping["target_id"]

        # Load test cycle mappings
        cycle_mappings = self.db.get_entity_mappings(
            self.zephyr_config.project_key, "cycle_to_cycle",
        )
        for mapping in cycle_mappings:
            self.entity_mappings["test_cycles"][mapping["source_id"]] = mapping["target_id"]

        # Load test execution mappings
        execution_mappings = self.db.get_entity_mappings(
            self.zephyr_config.project_key, "execution_to_run",
        )
        for mapping in execution_mappings:
            self.entity_mappings["test_executions"][mapping["source_id"]] = mapping["target_id"]

    def run_migration(self, phases: list[str] | None = None):
        """
        Run the full migration process or specific phases.

        Args:
            phases: Optional list of phases to run ("extract", "transform", "load")
                   If None, all phases will be run in sequence

        """
        if not phases:
            phases = ["extract", "transform", "load"]

        try:
            if "extract" in phases and self.state.can_extract():
                self.extract_data()

            if "transform" in phases and self.state.can_transform():
                self.transform_data()

            if "load" in phases and self.state.can_load():
                self.load_data()

            logger.info(f"Migration completed for project {self.zephyr_config.project_key}")

        except Exception as e:
            logger.error(f"Migration failed: {e!s}", exc_info=True)
            # Update state based on which phase was running
            if self.state.extraction_status == "in_progress":
                self.state.update_extraction_status("failed", str(e))
            elif self.state.transformation_status == "in_progress":
                self.state.update_transformation_status("failed", str(e))
            elif self.state.loading_status == "in_progress":
                self.state.update_loading_status("failed", str(e))
            raise

    def extract_data(self):
        """Extract data from Zephyr and store in database."""
        logger.info(f"Starting data extraction for project {self.zephyr_config.project_key}")
        self.state.update_extraction_status("in_progress")

        try:
            # Extract project information
            project = self.zephyr_client.get_project(self.zephyr_config.project_key)
            self.db.save_project(project)

            # Extract and save folders
            self._extract_folders()

            # Extract and save test cases with attachments
            self._extract_test_cases()

            # Extract and save test cycles
            self._extract_test_cycles()

            # Extract and save test executions
            self._extract_test_executions()

            self.state.update_extraction_status("completed")
            logger.info(f"Extraction completed for project {self.zephyr_config.project_key}")

        except Exception as e:
            self.state.update_extraction_status("failed", str(e))
            logger.error(f"Extraction failed: {e!s}", exc_info=True)
            raise

    def _extract_folders(self):
        """Extract folder data from Zephyr."""
        logger.info("Extracting folders")
        folders = list(self.zephyr_client.get_folders())

        # Initialize batch tracking
        folder_tracker = EntityBatchTracker(self.zephyr_config.project_key, "folders", self.db)
        folder_tracker.initialize_batches(len(folders), self.batch_size)

        # Process in batches
        for batch_idx, batch_start in enumerate(range(0, len(folders), self.batch_size)):
            batch_end = min(batch_start + self.batch_size, len(folders))
            batch = folders[batch_start:batch_end]

            try:
                # Save folders to database
                self.db.save_folders(batch)
                folder_tracker.update_batch_status(batch_idx, len(batch), "completed")
            except Exception as e:
                folder_tracker.update_batch_status(batch_idx, 0, "failed", str(e))
                logger.error(f"Failed to save folder batch {batch_idx}: {e!s}")

        logger.info(f"Extracted {len(folders)} folders")

    def _extract_test_cases(self):
        """Extract test case data from Zephyr."""
        logger.info("Extracting test cases")

        # Get test cases for the project
        test_cases = list(self.zephyr_client.get_test_cases())

        # Initialize batch tracking
        test_case_tracker = EntityBatchTracker(
            self.zephyr_config.project_key, "test_cases", self.db,
        )
        test_case_tracker.initialize_batches(len(test_cases), self.batch_size)

        # Process test cases in batches
        for batch_idx, batch_start in enumerate(range(0, len(test_cases), self.batch_size)):
            batch_end = min(batch_start + self.batch_size, len(test_cases))
            batch = test_cases[batch_start:batch_end]

            try:
                # For each test case, fetch test steps
                for test_case in batch:
                    # Get and save test steps for each test case
                    test_steps = self.zephyr_client.get_test_steps(test_case.id)
                    test_case.steps = list(test_steps)

                    # Handle attachments if they exist
                    self._extract_test_case_attachments(test_case)

                # Save test cases to database
                self.db.save_test_cases(batch)
                test_case_tracker.update_batch_status(batch_idx, len(batch), "completed")
            except Exception as e:
                test_case_tracker.update_batch_status(batch_idx, 0, "failed", str(e))
                logger.error(f"Failed to save test case batch {batch_idx}: {e!s}")

        logger.info(f"Extracted {len(test_cases)} test cases")

    def _extract_test_case_attachments(self, test_case):
        """Extract attachments for a test case."""
        if not hasattr(test_case, "attachments") or not test_case.attachments:
            return

        for attachment in test_case.attachments:
            try:
                # Download attachment
                attachment_data = self.zephyr_client.download_attachment(attachment.id)

                # Store in database
                self.db.save_attachment(
                    related_type="TestCase",
                    related_id=test_case.id,
                    name=attachment.filename,
                    content=attachment_data,
                    url=attachment.url,
                )

                # Optionally save to filesystem if attachments_dir is provided
                if self.attachments_dir:
                    attachment_path = (
                        self.attachments_dir / f"tc_{test_case.id}_{attachment.filename}"
                    )
                    attachment_path.parent.mkdir(parents=True, exist_ok=True)
                    attachment_path.write_bytes(attachment_data)

            except Exception as e:
                logger.warning(
                    f"Failed to download attachment {attachment.id} for test case {test_case.id}: {e!s}",
                )

    def _extract_test_cycles(self):
        """Extract test cycle data from Zephyr."""
        logger.info("Extracting test cycles")

        # Get test cycles for the project
        test_cycles = list(self.zephyr_client.get_test_cycles())

        # Initialize batch tracking
        test_cycle_tracker = EntityBatchTracker(
            self.zephyr_config.project_key, "test_cycles", self.db,
        )
        test_cycle_tracker.initialize_batches(len(test_cycles), self.batch_size)

        # Process test cycles in batches
        for batch_idx, batch_start in enumerate(range(0, len(test_cycles), self.batch_size)):
            batch_end = min(batch_start + self.batch_size, len(test_cycles))
            batch = test_cycles[batch_start:batch_end]

            try:
                # Save test cycles to database
                self.db.save_test_cycles(batch)
                test_cycle_tracker.update_batch_status(batch_idx, len(batch), "completed")
            except Exception as e:
                test_cycle_tracker.update_batch_status(batch_idx, 0, "failed", str(e))
                logger.error(f"Failed to save test cycle batch {batch_idx}: {e!s}")

        logger.info(f"Extracted {len(test_cycles)} test cycles")

    def _extract_test_executions(self):
        """Extract test execution data from Zephyr."""
        logger.info("Extracting test executions")

        # Get test executions for the project
        test_executions = list(self.zephyr_client.get_test_executions())

        # Initialize batch tracking
        execution_tracker = EntityBatchTracker(
            self.zephyr_config.project_key, "test_executions", self.db,
        )
        execution_tracker.initialize_batches(len(test_executions), self.batch_size)

        # Process test executions in batches
        for batch_idx, batch_start in enumerate(range(0, len(test_executions), self.batch_size)):
            batch_end = min(batch_start + self.batch_size, len(test_executions))
            batch = test_executions[batch_start:batch_end]

            try:
                # For each execution, fetch step results if they exist
                for execution in batch:
                    # Handle attachments if they exist
                    self._extract_execution_attachments(execution)

                # Save test executions to database
                self.db.save_test_executions(batch)
                execution_tracker.update_batch_status(batch_idx, len(batch), "completed")
            except Exception as e:
                execution_tracker.update_batch_status(batch_idx, 0, "failed", str(e))
                logger.error(f"Failed to save test execution batch {batch_idx}: {e!s}")

        logger.info(f"Extracted {len(test_executions)} test executions")

    def _extract_execution_attachments(self, execution):
        """Extract attachments for a test execution."""
        if not hasattr(execution, "attachments") or not execution.attachments:
            return

        for attachment in execution.attachments:
            try:
                # Download attachment
                attachment_data = self.zephyr_client.download_attachment(attachment.id)

                # Store in database
                self.db.save_attachment(
                    related_type="TestExecution",
                    related_id=execution.id,
                    name=attachment.filename,
                    content=attachment_data,
                    url=attachment.url,
                )

                # Optionally save to filesystem if attachments_dir is provided
                if self.attachments_dir:
                    attachment_path = (
                        self.attachments_dir / f"exec_{execution.id}_{attachment.filename}"
                    )
                    attachment_path.parent.mkdir(parents=True, exist_ok=True)
                    attachment_path.write_bytes(attachment_data)

            except Exception as e:
                logger.warning(
                    f"Failed to download attachment {attachment.id} for execution {execution.id}: {e!s}",
                )

    def transform_data(self):
        """Transform extracted Zephyr data to qTest format."""
        logger.info(f"Starting data transformation for project {self.zephyr_config.project_key}")
        self.state.update_transformation_status("in_progress")

        try:
            # Transform project
            self._transform_project()

            # Transform folders to modules
            self._transform_folders_to_modules()

            # Transform test cases
            self._transform_test_cases()

            # Transform test cycles
            self._transform_test_cycles()

            # Transform test executions
            self._transform_test_executions()

            self.state.update_transformation_status("completed")
            logger.info(f"Transformation completed for project {self.zephyr_config.project_key}")

        except Exception as e:
            self.state.update_transformation_status("failed", str(e))
            logger.error(f"Transformation failed: {e!s}", exc_info=True)
            raise

    def _transform_project(self):
        """Transform project data from Zephyr to qTest format."""
        logger.info("Transforming project data")

        # Get project from database
        project = self.db.get_project(self.zephyr_config.project_key)

        # Transform to qTest format
        qtest_project = QTestProject(
            id=self.qtest_config.project_id,  # Use the configured project ID for qTest
            name=project.get("name", ""),
            description=project.get("description", ""),
        )

        # Save transformed project to database
        self.db.save_transformed_project(self.zephyr_config.project_key, qtest_project)
        logger.info("Project transformation completed")

    def _transform_folders_to_modules(self):
        """Transform Zephyr folders to qTest modules."""
        logger.info("Transforming folders to modules")

        # Get folders from database
        folders = self.db.get_folders(self.zephyr_config.project_key)

        # Build folder hierarchy (parent-child relationships)
        folder_hierarchy = {}
        root_folders = []

        for folder in folders:
            folder.get("id")
            parent_id = folder.get("parentId")

            if parent_id is None:
                root_folders.append(folder)
            else:
                if parent_id not in folder_hierarchy:
                    folder_hierarchy[parent_id] = []
                folder_hierarchy[parent_id].append(folder)

        # Helper function to transform folder and its children recursively
        def transform_folder(folder, parent_module_id=None, path_prefix=""):
            folder_id = folder.get("id")
            name = folder.get("name", "")
            path = f"{path_prefix}/{name}" if path_prefix else name

            # Create qTest module
            module = QTestModule(
                name=name,
                description=f"Migrated from Zephyr folder: {folder.get('id')}",
                parent_id=parent_module_id,
            )

            # Save transformed module to database
            module_id = self.db.save_transformed_module(
                self.zephyr_config.project_key, folder_id, module,
            )

            # Process child folders recursively
            if folder_id in folder_hierarchy:
                for child_folder in folder_hierarchy[folder_id]:
                    transform_folder(child_folder, module_id, path)

        # Start processing from root folders
        for root_folder in root_folders:
            transform_folder(root_folder)

        logger.info(f"Transformed {len(folders)} folders to modules")

    def _transform_test_cases(self):
        """Transform Zephyr test cases to qTest test cases."""
        logger.info("Transforming test cases")

        # Get test cases from database with their steps
        test_cases = self.db.get_test_cases_with_steps(self.zephyr_config.project_key)

        # Initialize batch tracking
        test_case_tracker = EntityBatchTracker(
            self.zephyr_config.project_key, "transformed_test_cases", self.db,
        )
        test_case_tracker.initialize_batches(len(test_cases), self.batch_size)

        # Process test cases in batches
        for batch_idx, batch_start in enumerate(range(0, len(test_cases), self.batch_size)):
            batch_end = min(batch_start + self.batch_size, len(test_cases))
            batch = test_cases[batch_start:batch_end]

            try:
                transformed_batch = []

                for test_case in batch:
                    # Get module ID for the test case's folder
                    module_id = None
                    folder_id = test_case.get("folderId")

                    if folder_id:
                        module_mapping = self.db.get_entity_mapping(
                            self.zephyr_config.project_key, "folder_to_module", folder_id,
                        )
                        if module_mapping:
                            module_id = module_mapping.get("target_id")

                    # Transform test steps
                    qtest_steps = []
                    steps = test_case.get("steps", [])

                    for idx, step in enumerate(steps):
                        # Get description and test data
                        description = step.get("description", "")
                        test_data = step.get("testData", "")

                        # If test data exists, combine it with description
                        if test_data:
                            description = f"{description}\n\nTest Data: {test_data}"

                        # Create qTest step
                        qtest_step = QTestStep(
                            description=description,
                            expected_result=step.get("expectedResult", ""),
                            order=idx + 1,
                        )
                        qtest_steps.append(qtest_step)

                    # Transform custom fields using the field mapper
                    qtest_custom_fields = self.field_mapper.map_testcase_fields(test_case)

                    # Create qTest test case
                    qtest_test_case = QTestTestCase(
                        name=test_case.get("name", ""),
                        description=test_case.get("description", ""),
                        precondition=test_case.get("precondition", ""),
                        test_steps=qtest_steps,
                        properties=qtest_custom_fields,
                        module_id=module_id,
                        priority_id=self._map_priority(test_case.get("priority", "")),
                    )

                    # Save transformed test case
                    self.db.save_transformed_test_case(
                        self.zephyr_config.project_key, test_case.get("id"), qtest_test_case,
                    )

                    transformed_batch.append(qtest_test_case)

                test_case_tracker.update_batch_status(batch_idx, len(batch), "completed")
            except Exception as e:
                test_case_tracker.update_batch_status(batch_idx, 0, "failed", str(e))
                logger.error(f"Failed to transform test case batch {batch_idx}: {e!s}")

        logger.info(f"Transformed {len(test_cases)} test cases")

    def _map_priority(self, zephyr_priority: str) -> int:
        """Map Zephyr priority to qTest priority ID."""
        # Default mapping - should be customized based on actual qTest priority IDs
        priority_map = {
            "highest": 1,
            "high": 2,
            "medium": 3,
            "low": 4,
            "lowest": 5,
            # Additional mappings
            "critical": 1,
            "blocker": 1,
            "major": 2,
            "minor": 4,
            "trivial": 5,
        }

        return priority_map.get(zephyr_priority.lower(), 3)  # Default to medium

    def _transform_test_cycles(self):
        """Transform Zephyr test cycles to qTest test cycles."""
        logger.info("Transforming test cycles")

        # Get test cycles from database
        test_cycles = self.db.get_test_cycles(self.zephyr_config.project_key)

        # Initialize batch tracking
        cycle_tracker = EntityBatchTracker(
            self.zephyr_config.project_key, "transformed_test_cycles", self.db,
        )
        cycle_tracker.initialize_batches(len(test_cycles), self.batch_size)

        # Process test cycles in batches
        for batch_idx, batch_start in enumerate(range(0, len(test_cycles), self.batch_size)):
            batch_end = min(batch_start + self.batch_size, len(test_cycles))
            batch = test_cycles[batch_start:batch_end]

            try:
                transformed_batch = []

                for cycle in batch:
                    # Get folder mapping if available
                    parent_id = None
                    folder_id = cycle.get("folderId")

                    if folder_id:
                        folder_mapping = self.db.get_entity_mapping(
                            self.zephyr_config.project_key, "folder_to_module", folder_id,
                        )
                        if folder_mapping:
                            parent_id = folder_mapping.get("target_id")

                    # Transform custom fields using the field mapper
                    qtest_custom_fields = self.field_mapper.map_testcycle_fields(cycle)

                    # Create qTest test cycle
                    qtest_cycle = QTestTestCycle(
                        name=cycle.get("name", ""),
                        description=cycle.get("description", ""),
                        parent_id=parent_id,
                        start_date=cycle.get("startDate"),
                        end_date=cycle.get("endDate"),
                        properties=qtest_custom_fields,
                    )

                    # Save transformed cycle
                    self.db.save_transformed_test_cycle(
                        self.zephyr_config.project_key, cycle.get("id"), qtest_cycle,
                    )

                    transformed_batch.append(qtest_cycle)

                cycle_tracker.update_batch_status(batch_idx, len(batch), "completed")
            except Exception as e:
                cycle_tracker.update_batch_status(batch_idx, 0, "failed", str(e))
                logger.error(f"Failed to transform test cycle batch {batch_idx}: {e!s}")

        logger.info(f"Transformed {len(test_cycles)} test cycles")

    def _transform_test_executions(self):
        """Transform Zephyr test executions to qTest test runs and logs."""
        logger.info("Transforming test executions")

        # Get test executions from database
        executions = self.db.get_test_executions(self.zephyr_config.project_key)

        # Initialize batch tracking
        execution_tracker = EntityBatchTracker(
            self.zephyr_config.project_key, "transformed_test_executions", self.db,
        )
        execution_tracker.initialize_batches(len(executions), self.batch_size)

        # Process test executions in batches
        for batch_idx, batch_start in enumerate(range(0, len(executions), self.batch_size)):
            batch_end = min(batch_start + self.batch_size, len(executions))
            batch = executions[batch_start:batch_end]

            try:
                transformed_batch = []

                for execution in batch:
                    # Get mappings for related entities
                    test_case_id = execution.get("testCaseId")
                    test_cycle_id = execution.get("testCycleId")

                    qtest_test_case_id = None
                    qtest_test_cycle_id = None

                    if test_case_id:
                        case_mapping = self.db.get_entity_mapping(
                            self.zephyr_config.project_key, "testcase_to_testcase", test_case_id,
                        )
                        if case_mapping:
                            qtest_test_case_id = case_mapping.get("target_id")

                    if test_cycle_id:
                        cycle_mapping = self.db.get_entity_mapping(
                            self.zephyr_config.project_key, "cycle_to_cycle", test_cycle_id,
                        )
                        if cycle_mapping:
                            qtest_test_cycle_id = cycle_mapping.get("target_id")

                    # Map the status to qTest format
                    qtest_status = self._map_status(execution.get("status", ""))

                    # Transform custom fields using the field mapper
                    qtest_custom_fields = self.field_mapper.map_testrun_fields(execution)

                    # Create test run model
                    qtest_run = QTestTestRun(
                        name=f"Run for {test_case_id} in cycle {test_cycle_id}",
                        test_case_id=qtest_test_case_id,
                        test_cycle_id=qtest_test_cycle_id,
                        properties=qtest_custom_fields,
                    )

                    # Get execution steps and comments
                    steps = execution.get("steps", [])
                    comment = execution.get("comment", "")

                    # Format step results if they exist
                    step_results = []
                    for idx, step in enumerate(steps):
                        step_status = step.get("status") or qtest_status
                        actual_result = step.get("actualResult", "")

                        # Map step status to qTest status
                        qtest_step_status = self._map_status(step_status)

                        # Add step result to list
                        step_results.append(
                            {
                                "order": idx + 1,
                                "status": qtest_step_status,
                                "actualResult": actual_result,
                            },
                        )

                    # Create test log model
                    qtest_log = QTestTestLog(
                        status=qtest_status,
                        execution_date=execution.get("executionTime")
                        or execution.get("executedOn"),
                        note=comment,
                        test_step_logs=step_results if step_results else None,
                    )

                    # Save transformed execution
                    self.db.save_transformed_execution(
                        self.zephyr_config.project_key, execution.get("id"), qtest_run, qtest_log,
                    )

                    transformed_batch.append((qtest_run, qtest_log))

                execution_tracker.update_batch_status(batch_idx, len(batch), "completed")
            except Exception as e:
                execution_tracker.update_batch_status(batch_idx, 0, "failed", str(e))
                logger.error(f"Failed to transform execution batch {batch_idx}: {e!s}")

        logger.info(f"Transformed {len(executions)} test executions")

    def _map_status(self, zephyr_status: str) -> str:
        """Map Zephyr execution status to qTest status."""
        # Default mapping - customize based on actual qTest status values
        status_map = {
            "pass": "PASSED",
            "fail": "FAILED",
            "wip": "IN_PROGRESS",
            "blocked": "BLOCKED",
            "unexecuted": "NOT_RUN",
            "not_executed": "NOT_RUN",
            # Additional mappings
            "in_progress": "IN_PROGRESS",
            "passed": "PASSED",
            "failed": "FAILED",
            "incomplete": "IN_PROGRESS",
            "not_tested": "NOT_RUN",
            "executing": "IN_PROGRESS",
        }

        return status_map.get(zephyr_status.lower(), "NOT_RUN")

    def load_data(self):
        """Load transformed data into qTest."""
        logger.info(f"Starting data loading for project {self.zephyr_config.project_key}")
        self.state.update_loading_status("in_progress")

        try:
            # The project should already exist in qTest, so we don't create it

            # Load modules (folders)
            self._load_modules()

            # Load test cases
            self._load_test_cases()

            # Load test cycles
            self._load_test_cycles()

            # Load test runs and logs (executions)
            self._load_test_executions()

            self.state.update_loading_status("completed")
            logger.info(f"Loading completed for project {self.zephyr_config.project_key}")

        except Exception as e:
            self.state.update_loading_status("failed", str(e))
            logger.error(f"Loading failed: {e!s}", exc_info=True)
            raise

    def _load_modules(self):
        """Load modules (transformed folders) into qTest."""
        logger.info("Loading modules into qTest")

        # Get transformed modules (grouped by hierarchy level)
        modules_by_level = self.db.get_transformed_modules_by_level(self.zephyr_config.project_key)

        # Process levels in order (root modules first, then their children)
        for level, modules in enumerate(modules_by_level):
            logger.info(f"Loading level {level} modules ({len(modules)} modules)")

            # Initialize batch tracking
            module_tracker = EntityBatchTracker(
                self.zephyr_config.project_key, f"loaded_modules_level_{level}", self.db,
            )
            module_tracker.initialize_batches(len(modules), self.batch_size)

            # Process modules in batches
            for batch_idx, batch_start in enumerate(range(0, len(modules), self.batch_size)):
                batch_end = min(batch_start + self.batch_size, len(modules))
                batch = modules[batch_start:batch_end]

                created_count = 0
                try:
                    # Use ThreadPoolExecutor for parallel processing
                    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                        futures = []

                        for module_data in batch:
                            source_id = module_data.get("source_id")
                            module = module_data.get("module")

                            # Submit module creation task
                            future = executor.submit(
                                self._create_module_in_qtest, source_id, module,
                            )
                            futures.append((source_id, future))

                        # Process results
                        for source_id, future in futures:
                            try:
                                # Get result (will raise exception if task failed)
                                qtest_module = future.result()

                                # Update mapping
                                if qtest_module and qtest_module.id:
                                    self.entity_mappings["folders"][source_id] = qtest_module.id
                                    self.db.save_entity_mapping(
                                        self.zephyr_config.project_key,
                                        "folder_to_module",
                                        source_id,
                                        qtest_module.id,
                                    )
                                    created_count += 1
                            except Exception as e:
                                logger.error(
                                    f"Failed to create module for folder {source_id}: {e!s}",
                                )

                    module_tracker.update_batch_status(batch_idx, created_count, "completed")
                except Exception as e:
                    module_tracker.update_batch_status(batch_idx, created_count, "failed", str(e))
                    logger.error(f"Failed to process module batch {batch_idx}: {e!s}")

        logger.info("Modules loading completed")

    def _create_module_in_qtest(self, source_id, module_data):
        """Create a module in qTest."""
        # Create QTestModule object from data
        module = QTestModule(
            name=module_data.get("name", ""),
            description=module_data.get("description", ""),
            parent_id=module_data.get("parent_id"),
        )

        # Create in qTest
        try:
            created_module = self.qtest_client.create_module(module)
            logger.debug(f"Created module {created_module.id} for folder {source_id}")
            return created_module
        except Exception as e:
            logger.error(f"Error creating module for folder {source_id}: {e!s}")
            # Implement retry logic if needed
            raise

    def _load_test_cases(self):
        """Load test cases into qTest."""
        logger.info("Loading test cases into qTest")

        # Get transformed test cases
        test_cases = self.db.get_transformed_test_cases(self.zephyr_config.project_key)

        # Initialize batch tracking
        test_case_tracker = EntityBatchTracker(
            self.zephyr_config.project_key, "loaded_test_cases", self.db,
        )
        test_case_tracker.initialize_batches(len(test_cases), self.batch_size)

        # Process test cases in batches
        for batch_idx, batch_start in enumerate(range(0, len(test_cases), self.batch_size)):
            batch_end = min(batch_start + self.batch_size, len(test_cases))
            batch = test_cases[batch_start:batch_end]

            created_count = 0
            try:
                # Use ThreadPoolExecutor for parallel processing
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = []

                    for test_case_data in batch:
                        source_id = test_case_data.get("source_id")
                        test_case = test_case_data.get("test_case")

                        # Submit test case creation task
                        future = executor.submit(
                            self._create_test_case_in_qtest, source_id, test_case,
                        )
                        futures.append((source_id, future))

                    # Process results
                    for source_id, future in futures:
                        try:
                            # Get result (will raise exception if task failed)
                            qtest_test_case = future.result()

                            # Update mapping
                            if qtest_test_case and qtest_test_case.id:
                                self.entity_mappings["test_cases"][source_id] = qtest_test_case.id
                                self.db.save_entity_mapping(
                                    self.zephyr_config.project_key,
                                    "testcase_to_testcase",
                                    source_id,
                                    qtest_test_case.id,
                                )
                                created_count += 1

                                # Upload attachments if any
                                self._upload_test_case_attachments(source_id, qtest_test_case.id)
                        except Exception as e:
                            logger.error(f"Failed to create test case {source_id}: {e!s}")

                test_case_tracker.update_batch_status(batch_idx, created_count, "completed")
            except Exception as e:
                test_case_tracker.update_batch_status(batch_idx, created_count, "failed", str(e))
                logger.error(f"Failed to process test case batch {batch_idx}: {e!s}")

        logger.info("Test cases loading completed")

    def _create_test_case_in_qtest(self, source_id, test_case_data):
        """Create a test case in qTest."""
        # Create QTestTestCase object from data
        test_case = QTestTestCase(
            name=test_case_data.get("name", ""),
            description=test_case_data.get("description", ""),
            precondition=test_case_data.get("precondition", ""),
            test_steps=test_case_data.get("test_steps", []),
            properties=test_case_data.get("properties", []),
            module_id=test_case_data.get("module_id"),
            priority_id=test_case_data.get("priority_id"),
        )

        # Create in qTest
        try:
            created_test_case = self.qtest_client.create_test_case(test_case)
            logger.debug(f"Created test case {created_test_case.id} for source case {source_id}")
            return created_test_case
        except Exception as e:
            logger.error(f"Error creating test case for source {source_id}: {e!s}")
            # Implement retry logic if needed
            raise

    def _upload_test_case_attachments(self, source_id, qtest_test_case_id):
        """Upload attachments for a test case to qTest."""
        # Get attachments for the test case from database
        attachments = self.db.get_attachments("TestCase", source_id)

        for attachment in attachments:
            try:
                # Create temporary file
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=f"_{attachment['name']}",
                ) as tmp:
                    tmp.write(attachment["content"])
                    tmp_path = tmp.name

                # Upload to qTest
                try:
                    self.qtest_client.upload_attachment(
                        object_type="test-cases", object_id=qtest_test_case_id, file_path=tmp_path,
                    )
                    logger.debug(
                        f"Uploaded attachment {attachment['name']} for test case {qtest_test_case_id}",
                    )
                finally:
                    # Clean up temporary file
                    os.unlink(tmp_path)

            except Exception as e:
                logger.warning(
                    f"Failed to upload attachment {attachment['name']} for test case {qtest_test_case_id}: {e!s}",
                )

    def _load_test_cycles(self):
        """Load test cycles into qTest."""
        logger.info("Loading test cycles into qTest")

        # Get transformed test cycles
        test_cycles = self.db.get_transformed_test_cycles(self.zephyr_config.project_key)

        # Initialize batch tracking
        cycle_tracker = EntityBatchTracker(
            self.zephyr_config.project_key, "loaded_test_cycles", self.db,
        )
        cycle_tracker.initialize_batches(len(test_cycles), self.batch_size)

        # Process test cycles in batches
        for batch_idx, batch_start in enumerate(range(0, len(test_cycles), self.batch_size)):
            batch_end = min(batch_start + self.batch_size, len(test_cycles))
            batch = test_cycles[batch_start:batch_end]

            created_count = 0
            try:
                # Use ThreadPoolExecutor for parallel processing
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = []

                    for cycle_data in batch:
                        source_id = cycle_data.get("source_id")
                        cycle = cycle_data.get("test_cycle")

                        # Submit cycle creation task
                        future = executor.submit(self._create_test_cycle_in_qtest, source_id, cycle)
                        futures.append((source_id, future))

                    # Process results
                    for source_id, future in futures:
                        try:
                            # Get result (will raise exception if task failed)
                            qtest_cycle = future.result()

                            # Update mapping
                            if qtest_cycle and qtest_cycle.id:
                                self.entity_mappings["test_cycles"][source_id] = qtest_cycle.id
                                self.db.save_entity_mapping(
                                    self.zephyr_config.project_key,
                                    "cycle_to_cycle",
                                    source_id,
                                    qtest_cycle.id,
                                )
                                created_count += 1
                        except Exception as e:
                            logger.error(f"Failed to create test cycle {source_id}: {e!s}")

                cycle_tracker.update_batch_status(batch_idx, created_count, "completed")
            except Exception as e:
                cycle_tracker.update_batch_status(batch_idx, created_count, "failed", str(e))
                logger.error(f"Failed to process test cycle batch {batch_idx}: {e!s}")

        logger.info("Test cycles loading completed")

    def _create_test_cycle_in_qtest(self, source_id, cycle_data):
        """Create a test cycle in qTest."""
        # Create QTestTestCycle object from data
        cycle = QTestTestCycle(
            name=cycle_data.get("name", ""),
            description=cycle_data.get("description", ""),
            parent_id=cycle_data.get("parent_id"),
            release_id=cycle_data.get("release_id"),
            properties=cycle_data.get("properties", []),
            start_date=cycle_data.get("start_date"),
            end_date=cycle_data.get("end_date"),
        )

        # Create in qTest
        try:
            created_cycle = self.qtest_client.create_test_cycle(cycle)
            logger.debug(f"Created test cycle {created_cycle.id} for source cycle {source_id}")
            return created_cycle
        except Exception as e:
            logger.error(f"Error creating test cycle for source {source_id}: {e!s}")
            # Implement retry logic if needed
            raise

    def _load_test_executions(self):
        """Load test executions (runs and logs) into qTest."""
        logger.info("Loading test executions into qTest")

        # Get transformed test executions
        executions = self.db.get_transformed_executions(self.zephyr_config.project_key)

        # Initialize batch tracking
        execution_tracker = EntityBatchTracker(
            self.zephyr_config.project_key, "loaded_test_executions", self.db,
        )
        execution_tracker.initialize_batches(len(executions), self.batch_size)

        # Process executions in batches
        for batch_idx, batch_start in enumerate(range(0, len(executions), self.batch_size)):
            batch_end = min(batch_start + self.batch_size, len(executions))
            batch = executions[batch_start:batch_end]

            created_count = 0
            try:
                # Use ThreadPoolExecutor for parallel processing
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = []

                    for execution_data in batch:
                        source_id = execution_data.get("source_id")
                        test_run = execution_data.get("test_run")
                        test_log = execution_data.get("test_log")

                        # Submit test run and log creation task
                        future = executor.submit(
                            self._create_execution_in_qtest, source_id, test_run, test_log,
                        )
                        futures.append((source_id, future))

                    # Process results
                    for source_id, future in futures:
                        try:
                            # Get result (will raise exception if task failed)
                            qtest_run_id = future.result()

                            # Update mapping
                            if qtest_run_id:
                                self.entity_mappings["test_executions"][source_id] = qtest_run_id
                                self.db.save_entity_mapping(
                                    self.zephyr_config.project_key,
                                    "execution_to_run",
                                    source_id,
                                    qtest_run_id,
                                )
                                created_count += 1

                                # Upload attachments if any
                                self._upload_execution_attachments(source_id, qtest_run_id)
                        except Exception as e:
                            logger.error(f"Failed to create test execution {source_id}: {e!s}")

                execution_tracker.update_batch_status(batch_idx, created_count, "completed")
            except Exception as e:
                execution_tracker.update_batch_status(batch_idx, created_count, "failed", str(e))
                logger.error(f"Failed to process execution batch {batch_idx}: {e!s}")

        logger.info("Test executions loading completed")

    def _create_execution_in_qtest(self, source_id, test_run_data, test_log_data):
        """Create a test run and log in qTest."""
        # Check if required fields are available
        if not test_run_data.get("test_case_id") or not test_run_data.get("test_cycle_id"):
            logger.warning(f"Skipping execution {source_id}: Missing test case or cycle ID")
            return None

        # Create run
        try:
            # Create test run
            test_run = QTestTestRun(
                name=test_run_data.get("name", ""),
                test_case_id=test_run_data.get("test_case_id"),
                test_cycle_id=test_run_data.get("test_cycle_id"),
                properties=test_run_data.get("properties", []),
            )

            created_run = self.qtest_client.create_test_run(test_run)
            run_id = created_run.id

            # Submit test log
            if test_log_data:
                test_log = {
                    "status": test_log_data.get("status", "NOT_RUN"),
                    "executionDate": test_log_data.get("execution_date"),
                    "note": test_log_data.get("note", ""),
                }

                self.qtest_client.submit_test_log(run_id, test_log)

            logger.debug(f"Created test run {run_id} for source execution {source_id}")
            return run_id

        except Exception as e:
            logger.error(f"Error creating test execution for source {source_id}: {e!s}")
            # Implement retry logic if needed
            raise

    def _upload_execution_attachments(self, source_id, qtest_run_id):
        """Upload attachments for a test execution to qTest."""
        # Get attachments for the execution from database
        attachments = self.db.get_attachments("TestExecution", source_id)

        for attachment in attachments:
            try:
                # Create temporary file
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=f"_{attachment['name']}",
                ) as tmp:
                    tmp.write(attachment["content"])
                    tmp_path = tmp.name

                # Upload to qTest
                try:
                    self.qtest_client.upload_attachment(
                        object_type="test-runs", object_id=qtest_run_id, file_path=tmp_path,
                    )
                    logger.debug(
                        f"Uploaded attachment {attachment['name']} for test run {qtest_run_id}",
                    )
                finally:
                    # Clean up temporary file
                    os.unlink(tmp_path)

            except Exception as e:
                logger.warning(
                    f"Failed to upload attachment {attachment['name']} for test run {qtest_run_id}: {e!s}",
                )

    def get_last_migration_timestamp(self) -> datetime:
        """
        Get the timestamp of the last successful migration run.

        Returns:
            datetime object representing the last migration time or a default date in the past
            if no previous migration was found.

        """
        try:
            # Attempt to retrieve the last migration timestamp from the database
            timestamp = self.db.get_last_migration_timestamp(self.zephyr_config.project_key)
            if timestamp:
                return timestamp

            # If no timestamp is found, return a default date in the past
            return datetime.min
        except Exception as e:
            logger.warning(f"Error retrieving last migration timestamp: {e!s}")
            # In case of error, return a default date in the past
            return datetime.min

    def save_migration_timestamp(self):
        """
        Save the current timestamp as the last successful migration run time.
        This is used for future incremental migrations to determine what has changed.
        """
        try:
            current_time = datetime.now()
            self.db.save_migration_timestamp(self.zephyr_config.project_key, current_time)
            logger.info(f"Saved migration timestamp: {current_time.isoformat()}")
        except Exception as e:
            logger.error(f"Error saving migration timestamp: {e!s}")

    def get_changed_entities_since_last_run(self, entity_type: str) -> list[dict[str, Any]]:
        """
        Get entities that have changed since the last migration run.

        Args:
            entity_type: The type of entity to check for changes (e.g., 'test_cases', 'test_cycles')

        Returns:
            List of changed entities

        """
        # Get the timestamp of the last migration run
        last_migration_time = self.get_last_migration_timestamp()
        logger.info(f"Checking for {entity_type} changes since {last_migration_time.isoformat()}")

        # Get all entities of the specified type
        all_entities = list(self.zephyr_client.get_all_entities(entity_type))

        # Filter out entities that have not been updated since the last migration
        changed_entities = []
        for entity in all_entities:
            # Get the entity's updated timestamp - field name might vary by entity type
            updated_field = (
                entity.get("updated") or entity.get("updatedOn") or entity.get("lastUpdated")
            )

            if updated_field:
                # Parse the updated timestamp (format may vary)
                if isinstance(updated_field, str):
                    try:
                        updated_time = datetime.fromisoformat(updated_field.replace("Z", "+00:00"))
                    except ValueError:
                        # Try another common format
                        updated_time = datetime.strptime(updated_field, "%Y-%m-%dT%H:%M:%S.%fZ")
                else:
                    updated_time = updated_field

                # Check if the entity was updated after the last migration
                if updated_time > last_migration_time:
                    changed_entities.append(entity)
            else:
                # If we can't determine when the entity was updated, include it to be safe
                logger.warning(
                    f"Could not determine update time for {entity_type} {entity.get('id')}",
                )
                changed_entities.append(entity)

        logger.info(
            f"Found {len(changed_entities)} changed {entity_type} out of {len(all_entities)} total",
        )
        return changed_entities

    def resolve_entity_relationships(self, entity_type=None, changed_entities=None):
        """
        Resolve relationships between changed entities and existing entities.
        This ensures that incremental migration maintains proper relationships.

        Args:
            entity_type: The type of entity to resolve relationships for (e.g., 'test_cases')
            changed_entities: List of changed entities to process

        Returns:
            Dict with resolved entities and their dependencies

        """
        logger.info("Resolving entity relationships for incremental migration")

        try:
            # If no specific entities provided, use all changed entities
            if entity_type is None or changed_entities is None:
                # Default to resolving all entity types if not specified
                logger.info("No specific entities provided, resolving all relationships")
                resolved_relationships = {}

                # Resolve test case relationships
                test_case_entities = self.get_changed_entities_since_last_run("test_cases")
                resolved_relationships["test_cases"] = self._resolve_test_case_relationships(
                    test_case_entities,
                )

                # Resolve test cycle relationships
                test_cycle_entities = self.get_changed_entities_since_last_run("test_cycles")
                resolved_relationships["test_cycles"] = self._resolve_test_cycle_relationships(
                    test_cycle_entities,
                )

                # Resolve test execution relationships
                test_execution_entities = self.get_changed_entities_since_last_run(
                    "test_executions",
                )
                resolved_relationships[
                    "test_executions"
                ] = self._resolve_test_execution_relationships(test_execution_entities)

                return resolved_relationships

            # Entity type specific resolution
            if entity_type == "test_cases":
                return self._resolve_test_case_relationships(changed_entities)
            if entity_type == "test_cycles":
                return self._resolve_test_cycle_relationships(changed_entities)
            if entity_type == "test_executions":
                return self._resolve_test_execution_relationships(changed_entities)
            logger.warning(f"No relationship resolver for entity type: {entity_type}")
            return {"entities": changed_entities, "dependencies": []}

        except Exception as e:
            logger.error(f"Error resolving entity relationships: {e!s}", exc_info=True)
            raise

    def _resolve_test_case_relationships(self, changed_test_cases):
        """
        Resolve relationships for test cases.

        Args:
            changed_test_cases: List of changed test cases

        Returns:
            Dict with resolved entities and their dependencies

        """
        logger.info(f"Resolving relationships for {len(changed_test_cases)} test cases")
        test_case_dependencies = []

        # For each test case, identify dependencies
        for test_case in changed_test_cases:
            # Folder dependencies
            folder_id = test_case.get("folderId")
            if folder_id:
                # Check if folder exists in target system
                folder_mapping = self.db.get_entity_mapping(
                    source_id=str(folder_id),
                    source_type="folder",
                    project_key=self.zephyr_config.project_key,
                )

                if not folder_mapping:
                    # Need to include this folder in the migration
                    folder = self.zephyr_client.get_folder(folder_id)
                    if folder:
                        test_case_dependencies.append(
                            {"id": folder_id, "type": "folder", "entity": folder},
                        )

            # Attachment dependencies
            attachments = test_case.get("attachments", [])
            for attachment in attachments:
                attachment_id = attachment.get("id")
                if attachment_id:
                    test_case_dependencies.append(
                        {"id": attachment_id, "type": "attachment", "entity": attachment},
                    )

        return {"entities": changed_test_cases, "dependencies": test_case_dependencies}

    def _resolve_test_cycle_relationships(self, changed_test_cycles):
        """
        Resolve relationships for test cycles.

        Args:
            changed_test_cycles: List of changed test cycles

        Returns:
            Dict with resolved entities and their dependencies

        """
        logger.info(f"Resolving relationships for {len(changed_test_cycles)} test cycles")
        test_cycle_dependencies = []

        # For each test cycle, identify dependencies
        for test_cycle in changed_test_cycles:
            # Parent cycle dependencies
            parent_id = test_cycle.get("parentId")
            if parent_id:
                # Check if parent cycle exists in target system
                parent_mapping = self.db.get_entity_mapping(
                    source_id=str(parent_id),
                    source_type="test_cycle",
                    project_key=self.zephyr_config.project_key,
                )

                if not parent_mapping:
                    # Need to include this parent cycle in the migration
                    parent_cycle = self.zephyr_client.get_test_cycle(parent_id)
                    if parent_cycle:
                        test_cycle_dependencies.append(
                            {"id": parent_id, "type": "test_cycle", "entity": parent_cycle},
                        )

            # Folder dependencies
            folder_id = test_cycle.get("folderId")
            if folder_id:
                folder_mapping = self.db.get_entity_mapping(
                    source_id=str(folder_id),
                    source_type="folder",
                    project_key=self.zephyr_config.project_key,
                )

                if not folder_mapping:
                    folder = self.zephyr_client.get_folder(folder_id)
                    if folder:
                        test_cycle_dependencies.append(
                            {"id": folder_id, "type": "folder", "entity": folder},
                        )

        return {"entities": changed_test_cycles, "dependencies": test_cycle_dependencies}

    def _resolve_test_execution_relationships(self, changed_test_executions):
        """
        Resolve relationships for test executions.

        Args:
            changed_test_executions: List of changed test executions

        Returns:
            Dict with resolved entities and their dependencies

        """
        logger.info(f"Resolving relationships for {len(changed_test_executions)} test executions")
        test_execution_dependencies = []

        # For each test execution, identify dependencies
        for test_execution in changed_test_executions:
            # Test case dependency
            test_case_id = test_execution.get("testCaseId")
            if test_case_id:
                # Check if test case exists in target system
                test_case_mapping = self.db.get_entity_mapping(
                    source_id=str(test_case_id),
                    source_type="test_case",
                    project_key=self.zephyr_config.project_key,
                )

                if not test_case_mapping:
                    # Need to include this test case in the migration
                    test_case = self.zephyr_client.get_test_case(test_case_id)
                    if test_case:
                        test_execution_dependencies.append(
                            {"id": test_case_id, "type": "test_case", "entity": test_case},
                        )

            # Test cycle dependency
            test_cycle_id = test_execution.get("testCycleId")
            if test_cycle_id:
                test_cycle_mapping = self.db.get_entity_mapping(
                    source_id=str(test_cycle_id),
                    source_type="test_cycle",
                    project_key=self.zephyr_config.project_key,
                )

                if not test_cycle_mapping:
                    test_cycle = self.zephyr_client.get_test_cycle(test_cycle_id)
                    if test_cycle:
                        test_execution_dependencies.append(
                            {"id": test_cycle_id, "type": "test_cycle", "entity": test_cycle},
                        )

            # Attachment dependencies
            attachments = test_execution.get("attachments", [])
            for attachment in attachments:
                attachment_id = attachment.get("id")
                if attachment_id:
                    test_execution_dependencies.append(
                        {"id": attachment_id, "type": "attachment", "entity": attachment},
                    )

        return {"entities": changed_test_executions, "dependencies": test_execution_dependencies}

    def transform_test_cases_batch(self, batch):
        """
        Transform a batch of Zephyr test cases to qTest format.

        Args:
            batch: A list of Zephyr test case entities to transform

        Returns:
            List of transformed qTest test case objects

        """
        logger.info(f"Transforming batch of {len(batch)} test cases")
        transformed_batch = []

        for test_case in batch:
            # Get module ID for the test case's folder
            module_id = None
            folder_id = test_case.get("folderId")

            if folder_id:
                module_mapping = self.db.get_entity_mapping(
                    self.zephyr_config.project_key, "folder_to_module", folder_id,
                )
                if module_mapping:
                    module_id = module_mapping.get("target_id")

            # Transform test steps
            qtest_steps = []
            steps = test_case.get("steps", [])

            for idx, step in enumerate(steps):
                # Get description and test data
                description = step.get("description", "")
                test_data = step.get("testData", "")

                # If test data exists, combine it with description
                if test_data:
                    description = f"{description}\n\nTest Data: {test_data}"

                # Create qTest step
                qtest_step = QTestStep(
                    description=description,
                    expected_result=step.get("expectedResult", ""),
                    order=idx + 1,
                )
                qtest_steps.append(qtest_step)

            # Transform custom fields using the field mapper
            qtest_custom_fields = self.field_mapper.map_testcase_fields(test_case)

            # Create qTest test case
            qtest_test_case = QTestTestCase(
                name=test_case.get("name", ""),
                description=test_case.get("description", ""),
                precondition=test_case.get("precondition", ""),
                test_steps=qtest_steps,
                properties=qtest_custom_fields,
                module_id=module_id,
                priority_id=self._map_priority(test_case.get("priority", "")),
            )

            # Save mapping between source and transformed entity
            source_id = test_case.get("id")
            if source_id:
                self.db.save_transformed_test_case(
                    self.zephyr_config.project_key, source_id, qtest_test_case,
                )

            transformed_batch.append(qtest_test_case)

        logger.info(f"Transformed {len(transformed_batch)} test cases")
        return transformed_batch

    def transform_test_cycles_batch(self, batch):
        """
        Transform a batch of Zephyr test cycles to qTest format.

        Args:
            batch: A list of Zephyr test cycle entities to transform

        Returns:
            List of transformed qTest test cycle objects

        """
        logger.info(f"Transforming batch of {len(batch)} test cycles")
        transformed_batch = []

        for cycle in batch:
            # Get folder mapping if available
            parent_id = None
            folder_id = cycle.get("folderId")

            if folder_id:
                folder_mapping = self.db.get_entity_mapping(
                    self.zephyr_config.project_key, "folder_to_module", folder_id,
                )
                if folder_mapping:
                    parent_id = folder_mapping.get("target_id")

            # Transform custom fields using the field mapper
            qtest_custom_fields = self.field_mapper.map_testcycle_fields(cycle)

            # Create qTest test cycle
            qtest_cycle = QTestTestCycle(
                name=cycle.get("name", ""),
                description=cycle.get("description", ""),
                parent_id=parent_id,
                start_date=cycle.get("startDate"),
                end_date=cycle.get("endDate"),
                properties=qtest_custom_fields,
            )

            # Save mapping between source and transformed entity
            source_id = cycle.get("id")
            if source_id:
                self.db.save_transformed_test_cycle(
                    self.zephyr_config.project_key, source_id, qtest_cycle,
                )

            transformed_batch.append(qtest_cycle)

        logger.info(f"Transformed {len(transformed_batch)} test cycles")
        return transformed_batch

    def transform_test_executions_batch(self, batch):
        """
        Transform a batch of Zephyr test executions to qTest format.

        Args:
            batch: A list of Zephyr test execution entities to transform

        Returns:
            List of tuples containing (QTestTestRun, QTestTestLog) objects

        """
        logger.info(f"Transforming batch of {len(batch)} test executions")
        transformed_batch = []

        for execution in batch:
            # Get mappings for related entities
            test_case_id = execution.get("testCaseId")
            test_cycle_id = execution.get("testCycleId")

            qtest_test_case_id = None
            qtest_test_cycle_id = None

            if test_case_id:
                case_mapping = self.db.get_entity_mapping(
                    self.zephyr_config.project_key, "testcase_to_testcase", test_case_id,
                )
                if case_mapping:
                    qtest_test_case_id = case_mapping.get("target_id")

            if test_cycle_id:
                cycle_mapping = self.db.get_entity_mapping(
                    self.zephyr_config.project_key, "cycle_to_cycle", test_cycle_id,
                )
                if cycle_mapping:
                    qtest_test_cycle_id = cycle_mapping.get("target_id")

            # Map the status to qTest format
            qtest_status = self._map_status(execution.get("status", ""))

            # Transform custom fields using the field mapper
            qtest_custom_fields = self.field_mapper.map_testrun_fields(execution)

            # Create test run model
            qtest_run = QTestTestRun(
                name=f"Run for {test_case_id} in cycle {test_cycle_id}",
                test_case_id=qtest_test_case_id,
                test_cycle_id=qtest_test_cycle_id,
                properties=qtest_custom_fields,
            )

            # Get execution steps and comments
            steps = execution.get("steps", [])
            comment = execution.get("comment", "")

            # Format step results if they exist
            step_results = []
            for idx, step in enumerate(steps):
                step_status = step.get("status") or qtest_status
                actual_result = step.get("actualResult", "")

                # Map step status to qTest status
                qtest_step_status = self._map_status(step_status)

                # Add step result to list
                step_results.append(
                    {"order": idx + 1, "status": qtest_step_status, "actualResult": actual_result},
                )

            # Create test log model
            qtest_log = QTestTestLog(
                status=qtest_status,
                execution_date=execution.get("executionTime") or execution.get("executedOn"),
                note=comment,
                test_step_logs=step_results if step_results else None,
            )

            # Save mapping between source and transformed entity
            source_id = execution.get("id")
            if source_id:
                self.db.save_transformed_execution(
                    self.zephyr_config.project_key, source_id, qtest_run, qtest_log,
                )

            transformed_batch.append((qtest_run, qtest_log))

        logger.info(f"Transformed {len(transformed_batch)} test executions")
        return transformed_batch


def create_migration(
    zephyr_config: ZephyrConfig,
    qtest_config: QTestConfig,
    database_manager: Any,
    batch_size: int = 50,
    max_workers: int = 5,
    attachments_dir: Path | None = None,
    enable_validation: bool = True,
) -> ZephyrToQTestMigration:
    """
    Factory function to create a migration instance with optional validation enhancement.

    Args:
        zephyr_config: The Zephyr API configuration
        qtest_config: The qTest API configuration
        database_manager: The database manager for storing migration data
        batch_size: Number of items to process in a batch
        max_workers: Maximum number of concurrent workers
        attachments_dir: Optional directory for attachment storage
        enable_validation: Whether to enable enhanced validation

    Returns:
        ZephyrToQTestMigration or EnhancedMigration: A migration instance

    """
    # Create base migration instance
    migration = ZephyrToQTestMigration(
        zephyr_config=zephyr_config,
        qtest_config=qtest_config,
        database_manager=database_manager,
        batch_size=batch_size,
        max_workers=max_workers,
        attachments_dir=attachments_dir,
        enable_validation=enable_validation,
    )

    # Enhance with validation if enabled
    if enable_validation:
        logger.info("Creating enhanced migration with validation framework")
        return get_enhanced_migration(migration, database_manager, zephyr_config.project_key)

    logger.info("Creating standard migration without validation framework")
    return migration
