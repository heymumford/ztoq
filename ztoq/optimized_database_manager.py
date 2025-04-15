"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Optimized database manager for ZTOQ.

This module extends the standard database manager with optimized database
access patterns for improved performance with large datasets.
"""

import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Type, TypeVar, Union, cast

from sqlalchemy import Column, Table, func, text
from sqlalchemy.engine import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Query, Session, sessionmaker

from ztoq.core.db_manager import SQLDatabaseManager
from ztoq.core.db_models import (
    Base,
    EntityBatchState,
    Folder,
    Project,
    TestCase,
    TestCycle,
    TestExecution,
)
from ztoq.database_optimizations import (
    QueryCache,
    bulk_insert,
    bulk_update,
    cached_query,
    chunked_fetch,
    db_stats,
    keyset_pagination,
    transaction_scope,
    tracked_execution,
    with_retry,
)
from ztoq.models import (
    Case as CaseModel,
    CustomField as CustomFieldModel,
    CycleInfo as CycleInfoModel,
    Execution as ExecutionModel,
    Folder as FolderModel,
    Project as ProjectModel,
)

# Setup logging
logger = logging.getLogger(__name__)

# Type variable for database models
T = TypeVar("T", bound=Base)

# Global query cache
model_cache = QueryCache[str, Any](ttl_seconds=60)  # Short TTL for entity data


class OptimizedDatabaseManager(SQLDatabaseManager):
    """
    Optimized database manager with improved performance for large datasets.

    This class extends the standard SQLDatabaseManager with optimized database
    access patterns, caching, and batch processing for better performance.
    """

    def __init__(self, config=None, base_manager=None):
        """
        Initialize the optimized database manager.

        Args:
            config: Database configuration (optional if base_manager is provided)
            base_manager: Base database manager instance to wrap (optional)
        """
        if base_manager:
            # If base_manager is provided, we'll delegate to it
            self.engine = getattr(base_manager, "engine", None)
            self.session_factory = getattr(base_manager, "session_factory", None)
            self.config = getattr(base_manager, "config", None)
            self.base_manager = base_manager
        else:
            # Otherwise, initialize normally
            super().__init__(config)
            self.base_manager = None

        self._model_cache = model_cache

    @tracked_execution("get_project")
    @cached_query(ttl_seconds=300)  # Cache projects for 5 minutes
    def get_project(self, project_key: str) -> Optional[Project]:
        """
        Get a project by key with caching.

        Args:
            project_key: Project key

        Returns:
            Project instance or None if not found
        """
        with self.get_session() as session:
            return session.query(Project).filter_by(key=project_key).first()

    @tracked_execution("save_project")
    def save_project(self, project_model: ProjectModel) -> None:
        """
        Save a project with cache invalidation.

        Args:
            project_model: Project model instance
        """
        super().save_project(project_model)

        # Invalidate project cache
        self._model_cache.invalidate(f"get_project:{project_model.key}")

    @tracked_execution("batch_save_folders")
    def batch_save_folders(self, folders: List[FolderModel], project_key: str) -> None:
        """
        Save multiple folders in a single batch operation.

        This is much more efficient than saving folders one by one.

        Args:
            folders: List of folder models
            project_key: Project key
        """
        if not folders:
            return

        folder_dicts = []
        for folder in folders:
            folder_dict = {
                "id": folder.id,
                "name": folder.name,
                "folder_type": folder.folder_type,
                "parent_id": folder.parent_id,
                "project_key": project_key,
            }
            folder_dicts.append(folder_dict)

        with self.get_session() as session:
            bulk_insert(session, Folder, folder_dicts)

    @tracked_execution("batch_save_test_cases")
    def batch_save_test_cases(self, test_cases: List[CaseModel], project_key: str) -> None:
        """
        Save multiple test cases in a single batch operation.

        Args:
            test_cases: List of test case models
            project_key: Project key
        """
        if not test_cases:
            return

        # Process in smaller batches to avoid transaction size issues
        batch_size = 100

        for i in range(0, len(test_cases), batch_size):
            batch = test_cases[i : i + batch_size]
            self._save_test_case_batch(batch, project_key)

    def _save_test_case_batch(self, test_cases: List[CaseModel], project_key: str) -> None:
        """
        Save a batch of test cases.

        Args:
            test_cases: Batch of test case models
            project_key: Project key
        """
        with self.get_session() as session:
            with transaction_scope(session):
                for test_case in test_cases:
                    # Convert to TestCase model
                    tc_dict = self._test_case_to_dict(test_case, project_key)

                    # Check if the test case already exists
                    existing = session.query(TestCase).filter_by(id=test_case.id).first()

                    if existing:
                        # Update existing test case
                        for key, value in tc_dict.items():
                            setattr(existing, key, value)
                    else:
                        # Create new test case
                        db_test_case = TestCase(**tc_dict)
                        session.add(db_test_case)

                    # Handle related entities
                    self._handle_test_case_relations(session, test_case, project_key)

    def _test_case_to_dict(self, test_case: CaseModel, project_key: str) -> Dict[str, Any]:
        """
        Convert a test case model to a dictionary for database storage.

        Args:
            test_case: Test case model
            project_key: Project key

        Returns:
            Dictionary representation of the test case
        """
        # Handle priority - it could be an object or a dict
        priority_id = None
        if test_case.priority:
            if isinstance(test_case.priority, dict):
                priority_id = test_case.priority.get("id")
            else:
                priority_id = test_case.priority.id

        # Convert test case to dictionary
        return {
            "id": test_case.id,
            "key": test_case.key,
            "name": test_case.name,
            "objective": test_case.objective,
            "precondition": test_case.precondition,
            "description": test_case.description,
            "status": test_case.status,
            "priority_id": priority_id,
            "priority_name": test_case.priority_name,
            "folder_id": test_case.folder,
            "folder_name": test_case.folder_name,
            "owner": test_case.owner,
            "owner_name": test_case.owner_name,
            "component": test_case.component,
            "component_name": test_case.component_name,
            "created_on": test_case.created_on,
            "created_by": test_case.created_by,
            "updated_on": test_case.updated_on,
            "updated_by": test_case.updated_by,
            "version": test_case.version,
            "estimated_time": test_case.estimated_time,
            "labels": json.dumps(test_case.labels) if test_case.labels else None,
            "project_key": project_key,
        }

    def _handle_test_case_relations(
        self, session: Session, test_case: CaseModel, project_key: str
    ) -> None:
        """
        Handle relations for a test case.

        Args:
            session: Database session
            test_case: Test case model
            project_key: Project key
        """
        # This is a simplified implementation - in a real implementation
        # we would handle steps, custom fields, links, scripts, versions, and attachments
        pass

    @tracked_execution("get_test_cases")
    def get_test_cases(
        self, project_key: str, page_size: int = 100, last_id: Optional[str] = None
    ) -> List[TestCase]:
        """
        Get test cases using efficient keyset pagination.

        Args:
            project_key: Project key
            page_size: Number of test cases per page
            last_id: Last test case ID from previous page

        Returns:
            List of test cases
        """
        with self.get_session() as session:
            return keyset_pagination(
                session,
                TestCase,
                TestCase.id,
                page_size,
                last_id,
                TestCase.project_key == project_key,
            )

    @tracked_execution("get_test_cases_count")
    @cached_query(ttl_seconds=60)
    def get_test_cases_count(self, project_key: str) -> int:
        """
        Get the count of test cases for a project with caching.

        Args:
            project_key: Project key

        Returns:
            Count of test cases
        """
        with self.get_session() as session:
            return (
                session.query(func.count(TestCase.id)).filter_by(project_key=project_key).scalar()
                or 0
            )

    @tracked_execution("get_test_case_by_key")
    def get_test_case_by_key(self, test_case_key: str) -> Optional[TestCase]:
        """
        Get a test case by key with index optimization.

        Args:
            test_case_key: Test case key

        Returns:
            Test case instance or None if not found
        """
        with self.get_session() as session:
            return session.query(TestCase).filter_by(key=test_case_key).first()

    @tracked_execution("batch_save_test_cycles")
    def batch_save_test_cycles(self, test_cycles: List[CycleInfoModel], project_key: str) -> None:
        """
        Save multiple test cycles in a single batch operation.

        Args:
            test_cycles: List of test cycle models
            project_key: Project key
        """
        if not test_cycles:
            return

        # Process in smaller batches
        batch_size = 100

        for i in range(0, len(test_cycles), batch_size):
            batch = test_cycles[i : i + batch_size]
            self._save_test_cycle_batch(batch, project_key)

    def _save_test_cycle_batch(self, test_cycles: List[CycleInfoModel], project_key: str) -> None:
        """
        Save a batch of test cycles.

        Args:
            test_cycles: Batch of test cycle models
            project_key: Project key
        """
        with self.get_session() as session:
            with transaction_scope(session):
                for test_cycle in test_cycles:
                    # Convert to TestCycle model
                    tc_dict = self._test_cycle_to_dict(test_cycle, project_key)

                    # Check if the test cycle already exists
                    existing = session.query(TestCycle).filter_by(id=test_cycle.id).first()

                    if existing:
                        # Update existing test cycle
                        for key, value in tc_dict.items():
                            setattr(existing, key, value)
                    else:
                        # Create new test cycle
                        db_test_cycle = TestCycle(**tc_dict)
                        session.add(db_test_cycle)

                    # Handle related entities
                    self._handle_test_cycle_relations(session, test_cycle, project_key)

    def _test_cycle_to_dict(self, test_cycle: CycleInfoModel, project_key: str) -> Dict[str, Any]:
        """
        Convert a test cycle model to a dictionary for database storage.

        Args:
            test_cycle: Test cycle model
            project_key: Project key

        Returns:
            Dictionary representation of the test cycle
        """
        return {
            "id": test_cycle.id,
            "key": test_cycle.key,
            "name": test_cycle.name,
            "description": test_cycle.description,
            "status": test_cycle.status,
            "status_name": test_cycle.status_name,
            "folder_id": test_cycle.folder,
            "folder_name": test_cycle.folder_name,
            "owner": test_cycle.owner,
            "owner_name": test_cycle.owner_name,
            "created_on": test_cycle.created_on,
            "created_by": test_cycle.created_by,
            "updated_on": test_cycle.updated_on,
            "updated_by": test_cycle.updated_by,
            "project_key": project_key,
        }

    def _handle_test_cycle_relations(
        self, session: Session, test_cycle: CycleInfoModel, project_key: str
    ) -> None:
        """
        Handle relations for a test cycle.

        Args:
            session: Database session
            test_cycle: Test cycle model
            project_key: Project key
        """
        # This is a simplified implementation - in a real implementation
        # we would handle custom fields, links, and attachments
        pass

    @tracked_execution("batch_save_test_executions")
    def batch_save_test_executions(
        self, test_executions: List[ExecutionModel], project_key: str
    ) -> None:
        """
        Save multiple test executions in a single batch operation.

        Args:
            test_executions: List of test execution models
            project_key: Project key
        """
        if not test_executions:
            return

        # Process in smaller batches
        batch_size = 100

        for i in range(0, len(test_executions), batch_size):
            batch = test_executions[i : i + batch_size]
            self._save_test_execution_batch(batch, project_key)

    def _save_test_execution_batch(
        self, test_executions: List[ExecutionModel], project_key: str
    ) -> None:
        """
        Save a batch of test executions.

        Args:
            test_executions: Batch of test execution models
            project_key: Project key
        """
        with self.get_session() as session:
            with transaction_scope(session):
                for test_execution in test_executions:
                    # Convert to TestExecution model
                    te_dict = self._test_execution_to_dict(test_execution, project_key)

                    # Check if the test execution already exists
                    existing = session.query(TestExecution).filter_by(id=test_execution.id).first()

                    if existing:
                        # Update existing test execution
                        for key, value in te_dict.items():
                            setattr(existing, key, value)
                    else:
                        # Create new test execution
                        db_test_execution = TestExecution(**te_dict)
                        session.add(db_test_execution)

                    # Handle related entities
                    self._handle_test_execution_relations(session, test_execution, project_key)

    def _test_execution_to_dict(
        self, test_execution: ExecutionModel, project_key: str
    ) -> Dict[str, Any]:
        """
        Convert a test execution model to a dictionary for database storage.

        Args:
            test_execution: Test execution model
            project_key: Project key

        Returns:
            Dictionary representation of the test execution
        """
        # Handle camelCase to snake_case mapping for Pydantic model attributes
        test_case_key = getattr(test_execution, "testCaseKey", None) or getattr(
            test_execution, "test_case_key", None
        )
        cycle_id = getattr(test_execution, "cycleId", None) or getattr(
            test_execution, "cycle_id", None
        )
        environment_id = getattr(test_execution, "environment", None) or getattr(
            test_execution, "environment_id", None
        )

        return {
            "id": test_execution.id,
            "test_case_key": test_case_key,
            "cycle_id": cycle_id,
            "cycle_name": test_execution.cycle_name,
            "status": test_execution.status,
            "status_name": test_execution.status_name,
            "environment_id": environment_id,
            "environment_name": test_execution.environment_name,
            "executed_by": test_execution.executed_by,
            "executed_by_name": test_execution.executed_by_name,
            "executed_on": test_execution.executed_on,
            "created_on": test_execution.created_on,
            "created_by": test_execution.created_by,
            "updated_on": test_execution.updated_on,
            "updated_by": test_execution.updated_by,
            "actual_time": test_execution.actual_time,
            "comment": test_execution.comment,
            "project_key": project_key,
        }

    def _handle_test_execution_relations(
        self, session: Session, test_execution: ExecutionModel, project_key: str
    ) -> None:
        """
        Handle relations for a test execution.

        Args:
            session: Database session
            test_execution: Test execution model
            project_key: Project key
        """
        # This is a simplified implementation - in a real implementation
        # we would handle steps, custom fields, links, and attachments
        pass

    @tracked_execution("create_entity_batch_states")
    def create_entity_batch_states(
        self, project_key: str, entity_type: str, batch_count: int, items_per_batch: int
    ) -> List[EntityBatchState]:
        """
        Create multiple entity batch state records in a single operation.

        Args:
            project_key: Project key
            entity_type: Entity type
            batch_count: Number of batches
            items_per_batch: Number of items per batch

        Returns:
            List of created entity batch state records
        """
        batch_states = []

        with self.get_session() as session:
            with transaction_scope(session):
                for i in range(batch_count):
                    batch_state = EntityBatchState(
                        project_key=project_key,
                        entity_type=entity_type,
                        batch_number=i,
                        total_batches=batch_count,
                        items_count=items_per_batch,
                        status="not_started",
                        last_updated=datetime.now(),
                    )
                    session.add(batch_state)
                    batch_states.append(batch_state)

        return batch_states

    @tracked_execution("update_entity_batch_states")
    def update_entity_batch_states(
        self, batch_ids: List[int], status: str, processed_counts: Optional[List[int]] = None
    ) -> None:
        """
        Update multiple entity batch state records in a single operation.

        Args:
            batch_ids: List of batch IDs
            status: New status
            processed_counts: Optional list of processed counts
        """
        if not batch_ids:
            return

        now = datetime.now()

        with self.get_session() as session:
            with transaction_scope(session):
                for i, batch_id in enumerate(batch_ids):
                    batch = (
                        session.query(EntityBatchState)
                        .filter_by(id=batch_id)
                        .with_for_update()
                        .first()
                    )

                    if batch:
                        batch.status = status
                        batch.last_updated = now

                        if processed_counts and i < len(processed_counts):
                            batch.processed_count = processed_counts[i]

                        if status == "completed":
                            batch.completed_at = now

    @tracked_execution("get_statistics")
    def get_performance_statistics(self) -> Dict[str, Any]:
        """
        Get database performance statistics.

        Returns:
            Dictionary with performance statistics
        """
        stats = db_stats.get_stats()

        result = {
            "operations": stats,
            "cache": {
                "size": len(self._model_cache._cache),
            },
            "summary": {
                "total_operations": sum(s["count"] for s in stats.values()),
                "total_errors": sum(s["errors"] for s in stats.values()),
                "avg_operation_time": sum(s["total_time"] for s in stats.values())
                / sum(s["count"] for s in stats.values())
                if sum(s["count"] for s in stats.values()) > 0
                else 0,
            },
        }

        return result
