"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Parallel processing and work queue module.

This module provides optimized work queue implementations for parallel processing
using asyncio and thread/process pools. It enables efficient distribution of
tasks across workers while maintaining control over resource usage and provides
monitoring capabilities.
"""

import asyncio
import logging
import time
import uuid
from asyncio import Queue, QueueEmpty
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, Set, Tuple, TypeVar, Union, cast

logger = logging.getLogger("ztoq.work_queue")

# Type variables for generic functions
T = TypeVar("T")  # Input type
R = TypeVar("R")  # Result type


class WorkerType(str, Enum):
    """Type of worker to use for processing tasks."""

    THREAD = "thread"  # Use ThreadPoolExecutor (best for I/O-bound tasks)
    PROCESS = "process"  # Use ProcessPoolExecutor (best for CPU-bound tasks)
    ASYNCIO = "asyncio"  # Use asyncio tasks (best for async I/O operations)


class WorkStatus(str, Enum):
    """Status of a work item in the queue."""

    PENDING = "pending"  # Work is queued but not yet processing
    RUNNING = "running"  # Work is currently being processed
    COMPLETED = "completed"  # Work has been completed successfully
    FAILED = "failed"  # Work has failed with an exception
    CANCELLED = "cancelled"  # Work was cancelled before completion


@dataclass
class WorkItem(Generic[T, R]):
    """
    Represents a unit of work to be processed.

    Attributes:
        id: Unique identifier for the work item
        input_data: Input data for the work function
        status: Current status of the work item
        result: Result of the work function (if completed)
        error: Exception that occurred (if failed)
        priority: Priority of the work item (higher values have higher priority)
        dependencies: IDs of work items that must complete before this one
        created_at: Timestamp when the work item was created
        started_at: Timestamp when processing started
        completed_at: Timestamp when processing completed
        attempt: Number of attempts made to process this work item
        max_attempts: Maximum number of attempts allowed
        metadata: Additional metadata for the work item
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    input_data: T = field(default=None)
    status: WorkStatus = WorkStatus.PENDING
    result: Optional[R] = None
    error: Optional[Exception] = None
    priority: int = 0
    dependencies: Set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    attempt: int = 0
    max_attempts: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_running(self) -> None:
        """Mark this work item as running."""
        self.status = WorkStatus.RUNNING
        self.started_at = time.time()
        self.attempt += 1

    def mark_completed(self, result: R) -> None:
        """
        Mark this work item as completed.

        Args:
            result: The result of the work function
        """
        self.status = WorkStatus.COMPLETED
        self.result = result
        self.completed_at = time.time()

    def mark_failed(self, error: Exception) -> None:
        """
        Mark this work item as failed.

        Args:
            error: The exception that caused the failure
        """
        self.status = WorkStatus.FAILED
        self.error = error
        self.completed_at = time.time()

    def mark_cancelled(self) -> None:
        """Mark this work item as cancelled."""
        self.status = WorkStatus.CANCELLED
        self.completed_at = time.time()

    def is_retriable(self) -> bool:
        """
        Check if this work item can be retried.

        Returns:
            True if the work item can be retried, False otherwise
        """
        return self.status == WorkStatus.FAILED and self.attempt < self.max_attempts

    @property
    def processing_time(self) -> Optional[float]:
        """
        Calculate the processing time for this work item.

        Returns:
            Processing time in seconds or None if not started or completed
        """
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def waiting_time(self) -> Optional[float]:
        """
        Calculate the waiting time for this work item.

        Returns:
            Waiting time in seconds or None if not started
        """
        if self.started_at:
            return self.started_at - self.created_at
        return None

    @property
    def total_time(self) -> Optional[float]:
        """
        Calculate the total time for this work item.

        Returns:
            Total time in seconds or None if not completed
        """
        if self.completed_at:
            return self.completed_at - self.created_at
        return None


class PriorityQueue(Queue):
    """
    Priority queue implementation for asyncio.

    Items with higher priority values are processed first.
    """

    def _init(self, maxsize: int) -> None:
        """Initialize with an empty list."""
        self._queue: List[Tuple[int, Any]] = []

    def _put(self, item: Tuple[int, T]) -> None:
        """Put an item into the queue with priority."""
        # Insert item maintaining sort by priority (highest first)
        # Python's heapq is min-heap but we want max-heap for priorities
        # So we negate the priority value to get the desired behavior
        priority, data = item
        for i, (p, _) in enumerate(self._queue):
            if -priority > p:  # Note the negative priority comparison
                self._queue.insert(i, (-priority, data))
                break
        else:
            self._queue.append((-priority, data))

    def _get(self) -> T:
        """Get the next item with highest priority."""
        return self._queue.pop(0)[1]


