"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Performance tests for database operations.

This module contains performance tests for database operations, including
CRUD operations, batch processing, and transaction handling.
"""

import logging
import os
import random
import time
from typing import List, Optional

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from ztoq.core.db_models import Base, Project, RecommendationHistory, TestCase
from ztoq.database_factory import get_database_manager
from ztoq.database_manager import DatabaseManager
from tests.performance.base import PerformanceTest
from tests.fixtures.model_factories import ProjectFactory, TestCaseFactory


logger = logging.getLogger(__name__)


class DatabasePerformanceTest(PerformanceTest):
    """Base class for database performance tests."""

    def __init__(
        self,
        name: str,
        db_url: Optional[str] = None,
        output_dir: Optional[str] = None,
    ):
        """Initialize database performance test.

        Args:
            name: Name of the performance test
            db_url: Database URL (default: in-memory SQLite)
            output_dir: Output directory for test results
        """
        super().__init__(name=name, output_dir=output_dir)
        self.db_url = db_url or os.environ.get(
            "ZTOQ_TEST_DB_URL", "sqlite:///:memory:"
        )
        self.db_manager = None
        self.engine = None
        self.result.metadata["db_url"] = self.db_url

    def setup(self) -> None:
        """Set up database connection and schema."""
        super().setup()

        # Create database manager
        self.db_manager = get_database_manager(self.db_url)

        # Get engine and create tables
        self.engine = self.db_manager._engine
        Base.metadata.create_all(self.engine)

        # Log database setup
        logger.info(f"Database setup complete: {self.db_url}")

    def teardown(self) -> None:
        """Clean up database resources."""
        if self.engine and "sqlite" in self.db_url:
            # Drop all tables for SQLite
            Base.metadata.drop_all(self.engine)

        # Close connections
        if self.db_manager:
            self.db_manager.close()

        super().teardown()

    def _create_test_projects(self, count: int) -> List[Project]:
        """Create test project records.

        Args:
            count: Number of projects to create

        Returns:
            List of created projects
        """
        projects = []

        with Session(self.engine) as session:
            for i in range(count):
                project = ProjectFactory.build()
                session.add(project)
                projects.append(project)
            session.commit()

        return projects

    def _create_test_cases(self, count: int, project_ids: List[str]) -> List[TestCase]:
        """Create test case records.

        Args:
            count: Number of test cases to create
            project_ids: List of project IDs to assign test cases to

        Returns:
            List of created test cases
        """
        test_cases = []

        with Session(self.engine) as session:
            for i in range(count):
                project_id = random.choice(project_ids)
                test_case = TestCaseFactory.build(project_id=project_id)
                session.add(test_case)
                test_cases.append(test_case)
            session.commit()

        return test_cases


class CrudPerformanceTest(DatabasePerformanceTest):
    """Performance tests for basic CRUD operations."""

    def __init__(
        self,
        db_url: Optional[str] = None,
        output_dir: Optional[str] = None,
        num_projects: int = 10,
        num_test_cases: int = 1000,
    ):
        """Initialize CRUD performance test.

        Args:
            db_url: Database URL
            output_dir: Output directory for test results
            num_projects: Number of projects to create
            num_test_cases: Number of test cases to create
        """
        super().__init__(name="crud_performance", db_url=db_url, output_dir=output_dir)
        self.num_projects = num_projects
        self.num_test_cases = num_test_cases
        self.projects = []
        self.test_cases = []

    def _run_test(self) -> None:
        """Run CRUD performance tests."""
        # Create test data
        self._test_create()

        # Run read tests
        self._test_read()

        # Run update tests
        self._test_update()

        # Run delete tests
        self._test_delete()

    @PerformanceTest.measure(operation="create_projects", dataset_size=None)
    def _test_create_projects(self) -> None:
        """Test performance of creating projects."""
        self.projects = self._create_test_projects(self.num_projects)

    @PerformanceTest.measure(operation="create_test_cases", dataset_size=None)
    def _test_create_test_cases(self) -> None:
        """Test performance of creating test cases."""
        project_ids = [p.project_id for p in self.projects]
        self.test_cases = self._create_test_cases(self.num_test_cases, project_ids)

    def _test_create(self) -> None:
        """Test performance of create operations."""
        self._test_create_projects()
        self._test_create_test_cases()

    @PerformanceTest.measure(operation="read_projects_all", dataset_size=None)
    def _test_read_projects_all(self) -> None:
        """Test performance of reading all projects."""
        with Session(self.engine) as session:
            projects = session.query(Project).all()
            return projects

    @PerformanceTest.measure(operation="read_test_cases_all", dataset_size=None)
    def _test_read_test_cases_all(self) -> None:
        """Test performance of reading all test cases."""
        with Session(self.engine) as session:
            test_cases = session.query(TestCase).all()
            return test_cases

    @PerformanceTest.measure(operation="read_test_cases_by_project", dataset_size=None)
    def _test_read_test_cases_by_project(self) -> None:
        """Test performance of reading test cases by project."""
        project_id = self.projects[0].project_id
        with Session(self.engine) as session:
            test_cases = session.query(TestCase).filter(
                TestCase.project_id == project_id
            ).all()
            return test_cases

    @PerformanceTest.measure(operation="read_test_case_by_id", dataset_size=None)
    def _test_read_test_case_by_id(self) -> None:
        """Test performance of reading a test case by ID."""
        test_case_id = self.test_cases[0].test_case_id
        with Session(self.engine) as session:
            test_case = session.query(TestCase).filter(
                TestCase.test_case_id == test_case_id
            ).first()
            return test_case

    def _test_read(self) -> None:
        """Test performance of read operations."""
        self._test_read_projects_all()
        self._test_read_test_cases_all()
        self._test_read_test_cases_by_project()
        self._test_read_test_case_by_id()

    @PerformanceTest.measure(operation="update_test_case", dataset_size=None)
    def _test_update_test_case(self) -> None:
        """Test performance of updating a test case."""
        test_case_id = self.test_cases[0].test_case_id
        with Session(self.engine) as session:
            test_case = session.query(TestCase).filter(
                TestCase.test_case_id == test_case_id
            ).first()
            test_case.name = f"Updated {test_case.name}"
            test_case.objective = f"Updated objective for {test_case.name}"
            session.commit()

    @PerformanceTest.measure(operation="update_test_cases_batch", dataset_size=None)
    def _test_update_test_cases_batch(self) -> None:
        """Test performance of updating test cases in batch."""
        batch_size = min(100, len(self.test_cases))
        test_case_ids = [tc.test_case_id for tc in self.test_cases[:batch_size]]

        with Session(self.engine) as session:
            session.query(TestCase).filter(
                TestCase.test_case_id.in_(test_case_ids)
            ).update(
                {TestCase.status: "Updated"},
                synchronize_session=False
            )
            session.commit()

    def _test_update(self) -> None:
        """Test performance of update operations."""
        self._test_update_test_case()
        self._test_update_test_cases_batch()

    @PerformanceTest.measure(operation="delete_test_case", dataset_size=None)
    def _test_delete_test_case(self) -> None:
        """Test performance of deleting a test case."""
        test_case_id = self.test_cases[-1].test_case_id
        with Session(self.engine) as session:
            test_case = session.query(TestCase).filter(
                TestCase.test_case_id == test_case_id
            ).first()
            session.delete(test_case)
            session.commit()

    @PerformanceTest.measure(operation="delete_test_cases_batch", dataset_size=None)
    def _test_delete_test_cases_batch(self) -> None:
        """Test performance of deleting test cases in batch."""
        batch_size = min(100, len(self.test_cases) - 1)
        test_case_ids = [tc.test_case_id for tc in self.test_cases[-batch_size-1:-1]]

        with Session(self.engine) as session:
            session.query(TestCase).filter(
                TestCase.test_case_id.in_(test_case_ids)
            ).delete(synchronize_session=False)
            session.commit()

    def _test_delete(self) -> None:
        """Test performance of delete operations."""
        self._test_delete_test_case()
        self._test_delete_test_cases_batch()


class BatchPerformanceTest(DatabasePerformanceTest):
    """Performance tests for batch operations."""

    def __init__(
        self,
        db_url: Optional[str] = None,
        output_dir: Optional[str] = None,
        num_projects: int = 5,
        num_records: int = 5000,
        batch_sizes: Optional[List[int]] = None,
    ):
        """Initialize batch operation performance test.

        Args:
            db_url: Database URL
            output_dir: Output directory for test results
            num_projects: Number of projects to create
            num_records: Total number of records to create
            batch_sizes: List of batch sizes to test
        """
        super().__init__(name="batch_performance", db_url=db_url, output_dir=output_dir)
        self.num_projects = num_projects
        self.num_records = num_records
        self.batch_sizes = batch_sizes or [1, 10, 50, 100, 500, 1000]
        self.projects = []

    def _run_test(self) -> None:
        """Run batch performance tests."""
        # Create projects
        self.projects = self._create_test_projects(self.num_projects)
        project_ids = [p.project_id for p in self.projects]

        # Test batch inserts with different batch sizes
        for batch_size in self.batch_sizes:
            self._test_batch_insert(batch_size, project_ids)

        # Test batch updates with different batch sizes
        for batch_size in self.batch_sizes:
            self._test_batch_update(batch_size)

        # Test batch deletes with different batch sizes
        for batch_size in self.batch_sizes:
            self._test_batch_delete(batch_size)

    @PerformanceTest.measure(operation="batch_insert")
    def _test_batch_insert(self, batch_size: int, project_ids: List[str]) -> None:
        """Test performance of batch insert operations.

        Args:
            batch_size: Number of records per batch
            project_ids: List of project IDs to use
        """
        self.result.metadata["batch_size"] = batch_size
        remaining = self.num_records

        with Session(self.engine) as session:
            while remaining > 0:
                batch_count = min(batch_size, remaining)
                records = []

                for i in range(batch_count):
                    record = RecommendationHistory(
                        project_key=random.choice(project_ids),
                        recommendation_id=f"REC-{random.randint(1, 1000)}",
                        priority=random.choice(["High", "Medium", "Low"]),
                        category=random.choice(["Performance", "Security", "Usability"]),
                        issue=f"Test issue {i} for batch {remaining // batch_size}",
                        action=f"Test action {i} for batch {remaining // batch_size}",
                        status=random.choice(["open", "closed", "in_progress"]),
                        impact_score=random.uniform(0.0, 10.0),
                        migration_phase=random.choice(["extract", "transform", "load"]),
                        entity_type=random.choice(["TestCase", "TestCycle", "TestExecution"]),
                    )
                    records.append(record)

                session.add_all(records)
                session.commit()
                remaining -= batch_count

    @PerformanceTest.measure(operation="batch_update")
    def _test_batch_update(self, batch_size: int) -> None:
        """Test performance of batch update operations.

        Args:
            batch_size: Number of records per batch
        """
        self.result.metadata["batch_size"] = batch_size

        with Session(self.engine) as session:
            # Get total count
            total = session.query(sa.func.count(RecommendationHistory.id)).scalar()

            # Process in batches
            for offset in range(0, total, batch_size):
                # Get batch of IDs
                ids = [
                    r[0] for r in session.query(RecommendationHistory.id)
                    .order_by(RecommendationHistory.id)
                    .offset(offset)
                    .limit(batch_size)
                    .all()
                ]

                # Update batch
                session.query(RecommendationHistory).filter(
                    RecommendationHistory.id.in_(ids)
                ).update(
                    {RecommendationHistory.status: "updated"},
                    synchronize_session=False
                )
                session.commit()

    @PerformanceTest.measure(operation="batch_delete")
    def _test_batch_delete(self, batch_size: int) -> None:
        """Test performance of batch delete operations.

        Args:
            batch_size: Number of records per batch
        """
        self.result.metadata["batch_size"] = batch_size

        with Session(self.engine) as session:
            # Process in batches until all records are deleted
            while True:
                # Get batch of IDs
                ids = [
                    r[0] for r in session.query(RecommendationHistory.id)
                    .order_by(RecommendationHistory.id)
                    .limit(batch_size)
                    .all()
                ]

                if not ids:
                    break

                # Delete batch
                session.query(RecommendationHistory).filter(
                    RecommendationHistory.id.in_(ids)
                ).delete(synchronize_session=False)
                session.commit()


@pytest.mark.performance
def test_crud_performance():
    """Run CRUD performance test."""
    test = CrudPerformanceTest()
    test.run()


@pytest.mark.performance
def test_batch_performance():
    """Run batch performance test."""
    test = BatchPerformanceTest()
    test.run()


if __name__ == "__main__":
    # Run the tests directly when executed as a script
    logging.basicConfig(level=logging.INFO)

    print("Running CRUD performance test...")
    crud_test = CrudPerformanceTest()
    crud_result = crud_test.run()

    print("\nRunning batch performance test...")
    batch_test = BatchPerformanceTest()
    batch_result = batch_test.run()

    print("\nPerformance tests completed. Results in:", batch_test.output_path)
