"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Intelligent batching strategies for optimizing ETL performance.

This module provides various batching strategies to optimize the performance
of extraction, transformation, and loading operations in the ETL pipeline.
Each strategy is designed to handle different performance constraints and
optimization goals.
"""

import bisect
import logging
import math
import os
import psutil
import random
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar, Union, cast

T = TypeVar('T')  # Generic type for entities

logger = logging.getLogger("ztoq.batch_strategies")


class BatchStrategy(Generic[T], ABC):
    """
    Abstract base class for batch creation strategies.

    All batching strategies must implement the create_batches method to
    divide a list of entities into optimized batches according to their
    specific logic.
    """

    @abstractmethod
    def create_batches(self, entities: List[T]) -> List[List[T]]:
        """
        Create batches from a list of entities.

        Args:
            entities: List of entities to batch

        Returns:
            List of batches, where each batch is a list of entities
        """
        pass


class SizeBatchStrategy(BatchStrategy[T]):
    """
    Batch strategy based on total size of entities.

    This strategy creates batches that don't exceed a maximum size limit,
    which is useful for memory-constrained environments or API limitations.
    """

    def __init__(
        self,
        max_batch_size: int,
        size_estimator: Optional[Callable[[T], int]] = None
    ):
        """
        Initialize the size-based batch strategy.

        Args:
            max_batch_size: Maximum size for a batch
            size_estimator: Function to estimate the size of an entity (defaults to using
                           the 'size' field if available or 1 otherwise)
        """
        self.max_batch_size = max_batch_size
        self.size_estimator = size_estimator or self._default_size_estimator

    def _default_size_estimator(self, entity: T) -> int:
        """Default function to estimate entity size."""
        if isinstance(entity, dict) and 'size' in entity:
            return cast(int, entity['size'])
        return 1  # Default size if no estimator provided

    def create_batches(self, entities: List[T]) -> List[List[T]]:
        """
        Create batches based on size constraints.

        Args:
            entities: List of entities to batch

        Returns:
            List of batches that each fit within the maximum size limit
        """
        if not entities:
            return []

        batches = []
        current_batch = []
        current_size = 0

        for entity in entities:
            entity_size = self.size_estimator(entity)

            # If adding this entity would exceed the max size, start a new batch
            if current_size + entity_size > self.max_batch_size and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_size = 0

            # Special case: if a single entity exceeds max size, it gets its own batch
            if entity_size > self.max_batch_size:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_size = 0
                batches.append([entity])
                continue

            current_batch.append(entity)
            current_size += entity_size

        # Add the last batch if it's not empty
        if current_batch:
            batches.append(current_batch)

        return batches


class TimeBatchStrategy(BatchStrategy[T]):
    """
    Batch strategy based on estimated processing time.

    This strategy creates batches that don't exceed a maximum estimated
    processing time, which is useful for balancing workload and optimizing
    overall throughput.
    """

    def __init__(
        self,
        time_estimator: Callable[[T], float],
        max_batch_time: float
    ):
        """
        Initialize the time-based batch strategy.

        Args:
            time_estimator: Function to estimate processing time for an entity
            max_batch_time: Maximum estimated processing time for a batch
        """
        self.time_estimator = time_estimator
        self.max_batch_time = max_batch_time

    def create_batches(self, entities: List[T]) -> List[List[T]]:
        """
        Create batches based on estimated processing time.

        Args:
            entities: List of entities to batch

        Returns:
            List of batches that each fit within the maximum time limit
        """
        if not entities:
            return []

        batches = []
        current_batch = []
        current_time = 0.0

        for entity in entities:
            entity_time = self.time_estimator(entity)

            # If adding this entity would exceed the max time, start a new batch
            # If adding this entity would exceed the max time, start a new batch
            if current_time + entity_time > self.max_batch_time and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_time = 0.0

            # Special case: if a single entity exceeds max time, it gets its own batch
            # But we need to ensure we don't have entities that can't be processed at all
            if entity_time > self.max_batch_time:
                # For entities that exceed the max time on their own, we still include them
                # but warn about them since they'll always exceed the time limit
                logger.warning(f"Entity processing time {entity_time:.2f}s exceeds max batch time {self.max_batch_time:.2f}s")
                if current_batch:  # If we have an existing batch, finalize it first
                    batches.append(current_batch)
                    current_batch = []
                    current_time = 0.0
                batches.append([entity])  # Put the large entity in its own batch
                continue

            current_batch.append(entity)
            current_time += entity_time

        # Add the last batch if it's not empty
        if current_batch:
            batches.append(current_batch)

        return batches


class AdaptiveBatchStrategy(BatchStrategy[T]):
    """
    Adaptive batch strategy that learns the optimal batch size.

    This strategy adjusts the batch size based on actual processing times to
    find the optimal batch size for maximizing throughput. It's useful for
    environments where the ideal batch size may change over time.
    """

    def __init__(
        self,
        initial_batch_size: int = 10,
        min_batch_size: int = 1,
        max_batch_size: int = 100,
        target_processing_time: float = 1.0,
        adaptation_rate: float = 0.1
    ):
        """
        Initialize the adaptive batch strategy.

        Args:
            initial_batch_size: Starting batch size
            min_batch_size: Minimum allowed batch size
            max_batch_size: Maximum allowed batch size
            target_processing_time: Target processing time per batch in seconds
            adaptation_rate: Rate at which batch size is adjusted (0.1 = 10% change)
        """
        self.current_batch_size = initial_batch_size
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.target_processing_time = target_processing_time
        self.adaptation_rate = adaptation_rate
        self.processing_history: List[Tuple[int, float]] = []  # (batch_size, time) pairs

    def create_batches(self, entities: List[T]) -> List[List[T]]:
        """
        Create batches using the current optimal batch size.

        Args:
            entities: List of entities to batch

        Returns:
            List of batches with the current optimal batch size
        """
        if not entities:
            return []

        # Use simple fixed-size batching with the current batch size
        batch_size = self.current_batch_size
        return create_batches(entities, batch_size=batch_size)

    def adapt(self, processing_time: float) -> int:
        """
        Adapt the batch size based on actual processing time.

        Args:
            processing_time: Actual processing time for the last batch

        Returns:
            The new batch size
        """
        # Record processing time for this batch size
        self.processing_history.append((self.current_batch_size, processing_time))

        # Calculate new batch size
        new_batch_size = self.adapt_batch_size(self.current_batch_size, processing_time)

        # Update current batch size
        self.current_batch_size = new_batch_size
        return new_batch_size

    def adapt_batch_size(self, batch_size: int, processing_time: float) -> int:
        """
        Calculate the adapted batch size based on processing time.

        Args:
            batch_size: Current batch size
            processing_time: Processing time for the batch

        Returns:
            New batch size
        """
        # If processing time is too high, decrease batch size
        if processing_time > self.target_processing_time:
            # Calculate adjustment factor (larger difference = larger adjustment)
            ratio = processing_time / self.target_processing_time
            adjustment = max(0.5, min(0.9, 1.0 / ratio))  # Limit extreme adjustments
            new_size = max(self.min_batch_size, int(batch_size * adjustment))
        # If processing time is too low, increase batch size
        elif processing_time < self.target_processing_time * 0.8:  # 20% below target
            # Calculate adjustment factor
            ratio = self.target_processing_time / max(0.001, processing_time)  # Avoid division by zero
            adjustment = min(1.5, max(1.1, ratio * self.adaptation_rate + 1.0))
            new_size = min(self.max_batch_size, int(batch_size * adjustment))
        # If processing time is close to target, maintain batch size
        else:
            new_size = batch_size

        # Cap at min/max bounds
        new_size = max(self.min_batch_size, min(new_size, self.max_batch_size))

        # Log the adaptation
        if new_size != batch_size:
            logger.debug(
                f"Adaptive batch size changed from {batch_size} to {new_size} "
                f"(processing time: {processing_time:.3f}s, target: {self.target_processing_time:.3f}s)"
            )

        return new_size


class EntityTypeBatchStrategy(BatchStrategy[T]):
    """
    Batch strategy that groups entities by type.

    This strategy creates batches of entities that have the same type or
    category, which is useful for operations that are more efficient when
    processing similar entities together.
    """

    def __init__(
        self,
        type_extractor: Callable[[T], Any],
        max_batch_size: Optional[int] = None
    ):
        """
        Initialize the entity type batch strategy.

        Args:
            type_extractor: Function to extract the type or category from an entity
            max_batch_size: Optional maximum batch size limit
        """
        self.type_extractor = type_extractor
        self.max_batch_size = max_batch_size

    def create_batches(self, entities: List[T]) -> List[List[T]]:
        """
        Create batches grouped by entity type.

        Args:
            entities: List of entities to batch

        Returns:
            List of batches where each batch contains entities of the same type
        """
        if not entities:
            return []

        # Group entities by type
        type_groups: Dict[Any, List[T]] = {}
        for entity in entities:
            entity_type = self.type_extractor(entity)
            if entity_type not in type_groups:
                type_groups[entity_type] = []
            type_groups[entity_type].append(entity)

        # Convert groups to batches
        batches = []
        for entity_type, group in type_groups.items():
            # If max batch size is specified, split large groups
            if self.max_batch_size and len(group) > self.max_batch_size:
                for i in range(0, len(group), self.max_batch_size):
                    batch = group[i:i + self.max_batch_size]
                    batches.append(batch)
            else:
                batches.append(group)

        return batches


class SimilarityBatchStrategy(BatchStrategy[T]):
    """
    Batch strategy that groups similar entities together.

    This strategy creates batches of entities that have similar features or
    characteristics, which can improve processing efficiency for operations
    that benefit from handling similar items together.
    """

    def __init__(
        self,
        feature_extractor: Callable[[T], Tuple],
        similarity_threshold: float = 0.8,
        max_batch_size: Optional[int] = None
    ):
        """
        Initialize the similarity-based batch strategy.

        Args:
            feature_extractor: Function to extract features for similarity comparison
            similarity_threshold: Threshold for considering entities similar (0-1)
            max_batch_size: Optional maximum batch size limit
        """
        self.feature_extractor = feature_extractor
        self.similarity_threshold = similarity_threshold
        self.max_batch_size = max_batch_size

    def create_batches(self, entities: List[T]) -> List[List[T]]:
        """
        Create batches of similar entities.

        Args:
            entities: List of entities to batch

        Returns:
            List of batches where each batch contains similar entities
        """
        if not entities:
            return []

        remaining = entities.copy()
        batches = []

        while remaining:
            # Take the first entity as the reference for a new batch
            reference = remaining.pop(0)
            ref_features = self.feature_extractor(reference)

            # Start a new batch with the reference entity
            current_batch = [reference]

            # Find similar entities
            similar_indices = []
            for i, entity in enumerate(remaining):
                features = self.feature_extractor(entity)

                # Calculate similarity (Euclidean distance-based)
                squared_diffs = sum((a - b) ** 2 for a, b in zip(ref_features, features))
                distance = squared_diffs ** 0.5

                # Normalize distance to similarity score
                # For simplicity, we assume features are normalized to [0, 1]
                # The max possible distance in N-dimensional space with normalized
                # features is sqrt(N), so we divide by that to get a [0, 1] similarity
                max_distance = math.sqrt(len(ref_features))
                similarity = 1 - distance / max_distance

                if similarity >= self.similarity_threshold:
                    similar_indices.append(i)

                    # If we've reached max batch size, stop adding similar entities
                    if self.max_batch_size and len(current_batch) + len(similar_indices) >= self.max_batch_size:
                        break

            # Add similar entities to the batch and remove from remaining
            # Process in reverse order to avoid index shifting
            for i in sorted(similar_indices, reverse=True):
                current_batch.append(remaining.pop(i))

            batches.append(current_batch)

        return batches


def configure_optimal_batch_size(
    entity_count: int,
    available_memory: Optional[int] = None,
    entity_size_mb: float = 0.1,
    parallelism: int = 4,
    api_rate_limit: Optional[int] = None,
    min_batch_size: int = 1,
    max_batch_size: int = 1000
) -> int:
    """
    Configure the optimal batch size based on system constraints.

    This function calculates an optimal batch size considering memory constraints,
    API rate limits, and parallelism.

    Args:
        entity_count: Total number of entities to process
        available_memory: Available memory in MB (if None, uses system memory)
        entity_size_mb: Average memory footprint per entity in MB
        parallelism: Number of parallel workers
        api_rate_limit: API rate limit in requests per minute (if applicable)
        min_batch_size: Minimum allowed batch size
        max_batch_size: Maximum allowed batch size

    Returns:
        Optimal batch size
    """
    # If available memory not specified, estimate from system
    if available_memory is None:
        mem_info = psutil.virtual_memory()
        available_memory = int(mem_info.available / (1024 * 1024))  # Convert to MB

        # Leave some headroom (use only 80% of available memory)
        available_memory = int(available_memory * 0.8)

    # Calculate memory-based constraint
    # Each worker needs memory for its batch, so divide by parallelism
    memory_constraint = int(available_memory / entity_size_mb / parallelism)

    # Calculate rate limit constraint (if applicable)
    rate_constraint = max_batch_size
    if api_rate_limit:
        # Calculate requests per worker per minute
        requests_per_worker = api_rate_limit / parallelism

        # Add some safety margin (use 90% of the limit)
        rate_constraint = int(requests_per_worker * 0.9)

    # Calculate optimal batch size
    batch_size = min(memory_constraint, rate_constraint, entity_count)

    # Apply min/max constraints
    batch_size = max(min_batch_size, min(batch_size, max_batch_size))

    logger.info(
        f"Configured optimal batch size: {batch_size} "
        f"(memory constraint: {memory_constraint}, "
        f"rate constraint: {rate_constraint}, "
        f"total entities: {entity_count})"
    )

    return batch_size


def create_batches(
    entities: List[T],
    batch_size: Optional[int] = None,
    size_calculator: Optional[Callable[[List[T]], int]] = None,
    sort_key: Optional[Callable[[T], Any]] = None,
    reverse: bool = False
) -> List[List[T]]:
    """
    Create batches from a list of entities with optional sorting.

    This is a utility function that provides flexible batching with options
    for sorting entities first and calculating dynamic batch sizes.

    Args:
        entities: List of entities to batch
        batch_size: Fixed batch size (if None, uses size_calculator)
        size_calculator: Function to calculate batch size based on entities
        sort_key: Optional key function for sorting entities before batching
        reverse: Whether to sort in descending order

    Returns:
        List of batches
    """
    if not entities:
        return []

    # Make a copy to avoid modifying the input
    entities_copy = entities.copy()

    # Sort entities if requested
    if sort_key:
        entities_copy.sort(key=sort_key, reverse=reverse)

    # Create batches
    batches = []

    # If using fixed batch size
    if batch_size:
        for i in range(0, len(entities_copy), batch_size):
            batches.append(entities_copy[i:i + batch_size])
    # If using dynamic batch size calculator
    elif size_calculator:
        remaining = entities_copy
        while remaining:
            # Calculate batch size for remaining entities
            size = size_calculator(remaining)
            size = max(1, min(size, len(remaining)))  # Ensure valid size

            batches.append(remaining[:size])
            remaining = remaining[size:]
    # Default to single batch if no sizing specified
    else:
        batches = [entities_copy]

    return batches


def estimate_processing_time(
    batch_size: int,
    history: List[Tuple[int, float]],
    default_estimate: float = 0.1
) -> float:
    """
    Estimate processing time for a batch based on historical data.

    This function uses linear interpolation or extrapolation to estimate
    processing time for a batch size based on previous batch processing times.

    Args:
        batch_size: Size of the batch to estimate time for
        history: List of (batch_size, processing_time) tuples from previous batches
        default_estimate: Default time estimate when no history is available

    Returns:
        Estimated processing time in seconds
    """
    if not history:
        # No history, use simple estimation
        return default_estimate * batch_size

    # Check for exact match in history
    for size, time in history:
        if size == batch_size:
            return time

    # Sort history by batch size for interpolation
    sorted_history = sorted(history)  # Sorts by first item in tuple (batch_size)

    # Find insertion point for interpolation
    idx = bisect.bisect_left([h[0] for h in sorted_history], batch_size)

    # If batch_size is smaller than all history, extrapolate from the smallest
    if idx == 0:
        size, time = sorted_history[0]
        # Linear extrapolation (assuming processing time scales linearly)
        return (time / size) * batch_size

    # If batch_size is larger than all history, extrapolate from the largest
    if idx == len(sorted_history):
        size, time = sorted_history[-1]
        # Linear extrapolation
        return (time / size) * batch_size

    # Interpolate between the two closest batch sizes
    size1, time1 = sorted_history[idx - 1]
    size2, time2 = sorted_history[idx]

    # Linear interpolation formula: y = y1 + (x - x1) * (y2 - y1) / (x2 - x1)
    estimated_time = time1 + (batch_size - size1) * (time2 - time1) / (size2 - size1)

    return estimated_time