class WorkQueue(Generic[T, R]):
    """
    Work queue for parallel processing of tasks.

    This class provides a robust work queue implementation that supports
    multiple worker types (thread, process, asyncio), priority-based scheduling,
    dependency management, and automatic retries.
    """

    def __init__(
        self,
        worker_type: WorkerType = WorkerType.THREAD,
        max_workers: int = 5,
        max_queue_size: int = 0,  # 0 means unlimited
        worker_function: Optional[Callable[[T], R]] = None,
        async_worker_function: Optional[Callable[[T], asyncio.Future[R]]] = None,
        on_complete: Optional[Callable[[WorkItem[T, R]], None]] = None,
        on_error: Optional[Callable[[WorkItem[T, R]], None]] = None,
    ):
        """
        Initialize the work queue.

        Args:
            worker_type: Type of worker to use for processing tasks
            max_workers: Maximum number of concurrent workers
            max_queue_size: Maximum size of the queue (0 means unlimited)
            worker_function: Function to process work items for thread/process workers
            async_worker_function: Async function to process work items for asyncio workers
            on_complete: Callback function called when a work item completes
            on_error: Callback function called when a work item fails
        """
        self.worker_type = worker_type
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.worker_function = worker_function
        self.async_worker_function = async_worker_function
        self.on_complete = on_complete
        self.on_error = on_error

        # Initialize appropriate executor based on worker type
        if worker_type == WorkerType.THREAD:
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
        elif worker_type == WorkerType.PROCESS:
            self.executor = ProcessPoolExecutor(max_workers=max_workers)
        else:
            self.executor = None

        # Initialize queue
        if worker_type == WorkerType.ASYNCIO:
            self.queue: Queue = PriorityQueue(maxsize=max_queue_size)
        else:
            # For thread/process workers, we'll use an in-memory list
            self.queue = []

        # Tracking collections
        self.work_items: Dict[str, WorkItem[T, R]] = {}
        self.pending_work_ids: Set[str] = set()
        self.running_work_ids: Set[str] = set()
        self.completed_work_ids: Set[str] = set()
        self.failed_work_ids: Set[str] = set()
        self.futures: Dict[str, Future] = {}

        # State tracking
        self.is_running = False
        self.should_stop = False
        self.worker_task = None

    async def start(self) -> None:
        """Start processing items in the queue."""
        if self.is_running:
            return

        self.is_running = True
        self.should_stop = False

        if self.worker_type == WorkerType.ASYNCIO:
            # Start asyncio worker
            self.worker_task = asyncio.create_task(self._process_asyncio_queue())
        else:
            # For thread/process workers, we need to manage the queue ourselves
            self.worker_task = asyncio.create_task(self._manage_executor_queue())

        logger.info(f"Work queue started with {self.max_workers} {self.worker_type.value} workers")

    async def stop(self, wait_for_completion: bool = True) -> None:
        """
        Stop processing items in the queue.

        Args:
            wait_for_completion: If True, wait for all items to complete before stopping
        """
        if not self.is_running:
            return

        self.should_stop = True

        if wait_for_completion:
            # Wait for all running work to complete
            if self.running_work_ids:
                logger.info(f"Waiting for {len(self.running_work_ids)} running tasks to complete")
                while self.running_work_ids and not self.should_stop:
                    await asyncio.sleep(0.1)

        # Cancel all pending work
        for work_id in list(self.pending_work_ids):
            work_item = self.work_items.get(work_id)
            if work_item:
                work_item.mark_cancelled()
                self.pending_work_ids.remove(work_id)

        # Shut down executor
        if self.executor:
            self.executor.shutdown(wait=wait_for_completion)

        # Cancel asyncio worker task
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        self.is_running = False
        logger.info("Work queue stopped")

    async def add_work(
        self,
        input_data: T,
        priority: int = 0,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        max_attempts: int = 3,
    ) -> str:
        """
        Add a work item to the queue.

        Args:
            input_data: Input data for the work function
            priority: Priority of the work item (higher values have higher priority)
            dependencies: IDs of work items that must complete before this one
            metadata: Additional metadata for the work item
            max_attempts: Maximum number of attempts allowed

        Returns:
            ID of the created work item
        """
        # Create work item
        work_item = WorkItem[T, R](
            input_data=input_data,
            priority=priority,
            dependencies=set(dependencies or []),
            metadata=metadata or {},
            max_attempts=max_attempts,
        )

        # Add to tracking collections
        self.work_items[work_item.id] = work_item
        self.pending_work_ids.add(work_item.id)

        # Add to queue based on worker type
        if self.worker_type == WorkerType.ASYNCIO:
            # For asyncio, we add the item ID to the queue with priority
            await self.queue.put((priority, work_item.id))
        else:
            # For thread/process workers, we add the item to our in-memory list
            self.queue.append(work_item.id)
            # Sort the queue by priority (highest first)
            self.queue.sort(key=lambda wid: self.work_items[wid].priority, reverse=True)

        logger.debug(f"Added work item {work_item.id} to queue with priority {priority}")
        return work_item.id

    async def add_batch(
        self,
        batch_items: List[T],
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        max_attempts: int = 3,
    ) -> List[str]:
        """
        Add a batch of work items to the queue.

        Args:
            batch_items: List of input data items
            priority: Priority for all items (higher values have higher priority)
            metadata: Base metadata for all items (will be copied)
            max_attempts: Maximum number of attempts allowed

        Returns:
            List of work item IDs
        """
        work_ids = []
        for input_data in batch_items:
            # Create a copy of metadata for each item
            item_metadata = dict(metadata or {})
            work_id = await self.add_work(
                input_data=input_data,
                priority=priority,
                metadata=item_metadata,
                max_attempts=max_attempts,
            )
            work_ids.append(work_id)

        logger.debug(f"Added batch of {len(batch_items)} work items to queue")
        return work_ids

    async def add_with_dependencies(
        self,
        dependency_graph: Dict[T, List[T]],
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        max_attempts: int = 3,
    ) -> Dict[T, str]:
        """
        Add work items with dependencies to the queue.

        Args:
            dependency_graph: Dictionary mapping input data to its dependencies
            priority: Priority for all items (higher values have higher priority)
            metadata: Base metadata for all items (will be copied)
            max_attempts: Maximum number of attempts allowed

        Returns:
            Dictionary mapping input data to work item IDs
        """
        # First pass: create all work items without dependencies
        data_to_work_id = {}
        for input_data in dependency_graph:
            # Create a copy of metadata for each item
            item_metadata = dict(metadata or {})
            work_id = await self.add_work(
                input_data=input_data,
                priority=priority,
                metadata=item_metadata,
                max_attempts=max_attempts,
            )
            data_to_work_id[input_data] = work_id

        # Second pass: update dependencies
        for input_data, dependencies in dependency_graph.items():
            work_id = data_to_work_id[input_data]
            work_item = self.work_items[work_id]

            # Add dependencies
            for dep_data in dependencies:
                if dep_data in data_to_work_id:
                    dep_id = data_to_work_id[dep_data]
                    work_item.dependencies.add(dep_id)

        logger.debug(f"Added {len(dependency_graph)} work items with dependencies to queue")
        return data_to_work_id

    async def get_result(self, work_id: str, timeout: Optional[float] = None) -> R:
        """
        Get the result of a work item, waiting if necessary.

        Args:
            work_id: ID of the work item
            timeout: Maximum time to wait in seconds (None means wait indefinitely)

        Returns:
            Result of the work item

        Raises:
            KeyError: If the work item is not found
            asyncio.TimeoutError: If the timeout is reached
            Exception: If the work item failed with an exception
        """
        work_item = self.work_items.get(work_id)
        if not work_item:
            raise KeyError(f"Work item {work_id} not found")

        start_time = time.time()
        while work_item.status != WorkStatus.COMPLETED:
            if work_item.status == WorkStatus.FAILED:
                if work_item.error:
                    raise work_item.error
                raise RuntimeError(f"Work item {work_id} failed")

            if work_item.status == WorkStatus.CANCELLED:
                raise RuntimeError(f"Work item {work_id} was cancelled")

            # Check timeout
            if timeout is not None and time.time() - start_time > timeout:
                raise asyncio.TimeoutError(f"Timeout waiting for work item {work_id}")

            # Wait a bit before checking again
            await asyncio.sleep(0.1)

        return cast(R, work_item.result)

    async def get_batch_results(
        self,
        work_ids: List[str],
        timeout: Optional[float] = None,
        raise_on_error: bool = True,
    ) -> Dict[str, Union[R, Exception]]:
        """
        Get the results of multiple work items, waiting if necessary.

        Args:
            work_ids: IDs of the work items
            timeout: Maximum time to wait in seconds (None means wait indefinitely)
            raise_on_error: If True, raise an exception if any work item fails

        Returns:
            Dictionary mapping work IDs to results or exceptions

        Raises:
            asyncio.TimeoutError: If the timeout is reached
            Exception: If any work item failed and raise_on_error is True
        """
        results = {}
        start_time = time.time()

        # Create a set of IDs we're waiting for
        pending_ids = set(work_ids)

        while pending_ids:
            # Check each pending ID
            for work_id in list(pending_ids):
                work_item = self.work_items.get(work_id)
                if not work_item:
                    # Work item not found
                    results[work_id] = KeyError(f"Work item {work_id} not found")
                    pending_ids.remove(work_id)
                    continue

                if work_item.status == WorkStatus.COMPLETED:
                    # Work item completed
                    results[work_id] = work_item.result
                    pending_ids.remove(work_id)

                elif work_item.status == WorkStatus.FAILED:
                    # Work item failed
                    if work_item.error:
                        results[work_id] = work_item.error
                    else:
                        results[work_id] = RuntimeError(f"Work item {work_id} failed")
                    pending_ids.remove(work_id)

                    if raise_on_error:
                        error = results[work_id]
                        if isinstance(error, Exception):
                            raise error

                elif work_item.status == WorkStatus.CANCELLED:
                    # Work item cancelled
                    results[work_id] = RuntimeError(f"Work item {work_id} was cancelled")
                    pending_ids.remove(work_id)

                    if raise_on_error:
                        raise results[work_id]

            # Check timeout
            if timeout is not None and time.time() - start_time > timeout:
                raise asyncio.TimeoutError(f"Timeout waiting for {len(pending_ids)} work items")

            # If we still have pending items, wait a bit before checking again
            if pending_ids:
                await asyncio.sleep(0.1)

        return results

    async def cancel_work(self, work_id: str) -> bool:
        """
        Cancel a work item.

        Args:
            work_id: ID of the work item

        Returns:
            True if the work item was cancelled, False otherwise
        """
        work_item = self.work_items.get(work_id)
        if not work_item:
            return False

        # Can only cancel pending or failed work
        if work_item.status not in [WorkStatus.PENDING, WorkStatus.FAILED]:
            return False

        # Update status
        work_item.mark_cancelled()

        # Remove from tracking collections
        if work_id in self.pending_work_ids:
            self.pending_work_ids.remove(work_id)

        if work_id in self.failed_work_ids:
            self.failed_work_ids.remove(work_id)

        # For asyncio queues, we can't remove items directly
        # They'll be filtered out when dequeueing
        if self.worker_type != WorkerType.ASYNCIO and work_id in self.queue:
            self.queue.remove(work_id)

        # Cancel future if it exists
        if work_id in self.futures:
            self.futures[work_id].cancel()
            del self.futures[work_id]

        logger.debug(f"Cancelled work item {work_id}")
        return True

    async def retry_work(self, work_id: str) -> bool:
        """
        Retry a failed work item.

        Args:
            work_id: ID of the work item

        Returns:
            True if the work item was queued for retry, False otherwise
        """
        work_item = self.work_items.get(work_id)
        if not work_item:
            return False

        # Can only retry failed work that hasn't exceeded max attempts
        if not work_item.is_retriable():
            return False

        # Update status
        work_item.status = WorkStatus.PENDING

        # Update tracking collections
        if work_id in self.failed_work_ids:
            self.failed_work_ids.remove(work_id)

        self.pending_work_ids.add(work_id)

        # Add back to queue
        if self.worker_type == WorkerType.ASYNCIO:
            await self.queue.put((work_item.priority, work_id))
        else:
            self.queue.append(work_id)
            # Sort the queue by priority
            self.queue.sort(key=lambda wid: self.work_items[wid].priority, reverse=True)

        logger.debug(f"Retrying work item {work_id} (attempt {work_item.attempt + 1})")
        return True

    def get_work_item(self, work_id: str) -> Optional[WorkItem[T, R]]:
        """
        Get a work item by ID.

        Args:
            work_id: ID of the work item

        Returns:
            The work item or None if not found
        """
        return self.work_items.get(work_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the work queue.

        Returns:
            Dictionary with queue statistics
        """
        completed_items = [
            item for item in self.work_items.values() if item.status == WorkStatus.COMPLETED
        ]
        failed_items = [
            item for item in self.work_items.values() if item.status == WorkStatus.FAILED
        ]

        # Calculate average processing times
        processing_times = [
            item.processing_time for item in completed_items if item.processing_time is not None
        ]
        avg_processing_time = (
            sum(processing_times) / len(processing_times) if processing_times else 0
        )

        # Calculate average waiting times
        waiting_times = [
            item.waiting_time for item in completed_items if item.waiting_time is not None
        ]
        avg_waiting_time = sum(waiting_times) / len(waiting_times) if waiting_times else 0

        return {
            "worker_type": self.worker_type.value,
            "max_workers": self.max_workers,
            "is_running": self.is_running,
            "queue_size": (
                self.queue.qsize() if self.worker_type == WorkerType.ASYNCIO else len(self.queue)
            ),
            "pending_count": len(self.pending_work_ids),
            "running_count": len(self.running_work_ids),
            "completed_count": len(self.completed_work_ids),
            "failed_count": len(self.failed_work_ids),
            "total_count": len(self.work_items),
            "avg_processing_time": avg_processing_time,
            "avg_waiting_time": avg_waiting_time,
            "success_rate": (
                len(completed_items) / (len(completed_items) + len(failed_items))
                if completed_items or failed_items
                else 0
            ),
        }

    async def _process_asyncio_queue(self) -> None:
        """Process items in the asyncio queue."""
        if not self.async_worker_function:
            logger.error("Cannot process asyncio queue without async_worker_function")
            return

        # Track active tasks
        active_tasks: Set[asyncio.Task] = set()

        while not self.should_stop:
            try:
                # Clean up completed tasks
                done_tasks = {task for task in active_tasks if task.done()}
                active_tasks -= done_tasks

                # Check if we can process more items
                if len(active_tasks) >= self.max_workers:
                    # Max workers reached, wait for some to complete
                    await asyncio.sleep(0.1)
                    continue

                try:
                    # Get the next item from the queue with a timeout
                    # Using get_nowait() + sleep instead of wait_for(get()) for better cancellation
                    priority, work_id = self.queue.get_nowait()

                    # Get the work item
                    work_item = self.work_items.get(work_id)
                    if not work_item:
                        # Work item not found, skip
                        self.queue.task_done()
                        continue

                    # Skip cancelled items
                    if work_item.status == WorkStatus.CANCELLED:
                        self.queue.task_done()
                        continue

                    # Check dependencies
                    if work_item.dependencies:
                        # Check if all dependencies are completed
                        deps_completed = all(
                            self.work_items.get(dep_id) is not None
                            and self.work_items[dep_id].status == WorkStatus.COMPLETED
                            for dep_id in work_item.dependencies
                        )

                        if not deps_completed:
                            # Not all dependencies are completed, put back in queue
                            await self.queue.put((priority, work_id))
                            self.queue.task_done()
                            await asyncio.sleep(0.1)  # Avoid tight loop
                            continue

                    # Mark as running
                    work_item.mark_running()
                    self.pending_work_ids.remove(work_id)
                    self.running_work_ids.add(work_id)

                    # Create task to process the item
                    task = asyncio.create_task(self._process_asyncio_item(work_item))
                    active_tasks.add(task)

                    # Mark queue task as done
                    self.queue.task_done()

                except QueueEmpty:
                    # Queue is empty, wait a bit
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                # Worker was cancelled
                logger.debug("Asyncio worker cancelled")
                break

            except Exception as e:
                # Log error but keep running
                logger.error(f"Error in asyncio worker: {str(e)}", exc_info=True)
                await asyncio.sleep(1)  # Wait a bit to avoid tight loop

        # Wait for all active tasks to complete
        if active_tasks:
            await asyncio.gather(*active_tasks, return_exceptions=True)

    async def _process_asyncio_item(self, work_item: WorkItem[T, R]) -> None:
        """
        Process a single work item using the async worker function.

        Args:
            work_item: Work item to process
        """
        work_id = work_item.id
        try:
            # Process the item
            result = await self.async_worker_function(work_item.input_data)

            # Mark as completed
            work_item.mark_completed(result)
            self.running_work_ids.remove(work_id)
            self.completed_work_ids.add(work_id)

            # Call completion callback
            if self.on_complete:
                try:
                    self.on_complete(work_item)
                except Exception as e:
                    logger.error(f"Error in completion callback: {str(e)}", exc_info=True)

        except Exception as e:
            # Mark as failed
            work_item.mark_failed(e)
            self.running_work_ids.remove(work_id)
            self.failed_work_ids.add(work_id)

            # Call error callback
            if self.on_error:
                try:
                    self.on_error(work_item)
                except Exception as e:
                    logger.error(f"Error in error callback: {str(e)}", exc_info=True)

            # If retriable, add back to queue
            if work_item.is_retriable():
                logger.debug(f"Work item {work_id} failed, retrying (attempt {work_item.attempt})")
                await self.retry_work(work_id)
            else:
                logger.warning(f"Work item {work_id} failed after {work_item.attempt} attempts")

    async def _manage_executor_queue(self) -> None:
        """Manage the executor queue for thread/process workers."""
        if not self.executor or not self.worker_function:
            logger.error("Cannot manage executor queue without executor and worker_function")
            return

        # Dictionary of futures by work_id
        futures: Dict[str, Future] = {}

        while not self.should_stop:
            try:
                # Complete finished futures
                done_futures = [fut for fut in futures.values() if fut.done()]
                for future in done_futures:
                    work_id = next(wid for wid, fut in futures.items() if fut is future)
                    self._handle_completed_future(work_id, future)
                    del futures[work_id]

                # Check if we can submit more work
                if len(futures) >= self.max_workers:
                    # Max workers reached, wait for some to complete
                    await asyncio.sleep(0.1)
                    continue

                # Get the next work item
                if not self.queue:
                    # Queue is empty, wait a bit
                    await asyncio.sleep(0.1)
                    continue

                # Pop the next item from the queue
                work_id = self.queue.pop(0)

                # Get the work item
                work_item = self.work_items.get(work_id)
                if not work_item:
                    # Work item not found, skip
                    continue

                # Skip cancelled items
                if work_item.status == WorkStatus.CANCELLED:
                    continue

                # Check dependencies
                if work_item.dependencies:
                    # Check if all dependencies are completed
                    deps_completed = all(
                        self.work_items.get(dep_id) is not None
                        and self.work_items[dep_id].status == WorkStatus.COMPLETED
                        for dep_id in work_item.dependencies
                    )

                    if not deps_completed:
                        # Not all dependencies are completed, put back in queue
                        self.queue.append(work_id)
                        # Sort the queue by priority
                        self.queue.sort(key=lambda wid: self.work_items[wid].priority, reverse=True)
                        await asyncio.sleep(0.1)  # Avoid tight loop
                        continue

                # Mark as running
                work_item.mark_running()
                self.pending_work_ids.remove(work_id)
                self.running_work_ids.add(work_id)

                # Submit to executor
                future = self.executor.submit(self._process_worker_item, work_item.id)
                futures[work_id] = future
                self.futures[work_id] = future

            except asyncio.CancelledError:
                # Worker was cancelled
                logger.debug("Executor manager cancelled")
                break

            except Exception as e:
                # Log error but keep running
                logger.error(f"Error in executor manager: {str(e)}", exc_info=True)
                await asyncio.sleep(1)  # Wait a bit to avoid tight loop

        # Cancel all pending futures
        for future in futures.values():
            future.cancel()

    def _process_worker_item(self, work_id: str) -> None:
        """
        Process a work item in the thread/process pool.

        Args:
            work_id: ID of the work item to process
        """
        # Get the work item
        work_item = self.work_items.get(work_id)
        if not work_item:
            return

        try:
            # Process the item
            result = self.worker_function(work_item.input_data)

            # Mark as completed
            work_item.mark_completed(result)

        except Exception as e:
            # Mark as failed
            work_item.mark_failed(e)

    def _handle_completed_future(self, work_id: str, future: Future) -> None:
        """
        Handle a completed future from the executor.

        Args:
            work_id: ID of the work item
            future: Completed future
        """
        # Get the work item
        work_item = self.work_items.get(work_id)
        if not work_item:
            return

        # Update tracking collections
        self.running_work_ids.remove(work_id)

        if work_item.status == WorkStatus.COMPLETED:
            # Work completed successfully
            self.completed_work_ids.add(work_id)

            # Call completion callback
            if self.on_complete:
                try:
                    self.on_complete(work_item)
                except Exception as e:
                    logger.error(f"Error in completion callback: {str(e)}", exc_info=True)

        elif work_item.status == WorkStatus.FAILED:
            # Work failed
            self.failed_work_ids.add(work_id)

            # Call error callback
            if self.on_error:
                try:
                    self.on_error(work_item)
                except Exception as e:
                    logger.error(f"Error in error callback: {str(e)}", exc_info=True)

            # If retriable, add back to queue
            if work_item.is_retriable():
                logger.debug(f"Work item {work_id} failed, retrying (attempt {work_item.attempt})")
                work_item.status = WorkStatus.PENDING
                self.pending_work_ids.add(work_id)
                self.failed_work_ids.remove(work_id)
                self.queue.append(work_id)
                # Sort the queue by priority
                self.queue.sort(key=lambda wid: self.work_items[wid].priority, reverse=True)
            else:
                logger.warning(f"Work item {work_id} failed after {work_item.attempt} attempts")


# Convenience functions


async def run_in_thread_pool(
    func: Callable[[T], R],
    items: List[T],
    max_workers: int = 5,
    on_complete: Optional[Callable[[WorkItem[T, R]], None]] = None,
    on_error: Optional[Callable[[WorkItem[T, R]], None]] = None,
) -> List[R]:
    """
    Run a function on multiple items in a thread pool.

    Args:
        func: Function to apply to each item
        items: List of items to process
        max_workers: Maximum number of threads to use
        on_complete: Optional callback for completed items
        on_error: Optional callback for failed items

    Returns:
        List of results in the same order as items
    """
    # Create work queue
    queue = WorkQueue[T, R](
        worker_type=WorkerType.THREAD,
        max_workers=max_workers,
        worker_function=func,
        on_complete=on_complete,
        on_error=on_error,
    )

    try:
        # Start queue
        await queue.start()

        # Add items to queue
        work_ids = await queue.add_batch(items)

        # Wait for all items to complete
        results = await queue.get_batch_results(work_ids)

        # Return results in original order
        return [results[wid] for wid in work_ids]

    finally:
        # Stop queue
        await queue.stop()


async def run_in_process_pool(
    func: Callable[[T], R],
    items: List[T],
    max_workers: int = 5,
    on_complete: Optional[Callable[[WorkItem[T, R]], None]] = None,
    on_error: Optional[Callable[[WorkItem[T, R]], None]] = None,
) -> List[R]:
    """
    Run a function on multiple items in a process pool.

    Args:
        func: Function to apply to each item
        items: List of items to process
        max_workers: Maximum number of processes to use
        on_complete: Optional callback for completed items
        on_error: Optional callback for failed items

    Returns:
        List of results in the same order as items
    """
    # Create work queue
    queue = WorkQueue[T, R](
        worker_type=WorkerType.PROCESS,
        max_workers=max_workers,
        worker_function=func,
        on_complete=on_complete,
        on_error=on_error,
    )

    try:
        # Start queue
        await queue.start()

        # Add items to queue
        work_ids = await queue.add_batch(items)

        # Wait for all items to complete
        results = await queue.get_batch_results(work_ids)

        # Return results in original order
        return [results[wid] for wid in work_ids]

    finally:
        # Stop queue
        await queue.stop()


async def run_with_asyncio(
    func: Callable[[T], asyncio.Future[R]],
    items: List[T],
    max_workers: int = 5,
    on_complete: Optional[Callable[[WorkItem[T, R]], None]] = None,
    on_error: Optional[Callable[[WorkItem[T, R]], None]] = None,
) -> List[R]:
    """
    Run a function on multiple items with asyncio.

    Args:
        func: Async function to apply to each item
        items: List of items to process
        max_workers: Maximum number of concurrent tasks
        on_complete: Optional callback for completed items
        on_error: Optional callback for failed items

    Returns:
        List of results in the same order as items
    """
    # Create work queue
    queue = WorkQueue[T, R](
        worker_type=WorkerType.ASYNCIO,
        max_workers=max_workers,
        async_worker_function=func,
        on_complete=on_complete,
        on_error=on_error,
    )

    try:
        # Start queue
        await queue.start()

        # Add items to queue
        work_ids = await queue.add_batch(items)

        # Wait for all items to complete
        results = await queue.get_batch_results(work_ids)

        # Return results in original order
        return [results[wid] for wid in work_ids]

    finally:
        # Stop queue
        await queue.stop()
