"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import concurrent.futures
import logging
import os
import shutil
import tempfile
import time

import pytest
from sqlalchemy.exc import IntegrityError

from ztoq.core.db_manager import DatabaseConfig, SQLDatabaseManager
from ztoq.core.db_models import EntityBatchState, Folder, TestCase
from ztoq.models import (
    Case as CaseModel,
    CustomField as CustomFieldModel,
    CycleInfo as CycleInfoModel,
    Execution as ExecutionModel,
    Folder as FolderModel,
    Project as ProjectModel,
)

# Setup test logger
logger = logging.getLogger(__name__)


@pytest.mark.integration
class TestDatabaseParallelOperations:
    """Integration tests for parallel database operations."""

    @pytest.fixture(scope="class")
    def temp_db_path(self):
        """Create a temporary directory for the test database."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_parallel.db")
        yield db_path
        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create a database manager for testing."""
        config = DatabaseConfig(db_type="sqlite", db_path=temp_db_path)
        manager = SQLDatabaseManager(config)
        # Initialize the database with current models
        manager.initialize_database()

        # Enable SQLite foreign keys (important for transaction tests)
        with manager.get_session() as session:
            session.execute("PRAGMA foreign_keys = ON")

        return manager

    @pytest.fixture
    def test_project(self, db_manager):
        """Create a test project in the database."""
        project = ProjectModel(
            id="PARALLEL-1",
            key="PARALLEL",
            name="Parallel Test Project",
            description="A test project for parallel operations",
        )
        db_manager.save_project(project)
        return project

    def test_concurrent_reads(self, db_manager, test_project):
        """Test concurrent read operations from multiple threads."""
        # First, add some test data
        for i in range(10):
            folder = FolderModel(id=f"folder-{i}", name=f"Folder {i}", folderType="TEST_CASE")
            db_manager.save_folder(folder, test_project.key)

        # Function to read folders in each thread
        def read_folders():
            with db_manager.get_session() as session:
                folders = session.query(Folder).filter_by(project_key=test_project.key).all()
                time.sleep(0.1)  # Simulate some processing time
                return len(folders)

        # Execute concurrent reads
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(read_folders) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All threads should read the same number of folders
        assert all(count == 10 for count in results), "All threads should read 10 folders"

    def test_concurrent_writes(self, db_manager, test_project):
        """Test concurrent write operations from multiple threads."""

        # Function to create a test case in each thread
        def create_test_case(index):
            try:
                test_case = CaseModel(
                    id=f"TC-{index}",
                    key=f"PARALLEL-TC-{index}",
                    name=f"Test Case {index}",
                    status="Draft",
                    custom_fields=[],
                    attachments=[],
                    links=[],
                    steps=[],
                    scripts=[],
                    versions=[],
                )
                db_manager.save_test_case(test_case, test_project.key)
                return True
            except Exception as e:
                logger.error(f"Error creating test case {index}: {e}")
                return False

        # Execute concurrent writes
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_test_case, i) for i in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Verify all test cases were created
        assert all(results), "All test cases should be created successfully"

        with db_manager.get_session() as session:
            test_cases = session.query(TestCase).filter_by(project_key=test_project.key).all()
            assert len(test_cases) == 20, "20 test cases should be created"

    def test_concurrent_updates(self, db_manager, test_project):
        """Test concurrent update operations from multiple threads."""
        # Create a test case to update
        test_case = CaseModel(
            id="UPDATE-TC",
            key="PARALLEL-UPDATE",
            name="Concurrent Update Test",
            status="Draft",
            custom_fields=[],
            attachments=[],
            links=[],
            steps=[],
            scripts=[],
            versions=[],
        )
        db_manager.save_test_case(test_case, test_project.key)

        # Function to update the test case in each thread
        def update_test_case(new_name):
            try:
                # First read the current test case
                with db_manager.get_session() as session:
                    session.query(TestCase).filter_by(key="PARALLEL-UPDATE").first()
                    time.sleep(0.1)  # Simulate processing time

                # Update with new values
                updated_case = CaseModel(
                    id="UPDATE-TC",
                    key="PARALLEL-UPDATE",
                    name=new_name,
                    status="Active",
                    description=f"Updated by thread at {time.time()}",
                    custom_fields=[],
                    attachments=[],
                    links=[],
                    steps=[],
                    scripts=[],
                    versions=[],
                )
                db_manager.save_test_case(updated_case, test_project.key)
                return True
            except Exception as e:
                logger.error(f"Error updating test case: {e}")
                return False

        # Execute concurrent updates
        update_names = [f"Updated Name {i}" for i in range(5)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(update_test_case, name) for name in update_names]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Verify all updates were successful
        assert all(results), "All updates should be successful"

        # Verify the test case was updated
        with db_manager.get_session() as session:
            case = session.query(TestCase).filter_by(key="PARALLEL-UPDATE").first()
            assert case is not None, "Test case should still exist"
            assert case.status == "Active", "Status should be updated"
            assert case.name in update_names, "Name should be one of the updates"

    def test_concurrent_mixed_operations(self, db_manager, test_project):
        """Test mixed read/write/update operations from multiple threads."""
        # Prepare some test data
        for i in range(5):
            test_case = CaseModel(
                id=f"MIXED-{i}",
                key=f"PARALLEL-MIXED-{i}",
                name=f"Mixed Test {i}",
                status="Draft",
                custom_fields=[],
                attachments=[],
                links=[],
                steps=[],
                scripts=[],
                versions=[],
            )
            db_manager.save_test_case(test_case, test_project.key)

        # Function to read test cases
        def read_test_cases():
            with db_manager.get_session() as session:
                cases = session.query(TestCase).filter_by(project_key=test_project.key).all()
                time.sleep(0.05)  # Simulate processing time
                return len(cases)

        # Function to create a new test case
        def create_test_case(index):
            try:
                test_case = CaseModel(
                    id=f"MIXED-NEW-{index}",
                    key=f"PARALLEL-MIXED-NEW-{index}",
                    name=f"New Mixed Test {index}",
                    status="Draft",
                    custom_fields=[],
                    attachments=[],
                    links=[],
                    steps=[],
                    scripts=[],
                    versions=[],
                )
                db_manager.save_test_case(test_case, test_project.key)
                return "created"
            except Exception as e:
                logger.error(f"Error creating test case: {e}")
                return f"create_error: {e!s}"

        # Function to update an existing test case
        def update_test_case(index):
            try:
                case_key = f"PARALLEL-MIXED-{index % 5}"  # Update one of the existing cases
                with db_manager.get_session() as session:
                    case = session.query(TestCase).filter_by(key=case_key).first()
                    if not case:
                        return f"not_found: {case_key}"

                updated_case = CaseModel(
                    id=case.id,
                    key=case_key,
                    name=f"Updated Mixed Test {index}",
                    status="Active",
                    description=f"Updated by thread {index} at {time.time()}",
                    custom_fields=[],
                    attachments=[],
                    links=[],
                    steps=[],
                    scripts=[],
                    versions=[],
                )
                db_manager.save_test_case(updated_case, test_project.key)
                return "updated"
            except Exception as e:
                logger.error(f"Error updating test case: {e}")
                return f"update_error: {e!s}"

        # Function to delete a test case
        def delete_test_case(index):
            try:
                with db_manager.get_session() as session:
                    case_key = f"PARALLEL-MIXED-{index % 5}"
                    case = session.query(TestCase).filter_by(key=case_key).first()
                    if not case:
                        return f"not_found: {case_key}"

                    session.delete(case)
                    session.commit()
                    return "deleted"
            except Exception as e:
                logger.error(f"Error deleting test case: {e}")
                return f"delete_error: {e!s}"

        # Define the operations (10 reads, 5 creates, 5 updates, 3 deletes)
        operations = []
        for i in range(10):
            operations.append(("read", i))
        for i in range(5):
            operations.append(("create", i))
        for i in range(5):
            operations.append(("update", i))
        for i in range(3):
            operations.append(("delete", i))

        # Execute mixed operations
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []

            for op_type, index in operations:
                if op_type == "read":
                    futures.append((op_type, executor.submit(read_test_cases)))
                elif op_type == "create":
                    futures.append((op_type, executor.submit(create_test_case, index)))
                elif op_type == "update":
                    futures.append((op_type, executor.submit(update_test_case, index)))
                elif op_type == "delete":
                    futures.append((op_type, executor.submit(delete_test_case, index)))

            # Collect results
            for op_type, future in futures:
                if op_type not in results:
                    results[op_type] = []
                results[op_type].append(future.result())

        # Verify results
        logger.info(f"Mixed operation results: {results}")

        # Check that reads returned data
        assert all(
            isinstance(count, int) for count in results.get("read", [])
        ), "Read operations should return counts"

        # Check that creates were successful
        assert (
            results.get("create", []).count("created") > 0
        ), "Some create operations should succeed"

        # Check that updates were successful or returned not_found (if the item was deleted)
        assert any(
            r == "updated" or r.startswith("not_found") for r in results.get("update", [])
        ), "Update operations should either succeed or not find the item"

        # Check that deletes were successful or returned not_found
        assert any(
            r == "deleted" or r.startswith("not_found") for r in results.get("delete", [])
        ), "Delete operations should either succeed or not find the item"

        # Verify final state
        with db_manager.get_session() as session:
            final_count = session.query(TestCase).filter_by(project_key=test_project.key).count()
            logger.info(f"Final test case count: {final_count}")
            # We can't assert exact count due to race conditions, but we can check it's reasonable
            assert final_count >= 5, "Should have at least 5 test cases"

    def test_concurrent_batch_operations(self, db_manager, test_project):
        """Test concurrent batch operations with entity batch state tracking."""
        # Create batch state records
        for i in range(5):
            db_manager.create_entity_batch_state(
                project_key=test_project.key,
                entity_type="test_case",
                batch_number=i,
                total_batches=5,
                items_count=20,
                status="not_started",
            )

        # Function to process a batch
        def process_batch(batch_number):
            try:
                # Update batch to in_progress
                db_manager.update_entity_batch_state(
                    project_key=test_project.key,
                    entity_type="test_case",
                    batch_number=batch_number,
                    status="in_progress",
                )

                # Create test cases for this batch
                for j in range(20):
                    case_id = f"BATCH-{batch_number}-{j}"
                    test_case = CaseModel(
                        id=case_id,
                        key=f"PARALLEL-BATCH-{batch_number}-{j}",
                        name=f"Batch {batch_number} Test Case {j}",
                        status="Draft",
                        custom_fields=[],
                        attachments=[],
                        links=[],
                        steps=[],
                        scripts=[],
                        versions=[],
                    )
                    db_manager.save_test_case(test_case, test_project.key)

                    # Update processed count
                    db_manager.update_entity_batch_state(
                        project_key=test_project.key,
                        entity_type="test_case",
                        batch_number=batch_number,
                        processed_count=j + 1,
                    )

                    # Simulate some work
                    time.sleep(0.01)

                # Update batch to completed
                db_manager.update_entity_batch_state(
                    project_key=test_project.key,
                    entity_type="test_case",
                    batch_number=batch_number,
                    status="completed",
                )

                return batch_number, True
            except Exception as e:
                logger.error(f"Error processing batch {batch_number}: {e}")

                # Update batch to failed
                db_manager.update_entity_batch_state(
                    project_key=test_project.key,
                    entity_type="test_case",
                    batch_number=batch_number,
                    status="failed",
                    error_message=str(e),
                )

                return batch_number, False

        # Execute concurrent batch processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_batch, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Verify all batches were processed
        for batch_number, success in results:
            assert success, f"Batch {batch_number} should be processed successfully"

        # Verify batch states
        with db_manager.get_session() as session:
            for i in range(5):
                batch = (
                    session.query(EntityBatchState)
                    .filter_by(
                        project_key=test_project.key, entity_type="test_case", batch_number=i,
                    )
                    .first()
                )

                assert batch is not None, f"Batch {i} state should exist"
                assert batch.status == "completed", f"Batch {i} should be completed"
                assert batch.processed_count == 20, f"Batch {i} should have processed 20 items"
                assert batch.completed_at is not None, f"Batch {i} should have completion time"

        # Verify the created test cases
        with db_manager.get_session() as session:
            test_cases = session.query(TestCase).filter_by(project_key=test_project.key).all()
            assert len(test_cases) == 100, "100 test cases should be created (5 batches × 20 cases)"

    def test_parallel_transaction_isolation(self, db_manager, test_project):
        """Test transaction isolation levels in parallel operations."""

        # Function to update a test case with a transaction
        def update_with_transaction(case_id, new_status, sleep_time):
            try:
                with db_manager.get_session() as session:
                    # Read the current case
                    case = session.query(TestCase).filter_by(id=case_id).first()
                    if not case:
                        case = TestCase(
                            id=case_id,
                            key=f"TX-{case_id}",
                            name=f"Transaction Test {case_id}",
                            status="Draft",
                            project_key=test_project.key,
                        )
                        session.add(case)

                    # Sleep to simulate work and increase chance of concurrent access
                    time.sleep(sleep_time)

                    # Update the status
                    old_status = case.status
                    case.status = new_status

                    # Commit is handled by the context manager
                    return case_id, old_status, new_status, True
            except Exception as e:
                logger.error(f"Error in transaction {case_id}: {e}")
                return case_id, None, new_status, False

        # Create a test case first
        case_id = "TX-TEST-1"
        test_case = CaseModel(
            id=case_id,
            key="PARALLEL-TX-1",
            name="Transaction Test Case",
            status="Draft",
            custom_fields=[],
            attachments=[],
            links=[],
            steps=[],
            scripts=[],
            versions=[],
        )
        db_manager.save_test_case(test_case, test_project.key)

        # Execute parallel transactions that update the same test case
        statuses = ["In Progress", "Ready", "Blocked", "Active", "Completed"]
        sleep_times = [0.2, 0.1, 0.15, 0.05, 0.25]  # Different sleep times to create interleaving

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(update_with_transaction, case_id, status, sleep_time)
                for status, sleep_time in zip(statuses, sleep_times, strict=False)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Check that all transactions completed successfully
        for case_id, _old_status, new_status, success in results:
            assert success, f"Transaction to set status to {new_status} should succeed"

        # Verify the final state
        with db_manager.get_session() as session:
            case = session.query(TestCase).filter_by(id=case_id).first()
            assert case is not None, "Test case should exist"

            # The final status should be one of the updates, based on which transaction committed last
            assert (
                case.status in statuses
            ), f"Final status should be one of {statuses}, got {case.status}"

            # Log the results for analysis
            logger.info(f"Transaction results: {results}")
            logger.info(f"Final test case status: {case.status}")

    def test_concurrent_integrity_constraints(self, db_manager, test_project):
        """Test concurrent operations with integrity constraints."""

        # Function to create a test case with the same key
        def create_duplicate_case(index):
            try:
                test_case = CaseModel(
                    id=f"DUP-{index}",
                    key="PARALLEL-DUPLICATE",  # Same key for all - should cause constraint violation
                    name=f"Duplicate Test {index}",
                    status="Draft",
                    custom_fields=[],
                    attachments=[],
                    links=[],
                    steps=[],
                    scripts=[],
                    versions=[],
                )
                db_manager.save_test_case(test_case, test_project.key)
                return index, True
            except IntegrityError as e:
                logger.info(f"Expected integrity error for index {index}: {e}")
                return index, False
            except Exception as e:
                logger.error(f"Unexpected error for index {index}: {e}")
                return index, False

        # Execute concurrent operations with integrity constraints
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_duplicate_case, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Exactly one operation should succeed, the rest should fail with integrity errors
        success_count = sum(1 for _, success in results if success)
        assert success_count == 1, "Exactly one operation should succeed due to unique constraint"

        # Verify only one test case exists with that key
        with db_manager.get_session() as session:
            cases = session.query(TestCase).filter_by(key="PARALLEL-DUPLICATE").all()
            assert len(cases) == 1, "Only one test case should exist with the duplicate key"

    def test_concurrent_complex_operations(self, db_manager, test_project):
        """Test concurrent complex operations with interdependent entities."""

        # Function to create a complete test hierarchy (folder -> test case -> test cycle -> execution)
        def create_hierarchy(index):
            try:
                # Create a unique folder
                folder = FolderModel(
                    id=f"HIER-FOLDER-{index}",
                    name=f"Hierarchy Folder {index}",
                    folderType="TEST_CASE",
                )
                db_manager.save_folder(folder, test_project.key)

                # Create a test case in the folder
                test_case = CaseModel(
                    id=f"HIER-CASE-{index}",
                    key=f"PARALLEL-HIER-CASE-{index}",
                    name=f"Hierarchy Test Case {index}",
                    status="Draft",
                    folder=folder.id,
                    custom_fields=[
                        CustomFieldModel(
                            id=f"CF-{index}-1", name="Priority", type="dropdown", value="High",
                        ),
                        CustomFieldModel(
                            id=f"CF-{index}-2", name="Complexity", type="dropdown", value="Medium",
                        ),
                    ],
                    attachments=[],
                    links=[],
                    steps=[],
                    scripts=[],
                    versions=[],
                )
                db_manager.save_test_case(test_case, test_project.key)

                # Create a test cycle
                test_cycle = CycleInfoModel(
                    id=f"HIER-CYCLE-{index}",
                    key=f"PARALLEL-HIER-CYCLE-{index}",
                    name=f"Hierarchy Test Cycle {index}",
                    status="Active",
                    folder=folder.id,
                    custom_fields=[],
                    attachments=[],
                    links=[],
                )
                db_manager.save_test_cycle(test_cycle, test_project.key)

                # Create a test execution linking the case and cycle
                test_execution = ExecutionModel(
                    id=f"HIER-EXEC-{index}",
                    testCaseKey=test_case.key,
                    cycleId=test_cycle.id,
                    status="Passed",
                    steps=[],
                    custom_fields=[],
                    attachments=[],
                    links=[],
                )
                db_manager.save_test_execution(test_execution, test_project.key)

                return index, True
            except Exception as e:
                logger.error(f"Error creating hierarchy {index}: {e}")
                return index, False

        # Execute concurrent complex operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_hierarchy, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Verify all operations were successful
        for index, success in results:
            assert success, f"Hierarchy {index} should be created successfully"

        # Verify the created hierarchies
        with db_manager.get_session() as session:
            # Check folders
            folders = session.query(Folder).filter(Folder.id.like("HIER-FOLDER-%")).all()
            assert len(folders) == 10, "10 folders should be created"

            # Check test cases
            test_cases = session.query(TestCase).filter(TestCase.id.like("HIER-CASE-%")).all()
            assert len(test_cases) == 10, "10 test cases should be created"

            # We could also verify test cycles and executions similarly
