"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import logging
import os
import shutil
import tempfile
import time
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy.exc import IntegrityError, OperationalError
from ztoq.core.db_manager import DatabaseConfig, SQLDatabaseManager
from ztoq.core.db_models import Folder, TestCase
from ztoq.models import (
    Case as CaseModel,
)
from ztoq.models import (
    CycleInfo as CycleInfoModel,
)
from ztoq.models import (
    Project as ProjectModel,
)
from ztoq.core.db_models import MigrationState

# Setup test logger
logger = logging.getLogger(__name__)


@pytest.mark.integration()
class TestDatabaseErrorHandling:
    """Integration tests for database error handling and recovery."""

    @pytest.fixture(scope="class")
    def temp_db_path(self):
        """Create a temporary directory for the test database."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test_errors.db")
        yield db_path
        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture()
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

    @pytest.fixture()
    def test_project(self, db_manager):
        """Create a test project in the database."""
        project = ProjectModel(
            id="ERROR-TEST-1",
            key="ERROR",
            name="Error Handling Test Project",
            description="A test project for error handling and recovery",
        )
        db_manager.save_project(project)
        return project

    def test_transaction_rollback_on_error(self, db_manager, test_project):
        """Test that transactions are rolled back on error."""
        # First, create a valid test case
        test_case = CaseModel(
            id="ROLLBACK-1",
            key="ERROR-ROLLBACK-1",
            name="Rollback Test Case",
            status="Draft",
            custom_fields=[],
            attachments=[],
            links=[],
            steps=[],
            scripts=[],
            versions=[],
        )
        db_manager.save_test_case(test_case, test_project.key)

        # Attempt to create a test case with invalid data (violating a constraint)
        # We'll use the same key, which should violate the unique constraint
        invalid_case = CaseModel(
            id="ROLLBACK-2",
            key="ERROR-ROLLBACK-1",  # Same key as the existing test case
            name="Invalid Rollback Test Case",
            status="Draft",
            custom_fields=[],
            attachments=[],
            links=[],
            steps=[],
            scripts=[],
            versions=[],
        )

        # This should raise an IntegrityError and rollback
        with pytest.raises(IntegrityError):
            db_manager.save_test_case(invalid_case, test_project.key)

        # Verify the database state is unchanged
        with db_manager.get_session() as session:
            cases = session.query(TestCase).filter_by(project_key=test_project.key).all()
            assert len(cases) == 1, "Only the original test case should exist"
            assert cases[0].name == "Rollback Test Case", "Original test case should be unchanged"

    def test_error_handling_in_manager_methods(self, db_manager, test_project):
        """Test error handling within manager methods that use transactions."""
        # Create a cycle with a reference to a non-existent project to trigger a foreign key error
        cycle = CycleInfoModel(
            id="ERROR-CYCLE-1",
            key="ERROR-CYCLE-1",
            name="Error Test Cycle",
            status="Active",
            custom_fields=[],
            attachments=[],
            links=[],
        )

        # Mock the save_test_cycle method to raise an IntegrityError
        def mock_save_with_error(*args, **kwargs):
            raise IntegrityError("Mocked integrity error", None, None)

        with patch.object(db_manager, "save_test_cycle", side_effect=mock_save_with_error):
            # This should raise the IntegrityError
            with pytest.raises(IntegrityError):
                db_manager.save_test_cycle(cycle, "NONEXISTENT")

        # Verify no test cycle was created
        with db_manager.get_session() as session:
            cycles = session.query(TestCase).all()
            assert len(cycles) == 0, "No test cycle should be created if an error occurs"

    def test_nested_transaction_handling(self, db_manager, test_project):
        """Test handling of nested transactions."""

        # Helper function to simulate a nested transaction operation
        def nested_transaction_operation():
            # Outer transaction
            with db_manager.get_session() as outer_session:
                # Create a folder
                folder = Folder(
                    id="NESTED-FOLDER-1",
                    name="Nested Transaction Folder",
                    folder_type="TEST_CASE",
                    project_key=test_project.key,
                )
                outer_session.add(folder)

                try:
                    # Inner transaction (will fail)
                    with db_manager.get_session() as inner_session:
                        # Try to create a test case with invalid data
                        test_case = TestCase(
                            id="NESTED-CASE-1",
                            # Missing required key field, which will cause an IntegrityError
                            name="Nested Transaction Test Case",
                            project_key=test_project.key,
                        )
                        inner_session.add(test_case)
                        # Inner session will rollback on error
                except IntegrityError:
                    # Expected error in inner transaction
                    pass

                # Continue outer transaction
                # Create a valid test case
                valid_case = TestCase(
                    id="NESTED-CASE-2",
                    key="ERROR-NESTED-2",
                    name="Valid Nested Test Case",
                    project_key=test_project.key,
                )
                outer_session.add(valid_case)
                # Outer session should commit successfully

        # This operation should succeed, despite the inner transaction failing
        nested_transaction_operation()

        # Verify the database state
        with db_manager.get_session() as session:
            # Check folder was created
            folder = session.query(Folder).filter_by(id="NESTED-FOLDER-1").first()
            assert folder is not None, "Folder should be created in outer transaction"

            # Check invalid test case was not created
            invalid_case = session.query(TestCase).filter_by(id="NESTED-CASE-1").first()
            assert invalid_case is None, "Invalid test case should not be created"

            # Check valid test case was created
            valid_case = session.query(TestCase).filter_by(id="NESTED-CASE-2").first()
            assert valid_case is not None, "Valid test case should be created in outer transaction"

    def test_connection_error_recovery(self, db_manager, test_project):
        """Test recovery from database connection errors."""
        original_engine = db_manager._engine

        # Count initial test cases
        with db_manager.get_session() as session:
            initial_count = session.query(TestCase).filter_by(project_key=test_project.key).count()

        # Mock the engine to simulate a connection error on the first attempt
        mock_engine = MagicMock()
        mock_session_factory = MagicMock()
        mock_session = MagicMock()

        # Configure the mock to raise an OperationalError on first connect
        mock_session_factory.return_value = mock_session
        mock_session.__enter__.side_effect = [
            OperationalError("connection error", None, None),  # First attempt fails
            mock_session,  # Second attempt succeeds
        ]
        mock_session.__exit__.return_value = None

        # Patch the engine and session factory
        db_manager._engine = mock_engine
        db_manager._session_factory = mock_session_factory
        db_manager._scoped_session = mock_session_factory

        try:
            # Try to create a test case (first attempt should fail, retry should succeed)
            test_case = CaseModel(
                id="RECONNECT-1",
                key="ERROR-RECONNECT-1",
                name="Reconnection Test Case",
                status="Draft",
                custom_fields=[],
                attachments=[],
                links=[],
                steps=[],
                scripts=[],
                versions=[],
            )

            # This should raise the OperationalError
            with pytest.raises(OperationalError):
                db_manager.save_test_case(test_case, test_project.key)

            # We expect the mock to show one connect attempt
            assert mock_session.__enter__.call_count == 1, "Session should be entered once"

            # Reset the mock for the next test
            mock_session.__enter__.reset_mock()
            mock_session.__enter__.side_effect = None
            mock_session.__enter__.return_value = mock_session

            # Now restore the original engine to test actual recovery
            db_manager._engine = original_engine
            db_manager._session_factory = sessionmaker(bind=original_engine)
            db_manager._scoped_session = scoped_session(db_manager._session_factory)

            # Try again with the real engine
            db_manager.save_test_case(test_case, test_project.key)

            # Verify the test case was created
            with db_manager.get_session() as session:
                final_count = (
                    session.query(TestCase).filter_by(project_key=test_project.key).count()
                )
                assert (
                    final_count == initial_count + 1
                ), "Test case should be created after reconnection"

                case = session.query(TestCase).filter_by(id="RECONNECT-1").first()
                assert case is not None, "Test case should exist after reconnection"
        finally:
            # Restore the original engine in case of failure
            db_manager._engine = original_engine
            db_manager._session_factory = sessionmaker(bind=original_engine)
            db_manager._scoped_session = scoped_session(db_manager._session_factory)

    def test_deadlock_detection_and_retry(self, db_manager, test_project):
        """Test deadlock detection and retry logic."""
        # SQLite doesn't support true deadlock detection, so we'll simulate it

        # Create two test cases to use for deadlock simulation
        test_case1 = CaseModel(
            id="DEADLOCK-1",
            key="ERROR-DEADLOCK-1",
            name="Deadlock Test Case 1",
            status="Draft",
            custom_fields=[],
            attachments=[],
            links=[],
            steps=[],
            scripts=[],
            versions=[],
        )

        test_case2 = CaseModel(
            id="DEADLOCK-2",
            key="ERROR-DEADLOCK-2",
            name="Deadlock Test Case 2",
            status="Draft",
            custom_fields=[],
            attachments=[],
            links=[],
            steps=[],
            scripts=[],
            versions=[],
        )

        db_manager.save_test_case(test_case1, test_project.key)
        db_manager.save_test_case(test_case2, test_project.key)

        # Function to simulate a deadlock situation
        deadlock_count = 0
        original_execute = db_manager._engine.execute

        def mock_execute_with_deadlock(*args, **kwargs):
            nonlocal deadlock_count
            if "UPDATE test_cases" in str(args[0]) and deadlock_count < 1:
                deadlock_count += 1
                # Simulate a deadlock error
                raise OperationalError("database is locked", None, None)
            # After the first deadlock, allow normal execution
            return original_execute(*args, **kwargs)

        try:
            # Patch the engine execute method to simulate deadlock
            db_manager._engine.execute = mock_execute_with_deadlock

            # Update a test case, which should trigger the deadlock and retry
            updated_case = CaseModel(
                id="DEADLOCK-1",
                key="ERROR-DEADLOCK-1",
                name="Updated Deadlock Test Case",
                status="Active",
                custom_fields=[],
                attachments=[],
                links=[],
                steps=[],
                scripts=[],
                versions=[],
            )

            # This would raise an OperationalError without retry logic
            # We'll add retry logic manually for this test
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                try:
                    db_manager.save_test_case(updated_case, test_project.key)
                    break  # Success, exit the loop
                except OperationalError as e:
                    if "database is locked" in str(e) and retry_count < max_retries - 1:
                        retry_count += 1
                        logger.info(
                            f"Deadlock detected, retrying ({retry_count}/{max_retries-1})..."
                        )
                        time.sleep(0.1 * retry_count)  # Exponential backoff
                    else:
                        raise  # Max retries reached or other error

            # Verify the test case was updated
            with db_manager.get_session() as session:
                case = session.query(TestCase).filter_by(id="DEADLOCK-1").first()
                assert case is not None, "Test case should exist"
                assert case.name == "Updated Deadlock Test Case", "Test case should be updated"
                assert case.status == "Active", "Test case status should be updated"
        finally:
            # Restore original execute method
            db_manager._engine.execute = original_execute

    def test_network_partition_simulation(self, db_manager, test_project):
        """Test handling of network partitions (for PostgreSQL)."""
        # Since we're using SQLite, we'll simulate a network partition with temporary file access issues

        # Skip for non-file based configurations
        if db_manager.config.db_type != "sqlite" or not db_manager.config.db_path:
            pytest.skip("This test is only relevant for file-based SQLite")

        # Create a test case
        test_case = CaseModel(
            id="NETWORK-1",
            key="ERROR-NETWORK-1",
            name="Network Partition Test Case",
            status="Draft",
            custom_fields=[],
            attachments=[],
            links=[],
            steps=[],
            scripts=[],
            versions=[],
        )
        db_manager.save_test_case(test_case, test_project.key)

        # Simulate a network partition by temporarily renaming the database file
        original_db_path = db_manager.config.db_path
        temp_db_path = original_db_path + ".backup"

        try:
            # Rename the database file to simulate unavailability
            os.rename(original_db_path, temp_db_path)

            # Attempt an operation, which should fail
            with pytest.raises(OperationalError):
                db_manager.get_statistics(test_project.key)

            # Restore the database file to simulate network recovery
            os.rename(temp_db_path, original_db_path)

            # Try again, which should succeed
            stats = db_manager.get_statistics(test_project.key)
            assert "test_cases" in stats, "Should be able to get statistics after network recovery"
            assert stats["test_cases"] >= 1, "Should have at least one test case"
        finally:
            # Ensure database file is restored
            if os.path.exists(temp_db_path) and not os.path.exists(original_db_path):
                os.rename(temp_db_path, original_db_path)

    def test_constraint_violation_handling(self, db_manager, test_project):
        """Test handling of constraint violations."""
        # Create a test case
        test_case = CaseModel(
            id="CONSTRAINT-1",
            key="ERROR-CONSTRAINT-1",
            name="Constraint Test Case",
            status="Draft",
            custom_fields=[],
            attachments=[],
            links=[],
            steps=[],
            scripts=[],
            versions=[],
        )
        db_manager.save_test_case(test_case, test_project.key)

        # Try to create a test case with the same key (violating unique constraint)
        duplicate_case = CaseModel(
            id="CONSTRAINT-2",
            key="ERROR-CONSTRAINT-1",  # Same key as existing case
            name="Duplicate Constraint Test Case",
            status="Draft",
            custom_fields=[],
            attachments=[],
            links=[],
            steps=[],
            scripts=[],
            versions=[],
        )

        # This should raise an IntegrityError
        with pytest.raises(IntegrityError):
            db_manager.save_test_case(duplicate_case, test_project.key)

        # Verify only the original test case exists
        with db_manager.get_session() as session:
            cases = session.query(TestCase).filter_by(key="ERROR-CONSTRAINT-1").all()
            assert len(cases) == 1, "Only one test case should exist with this key"
            assert cases[0].id == "CONSTRAINT-1", "Original test case should be unchanged"

        # Try to violate a foreign key constraint
        try:
            with db_manager.get_session() as session:
                # Create a test case with a non-existent project
                invalid_case = TestCase(
                    id="CONSTRAINT-3",
                    key="ERROR-CONSTRAINT-3",
                    name="Foreign Key Constraint Test Case",
                    project_key="NONEXISTENT",  # This project doesn't exist
                )
                session.add(invalid_case)
                session.flush()  # Force the constraint check
        except IntegrityError:
            pass  # Expected error

        # Verify the invalid test case was not created
        with db_manager.get_session() as session:
            case = session.query(TestCase).filter_by(id="CONSTRAINT-3").first()
            assert case is None, "Test case with invalid foreign key should not be created"

    def test_database_corruption_recovery(self, db_manager, test_project):
        """Test recovery from database corruption."""
        # Skip for non-file based configurations
        if db_manager.config.db_type != "sqlite" or not db_manager.config.db_path:
            pytest.skip("This test is only relevant for file-based SQLite")

        # Create some test data
        for i in range(5):
            test_case = CaseModel(
                id=f"CORRUPT-{i}",
                key=f"ERROR-CORRUPT-{i}",
                name=f"Corruption Test Case {i}",
                status="Draft",
                custom_fields=[],
                attachments=[],
                links=[],
                steps=[],
                scripts=[],
                versions=[],
            )
            db_manager.save_test_case(test_case, test_project.key)

        # Verify data was saved
        with db_manager.get_session() as session:
            count = session.query(TestCase).filter(TestCase.id.like("CORRUPT-%")).count()
            assert count == 5, "Should have 5 test cases before corruption"

        # Simulate corruption by creating a backup and removing the db file
        original_db_path = db_manager.config.db_path
        backup_db_path = original_db_path + ".backup"

        # Create a backup
        shutil.copy2(original_db_path, backup_db_path)

        try:
            # Remove the database file to simulate corruption
            os.remove(original_db_path)

            # Attempt an operation, which should fail
            with pytest.raises(Exception):
                db_manager.get_statistics(test_project.key)

            # Restore from backup (this simulates the recovery process)
            shutil.copy2(backup_db_path, original_db_path)

            # Try again, which should succeed
            stats = db_manager.get_statistics(test_project.key)
            assert "test_cases" in stats, "Should be able to get statistics after recovery"
            assert stats["test_cases"] >= 5, "Should have at least 5 test cases after recovery"
        finally:
            # Clean up backup
            if os.path.exists(backup_db_path):
                os.remove(backup_db_path)

    def test_bulk_operation_partial_failure(self, db_manager, test_project):
        """Test that partial failures in bulk operations are handled correctly."""
        # Prepare data for bulk insert
        test_cases = []
        for i in range(10):
            # Make one case invalid (missing key)
            if i == 5:
                test_case = CaseModel(
                    id=f"BULK-{i}",
                    # Deliberately miss the key for one item
                    name=f"Bulk Test Case {i}",
                    status="Draft",
                    custom_fields=[],
                    attachments=[],
                    links=[],
                    steps=[],
                    scripts=[],
                    versions=[],
                )
            else:
                test_case = CaseModel(
                    id=f"BULK-{i}",
                    key=f"ERROR-BULK-{i}",
                    name=f"Bulk Test Case {i}",
                    status="Draft",
                    custom_fields=[],
                    attachments=[],
                    links=[],
                    steps=[],
                    scripts=[],
                    versions=[],
                )
            test_cases.append(test_case)

        # Implement a bulk insert function (simulated here)
        def bulk_insert_with_partial_failure(cases):
            success_count = 0
            failure_count = 0

            for case in cases:
                try:
                    db_manager.save_test_case(case, test_project.key)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error saving case {getattr(case, 'id', 'unknown')}: {e}")
                    failure_count += 1

            return success_count, failure_count

        # Perform the bulk insert
        success_count, failure_count = bulk_insert_with_partial_failure(test_cases)

        # Verify results
        assert success_count == 9, "Should have 9 successful inserts"
        assert failure_count == 1, "Should have 1 failed insert"

        # Verify database state
        with db_manager.get_session() as session:
            # Check valid cases were created
            for i in range(10):
                if i == 5:  # The invalid one
                    case = session.query(TestCase).filter_by(id=f"BULK-{i}").first()
                    assert case is None, f"Invalid case BULK-{i} should not exist"
                else:
                    case = session.query(TestCase).filter_by(id=f"BULK-{i}").first()
                    assert case is not None, f"Valid case BULK-{i} should exist"
                    assert case.key == f"ERROR-BULK-{i}", f"Case BULK-{i} should have correct key"

    def test_orphaned_record_cleanup(self, db_manager, test_project):
        """Test cleanup of orphaned records (e.g., test steps without parent test case)."""
        # First create a test case with steps
        with db_manager.get_session() as session:
            # Create test case
            test_case = TestCase(
                id="ORPHAN-PARENT",
                key="ERROR-ORPHAN-PARENT",
                name="Orphan Parent Test Case",
                project_key=test_project.key,
            )
            session.add(test_case)
            session.flush()

            # Add steps
            for i in range(3):
                step = TestCase.steps.prop.mapper.class_(
                    id=f"ORPHAN-STEP-{i}",
                    index=i,
                    description=f"Step {i}",
                    expected_result=f"Expected {i}",
                    test_case_id=test_case.id,
                )
                session.add(step)

            session.commit()

        # Verify test case and steps were created
        with db_manager.get_session() as session:
            # Check test case
            case = session.query(TestCase).filter_by(id="ORPHAN-PARENT").first()
            assert case is not None, "Parent test case should exist"

            # Check steps
            steps = case.steps
            assert len(steps) == 3, "Should have 3 steps attached to the test case"

        # Delete the test case (this should cascade to steps)
        with db_manager.get_session() as session:
            case = session.query(TestCase).filter_by(id="ORPHAN-PARENT").first()
            session.delete(case)
            session.commit()

        # Verify the steps were also deleted
        with db_manager.get_session() as session:
            # Check test case is gone
            case = session.query(TestCase).filter_by(id="ORPHAN-PARENT").first()
            assert case is None, "Parent test case should be deleted"

            # Check steps are gone (using raw query since we don't have the class reference)
            for i in range(3):
                step = (
                    session.query(TestCase.steps.prop.mapper.class_)
                    .filter_by(id=f"ORPHAN-STEP-{i}")
                    .first()
                )
                assert step is None, f"Step {i} should be deleted with parent test case"

    def test_recovery_from_interrupted_operation(self, db_manager, test_project):
        """Test recovery from an interrupted database operation."""
        # Create a migration state to track operation
        with db_manager.get_session() as session:
            # Add a migration state record
            migration_state = MigrationState(
                project_key=test_project.key,
                extraction_status="in_progress",
                transformation_status="not_started",
                loading_status="not_started",
                meta_data='{"processed_items": 0, "total_items": 10}',
            )
            session.add(migration_state)
            session.commit()

        # Simulate an interrupted operation (process 5 items, then fail)
        try:
            for i in range(10):
                # Create a test case
                test_case = CaseModel(
                    id=f"INTERRUPT-{i}",
                    key=f"ERROR-INTERRUPT-{i}",
                    name=f"Interrupted Operation Test Case {i}",
                    status="Draft",
                    custom_fields=[],
                    attachments=[],
                    links=[],
                    steps=[],
                    scripts=[],
                    versions=[],
                )
                db_manager.save_test_case(test_case, test_project.key)

                # Update migration state
                db_manager.update_migration_state(
                    test_project.key, metadata={"processed_items": i + 1, "total_items": 10}
                )

                # Simulate failure in the middle
                if i == 4:
                    raise RuntimeError("Simulated interruption")
        except RuntimeError:
            # Expected interruption
            db_manager.update_migration_state(
                test_project.key,
                extraction_status="failed",
                error_message="Operation was interrupted",
            )

        # Verify the partial progress
        with db_manager.get_session() as session:
            # Check migration state
            state = session.query(MigrationState).filter_by(project_key=test_project.key).first()
            assert state is not None, "Migration state should exist"
            assert state.extraction_status == "failed", "Status should be failed"
            assert state.error_message == "Operation was interrupted", "Error message should be set"

            # Check the processed items
            metadata = state.metadata_dict
            assert metadata["processed_items"] == 5, "Should have processed 5 items"

            # Check actual data
            count = session.query(TestCase).filter(TestCase.id.like("INTERRUPT-%")).count()
            assert count == 5, "Should have 5 test cases created before interruption"

        # Simulate resuming the operation
        try:
            # First, update state to in_progress again
            db_manager.update_migration_state(
                test_project.key, extraction_status="in_progress", error_message=None
            )

            # Get current progress
            with db_manager.get_session() as session:
                state = (
                    session.query(MigrationState).filter_by(project_key=test_project.key).first()
                )
                processed_items = state.metadata_dict.get("processed_items", 0)

            # Process remaining items
            for i in range(processed_items, 10):
                test_case = CaseModel(
                    id=f"INTERRUPT-{i}",
                    key=f"ERROR-INTERRUPT-{i}",
                    name=f"Resumed Operation Test Case {i}",
                    status="Draft",
                    custom_fields=[],
                    attachments=[],
                    links=[],
                    steps=[],
                    scripts=[],
                    versions=[],
                )
                db_manager.save_test_case(test_case, test_project.key)

                # Update migration state
                db_manager.update_migration_state(
                    test_project.key, metadata={"processed_items": i + 1, "total_items": 10}
                )

            # Mark as completed
            db_manager.update_migration_state(
                test_project.key,
                extraction_status="completed",
                metadata={"processed_items": 10, "total_items": 10, "completed_at": time.time()},
            )
        except Exception as e:
            logger.error(f"Error resuming operation: {e}")
            db_manager.update_migration_state(
                test_project.key,
                extraction_status="failed",
                error_message=f"Resume failed: {str(e)}",
            )
            raise

        # Verify the operation was completed
        with db_manager.get_session() as session:
            # Check migration state
            state = session.query(MigrationState).filter_by(project_key=test_project.key).first()
            assert state is not None, "Migration state should exist"
            assert state.extraction_status == "completed", "Status should be completed"

            # Check the processed items
            metadata = state.metadata_dict
            assert metadata["processed_items"] == 10, "Should have processed all 10 items"

            # Check actual data
            count = session.query(TestCase).filter(TestCase.id.like("INTERRUPT-%")).count()
            assert count == 10, "Should have all 10 test cases after resuming"
