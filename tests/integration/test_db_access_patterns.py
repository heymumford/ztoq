"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Integration tests for database access patterns in ZTOQ.

These tests demonstrate and validate various database access pattern optimizations
that can be implemented to improve performance, including indexed queries,
batch loading, connection pooling, and more.
"""

import logging
import os
import shutil

# Import project modules
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import UTC, datetime

from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ztoq.core.db_manager import DatabaseConfig, SQLDatabaseManager
from ztoq.core.db_models import (
    EntityBatchState,
    TestCase,
    TestExecution,
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDatabaseAccessPatterns:
    """Integration tests for database access patterns and optimizations."""

    def setup(self):
        """Set up test resources."""
        # Create a temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_db_access.db")

        # Create database manager
        config = DatabaseConfig(db_type="sqlite", db_path=self.db_path)
        self.db_manager = SQLDatabaseManager(config)

        # Initialize the database
        self.db_manager.initialize_database()

        # Enable SQLite foreign keys
        with self.db_manager.get_session() as session:
            session.execute(text("PRAGMA foreign_keys = ON"))

        # Create test project
        self.test_project = ProjectModel(
            id="ACCESS-1",
            key="ACCESS",
            name="Access Pattern Test Project",
            description="A test project for database access pattern testing",
        )
        self.db_manager.save_project(self.test_project)

        # Create test data
        self.test_data = self.create_test_data()

        return self

    def teardown(self):
        """Tear down test resources."""
        # Clean up the temporary directory
        shutil.rmtree(self.temp_dir)

    def create_test_data(self):
        """Create test data for access pattern tests."""
        # Create folders
        folders = []
        for i in range(5):
            folder = FolderModel(
                id=f"folder-{i}",
                name=f"Folder {i}",
                folderType="TEST_CASE",
                projectKey=self.test_project.key,
            )
            self.db_manager.save_folder(folder, self.test_project.key)
            folders.append(folder)

        # Create test cases
        test_cases = []
        for i in range(50):
            folder_index = i % 5
            test_case = CaseModel(
                id=f"TC-{i}",
                key=f"ACCESS-TC-{i}",
                name=f"Test Case {i}",
                status="Draft",
                folder=folders[folder_index].id,
                folder_name=folders[folder_index].name,
                custom_fields=[
                    CustomFieldModel(
                        id=f"CF-{i}-1", name="Priority", type="dropdown", value="High",
                    ),
                    CustomFieldModel(
                        id=f"CF-{i}-2", name="Complexity", type="dropdown", value="Medium",
                    ),
                ],
                attachments=[],
                links=[],
                steps=[],
                scripts=[],
                versions=[],
            )
            self.db_manager.save_test_case(test_case, self.test_project.key)
            test_cases.append(test_case)

        # Create test cycles
        test_cycles = []
        for i in range(10):
            folder_index = i % 5
            test_cycle = CycleInfoModel(
                id=f"CYCLE-{i}",
                key=f"ACCESS-CYCLE-{i}",
                name=f"Test Cycle {i}",
                status="Active",
                folder=folders[folder_index].id,
                folder_name=folders[folder_index].name,
                projectKey=self.test_project.key,
                custom_fields=[],
                attachments=[],
                links=[],
            )
            self.db_manager.save_test_cycle(test_cycle, self.test_project.key)
            test_cycles.append(test_cycle)

        # Create test executions
        test_executions = []
        for i in range(100):
            case_index = i % 50
            cycle_index = i % 10
            test_execution = ExecutionModel(
                id=f"EXEC-{i}",
                testCaseKey=test_cases[case_index].key,
                cycleId=test_cycles[cycle_index].id,
                cycle_name=test_cycles[cycle_index].name,
                status="Passed" if i % 3 == 0 else "Failed" if i % 3 == 1 else "Blocked",
                steps=[],
                custom_fields=[],
                attachments=[],
                links=[],
                # Note: The Execution model doesn't seem to require projectKey
            )
            self.db_manager.save_test_execution(test_execution, self.test_project.key)
            test_executions.append(test_execution)

        return {
            "folders": folders,
            "test_cases": test_cases,
            "test_cycles": test_cycles,
            "test_executions": test_executions,
        }

    @contextmanager
    def measure_execution_time(self, operation_name):
        """Context manager to measure the execution time of a database operation."""
        start_time = time.time()
        yield
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Operation '{operation_name}' took {duration:.4f} seconds")
        return duration

    def test_indexed_query_performance(self):
        """Test the performance difference between indexed and non-indexed queries."""
        print("\n*** Testing indexed vs non-indexed query performance ***")

        # Query using indexed column (project_key)
        with self.measure_execution_time("Query with indexed column") as indexed_duration:
            with self.db_manager.get_session() as session:
                result = (
                    session.query(TestCase)
                    .filter(TestCase.project_key == self.test_project.key)
                    .all()
                )
                assert len(result) == 50, "Should retrieve all 50 test cases"

        # Query using a non-indexed field
        with self.measure_execution_time("Query with non-indexed column") as non_indexed_duration:
            with self.db_manager.get_session() as session:
                result = session.query(TestCase).filter(TestCase.status == "Draft").all()
                assert len(result) == 50, "Should retrieve all 50 test cases"

        # Log the difference (Note: This test is more illustrative in PostgreSQL;
        # SQLite's performance differences are less pronounced with small datasets)
        if indexed_duration and non_indexed_duration:
            ratio = non_indexed_duration / indexed_duration
            print(f"Performance difference: {ratio:.2f}x slower without index")
        else:
            print("Could not calculate performance difference - timing data unavailable")

        return True

    def test_batch_loading_performance(self):
        """Test the performance of batch loading vs individual inserts."""
        print("\n*** Testing batch loading performance ***")

        # Generate a new set of test cases
        new_test_cases = []
        for i in range(100, 200):
            test_case = CaseModel(
                id=f"TC-BATCH-{i}",
                key=f"ACCESS-BATCH-{i}",
                name=f"Batch Test Case {i}",
                status="Draft",
                custom_fields=[],
                attachments=[],
                links=[],
                steps=[],
                scripts=[],
                versions=[],
            )
            new_test_cases.append(test_case)

        # Method 1: Individual inserts with separate sessions
        sample_cases_individual = new_test_cases[:20]  # Take a subset for comparison
        with self.measure_execution_time(
            "Individual inserts with separate sessions",
        ) as individual_duration:
            for test_case in sample_cases_individual:
                self.db_manager.save_test_case(test_case, self.test_project.key)

        # Method 2: Batch insert
        sample_cases_batch = new_test_cases[20:40]  # Different subset
        with self.measure_execution_time("Batch insert") as batch_duration:
            with self.db_manager.get_session() as session:
                for test_case in sample_cases_batch:
                    # Create TestCase objects
                    db_test_case = TestCase(
                        id=test_case.id,
                        key=test_case.key,
                        name=test_case.name,
                        status=test_case.status,
                        project_key=self.test_project.key,
                    )
                    session.add(db_test_case)
                # Session commits at the end of the context manager

        # Compare results
        if individual_duration and batch_duration:
            ratio = individual_duration / batch_duration
            print(f"Performance improvement: {ratio:.2f}x faster with batch insert")
        else:
            print("Could not calculate performance improvement - timing data unavailable")

        # Verify both methods inserted the correct number of records
        with self.db_manager.get_session() as session:
            # Ensure the LIKE patterns match our test case IDs
            count_individual = (
                session.query(TestCase)
                .filter(TestCase.id.between("TC-BATCH-100", "TC-BATCH-119"))
                .count()
            )
            count_batch = (
                session.query(TestCase)
                .filter(TestCase.id.between("TC-BATCH-120", "TC-BATCH-139"))
                .count()
            )

            assert count_individual == 20, "Individual inserts should have created 20 records"
            assert count_batch == 20, "Batch insert should have created 20 records"

        return True

    def test_bulk_operations(self):
        """Test the performance of bulk insert and update operations."""
        print("\n*** Testing bulk operations performance ***")

        # Generate data for bulk operations
        num_records = 100
        data_to_insert = []

        for i in range(num_records):
            batch_state = {
                "project_key": self.test_project.key,
                "entity_type": "test_case",
                "batch_number": i,
                "total_batches": num_records,
                "items_count": 10,
                "processed_count": 0,
                "status": "not_started",
                "last_updated": datetime.now(UTC),
            }
            data_to_insert.append(batch_state)

        # Method 1: Individual inserts
        with self.measure_execution_time("Individual inserts") as individual_duration:
            for i in range(20):  # Insert 20 records individually
                self.db_manager.create_entity_batch_state(
                    project_key=self.test_project.key,
                    entity_type="test_case_individual",
                    batch_number=i,
                    total_batches=20,
                    items_count=10,
                    status="not_started",
                )

        # Method 2: Bulk insert with SQLAlchemy execute
        with self.measure_execution_time("Bulk insert") as bulk_duration:
            # Using SQLAlchemy Core for bulk insert
            with self.db_manager.get_session() as session:
                connection = session.connection()
                table = EntityBatchState.__table__

                # Prepare data for bulk insert
                bulk_data = []
                for i in range(20, 40):  # Insert next 20 records in bulk
                    bulk_data.append(
                        {
                            "project_key": self.test_project.key,
                            "entity_type": "test_case_bulk",
                            "batch_number": i,
                            "total_batches": 20,
                            "items_count": 10,
                            "status": "not_started",
                            "last_updated": datetime.now(UTC),
                        },
                    )

                # Execute bulk insert using the insert() method
                from sqlalchemy.sql import insert

                connection.execute(insert(table), bulk_data)

        # Compare results
        if individual_duration and bulk_duration:
            ratio = individual_duration / bulk_duration
            print(f"Bulk insert performance: {ratio:.2f}x faster than individual inserts")
        else:
            print("Could not calculate performance improvement - timing data unavailable")

        # Verify both methods inserted the correct number of records
        with self.db_manager.get_session() as session:
            count_individual = (
                session.query(EntityBatchState)
                .filter_by(entity_type="test_case_individual")
                .count()
            )
            count_bulk = (
                session.query(EntityBatchState).filter_by(entity_type="test_case_bulk").count()
            )

            assert count_individual == 20, "Individual inserts should have created 20 records"
            assert count_bulk == 20, "Bulk insert should have created 20 records"

        return True

    def test_query_with_pandas(self):
        """Test using pandas for optimized data processing."""
        print("\n*** Testing pandas data processing performance ***")

        # Method 1: Standard SQLAlchemy ORM query and processing
        with self.measure_execution_time("Standard ORM query and processing") as orm_duration:
            with self.db_manager.get_session() as session:
                executions = (
                    session.query(TestExecution)
                    .filter(TestExecution.project_key == self.test_project.key)
                    .all()
                )

                # Process the data - count executions by status
                status_counts = {}
                for execution in executions:
                    if execution.status not in status_counts:
                        status_counts[execution.status] = 0
                    status_counts[execution.status] += 1

            assert len(status_counts) > 0, "Should have counted executions by status"

        # Method 2: Using pandas for data processing
        with self.measure_execution_time("Pandas data processing") as pandas_duration:
            # Query directly to dataframe using the helper method
            df = self.db_manager.query_to_dataframe(
                "SELECT status, COUNT(*) as count FROM test_executions "
                "WHERE project_key = :project_key GROUP BY status",
                {"project_key": self.test_project.key},
            )

            # Convert to dictionary
            status_counts_pandas = dict(zip(df["status"], df["count"], strict=False))

            assert len(status_counts_pandas) > 0, "Should have counted executions by status"

        # Compare results
        if orm_duration and pandas_duration:
            ratio = orm_duration / pandas_duration
            print(f"Pandas processing performance: {ratio:.2f}x faster than ORM processing")
        else:
            print("Could not calculate performance improvement - timing data unavailable")

        return True

    def test_prepared_statements(self):
        """Test the performance benefits of prepared statements."""
        print("\n*** Testing prepared statements vs. multiple queries ***")

        # Create common test data
        test_case_ids = [f"TC-PREPARED-{i}" for i in range(100)]

        # Method 1: Multiple separate queries
        with self.measure_execution_time("Multiple separate queries") as separate_duration:
            with self.db_manager.get_session() as session:
                for i in range(20):  # Only do 20 to save time
                    result = session.query(TestCase).filter(TestCase.id == test_case_ids[i]).first()
                    # Result might be None since we haven't created these records

        # Method 2: Using IN clause (similar to a prepared statement)
        with self.measure_execution_time("IN clause query") as in_clause_duration:
            with self.db_manager.get_session() as session:
                result = session.query(TestCase).filter(TestCase.id.in_(test_case_ids[:20])).all()
                # This should return an empty list

        # Compare results
        if separate_duration and in_clause_duration:
            ratio = separate_duration / in_clause_duration
            print(f"IN clause performance: {ratio:.2f}x faster than separate queries")
        else:
            print("Could not calculate performance improvement - timing data unavailable")

        return True

    def run_all_tests(self):
        """Run all the database access pattern tests."""
        print("\n=== Running Database Access Pattern Tests ===\n")

        try:
            tests = [
                self.test_indexed_query_performance,
                self.test_batch_loading_performance,
                self.test_bulk_operations,
                self.test_query_with_pandas,
                self.test_prepared_statements,
            ]

            results = []
            for test in tests:
                try:
                    result = test()
                    results.append((test.__name__, result))
                except Exception as e:
                    logger.error(f"Error in test {test.__name__}: {e}")
                    results.append((test.__name__, False))

            # Print summary
            print("\n=== Test Results Summary ===")
            for name, result in results:
                print(f"{name}: {'PASS' if result else 'FAIL'}")

            return all(result for _, result in results)

        finally:
            self.teardown()


if __name__ == "__main__":
    test = TestDatabaseAccessPatterns().setup()
    success = test.run_all_tests()
    print(f"\n{'All tests passed successfully!' if success else 'Some tests failed!'}")
    sys.exit(0 if success else 1)
