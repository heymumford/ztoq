"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for the work queue module.
"""

import asyncio
import random
import time
from typing import Any, Dict, List
import pytest

from ztoq.work_queue import (
    WorkerType,
    WorkStatus,
    WorkItem,
    WorkQueue,
    run_in_thread_pool,
    run_in_process_pool,
    run_with_asyncio,
)

# Mark the whole module as unit tests
pytestmark = pytest.mark.unit


# Helper functions for tests
def sync_worker(x: int) -> int:
    """Simple synchronous worker that squares a number."""
    return x * x


async def async_worker(x: int) -> int:
    """Simple asynchronous worker that squares a number with delay."""
    await asyncio.sleep(0.01)  # Small delay to simulate async work
    return x * x


def slow_worker(x: int) -> int:
    """Worker with random delay to test concurrency."""
    time.sleep(random.uniform(0.01, 0.05))
    return x * x


def error_worker(x: int) -> int:
    """Worker that raises an exception for odd numbers."""
    if x % 2 == 1:
        raise ValueError(f"Cannot process odd number: {x}")
    return x * x


async def async_error_worker(x: int) -> int:
    """Async worker that raises an exception for odd numbers."""
    await asyncio.sleep(0.01)
    if x % 2 == 1:
        raise ValueError(f"Cannot process odd number: {x}")
    return x * x


# Tests
@pytest.mark.asyncio
async def test_work_item_lifecycle():
    """Test work item state transitions."""
    # Create work item
    work_item = WorkItem[int, int](input_data=5)

    # Initial state
    assert work_item.status == WorkStatus.PENDING
    assert work_item.attempt == 0
    assert work_item.result is None
    assert work_item.error is None

    # Mark as running
    work_item.mark_running()
    assert work_item.status == WorkStatus.RUNNING
    assert work_item.attempt == 1
    assert work_item.started_at is not None

    # Mark as completed
    work_item.mark_completed(25)
    assert work_item.status == WorkStatus.COMPLETED
    assert work_item.result == 25
    assert work_item.completed_at is not None
    assert work_item.processing_time is not None
    assert work_item.waiting_time is not None
    assert work_item.total_time is not None

    # Create a new work item for failure test
    work_item = WorkItem[int, int](input_data=5)

    # Mark as running
    work_item.mark_running()

    # Mark as failed
    error = ValueError("Test error")
    work_item.mark_failed(error)
    assert work_item.status == WorkStatus.FAILED
    assert work_item.error == error
    assert work_item.completed_at is not None

    # Check retriability
    assert work_item.is_retriable() == True

    # Mark as running again and fail again
    work_item.mark_running()
    work_item.mark_failed(error)

    # Mark as running again and fail again
    work_item.mark_running()
    work_item.mark_failed(error)

    # Now we've hit the default max_attempts (3)
    assert work_item.is_retriable() == False

    # Test cancellation
    work_item = WorkItem[int, int](input_data=5)
    work_item.mark_cancelled()
    assert work_item.status == WorkStatus.CANCELLED
    assert work_item.completed_at is not None


@pytest.mark.asyncio
async def test_thread_work_queue():
    """Test work queue with thread workers."""
    # Create work queue
    queue = WorkQueue[int, int](
        worker_type=WorkerType.THREAD,
        max_workers=5,
        worker_function=sync_worker,
    )

    # Start queue
    await queue.start()

    try:
        # Add work items
        work_ids = []
        for i in range(10):
            work_id = await queue.add_work(i)
            work_ids.append(work_id)

        # Wait for all work to complete
        results = await asyncio.gather(*[queue.get_result(wid) for wid in work_ids])

        # Check results
        assert results == [i * i for i in range(10)]

        # Check stats
        stats = queue.get_stats()
        assert stats["completed_count"] == 10
        assert stats["failed_count"] == 0
        assert stats["worker_type"] == "thread"

    finally:
        # Stop queue
        await queue.stop()


@pytest.mark.asyncio
async def test_asyncio_work_queue():
    """Test work queue with asyncio workers."""
    completed_items = []

    def on_complete(item: WorkItem[int, int]) -> None:
        completed_items.append(item.id)

    # Create work queue
    queue = WorkQueue[int, int](
        worker_type=WorkerType.ASYNCIO,
        max_workers=5,
        async_worker_function=async_worker,
        on_complete=on_complete,
    )

    # Start queue
    await queue.start()

    try:
        # Add work items
        work_ids = []
        for i in range(10):
            work_id = await queue.add_work(i)
            work_ids.append(work_id)

        # Wait for all work to complete
        results = await queue.get_batch_results(work_ids)

        # Check results
        assert [results[wid] for wid in work_ids] == [i * i for i in range(10)]

        # Check completed callback was called
        assert len(completed_items) == 10
        assert set(completed_items) == set(work_ids)

    finally:
        # Stop queue
        await queue.stop()


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in work queue."""
    error_items = []

    def on_error(item: WorkItem[int, int]) -> None:
        error_items.append(item.id)

    # Create work queue with no retry
    queue = WorkQueue[int, int](
        worker_type=WorkerType.THREAD,
        max_workers=5,
        worker_function=error_worker,
        on_error=on_error,
    )

    # Start queue
    await queue.start()

    try:
        # Add work items (0-9)
        work_ids = []
        for i in range(10):
            work_id = await queue.add_work(i, max_attempts=1)  # Only try once
            work_ids.append(work_id)

        # Wait for all work to complete or fail
        results = await queue.get_batch_results(work_ids, raise_on_error=False)

        # Check results - even numbers should have results, odd should have errors
        for i, wid in enumerate(work_ids):
            if i % 2 == 0:
                assert isinstance(results[wid], int)
                assert results[wid] == i * i
            else:
                assert isinstance(results[wid], ValueError)
                assert str(results[wid]) == f"Cannot process odd number: {i}"

        # Check error callback was called for odd numbers
        assert len(error_items) == 5  # 5 odd numbers out of 10

        # Check stats
        stats = queue.get_stats()
        assert stats["completed_count"] == 5
        assert stats["failed_count"] == 5

    finally:
        # Stop queue
        await queue.stop()


