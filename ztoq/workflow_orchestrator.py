"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Workflow orchestration module for ETL migration process.

This module provides a comprehensive workflow orchestration system for the ETL
(Extract, Transform, Load) migration process as defined in ADR-013. It handles
phase coordination, state management, error handling, and logging.
"""

import asyncio
import logging
import os
import time
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from ztoq.database_factory import DatabaseFactory, DatabaseType, get_database_manager
from ztoq.migration import EntityBatchTracker, MigrationState, ZephyrToQTestMigration
from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig
from ztoq.validation import ValidationManager, ValidationPhase, ValidationScope

logger = logging.getLogger("ztoq.workflow")
console = Console()


class WorkflowPhase(str, Enum):
    """Phases of the ETL migration workflow."""

    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    VALIDATE = "validate"
    ROLLBACK = "rollback"
    ALL = "all"


class WorkflowStatus(str, Enum):
    """Status of a workflow phase."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some batches completed, some failed


class WorkflowConfig:
    """Configuration for the workflow orchestrator."""

    def __init__(
        self,
        project_key: str,
        db_type: str = "sqlite",
        db_path: Optional[str] = None,
        pg_host: Optional[str] = None,
        pg_port: Optional[int] = None,
        pg_username: Optional[str] = None,
        pg_password: Optional[str] = None,
        pg_database: Optional[str] = None,
        batch_size: int = 50,
        max_workers: int = 5,
        validation_enabled: bool = True,
        rollback_enabled: bool = True,
        attachments_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        timeout: int = 3600,  # Default timeout is 1 hour
        zephyr_config: Optional[ZephyrConfig] = None,
        qtest_config: Optional[QTestConfig] = None,
        use_batch_transformer: bool = True,  # Enable batch transformer by default
    ):
        """
        Initialize workflow configuration.

        Args:
            project_key: The Zephyr project key
            db_type: Database type (sqlite or postgresql)
            db_path: Path to SQLite database
            pg_host: PostgreSQL host
            pg_port: PostgreSQL port
            pg_username: PostgreSQL username
            pg_password: PostgreSQL password
            pg_database: PostgreSQL database name
            batch_size: Number of items to process in a batch
            max_workers: Maximum number of concurrent workers
            validation_enabled: Whether to run validation
            attachments_dir: Directory for storing attachments
            output_dir: Directory for output files (reports, logs)
            timeout: Timeout in seconds for each phase
            rollback_enabled: Whether to enable rollback capability for failed migrations
            zephyr_config: Zephyr Scale configuration
            qtest_config: qTest configuration
            use_batch_transformer: Whether to use the SQL-based batch transformer for
                                  the transformation phase
        """
        self.project_key = project_key
        self.db_type = db_type
        self.db_path = db_path
        self.pg_host = pg_host
        self.pg_port = pg_port
        self.pg_username = pg_username
        self.pg_password = pg_password
        self.pg_database = pg_database
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.validation_enabled = validation_enabled
        self.attachments_dir = attachments_dir
        self.output_dir = output_dir
        self.timeout = timeout
        self.zephyr_config = zephyr_config
        self.qtest_config = qtest_config
        self.use_batch_transformer = use_batch_transformer

        # Set up output directory
        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)

        # Set up attachments directory
        if self.attachments_dir:
            os.makedirs(self.attachments_dir, exist_ok=True)


class WorkflowEvent:
    """Event for tracking workflow progress and updates."""

    def __init__(
        self,
        phase: str,
        status: str,
        message: str,
        entity_type: Optional[str] = None,
        entity_count: Optional[int] = None,
        batch_number: Optional[int] = None,
        total_batches: Optional[int] = None,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize workflow event.

        Args:
            phase: Workflow phase (extract, transform, load, validate)
            status: Status (in_progress, completed, failed, etc.)
            message: Human-readable message
            entity_type: Type of entity being processed
            entity_count: Number of entities processed
            batch_number: Current batch number
            total_batches: Total number of batches
            timestamp: Event timestamp
            metadata: Additional metadata
        """
        self.phase = phase
        self.status = status
        self.message = message
        self.entity_type = entity_type
        self.entity_count = entity_count
        self.batch_number = batch_number
        self.total_batches = total_batches
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}

    def as_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "phase": self.phase,
            "status": self.status,
            "message": self.message,
            "entity_type": self.entity_type,
            "entity_count": self.entity_count,
            "batch_number": self.batch_number,
            "total_batches": self.total_batches,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation of the event."""
        return (
            f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.phase.upper()}: "
            f"{self.message} ({self.status})"
        )


