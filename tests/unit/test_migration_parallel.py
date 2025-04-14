"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch
import pytest
from ztoq.migration import EntityBatchTracker, ZephyrToQTestMigration
from ztoq.models import ZephyrConfig
from ztoq.qtest_models import QTestConfig, QTestModule, QTestTestCase

@pytest.mark.unit()


class TestMigrationParallel:
    """Test the parallel processing capabilities of the migration module."""

    @pytest.fixture()
    def zephyr_config(self):
        """Create a test Zephyr configuration."""
        return ZephyrConfig(
            base_url="https://api.zephyrscale.example.com/v2",
                api_token="zephyr-token",
                project_key="DEMO",
            )

    @pytest.fixture()
    def qtest_config(self):
        """Create a test qTest configuration."""
        return QTestConfig(
            base_url="https://example.qtest.com",
                username="test-user",
                password="test-password",
                project_id=12345,
            )

    @pytest.fixture()
    def db_mock(self):
        """Create a mock database manager."""
        db = MagicMock()
        db.get_migration_state.return_value = None
        db.get_entity_mappings.return_value = []

        # Generate a lot of test data for batch processing tests
        test_cases = []
        for i in range(100):
            test_cases.append({
                "source_id": f"tc-{i:03d}",
                    "test_case": {
                    "name": f"Test Case {i}",
                        "description": f"Description for test case {i}",
                        "module_id": "module-1",
                        "priority_id": 2
                }
            })
        db.get_transformed_test_cases.return_value = test_cases

        # Generate test data for modules by level
        modules_level_0 = []
        for i in range(5):
            modules_level_0.append({
                "source_id": f"folder-{i}",
                    "module": {
                    "name": f"Module {i}",
                        "description": f"Root module {i}",
                        "parent_id": None
                }
            })

        modules_level_1 = []
        for i in range(5):
            for j in range(5):  # 5 children per parent
                modules_level_1.append({
                    "source_id": f"folder-{i}-{j}",
                        "module": {
                        "name": f"Module {i}.{j}",
                            "description": f"Child module {j} of {i}",
                            "parent_id": f"qmodule-module-{i}"
                    }
                })

        db.get_transformed_modules_by_level.return_value = [modules_level_0, modules_level_1]

        return db

    @pytest.fixture()
    def migration(self, zephyr_config, qtest_config, db_mock):
        """Create a test migration manager with mocked clients."""
        with patch("ztoq.migration.ZephyrClient") as mock_zephyr, patch(
            "ztoq.migration.QTestClient"
        ) as mock_qtest:
            # Configure mocks
            mock_zephyr_client = MagicMock()
            mock_qtest_client = MagicMock()

            # Create module with a delay to simulate API latency
            def create_module_with_delay(module):
                time.sleep(0.01)  # Small delay to simulate API call
                return QTestModule(
                    id=f"qmodule-{module.name.lower().replace(' ', '-').replace('.', '-')}",
                        name=module.name,
                        description=module.description,
                        parent_id=module.parent_id
                )

            mock_qtest_client.create_module.side_effect = create_module_with_delay

            # Create test case with a delay to simulate API latency
            def create_test_case_with_delay(test_case):
                time.sleep(0.01)  # Small delay to simulate API call
                return QTestTestCase(
                    id=f"qtc-{test_case.name.lower().replace(' ', '-')}",
                        name=test_case.name,
                        description=test_case.description,
                        module_id=test_case.module_id,
                        priority_id=test_case.priority_id
                )

            mock_qtest_client.create_test_case.side_effect = create_test_case_with_delay

            mock_zephyr.return_value = mock_zephyr_client
            mock_qtest.return_value = mock_qtest_client

            # Create migration with different max_workers values for testing
            migrations = {}
            for workers in [1, 5, 10]:
                migrations[workers] = ZephyrToQTestMigration(
                    zephyr_config,
                        qtest_config,
                        db_mock,
                        batch_size=20,
                        max_workers=workers
                )
                migrations[workers].zephyr_client_mock = mock_zephyr_client
                migrations[workers].qtest_client_mock = mock_qtest_client

            return migrations

    def test_batch_tracker_initialization(self, db_mock):
        """Test the batch tracker initialization with different batch sizes."""
        tracker = EntityBatchTracker("DEMO", "test_cases", db_mock)

        # Test with 100 items and batch size 20
        tracker.initialize_batches(100, 20)
        assert db_mock.create_entity_batch.call_count == 5

        # Reset mock
        db_mock.reset_mock()

        # Test with 101 items and batch size 20 (should create 6 batches)
        tracker.initialize_batches(101, 20)
        assert db_mock.create_entity_batch.call_count == 6

        # Check the last batch has correct item count
        last_call = db_mock.create_entity_batch.call_args_list[-1]
        assert last_call[0][4] == 1  # Last batch has 1 item

    def test_parallel_module_loading(self, migration, db_mock):
        """Test parallel loading of modules with different worker counts."""
        results = {}

        # Test with different numbers of workers
        for workers in [1, 5, 10]:
            # Reset mock
            db_mock.reset_mock()
            mock_qtest = migration[workers].qtest_client_mock
            mock_qtest.reset_mock()

            # Time the operation
            start_time = time.time()
            migration[workers]._load_modules()
            end_time = time.time()

            # Store results
            results[workers] = {
                'time': end_time - start_time,
                    'call_count': mock_qtest.create_module.call_count
            }

        # Verify all worker counts produced the same number of calls
        assert results[1]['call_count'] == results[5]['call_count'] == results[10]['call_count']

        # Verify that parallel processing was faster
        # Note: This test might be flaky in CI environments
        assert results[5]['time'] < results[1]['time']

        # Higher worker counts might not always be faster due to overhead
        # but they shouldn't be significantly slower
        assert results[10]['time'] < results[1]['time'] * 1.5

    def test_parallel_test_case_loading(self, migration, db_mock):
        """Test parallel loading of test cases."""
        # We'll just test with max_workers=5
        migration_instance = migration[5]

        # Configure mock database to return 100 test cases
        mock_qtest = migration_instance.qtest_client_mock
        mock_qtest.reset_mock()

        # Time the operation
        start_time = time.time()
        migration_instance._load_test_cases()
        end_time = time.time()
        duration = end_time - start_time

        # Verify all 100 test cases were created
        assert mock_qtest.create_test_case.call_count == 100

        # Verify mappings were saved
        assert db_mock.save_entity_mapping.call_count == 100

        # Estimate time for sequential processing (100 * 0.01s delay)
        sequential_estimate = 100 * 0.01

        # Parallel should be significantly faster
        # With 5 workers, theoretical max speedup is 5x
        # We'll be conservative and check for at least 2x speedup
        assert duration < sequential_estimate / 2, f"Parallel processing not fast enough: {duration} vs {sequential_estimate/2}"

    def test_batch_error_handling(self, migration, db_mock):
        """Test error handling during batch processing."""
        migration_instance = migration[5]
        mock_qtest = migration_instance.qtest_client_mock

        # Make every 10th test case creation fail
        original_side_effect = mock_qtest.create_test_case.side_effect

        def fail_every_10th(test_case):
            if test_case.name.endswith('0'):  # Test cases 0, 10, 20, ...
                raise Exception(f"Simulated API error for {test_case.name}")
            return original_side_effect(test_case)

        mock_qtest.create_test_case.side_effect = fail_every_10th

        # Run test case loading
        migration_instance._load_test_cases()

        # Should have 90 successful creations and 10 failures
        # Check entity mapping saves (only done for successful creations)
        assert db_mock.save_entity_mapping.call_count == 90

        # Check batch status updates
        # Should have 5 batches with errors (batches 0, 1, 2, 3, 4 all have at least one error)
        batch_failure_calls = [
            call for call in db_mock.update_entity_batch.call_args_list
            if call[0][4] == "failed"  # Status parameter
        ]
        assert len(batch_failure_calls) == 5

    def test_thread_pool_execution(self):
        """Test ThreadPoolExecutor behavior with tasks that might fail."""
        results = []
        errors = []

        def task(i):
            # Fail for every 3rd item
            if i % 3 == 0:
                raise Exception(f"Task {i} failed")
            return i * 2

        # Execute 10 tasks with 3 workers
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []

            for i in range(10):
                future = executor.submit(task, i)
                futures.append((i, future))

            # Process results
            for i, future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))

        # Verify we have successes and failures
        # (exact count may vary by implementation but we should have around 6-7 successes)
        assert 6 <= len(results) <= 7
        assert 3 <= len(errors) <= 4

        # Correct tasks failed - items 0, 3, 6, 9 should fail (if they're in the range)
        for i in [0, 3, 6, 9]:
            if i < 10:
                assert any(f"Task {i} failed" in error for error in errors)

    def test_parallel_execution_efficiency(self):
        """Test that parallel execution significantly improves performance."""
        # Create a test task that has a sleep delay
        def test_task(i, delay=0.05):
            time.sleep(delay)
            return i

        # Test with different worker counts
        results = {}
        for workers in [1, 5, 10]:
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = []

                for i in range(50):
                    future = executor.submit(test_task, i)
                    futures.append(future)

                # Wait for all to complete
                results[workers] = [f.result() for f in futures]

            end_time = time.time()
            results[f"{workers}_time"] = end_time - start_time

        # All should have same results
        assert len(results[1]) == len(results[5]) == len(results[10]) == 50

        # But 5 workers should be much faster than 1
        assert results["5_time"] < results["1_time"] / 2

        # 10 workers might not be proportionally faster than 5 due to overhead
        # but should still be faster
        assert results["10_time"] <= results["5_time"]