@pytest.mark.asyncio
async def test_retry_mechanism():
    """Test retry mechanism for failed work items."""
    retry_count: Dict[str, int] = {}

    # Custom worker that fails on first attempt for odd numbers
    def flaky_worker(x: int) -> int:
        work_id = next(
            wid
            for wid, item in queue.work_items.items()
            if item.input_data == x and item.status == WorkStatus.RUNNING
        )

        retry_count[work_id] = retry_count.get(work_id, 0) + 1

        # Fail on first attempt for odd numbers
        if x % 2 == 1 and retry_count[work_id] == 1:
            raise ValueError(f"First attempt failed for {x}")

        return x * x

    # Create work queue with retry
    queue = WorkQueue[int, int](
        worker_type=WorkerType.THREAD,
        max_workers=5,
        worker_function=flaky_worker,
    )

    # Start queue
    await queue.start()

    try:
        # Add work items (0-9)
        work_ids = []
        for i in range(10):
            work_id = await queue.add_work(i, max_attempts=3)
            work_ids.append(work_id)
            retry_count[work_id] = 0

        # Wait for all work to complete
        results = await queue.get_batch_results(work_ids)

        # Check all succeeded
        for i, wid in enumerate(work_ids):
            assert results[wid] == i * i

        # Odd numbers should have been retried once
        for i, wid in enumerate(work_ids):
            if i % 2 == 1:
                assert retry_count[wid] == 2  # 1 failure + 1 success
            else:
                assert retry_count[wid] == 1  # 1 success

    finally:
        # Stop queue
        await queue.stop()


@pytest.mark.asyncio
async def test_priority_scheduling():
    """Test priority-based scheduling in the work queue."""
    processed_order = []

    # Worker that records processing order
    def tracking_worker(x: int) -> int:
        processed_order.append(x)
        return x * x

    # Create work queue
    queue = WorkQueue[int, int](
        worker_type=WorkerType.THREAD,
        max_workers=1,  # Single worker to ensure sequential processing
        worker_function=tracking_worker,
    )

    # Start queue
    await queue.start()

    try:
        # Add work items with different priorities
        # Higher priority (10) should be processed first
        await queue.add_work(1, priority=1)  # Low priority
        await queue.add_work(2, priority=1)  # Low priority
        await queue.add_work(3, priority=5)  # Medium priority
        await queue.add_work(4, priority=10)  # High priority
        await queue.add_work(5, priority=5)  # Medium priority

        # Wait for completion
        while queue.get_stats()["completed_count"] < 5:
            await asyncio.sleep(0.1)

        # Check processing order - higher priority should come first
        # 4 (prio 10) should be first, then 3,5 (prio 5), then 1,2 (prio 1)
        assert processed_order[0] == 4  # Highest priority

        # 3 and 5 should be before 1 and 2
        assert processed_order.index(3) < processed_order.index(1)
        assert processed_order.index(3) < processed_order.index(2)
        assert processed_order.index(5) < processed_order.index(1)
        assert processed_order.index(5) < processed_order.index(2)

    finally:
        # Stop queue
        await queue.stop()


@pytest.mark.asyncio
async def test_dependency_resolution():
    """Test dependency resolution between work items."""
    processed_items = []

    # Worker that records processing order
    def tracking_worker(x: int) -> int:
        processed_items.append(x)
        return x * x

    # Create work queue
    queue = WorkQueue[int, int](
        worker_type=WorkerType.THREAD,
        max_workers=5,
        worker_function=tracking_worker,
    )

    # Start queue
    await queue.start()

    try:
        # Item 2 depends on item 1
        # Item 3 depends on item 2
        # Item 4 has no dependencies

        id1 = await queue.add_work(1)
        id2 = await queue.add_work(2, dependencies=[id1])
        id3 = await queue.add_work(3, dependencies=[id2])
        id4 = await queue.add_work(4)

        # Wait for completion
        results = await queue.get_batch_results([id1, id2, id3, id4])

        # Check all completed
        assert len(results) == 4
        assert all(isinstance(r, int) for r in results.values())

        # Check dependency order
        assert processed_items.index(1) < processed_items.index(2)
        assert processed_items.index(2) < processed_items.index(3)

        # Item 4 could be processed any time
        assert 4 in processed_items

    finally:
        # Stop queue
        await queue.stop()


