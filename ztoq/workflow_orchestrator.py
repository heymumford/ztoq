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
        attachments_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        timeout: int = 3600,  # Default timeout is 1 hour
        zephyr_config: Optional[ZephyrConfig] = None,
        qtest_config: Optional[QTestConfig] = None,
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
            zephyr_config: Zephyr Scale configuration
            qtest_config: qTest configuration
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
        self.validation_manager = ValidationManager(database=self.db) if config.validation_enabled else None

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
                    self._add_event(phase, "skipped", f"Skipping {phase} phase (already completed)")
                    if self.progress and phase in self.tasks:
                        self.progress.update(self.tasks[phase], description=f"{phase.capitalize()} (skipped)", completed=1, total=1)
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
        return False

    async def _run_extract_phase(self) -> None:
        """
        Run the extract phase of the workflow.

        This phase extracts data from Zephyr Scale and stores it in the database.
        """
        phase = WorkflowPhase.EXTRACT.value
        self._add_event(phase, "in_progress", "Starting data extraction")

        if self.progress and phase in self.tasks:
            self.progress.update(self.tasks[phase], description="Extracting data...", total=None)

        try:
            # Run extraction
            await asyncio.to_thread(self.migration.extract_data)

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

    async def _run_transform_phase(self) -> None:
        """
        Run the transform phase of the workflow.

        This phase transforms the extracted data into the format required by qTest.
        """
        phase = WorkflowPhase.TRANSFORM.value
        self._add_event(phase, "in_progress", "Starting data transformation")

        if self.progress and phase in self.tasks:
            self.progress.update(self.tasks[phase], description="Transforming data...", total=None)

        try:
            # Run transformation
            await asyncio.to_thread(self.migration.transform_data)

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
        """
        phase = WorkflowPhase.LOAD.value
        self._add_event(phase, "in_progress", "Starting data loading")

        if self.progress and phase in self.tasks:
            self.progress.update(self.tasks[phase], description="Loading data to qTest...", total=None)

        try:
            # Run loading
            await asyncio.to_thread(self.migration.load_data)

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
            self.progress.update(self.tasks[phase], description="Validating migration...", total=None)

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
                report_path = Path(self.config.output_dir) / f"validation_report_{self.config.project_key}.json"
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
        }

        # Execute validation rules
        results = []
        for rule in rules:
            if not rule.enabled:
                continue

            try:
                rule_result = rule.execute(context)
                results.append(rule_result)
            except Exception as e:
                logger.error(f"Error executing validation rule {rule.id}: {str(e)}", exc_info=True)
                # Create a validation issue for the rule execution error
                self.validation_manager.add_issue(
                    rule_id=rule.id,
                    level=rule.level,
                    message=f"Error executing rule: {str(e)}",
                    entity_id=None,
                    scope=rule.scope,
                    phase=ValidationPhase.POST_MIGRATION,
                    project_key=project_key,
                )

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
        }

        # Save validation report to database
        self.db.save_validation_report(project_key, validation_results)

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
        self._add_event("workflow", "in_progress", f"Resuming workflow with phases: {', '.join(phases)}")

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
            color = "green" if phase_status == "completed" else "yellow" if phase_status == "in_progress" else "red" if phase_status == "failed" else "blue"
            phase_table.add_row(phase.capitalize(), phase_status.replace("_", " ").title(), duration_str, style=color)

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

            validation_table.add_row("Critical", str(validation.get("critical_issues", 0)), style="red")
            validation_table.add_row("Error", str(validation.get("error_issues", 0)), style="yellow")
            validation_table.add_row("Warning", str(validation.get("warning_issues", 0)), style="blue")
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