class WorkflowOrchestrator:
    """
    Orchestrates the ETL migration workflow.

    This class coordinates the different phases of the ETL workflow,
    handles error recovery, and provides progress tracking.
    """

    def __init__(self, config: WorkflowConfig):
        """
        Initialize workflow orchestrator.

        Args:
            config: Workflow configuration
        """
        self.config = config
        self.events: List[WorkflowEvent] = []
        self.rollback_points: Dict[str, Any] = {}
        self.rollback_enabled = config.rollback_enabled

        # Initialize database manager
        if config.db_type == DatabaseType.POSTGRESQL:
            self.db = get_database_manager(
                db_type=config.db_type,
                host=config.pg_host,
                port=config.pg_port,
                username=config.pg_username,
                password=config.pg_password,
                database=config.pg_database,
            )
        else:
            self.db = get_database_manager(
                db_type=config.db_type,
                db_path=config.db_path,
            )

        # Initialize migration state
        self.state = MigrationState(config.project_key, self.db)

        # Initialize validation manager if validation is enabled
        self.validation_manager = (
            ValidationManager(database=self.db) if config.validation_enabled else None
        )

        # Initialize migration executor
        if config.zephyr_config and config.qtest_config:
            self.migration = ZephyrToQTestMigration(
                zephyr_config=config.zephyr_config,
                qtest_config=config.qtest_config,
                database_manager=self.db,
                batch_size=config.batch_size,
                max_workers=config.max_workers,
                attachments_dir=config.attachments_dir,
            )
        else:
            self.migration = None

        # Progress tracking
        self.progress = None
        self.tasks = {}

    def _add_event(
        self,
        phase: str,
        status: str,
        message: str,
        entity_type: Optional[str] = None,
        entity_count: Optional[int] = None,
        batch_number: Optional[int] = None,
        total_batches: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowEvent:
        """
        Add a workflow event.

        Args:
            phase: Workflow phase
            status: Status
            message: Human-readable message
            entity_type: Type of entity being processed
            entity_count: Number of entities processed
            batch_number: Current batch number
            total_batches: Total number of batches
            metadata: Additional metadata

        Returns:
            The created workflow event
        """
        event = WorkflowEvent(
            phase=phase,
            status=status,
            message=message,
            entity_type=entity_type,
            entity_count=entity_count,
            batch_number=batch_number,
            total_batches=total_batches,
            metadata=metadata,
        )

        # Add to in-memory events list
        self.events.append(event)

        # Log the event
        logger.info(str(event))

        # Save to database
        self.db.save_workflow_event(self.config.project_key, event.as_dict())

        return event

    async def run_workflow(
        self, phases: Optional[List[str]] = None, progress: Optional[Progress] = None
    ) -> Dict[str, Any]:
        """
        Run the migration workflow.

        Args:
            phases: List of phases to run (default: all)
            progress: Optional progress instance for UI updates

        Returns:
            Dictionary with workflow results and statistics
        """
        phases = phases or [WorkflowPhase.ALL.value]

        # If ALL is specified, run all phases in order
        if WorkflowPhase.ALL.value in phases:
            phases = [
                WorkflowPhase.EXTRACT.value,
                WorkflowPhase.TRANSFORM.value,
                WorkflowPhase.LOAD.value,
                WorkflowPhase.VALIDATE.value,
            ]

        # If ROLLBACK is specified, make it the only phase to run
        if WorkflowPhase.ROLLBACK.value in phases:
            phases = [WorkflowPhase.ROLLBACK.value]

        # Set up progress tracking if provided
        self.progress = progress
        if self.progress:
            self.tasks = {}
            for phase in phases:
                self.tasks[phase] = self.progress.add_task(
                    f"Running {phase.capitalize()} phase...", total=None
                )

        # Validate configuration
        if not self.migration and (
            WorkflowPhase.EXTRACT.value in phases
            or WorkflowPhase.TRANSFORM.value in phases
            or WorkflowPhase.LOAD.value in phases
        ):
            error_msg = "Missing Zephyr or qTest configuration"
            self._add_event("init", "failed", error_msg)
            raise ValueError(error_msg)

        results = {}

        # Execute each phase
        try:
            for phase in phases:
                # Check if we can skip this phase
                if self._can_skip_phase(phase):
                    # Don't skip rollback phase if explicitly requested
                    if phase != WorkflowPhase.ROLLBACK.value:
                        self._add_event(phase, "skipped", f"Skipping {phase} phase (already completed)")
                        if self.progress and phase in self.tasks:
                            self.progress.update(
                                self.tasks[phase],
                                description=f"{phase.capitalize()} (skipped)",
                                completed=1,
                                total=1,
                            )
                        continue

                # Run the appropriate phase
                if phase == WorkflowPhase.EXTRACT.value:
                    await self._run_extract_phase()
                    results[phase] = {"status": self.state.extraction_status}

                elif phase == WorkflowPhase.TRANSFORM.value:
                    await self._run_transform_phase()
                    results[phase] = {"status": self.state.transformation_status}

                elif phase == WorkflowPhase.LOAD.value:
                    await self._run_load_phase()
                    results[phase] = {"status": self.state.loading_status}

                elif phase == WorkflowPhase.VALIDATE.value:
                    validation_results = await self._run_validation_phase()
                    results[phase] = validation_results

                elif phase == WorkflowPhase.ROLLBACK.value:
                    if not self.rollback_enabled:
                        self._add_event(phase, "skipped", "Skipping rollback phase (rollback is disabled)")
                        results[phase] = {"status": "skipped", "reason": "Rollback is disabled"}
                    else:
                        rollback_results = await self._run_rollback_phase()
                        results[phase] = rollback_results

                # Mark progress as completed for this phase
                if self.progress and phase in self.tasks:
                    self.progress.update(
                        self.tasks[phase],
                        description=f"{phase.capitalize()} completed",
                        completed=1,
                        total=1,
                    )

            # Generate workflow summary
            summary = self._generate_workflow_summary()
            results["summary"] = summary

            return results

        except Exception as e:
            logger.error(f"Workflow error: {str(e)}", exc_info=True)
            self._add_event("workflow", "failed", f"Workflow failed: {str(e)}")

            # Update progress to show failure
            if self.progress:
                for phase in phases:
                    if phase in self.tasks:
                        self.progress.update(
                            self.tasks[phase],
                            description=f"{phase.capitalize()} (failed)",
                            completed=0,
                            total=1,
                        )

            raise

    def _can_skip_phase(self, phase: str) -> bool:
        """
        Check if a phase can be skipped (already completed).

        Args:
            phase: Phase to check

        Returns:
            True if the phase can be skipped
        """
        if phase == WorkflowPhase.EXTRACT.value:
            return self.state.extraction_status == "completed"
        elif phase == WorkflowPhase.TRANSFORM.value:
            return self.state.transformation_status == "completed"
        elif phase == WorkflowPhase.LOAD.value:
            return self.state.loading_status == "completed"
        elif phase == WorkflowPhase.VALIDATE.value:
            # Currently we always run validation
            return False
        elif phase == WorkflowPhase.ROLLBACK.value:
            # Never skip rollback if explicitly requested
            return False
        return False

    async def _run_extract_phase(self) -> None:
        """
        Run the extract phase of the workflow.

        This phase extracts data from Zephyr Scale and stores it in the database.
        If in incremental mode, it only extracts entities that have changed since
        the last migration.
        """
        phase = WorkflowPhase.EXTRACT.value
        self._add_event(phase, "in_progress", "Starting data extraction")

        if self.progress and phase in self.tasks:
            self.progress.update(self.tasks[phase], description="Extracting data...", total=None)

        try:
            # Check if we're in incremental mode
            if self.state.is_incremental:
                self._add_event(
                    phase,
                    "in_progress",
                    "Running incremental extraction (changed entities only)"
                )

                # Run incremental extraction
                await asyncio.to_thread(self._run_incremental_extraction)
            else:
                # Run full extraction using optimized work queue
                from ztoq.work_queue import WorkQueue, WorkerType, WorkStatus, WorkItem

                self._add_event(
                    phase,
                    "in_progress",
                    f"Running extraction with optimized work queue (max workers: {self.config.max_workers})"
                )

                # Create an extraction worker queue
                await self._run_extraction_with_work_queue()

            # Update state
            self._add_event(
                phase,
                "completed",
                "Data extraction completed",
                metadata={"extraction_status": self.state.extraction_status},
            )

        except Exception as e:
            error_msg = f"Data extraction failed: {str(e)}"
            self._add_event(phase, "failed", error_msg)
            self.state.update_extraction_status("failed", str(e))
            raise

    async def _run_extraction_with_work_queue(self) -> None:
        """
        Run extraction using an optimized work queue for parallel processing.

        This method leverages the WorkQueue implementation to parallelize extraction
        of different entity types and batches, providing better performance and
        resource utilization compared to the previous approach.
        """
        from ztoq.work_queue import WorkQueue, WorkerType, WorkStatus, run_in_thread_pool

        logger.info("Starting extraction with work queue")

        # Define extraction tasks to parallelize
        extraction_tasks = {
            "project": lambda: self.migration.extract_project(),
            "folders": lambda: self.migration.extract_folders(),
            "statuses": lambda: self.migration.extract_statuses(),
            "priorities": lambda: self.migration.extract_priorities(),
            "environments": lambda: self.migration.extract_environments(),
            "test_cases": lambda: self.migration.extract_test_cases(),
            "test_cycles": lambda: self.migration.extract_test_cycles(),
            "test_executions": lambda: self.migration.extract_test_executions(),
        }

        # Define worker function to run a task
        def task_worker(task_name_and_func):
            task_name, task_func = task_name_and_func
            logger.info(f"Extracting {task_name}...")
            start_time = time.time()
            result = task_func()
            end_time = time.time()
            logger.info(f"Extracted {task_name} in {end_time - start_time:.2f} seconds")
            return {"task": task_name, "result": result, "time": end_time - start_time}

        # Run the tasks in parallel
        task_items = [(name, func) for name, func in extraction_tasks.items()]
        results = await run_in_thread_pool(
            task_worker,
            task_items,
            max_workers=min(len(task_items), self.config.max_workers)
        )

        # Process the results
        extraction_results = {}
        total_time = 0
        for result in results:
            task_name = result["task"]
            extraction_results[task_name] = result["result"]
            total_time += result["time"]

            # Log results
            if isinstance(result["result"], list):
                self._add_event(
                    WorkflowPhase.EXTRACT.value,
                    "in_progress",
                    f"Extracted {len(result['result'])} {task_name} in {result['time']:.2f} seconds",
                    entity_type=task_name,
                    entity_count=len(result["result"]) if isinstance(result["result"], list) else 1,
                )

        # Log overall results
        logger.info(f"Completed extraction with work queue in {total_time:.2f} seconds")

        # Update extraction status
        self.state.update_extraction_status("completed")

        return extraction_results

    def _run_incremental_extraction(self) -> Dict[str, Any]:
        """
        Execute incremental extraction, only retrieving changed entities.

        Returns:
            Dictionary with extraction results
        """
        logger.info("Starting incremental extraction")

        try:
            extraction_results = {}

            # Get test cases that have changed since last migration
            test_cases = self.migration.get_changed_entities_since_last_run("test_cases")
            logger.info(f"Found {len(test_cases)} changed test cases")
            extraction_results["test_cases"] = test_cases

            # Get test cycles that have changed since last migration
            test_cycles = self.migration.get_changed_entities_since_last_run("test_cycles")
            logger.info(f"Found {len(test_cycles)} changed test cycles")
            extraction_results["test_cycles"] = test_cycles

            # Get test executions that have changed since last migration
            test_executions = self.migration.get_changed_entities_since_last_run("test_executions")
            logger.info(f"Found {len(test_executions)} changed test executions")
            extraction_results["test_executions"] = test_executions

            # Resolve relationships to ensure data integrity
            logger.info("Resolving entity relationships for incremental migration")
            relationships = self.migration.resolve_entity_relationships()

            # Store the extracted data in the database with appropriate batch tracking
            total_entities = 0
            for entity_type, entities in extraction_results.items():
                # Check if we have any entities of this type
                if entities:
                    # Get dependencies for this entity type from relationships
                    dependencies = relationships.get(entity_type, {}).get("dependencies", [])

                    # Store main entities
                    self.migration.store_extracted_entities(entity_type, entities)
                    total_entities += len(entities)

                    # Store dependencies if any
                    if dependencies:
                        logger.info(f"Storing {len(dependencies)} dependencies for {entity_type}")
                        # Group dependencies by type
                        deps_by_type = {}
                        for dep in dependencies:
                            dep_type = dep.get("type")
                            if dep_type not in deps_by_type:
                                deps_by_type[dep_type] = []
                            deps_by_type[dep_type].append(dep.get("entity"))

                        # Store each type of dependency
                        for dep_type, dep_entities in deps_by_type.items():
                            if dep_entities:
                                self.migration.store_extracted_entities(dep_type, dep_entities)
                                total_entities += len(dep_entities)

            # Update extraction status
            self.state.update_extraction_status("completed")

            logger.info(f"Incremental extraction completed with {total_entities} total entities")
            return extraction_results

        except Exception as e:
            logger.error(f"Incremental extraction failed: {str(e)}", exc_info=True)
            self.state.update_extraction_status("failed", str(e))
            raise

    async def _run_transform_phase(self) -> None:
        """
        Run the transform phase of the workflow.

        This phase transforms the extracted data into the format required by qTest.
        Uses SQLTestCaseTransformer for batch processing when available, falling back
        to standard transformation if not.

        In incremental mode, only transforms entities that have changed since the last
        migration.
        """
        phase = WorkflowPhase.TRANSFORM.value
        self._add_event(phase, "in_progress", "Starting data transformation")

        if self.progress and phase in self.tasks:
            self.progress.update(self.tasks[phase], description="Transforming data...", total=None)

        try:
            # Check if SQL-based batch transformation should be used
            use_batch_transformer = getattr(self.config, "use_batch_transformer", True)

            # Check if we're in incremental mode
            if self.state.is_incremental:
                self._add_event(
                    phase,
                    "in_progress",
                    "Running incremental transformation (changed entities only)"
                )

                # Run incremental transformation
                await asyncio.to_thread(self._run_incremental_transformation)
            elif use_batch_transformer:
                # Import here to avoid circular imports
                from ztoq.sql_test_case_transformer import SQLTestCaseTransformer
                from ztoq.work_queue import WorkQueue, WorkerType, WorkStatus, run_in_thread_pool

                self._add_event(
                    phase,
                    "in_progress",
                    f"Using optimized parallel SQL-based batch transformer with batch size {self.config.batch_size}",
                )

                # Create SQL transformer with database manager and batch size
                transformer = SQLTestCaseTransformer(
                    db_manager=self.db,
                    batch_size=self.config.batch_size,
                    field_mapper=self.migration.field_mapper if self.migration else None,
                )

                # Get all batches that need transformation
                batches = self.db.get_entity_batches_by_status(
                    project_key=self.config.project_key,
                    entity_type="test_case",
                    status="extracted"
                )

                if not batches:
                    self._add_event(
                        phase,
                        "completed",
                        "No test case batches to transform",
                    )
                    self.state.update_transformation_status("completed")
                else:
                    batch_ids = [batch.get("batch_id") for batch in batches]
                    self._add_event(
                        phase,
                        "in_progress",
                        f"Transforming {len(batch_ids)} batches with optimized work queue (max workers: {self.config.max_workers})"
                    )

                    # Define batch transformation worker
                    def transform_batch(batch_id):
                        start_time = time.time()
                        result = transformer.transform_batch(batch_id)
                        end_time = time.time()
                        return {
                            "batch_id": batch_id,
                            "result": result,
                            "time": end_time - start_time
                        }

                    # Run batch transformations in parallel
                    batch_results = await run_in_thread_pool(
                        transform_batch,
                        batch_ids,
                        max_workers=min(len(batch_ids), self.config.max_workers)
                    )

                    # Process results
                    successful = 0
                    failed = 0
                    warnings = 0
                    total_time = 0

                    for result in batch_results:
                        batch_result = result["result"]
                        total_time += result["time"]

                        successful += batch_result.get("successful", 0)
                        failed += batch_result.get("failed", 0)
                        warnings += batch_result.get("warnings", 0)

                    # Log statistics
                    self._add_event(
                        phase,
                        "in_progress",
                        f"Batch transformation completed: {successful} successful, "
                        f"{failed} failed out of {successful + failed} test cases in "
                        f"{len(batch_ids)} batches (took {total_time:.2f} seconds)",
                        entity_type="test_cases",
                        entity_count=successful + failed,
                        metadata={
                            "successful": successful,
                            "failed": failed,
                            "warnings": warnings,
                            "batches": len(batch_ids),
                            "time": total_time,
                        },
                    )

                    # Update state
                    if failed == 0:
                        self.state.update_transformation_status("completed")
                    elif successful > 0:
                        self.state.update_transformation_status(
                            "partial", f"{failed} test cases failed transformation"
                        )
                    else:
                        self.state.update_transformation_status(
                            "failed", "All test cases failed transformation"
                        )
            else:
                # Use optimized parallel transformation instead of the standard approach
                self._add_event(
                    phase,
                    "in_progress",
                    f"Using optimized parallel transformation with {self.config.max_workers} workers"
                )
                await self._run_parallel_transformation()

            # Update state
            self._add_event(
                phase,
                "completed",
                "Data transformation completed",
                metadata={"transformation_status": self.state.transformation_status},
            )

        except Exception as e:
            error_msg = f"Data transformation failed: {str(e)}"
            self._add_event(phase, "failed", error_msg)
            self.state.update_transformation_status("failed", str(e))
            raise

    async def _run_load_phase(self) -> None:
        """
        Run the load phase of the workflow.

        This phase loads the transformed data into qTest.
        In incremental mode, only loads entities that have changed since the last migration.
        """
        phase = WorkflowPhase.LOAD.value
        self._add_event(phase, "in_progress", "Starting data loading")

        if self.progress and phase in self.tasks:
            self.progress.update(
                self.tasks[phase], description="Loading data to qTest...", total=None
            )

        try:
            # Check if we're in incremental mode
            if self.state.is_incremental:
                self._add_event(
                    phase,
                    "in_progress",
                    "Running incremental loading (changed entities only)"
                )

                # Run incremental loading
                await asyncio.to_thread(self._run_incremental_loading)
            else:
                # Use optimized parallel loading with work queues
                self._add_event(
                    phase,
                    "in_progress",
                    f"Running optimized parallel loading with {self.config.max_workers} workers"
                )
                await self._run_parallel_loading()

            # Update state
            self._add_event(
                phase,
                "completed",
                "Data loading completed",
                metadata={"loading_status": self.state.loading_status},
            )

        except Exception as e:
            error_msg = f"Data loading failed: {str(e)}"
            self._add_event(phase, "failed", error_msg)
            self.state.update_loading_status("failed", str(e))
            raise

    async def _run_parallel_transformation(self) -> None:
        """
        Run transformation with optimized parallel processing.

        This method breaks down the transformation process into smaller chunks
        that can be processed in parallel, improving performance for large datasets.
        """
        from ztoq.work_queue import WorkQueue, WorkerType, WorkStatus, run_in_thread_pool

        logger.info("Starting parallel transformation")

        # Define transformation tasks for different entity types
        transformation_tasks = {
            "test_cases": self.migration.transform_test_cases,
            "test_cycles": self.migration.transform_test_cycles,
            "test_executions": self.migration.transform_test_executions,
        }

        # Define worker function to run a task
        def transform_worker(task_info):
            entity_type, transform_func = task_info
            logger.info(f"Transforming {entity_type}...")
            start_time = time.time()
            result = transform_func()
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"Transformed {entity_type} in {duration:.2f} seconds")
            return {
                "entity_type": entity_type,
                "result": result,
                "time": duration
            }

        # Run the tasks in parallel
        tasks = [(entity_type, func) for entity_type, func in transformation_tasks.items()]
        results = await run_in_thread_pool(
            transform_worker,
            tasks,
            max_workers=min(len(tasks), self.config.max_workers)
        )

        # Process the results
        transformation_results = {}
        total_time = 0
        for result in results:
            entity_type = result["entity_type"]
            transformation_results[entity_type] = result["result"]
            total_time += result["time"]

            # Add event
            count = 0
            if isinstance(result["result"], dict) and "count" in result["result"]:
                count = result["result"]["count"]
            elif isinstance(result["result"], list):
                count = len(result["result"])

            self._add_event(
                WorkflowPhase.TRANSFORM.value,
                "in_progress",
                f"Transformed {count} {entity_type} in {result['time']:.2f} seconds",
                entity_type=entity_type,
                entity_count=count,
            )

        # Update transformation status
        self.state.update_transformation_status("completed")

        # Log overall results
        logger.info(f"Completed parallel transformation in {total_time:.2f} seconds")
        return transformation_results

    def _run_incremental_transformation(self) -> Dict[str, Any]:
        """
        Execute incremental transformation, only transforming changed entities.

        Returns:
            Dictionary with transformation results
        """
        logger.info("Starting incremental transformation")

        try:
            transformation_results = {}

            # Import here to avoid circular imports
            from ztoq.sql_test_case_transformer import SQLTestCaseTransformer

            # Get database manager reference
            db = self.db

            # Create SQL transformer with database manager and batch size
            transformer = SQLTestCaseTransformer(
                db_manager=db,
                batch_size=self.config.batch_size,
                field_mapper=self.migration.field_mapper if self.migration else None,
            )

            # Get untransformed batches (specifically for incremental migration)
            # Filtered to only include entities that were extracted during incremental extraction
            untransformed_batches = db.get_entity_batches_by_status(
                project_key=self.config.project_key,
                entity_type="test_case",
                status="extracted",
                is_incremental=True
            )

            # Transform test cases
            if untransformed_batches:
                logger.info(f"Transforming {len(untransformed_batches)} batches of test cases")
                batch_ids = [batch.get("batch_id") for batch in untransformed_batches]
                transformer.transform_batches(batch_ids)
                transformation_results["test_cases"] = {"processed": len(untransformed_batches)}

            # Do similar for test cycles, test executions, etc.
            # ...

            # Update state
            self.state.update_transformation_status("completed")

            logger.info("Incremental transformation completed")
            return transformation_results

        except Exception as e:
            logger.error(f"Incremental transformation failed: {str(e)}", exc_info=True)
            self.state.update_transformation_status("failed", str(e))
            raise

    async def _run_parallel_loading(self) -> None:
        """
        Run loading with optimized parallel processing.

        This method leverages the WorkQueue implementation to parallelize loading
        of different entity types and batches, providing better performance and
        resource utilization compared to the previous approach.
        """
        from ztoq.work_queue import WorkQueue, WorkerType, WorkStatus, run_in_thread_pool

        logger.info("Starting parallel loading")

        # Group the loading tasks by their dependencies
        # Test cases must be loaded first, then test cycles, then test executions
        loading_phases = [
            {
                "name": "test_cases",
                "func": self.migration.load_test_cases,
            },
            {
                "name": "test_cycles",
                "func": self.migration.load_test_cycles,
            },
            {
                "name": "test_executions",
                "func": self.migration.load_test_executions,
            },
        ]

        # Process each phase sequentially (due to dependencies)
        for phase in loading_phases:
            entity_type = phase["name"]
            load_func = phase["func"]

            # Get all transformed batches for this entity type
            batches = self.db.get_entity_batches_by_status(
                project_key=self.config.project_key,
                entity_type=entity_type.replace("_", ""),  # Remove underscores for database naming
                status="transformed"
            )

            if not batches:
                self._add_event(
                    WorkflowPhase.LOAD.value,
                    "in_progress",
                    f"No {entity_type} to load",
                    entity_type=entity_type,
                )
                continue

            batch_ids = [batch.get("batch_id") for batch in batches]

            self._add_event(
                WorkflowPhase.LOAD.value,
                "in_progress",
                f"Loading {len(batch_ids)} batches of {entity_type} with work queue",
                entity_type=entity_type,
                batch_number=0,
                total_batches=len(batch_ids),
            )

            # Define batch loading worker
            def load_batch(batch_id):
                start_time = time.time()
                result = load_func(batch_ids=[batch_id])
                end_time = time.time()
                return {
                    "batch_id": batch_id,
                    "result": result,
                    "time": end_time - start_time
                }

            # Process batches in parallel
            batch_results = await run_in_thread_pool(
                load_batch,
                batch_ids,
                max_workers=min(len(batch_ids), self.config.max_workers)
            )

            # Process results
            success_count = 0
            failed_count = 0
            total_time = 0

            for result in batch_results:
                success_count += 1 if result.get("result", 0) > 0 else 0
                failed_count += 1 if result.get("result", 0) == 0 else 0
                total_time += result["time"]

            # Log results
            self._add_event(
                WorkflowPhase.LOAD.value,
                "in_progress",
                f"Loaded {success_count} batches of {entity_type} in {total_time:.2f} seconds ({failed_count} failed)",
                entity_type=entity_type,
                batch_number=len(batch_ids),
                total_batches=len(batch_ids),
                metadata={
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "total_time": total_time
                }
            )

        # Mark loading as completed
        self.state.update_loading_status("completed")
        logger.info("Parallel loading completed")

    def _run_incremental_loading(self) -> Dict[str, Any]:
        """
        Execute incremental loading, only loading changed entities.

        Returns:
            Dictionary with loading results
        """
        logger.info("Starting incremental loading")

        try:
            loading_results = {}

            # Get transformed batches ready for loading
            transformed_batches = self.db.get_entity_batches_by_status(
                project_key=self.config.project_key,
                entity_type="test_case",
                status="transformed",
                is_incremental=True
            )

            if transformed_batches:
                logger.info(f"Loading {len(transformed_batches)} batches of test cases")

                # Use the migration's load method but with specific batches
                # We could also implement a more selective loading strategy
                loaded_count = self.migration.load_test_cases(batch_ids=[
                    batch.get("batch_id") for batch in transformed_batches
                ])

                loading_results["test_cases"] = {
                    "processed": len(transformed_batches),
                    "loaded": loaded_count
                }

            # Do similar for test cycles, test executions, etc.
            # ...

            # Update state
            self.state.update_loading_status("completed")

            logger.info("Incremental loading completed")
            return loading_results

        except Exception as e:
            logger.error(f"Incremental loading failed: {str(e)}", exc_info=True)
            self.state.update_loading_status("failed", str(e))
            raise

    async def _run_rollback_phase(self) -> Dict[str, Any]:
        """
        Run the rollback phase of the workflow.

        This phase reverts changes made during the migration process in case of failures.

        Returns:
            Dictionary with rollback results
        """
        phase = WorkflowPhase.ROLLBACK.value
        self.state.update_rollback_status("in_progress")
        self._add_event(phase, "in_progress", "Starting migration rollback")

        if self.progress and phase in self.tasks:
            self.progress.update(self.tasks[phase], description="Rolling back migration...", total=None)

        try:
            # Start with determining what phases need to be rolled back
            phases_to_rollback = []

            if self.state.loading_status == "completed" or self.state.loading_status == "partial":
                phases_to_rollback.append(WorkflowPhase.LOAD.value)

            if self.state.transformation_status == "completed":
                phases_to_rollback.append(WorkflowPhase.TRANSFORM.value)

            if self.state.extraction_status == "completed":
                phases_to_rollback.append(WorkflowPhase.EXTRACT.value)

            if not phases_to_rollback:
                self._add_event(phase, "completed", "No phases to roll back")
                self.state.update_rollback_status("completed")
                return {
                    "status": "completed",
                    "message": "No phases to roll back",
                    "phases_rolled_back": []
                }

            # Roll back in reverse order of execution
            rolled_back_phases = []

            for phase_to_rollback in phases_to_rollback:
                self._add_event(
                    phase, "in_progress", f"Rolling back {phase_to_rollback} phase"
                )

                if phase_to_rollback == WorkflowPhase.LOAD.value:
                    # Roll back loaded data from qTest
                    await asyncio.to_thread(self._rollback_loaded_data)
                    rolled_back_phases.append(phase_to_rollback)

                elif phase_to_rollback == WorkflowPhase.TRANSFORM.value:
                    # Roll back transformed data in the database
                    await asyncio.to_thread(self._rollback_transformed_data)
                    rolled_back_phases.append(phase_to_rollback)

                elif phase_to_rollback == WorkflowPhase.EXTRACT.value:
                    # Roll back extracted data in the database
                    await asyncio.to_thread(self._rollback_extracted_data)
                    rolled_back_phases.append(phase_to_rollback)

            # Update state
            self.state.update_rollback_status("completed")
            self._add_event(
                phase,
                "completed",
                f"Migration rollback completed for phases: {', '.join(rolled_back_phases)}",
            )

            # Return results
            return {
                "status": "completed",
                "phases_rolled_back": rolled_back_phases,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            error_msg = f"Migration rollback failed: {str(e)}"
            self._add_event(phase, "failed", error_msg)
            self.state.update_rollback_status("failed", str(e))
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _rollback_loaded_data(self) -> None:
        """Roll back loaded data from qTest."""
        logger.info("Rolling back loaded data from qTest")

        try:
            if not self.migration or not self.migration.qtest_client:
                logger.error("Cannot roll back loaded data: qTest client not initialized")
                return

            # Get the project ID
            project_key = self.config.project_key

            # Get all entity mappings for this project
            mappings = self.db.get_entity_mappings_for_rollback(project_key)

            # Delete entities from qTest in the correct order to respect references
            # First delete test runs and logs
            execution_mappings = [m for m in mappings if m["entity_type"] == "execution_to_run"]
            logger.info(f"Deleting {len(execution_mappings)} test runs from qTest")

            for mapping in execution_mappings:
                target_id = mapping.get("target_id")
                if target_id:
                    try:
                        self.migration.qtest_client.delete_test_run(target_id)
                    except Exception as e:
                        logger.warning(f"Failed to delete test run {target_id}: {str(e)}")

            # Then delete test cycles
            cycle_mappings = [m for m in mappings if m["entity_type"] == "cycle_to_cycle"]
            logger.info(f"Deleting {len(cycle_mappings)} test cycles from qTest")

            for mapping in cycle_mappings:
                target_id = mapping.get("target_id")
                if target_id:
                    try:
                        self.migration.qtest_client.delete_test_cycle(target_id)
                    except Exception as e:
                        logger.warning(f"Failed to delete test cycle {target_id}: {str(e)}")

            # Finally delete test cases
            case_mappings = [m for m in mappings if m["entity_type"] == "testcase_to_testcase"]
            logger.info(f"Deleting {len(case_mappings)} test cases from qTest")

            for mapping in case_mappings:
                target_id = mapping.get("target_id")
                if target_id:
                    try:
                        self.migration.qtest_client.delete_test_case(target_id)
                    except Exception as e:
                        logger.warning(f"Failed to delete test case {target_id}: {str(e)}")

            # Update loading status to reflect the rollback
            self.state.update_loading_status("rolled_back")

        except Exception as e:
            logger.error(f"Error rolling back loaded data: {str(e)}", exc_info=True)
            raise

    def _rollback_transformed_data(self) -> None:
        """Roll back transformed data from the database."""
        logger.info("Rolling back transformed data from database")

        try:
            # Delete all transformed entities from the database
            project_key = self.config.project_key
            self.db.delete_transformed_entities(project_key)

            # Update transformation status to reflect the rollback
            self.state.update_transformation_status("rolled_back")

        except Exception as e:
            logger.error(f"Error rolling back transformed data: {str(e)}", exc_info=True)
            raise

    def _rollback_extracted_data(self) -> None:
        """Roll back extracted data from the database."""
        logger.info("Rolling back extracted data from database")

        try:
            # Delete all Zephyr entities from the database
            project_key = self.config.project_key
            self.db.delete_extracted_entities(project_key)

            # Update extraction status to reflect the rollback
            self.state.update_extraction_status("rolled_back")

        except Exception as e:
            logger.error(f"Error rolling back extracted data: {str(e)}", exc_info=True)
            raise

    async def _run_validation_phase(self) -> Dict[str, Any]:
        """
        Run the validation phase of the workflow.

        This phase validates the migrated data to ensure its integrity.

        Returns:
            Dictionary with validation results
        """
        phase = WorkflowPhase.VALIDATE.value
        self._add_event(phase, "in_progress", "Starting data validation")

        if self.progress and phase in self.tasks:
            self.progress.update(
                self.tasks[phase], description="Validating migration...", total=None
            )

        try:
            # If validation manager is not enabled, return empty results
            if not self.validation_manager:
                self._add_event(phase, "skipped", "Validation is disabled")
                return {"status": "skipped", "reason": "Validation is disabled"}

            # Run validation
            # This should validate that the migration was successful by comparing
            # the source and target data, checking relationships, etc.
            validation_results = await asyncio.to_thread(
                self._run_validation_checks, self.config.project_key
            )

            # Generate validation report
            report_path = None
            if self.config.output_dir:
                report_path = (
                    Path(self.config.output_dir)
                    / f"validation_report_{self.config.project_key}.json"
                )
                with open(report_path, "w") as f:
                    json.dump(validation_results, f, indent=2)

            # Update state
            status = "completed"
            if validation_results.get("has_critical_issues", False):
                status = "failed"

            self._add_event(
                phase,
                status,
                f"Data validation {status}",
                metadata={
                    "validation_status": status,
                    "report_path": str(report_path) if report_path else None,
                    "issues_count": validation_results.get("total_issues", 0),
                },
            )

            return validation_results

        except Exception as e:
            error_msg = f"Data validation failed: {str(e)}"
            self._add_event(phase, "failed", error_msg)
            raise

    def _run_validation_checks(self, project_key: str) -> Dict[str, Any]:
        """
        Run validation checks on the migrated data.

        Args:
            project_key: The project key to validate

        Returns:
            Dictionary with validation results
        """
        if not self.validation_manager:
            return {"status": "skipped", "reason": "Validation is disabled"}

        # Get validation rules for the POST_MIGRATION phase
        rules = self.validation_manager.registry.get_rules_for_phase(ValidationPhase.POST_MIGRATION)

        # Create context for validation
        context = {
            "database": self.db,
            "project_key": project_key,
            "phase": ValidationPhase.POST_MIGRATION.value,
            "qtest_client": self.migration.qtest_client if self.migration else None,
            "validator": self.validator if hasattr(self, "validator") else None,
        }

        # Execute validation rules
        results = []
        for rule in rules:
            if not rule.enabled:
                continue

            try:
                rule_result = rule.validate(None, context)
                if rule_result:
                    # Add issues to validation manager
                    for issue in rule_result:
                        self.validation_manager.add_issue(issue)
                    results.append({
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "issues_count": len(rule_result)
                    })
            except Exception as e:
                logger.error(f"Error executing validation rule {rule.id}: {str(e)}", exc_info=True)
                # Create a validation issue for the rule execution error
                issue = ValidationIssue(
                    id=f"rule_execution_error_{int(time.time())}",
                    level=rule.level,
                    scope=rule.scope,
                    phase=ValidationPhase.POST_MIGRATION,
                    message=f"Error executing rule: {str(e)}",
                    details={"rule_id": rule.id, "error": str(e)},
                )
                self.validation_manager.add_issue(issue)

        # Check if we need to run enhanced post-migration validation
        try:
            # Import here to avoid circular imports
            from ztoq.post_migration_validation import PostMigrationValidator

            # Run enhanced validation if available
            logger.info("Running enhanced post-migration validation checks")
            validator = self.validator or MigrationValidator(self.validation_manager,
                                                          project_key=project_key,
                                                          db_manager=self.db)

            post_validator = PostMigrationValidator(validator)
            enhanced_results = post_validator.run_post_migration_validation(
                self.migration.qtest_client if self.migration else None
            )

            # Include enhanced validation results
            enhanced_validation_performed = True

            # Try to retrieve validation report ID from database if it wasn't stored in results
            if "report_id" not in enhanced_results:
                # Get the most recent validation report for this project
                reports = self.db.get_post_migration_validation_reports(project_key, limit=1)
                if reports and len(reports) > 0:
                    enhanced_results["report_id"] = reports[0]["id"]

            logger.info(f"Enhanced validation completed with {enhanced_results.get('total_issues', 0)} issues")
            logger.info(f"Validation report ID: {enhanced_results.get('report_id', 'Not available')}")

            # Log the validation success status
            if enhanced_results.get("success", False):
                logger.info("Post-migration validation successful!")
            else:
                if enhanced_results.get("has_critical_issues", False):
                    logger.error("Post-migration validation FAILED with CRITICAL issues")
                elif enhanced_results.get("has_error_issues", False):
                    logger.warning("Post-migration validation FAILED with ERROR issues")
                else:
                    logger.info("Post-migration validation completed with warnings")

        except (ImportError, Exception) as e:
            logger.warning(f"Could not run enhanced post-migration validation: {str(e)}")
            enhanced_validation_performed = False
            enhanced_results = {}

        # Get validation issues
        issues = self.db.get_validation_issues(project_key, resolved=False)

        # Organize issues by level
        issues_by_level = {
            "critical": [],
            "error": [],
            "warning": [],
            "info": [],
        }

        for issue in issues:
            level = issue.get("level", "info").lower()
            if level in issues_by_level:
                issues_by_level[level].append(issue)

        # Generate validation summary
        validation_results = {
            "status": "completed",
            "project_key": project_key,
            "timestamp": datetime.now().isoformat(),
            "critical_issues": len(issues_by_level["critical"]),
            "error_issues": len(issues_by_level["error"]),
            "warning_issues": len(issues_by_level["warning"]),
            "info_issues": len(issues_by_level["info"]),
            "total_issues": len(issues),
            "has_critical_issues": len(issues_by_level["critical"]) > 0,
            "recent_issues": issues[:20],  # Only include the most recent 20 issues
            "rule_results": results,
            "enhanced_validation": {
                "performed": enhanced_validation_performed,
                "results": enhanced_results if enhanced_validation_performed else {}
            }
        }

        # Add recommendations if available
        if enhanced_validation_performed and "recommendations" in enhanced_results:
            validation_results["recommendations"] = enhanced_results["recommendations"]

        # Save validation report to database
        report_id = self.db.save_validation_report(project_key, validation_results)

        # Add report ID to results
        if report_id:
            validation_results["report_id"] = report_id

        # Add enhanced validation report ID to results if available
        if enhanced_validation_performed and "report_id" in enhanced_results:
            validation_results["enhanced_validation"]["report_id"] = enhanced_results["report_id"]

        return validation_results

    def _generate_workflow_summary(self) -> Dict[str, Any]:
        """
        Generate a summary of the workflow execution.

        Returns:
            Dictionary with workflow summary
        """
        summary = {
            "project_key": self.config.project_key,
            "timestamp": datetime.now().isoformat(),
            "extraction_status": self.state.extraction_status,
            "transformation_status": self.state.transformation_status,
            "loading_status": self.state.loading_status,
            "events_count": len(self.events),
            "duration": {
                "extract": self._calculate_phase_duration(WorkflowPhase.EXTRACT.value),
                "transform": self._calculate_phase_duration(WorkflowPhase.TRANSFORM.value),
                "load": self._calculate_phase_duration(WorkflowPhase.LOAD.value),
                "validate": self._calculate_phase_duration(WorkflowPhase.VALIDATE.value),
            },
            "entity_counts": self._get_entity_counts(),
        }

        return summary

    def _calculate_phase_duration(self, phase: str) -> Optional[float]:
        """
        Calculate the duration of a workflow phase.

        Args:
            phase: Phase name

        Returns:
            Duration in seconds or None if phase not run
        """
        # Find start event
        start_event = None
        for event in self.events:
            if event.phase == phase and event.status == "in_progress":
                start_event = event
                break

        if not start_event:
            return None

        # Find end event
        end_event = None
        for event in reversed(self.events):
            if event.phase == phase and event.status in ["completed", "failed", "skipped"]:
                end_event = event
                break

        if not end_event:
            return None

        # Calculate duration
        duration = (end_event.timestamp - start_event.timestamp).total_seconds()
        return duration

    def _get_entity_counts(self) -> Dict[str, Dict[str, int]]:
        """
        Get counts of entities before and after migration.

        Returns:
            Dictionary with entity counts
        """
        counts = {
            "source": {},
            "target": {},
            "mappings": {},
        }

        try:
            # Source counts (Zephyr)
            source_counts = self.db.get_source_entity_counts(self.config.project_key)
            counts["source"] = source_counts

            # Target counts (qTest)
            target_counts = self.db.get_target_entity_counts(self.config.project_key)
            counts["target"] = target_counts

            # Mapping counts
            mapping_counts = self.db.get_entity_mapping_counts(self.config.project_key)
            counts["mappings"] = mapping_counts

        except Exception as e:
            logger.error(f"Error getting entity counts: {str(e)}", exc_info=True)

        return counts

    def get_workflow_status(self) -> Dict[str, Any]:
        """
        Get the current status of the workflow.

        Returns:
            Dictionary with workflow status
        """
        status = {
            "project_key": self.config.project_key,
            "timestamp": datetime.now().isoformat(),
            "phases": {
                WorkflowPhase.EXTRACT.value: self.state.extraction_status,
                WorkflowPhase.TRANSFORM.value: self.state.transformation_status,
                WorkflowPhase.LOAD.value: self.state.loading_status,
                # We don't have a validation status in the state
                WorkflowPhase.VALIDATE.value: self._get_validation_status(),
            },
            "events": [event.as_dict() for event in self.events[-10:]],  # Last 10 events
            "entity_counts": self._get_entity_counts(),
            "incomplete_batches": self._get_incomplete_batches(),
        }

        return status

    def _get_validation_status(self) -> str:
        """
        Get the status of the validation phase.

        Returns:
            Validation status (not_started, in_progress, completed, failed)
        """
        # Check for validation events
        validation_events = [e for e in self.events if e.phase == WorkflowPhase.VALIDATE.value]

        if not validation_events:
            return "not_started"

        # Get the most recent validation event
        latest_event = max(validation_events, key=lambda e: e.timestamp)
        return latest_event.status

    def _get_incomplete_batches(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get information about incomplete batches.

        Returns:
            Dictionary with incomplete batches by entity type
        """
        try:
            # Get all incomplete batches
            batches = self.db.get_incomplete_batches(self.config.project_key)

            # Group by entity type
            batches_by_type = {}
            for batch in batches:
                entity_type = batch.get("entity_type", "unknown")
                if entity_type not in batches_by_type:
                    batches_by_type[entity_type] = []
                batches_by_type[entity_type].append(batch)

            return batches_by_type

        except Exception as e:
            logger.error(f"Error getting incomplete batches: {str(e)}", exc_info=True)
            return {}

    def run_incremental_migration(self, phases: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run an incremental migration that only processes entities changed since last run.

        This method differs from a full migration in that it only extracts, transforms,
        and loads entities that have been modified since the last migration. It maintains
        relationships with existing entities and ensures data consistency.

        Args:
            phases: List of phases to run (default: all)

        Returns:
            Dictionary with workflow results
        """
        # Update state to indicate this is an incremental migration
        self.state.is_incremental = True

        # If no phases are specified, run all phases
        if not phases:
            phases = [
                WorkflowPhase.EXTRACT.value,
                WorkflowPhase.TRANSFORM.value,
                WorkflowPhase.LOAD.value,
                WorkflowPhase.VALIDATE.value,
            ]

        self._add_event(
            "workflow",
            "in_progress",
            f"Starting incremental migration with phases: {', '.join(phases)}"
        )

        try:
            # Run the workflow with the specified phases
            result = asyncio.run(self.run_workflow(phases))

            # Save the current timestamp for future incremental migrations
            if self.migration:
                self.migration.save_migration_timestamp()

            return result

        except Exception as e:
            logger.error(f"Incremental migration error: {str(e)}", exc_info=True)
            self._add_event("workflow", "failed", f"Incremental migration failed: {str(e)}")
            raise

    def resume_workflow(self, phases: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Resume a previously interrupted workflow.

        Args:
            phases: List of phases to resume (default: all incomplete phases)

        Returns:
            Dictionary with workflow results
        """
        # Determine which phases need to be resumed
        if not phases:
            phases = []

            # Check extract phase
            if self.state.extraction_status in ["not_started", "in_progress", "failed"]:
                phases.append(WorkflowPhase.EXTRACT.value)

            # Check transform phase
            if self.state.transformation_status in ["not_started", "in_progress", "failed"]:
                phases.append(WorkflowPhase.TRANSFORM.value)

            # Check load phase
            if self.state.loading_status in ["not_started", "in_progress", "failed"]:
                phases.append(WorkflowPhase.LOAD.value)

            # Always run validation
            phases.append(WorkflowPhase.VALIDATE.value)

        # If no phases need to be resumed, just return the current status
        if not phases:
            self._add_event("workflow", "skipped", "No phases to resume")
            return {"status": "skipped", "reason": "No phases to resume"}

        # Resume each phase
        self._add_event(
            "workflow", "in_progress", f"Resuming workflow with phases: {', '.join(phases)}"
        )

        # Use the run_workflow method to execute the phases
        return asyncio.run(self.run_workflow(phases))

    def get_entity_batches(self, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get information about entity batches.

        Args:
            entity_type: Optional entity type filter

        Returns:
            List of batch information dictionaries
        """
        try:
            return self.db.get_entity_batches(self.config.project_key, entity_type)
        except Exception as e:
            logger.error(f"Error getting entity batches: {str(e)}", exc_info=True)
            return []

    def create_workflow_report(self, output_path: Optional[str] = None) -> str:
        """
        Create a comprehensive workflow report.

        Args:
            output_path: Optional path to save the report

        Returns:
            Path to the saved report or the report content
        """
        # Get workflow status and summary
        status = self.get_workflow_status()
        summary = self._generate_workflow_summary()

        # Get validation information
        validation_info = {}
        try:
            # Get the most recent validation report
            reports = self.db.get_validation_reports(self.config.project_key, limit=1)
            if reports:
                validation_info = reports[0]
        except Exception as e:
            logger.error(f"Error getting validation reports: {str(e)}", exc_info=True)

        # Combine all information into a comprehensive report
        report = {
            "project_key": self.config.project_key,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "summary": summary,
            "validation": validation_info,
            "events": [event.as_dict() for event in self.events],
            "configuration": {
                "db_type": self.config.db_type,
                "batch_size": self.config.batch_size,
                "max_workers": self.config.max_workers,
                "validation_enabled": self.config.validation_enabled,
                "use_batch_transformer": getattr(self.config, "use_batch_transformer", True),
            },
        }

        # Save the report if output_path is specified
        if output_path:
            output_path = os.path.abspath(output_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(report, f, indent=2)

            return output_path
        else:
            # Otherwise, just return the report as a JSON string
            return json.dumps(report, indent=2)

    def print_workflow_status(self, console: Optional[Console] = None) -> None:
        """
        Print the current workflow status to the console.

        Args:
            console: Optional rich console to use
        """
        console = console or Console()

        # Get status
        status = self.get_workflow_status()

        # Create a table for phase status
        phase_table = Table(title=f"Workflow Status for {self.config.project_key}")
        phase_table.add_column("Phase")
        phase_table.add_column("Status")
        phase_table.add_column("Duration")

        # Add phases to the table
        for phase, phase_status in status["phases"].items():
            # Get duration
            duration = status.get("duration", {}).get(phase)
            duration_str = f"{duration:.2f}s" if duration else "N/A"

            # Add row with appropriate color
            color = (
                "green"
                if phase_status == "completed"
                else "yellow"
                if phase_status == "in_progress"
                else "red"
                if phase_status == "failed"
                else "blue"
            )
            phase_table.add_row(
                phase.capitalize(),
                phase_status.replace("_", " ").title(),
                duration_str,
                style=color,
            )

        console.print(phase_table)

        # Create a table for entity counts
        counts_table = Table(title="Entity Counts")
        counts_table.add_column("Entity Type")
        counts_table.add_column("Source")
        counts_table.add_column("Target")
        counts_table.add_column("Mapped")

        # Add entity types to the table
        if "entity_counts" in status:
            source_counts = status["entity_counts"].get("source", {})
            target_counts = status["entity_counts"].get("target", {})
            mapping_counts = status["entity_counts"].get("mappings", {})

            # Get all entity types
            all_entity_types = set()
            all_entity_types.update(source_counts.keys())
            all_entity_types.update(target_counts.keys())
            all_entity_types.update(mapping_counts.keys())

            for entity_type in sorted(all_entity_types):
                source_count = source_counts.get(entity_type, 0)
                target_count = target_counts.get(entity_type, 0)
                mapping_count = mapping_counts.get(entity_type, 0)

                # Calculate completion percentage
                completion = f"{mapping_count}/{source_count}"

                counts_table.add_row(
                    entity_type.replace("_", " ").title(),
                    str(source_count),
                    str(target_count),
                    completion,
                )

        console.print(counts_table)

        # Print recent events
        events_table = Table(title="Recent Events")
        events_table.add_column("Timestamp")
        events_table.add_column("Phase")
        events_table.add_column("Status")
        events_table.add_column("Message")

        for event in status["events"]:
            phase = event["phase"].capitalize()
            event_status = event["status"].replace("_", " ").title()
            timestamp = datetime.fromisoformat(event["timestamp"]).strftime("%H:%M:%S")

            events_table.add_row(timestamp, phase, event_status, event["message"])

        console.print(events_table)

        # Print validation summary if available
        if "validation" in status and status["validation"]:
            validation = status["validation"]

            validation_table = Table(title="Validation Summary")
            validation_table.add_column("Level")
            validation_table.add_column("Count")

            validation_table.add_row(
                "Critical", str(validation.get("critical_issues", 0)), style="red"
            )
            validation_table.add_row(
                "Error", str(validation.get("error_issues", 0)), style="yellow"
            )
            validation_table.add_row(
                "Warning", str(validation.get("warning_issues", 0)), style="blue"
            )
            validation_table.add_row("Info", str(validation.get("info_issues", 0)), style="green")

            console.print(validation_table)

    # Context manager support
    def __enter__(self):
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        # Clean up resources if needed
        pass