@pytest.mark.asyncio
async def test_batch_processing():
    """Test batch processing helper functions."""
    # Test thread pool
    numbers = list(range(10))
    results = await run_in_thread_pool(sync_worker, numbers, max_workers=3)
    assert results == [n * n for n in numbers]

    # Test process pool - note this is slower due to process creation
    results = await run_in_process_pool(sync_worker, numbers[:5], max_workers=2)
    assert results == [n * n for n in numbers[:5]]

    # Test asyncio
    results = await run_with_asyncio(async_worker, numbers, max_workers=5)
    assert results == [n * n for n in numbers]


@pytest.mark.asyncio
async def test_complex_dependency_graph():
    """Test processing a complex dependency graph."""
    processed_items = []

    # Worker that records processing order with delay
    def tracking_worker(x: int) -> int:
        time.sleep(0.01)  # Small delay
        processed_items.append(x)
        return x * x

    # Create work queue
    queue = WorkQueue[int, int](
        worker_type=WorkerType.THREAD,
        max_workers=5,
        worker_function=tracking_worker,
    )

    # Start queue
    await queue.start()

    try:
        # Create dependency graph
        # 2, 3, 4 depend on 1
        # 5 depends on 2 and 3
        # 6 depends on 4
        # 7 has no dependencies
        dependency_graph = {
            1: [],  # No dependencies
            2: [1],  # Depends on 1
            3: [1],  # Depends on 1
            4: [1],  # Depends on 1
            5: [2, 3],  # Depends on 2 and 3
            6: [4],  # Depends on 4
            7: [],  # No dependencies
        }

        # Add with dependencies
        data_to_work_id = await queue.add_with_dependencies(dependency_graph)

        # Wait for completion
        work_ids = list(data_to_work_id.values())
        results = await queue.get_batch_results(work_ids)

        # Check order constraints
        assert processed_items.index(1) < processed_items.index(2)
        assert processed_items.index(1) < processed_items.index(3)
        assert processed_items.index(1) < processed_items.index(4)
        assert processed_items.index(2) < processed_items.index(5)
        assert processed_items.index(3) < processed_items.index(5)
        assert processed_items.index(4) < processed_items.index(6)

        # Check results
        assert all(results[data_to_work_id[i]] == i * i for i in range(1, 8))

    finally:
        # Stop queue
        await queue.stop()


@pytest.mark.asyncio
async def test_cancel_work():
    """Test cancellation of work items."""
    # Create work queue
    queue = WorkQueue[int, int](
        worker_type=WorkerType.THREAD,
        max_workers=5,
        worker_function=slow_worker,
    )

    # Start queue
    await queue.start()

    try:
        # Add work items
        work_ids = []
        for i in range(10):
            work_id = await queue.add_work(i)
            work_ids.append(work_id)

        # Cancel some items
        # Items 7, 8, 9 should still be pending
        for wid in work_ids[7:]:
            success = await queue.cancel_work(wid)
            assert success == True

        # Wait for remaining items
        results = await queue.get_batch_results(work_ids[:7], raise_on_error=False)

        # Check results for non-cancelled items
        for i, wid in enumerate(work_ids[:7]):
            assert results[wid] == i * i

        # Verify cancelled items are marked as cancelled
        for wid in work_ids[7:]:
            work_item = queue.get_work_item(wid)
            assert work_item.status == WorkStatus.CANCELLED

    finally:
        # Stop queue
        await queue.stop()


@pytest.mark.asyncio
async def test_work_queue_stress():
    """Stress test the work queue with many items."""
    # Skip in CI environments where this might be slow
    if "CI" in os.environ:
        pytest.skip("Skipping stress test in CI environment")

    # Create work queue
    queue = WorkQueue[int, int](
        worker_type=WorkerType.THREAD,
        max_workers=10,
        worker_function=sync_worker,
    )

    # Start queue
    await queue.start()

    try:
        # Add many work items
        work_ids = []
        for i in range(1000):
            work_id = await queue.add_work(i)
            work_ids.append(work_id)

        # Wait for all work to complete
        start_time = time.time()
        results = await queue.get_batch_results(work_ids)
        end_time = time.time()

        # Check results
        assert len(results) == 1000
        assert all(results[wid] == i * i for i, wid in enumerate(work_ids))

        # Check performance - should be much faster than sequential
        duration = end_time - start_time
        print(f"Processed 1000 items in {duration:.2f} seconds")

        # Sequential would take at least 1000*0.001 = 1 second
        # Parallel should be much faster
        assert duration < 0.5, f"Parallel processing was too slow: {duration:.2f} seconds"

    finally:
        # Stop queue
        await queue.stop()
