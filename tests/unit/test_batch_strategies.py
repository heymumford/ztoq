"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for the batching strategies module.

This module tests various intelligent batching strategies used to optimize
data processing performance in the ETL pipeline.
"""

import random
import time
from typing import Dict, List, Tuple, Any, Callable
import unittest.mock
import pytest

from ztoq.batch_strategies import (
    BatchStrategy, SizeBatchStrategy, TimeBatchStrategy, AdaptiveBatchStrategy,
    EntityTypeBatchStrategy, SimilarityBatchStrategy, configure_optimal_batch_size,
    create_batches, estimate_processing_time,
)

# Mark the whole module as unit tests
pytestmark = pytest.mark.unit


# Sample data for testing
def create_test_entities(count: int = 100) -> List[Dict[str, Any]]:
    """Create sample test case entities for testing."""
    return [
        {
            "id": f"TC-{i}",
            "name": f"Test Case {i}",
            "size": random.randint(1, 10),  # Size in KB
            "complexity": random.randint(1, 5),  # 1-5 complexity score
            "type": random.choice(["functional", "performance", "security", "usability"]),
            "steps_count": random.randint(1, 20),
            "attachments": random.randint(0, 3),
        }
        for i in range(count)
    ]


# Tests for individual batch strategies
def test_size_batch_strategy():
    """Test the size-based batching strategy."""
    entities = create_test_entities(100)
    strategy = SizeBatchStrategy(max_batch_size=30)

    batches = strategy.create_batches(entities)

    # Verify that each batch doesn't exceed the maximum size
    for batch in batches:
        total_size = sum(entity["size"] for entity in batch)
        assert total_size <= 30

    # Verify that all entities are included
    entities_in_batches = [entity for batch in batches for entity in batch]
    assert len(entities_in_batches) == len(entities)
    assert sorted([e["id"] for e in entities_in_batches]) == sorted([e["id"] for e in entities])


def test_time_batch_strategy():
    """Test the time-based batching strategy."""
    entities = create_test_entities(50)

    # Mock time estimator function
    def mock_time_estimator(entity: Dict[str, Any]) -> float:
        # Simple estimation based on complexity and steps
        return entity["complexity"] * 0.1 + entity["steps_count"] * 0.05

    strategy = TimeBatchStrategy(
        time_estimator=mock_time_estimator,
        max_batch_time=1.0  # 1 second max processing time per batch
    )

    batches = strategy.create_batches(entities)

    # Verify that estimated processing time for each batch doesn't exceed the limit
    # or contains only a single entity that exceeds the limit
    for batch in batches:
        estimated_time = sum(mock_time_estimator(entity) for entity in batch)
        if len(batch) == 1:
            # Single entity batches might exceed the limit if they can't be split further
            entity_time = mock_time_estimator(batch[0])
            if entity_time > 1.0:
                # This is expected for large entities
                continue
        assert estimated_time <= 1.0

    # All entities should be included
    entities_in_batches = [entity for batch in batches for entity in batch]
    assert len(entities_in_batches) == len(entities)


def test_adaptive_batch_strategy():
    """Test the adaptive batching strategy."""
    entities = create_test_entities(100)

    # Mock adaptation function
    processing_times = []

    def mock_process_batch(batch: List[Dict[str, Any]]) -> float:
        """Simulate processing a batch, returning the processing time."""
        # Simulated processing time increases with batch size but has some randomness
        processing_time = 0.01 * len(batch) + random.uniform(0.01, 0.05)
        processing_times.append((len(batch), processing_time))
        return processing_time

    strategy = AdaptiveBatchStrategy(
        initial_batch_size=10,
        min_batch_size=5,
        max_batch_size=30,
        target_processing_time=0.5,  # 0.5 seconds target
        adaptation_rate=0.2  # Adjust batch size by 20% each time
    )

    # Process several batches of entities to allow adaptation
    remaining_entities = entities.copy()
    all_batches = []

    # Run several adaptation cycles
    for _ in range(5):
        if not remaining_entities:
            break

        batch_size = strategy.current_batch_size
        batch = remaining_entities[:batch_size]
        remaining_entities = remaining_entities[batch_size:]

        all_batches.append(batch)
        processing_time = mock_process_batch(batch)

        # Adapt batch size based on processing time
        strategy.adapt(processing_time)

    # Verify that adaptation occurs in the right direction
    # If processing time is above target, batch size should decrease
    # If processing time is below target, batch size should increase
    for i in range(1, len(processing_times)):
        batch_size, time = processing_times[i-1]
        next_batch_size = strategy.adapt_batch_size(batch_size, time)

        if time > 0.5:  # Above target -> smaller batches
            assert next_batch_size <= batch_size
        elif time < 0.5 and batch_size < strategy.max_batch_size:  # Below target -> larger batches if not at max
            assert next_batch_size >= batch_size
        else:  # On target or at limits -> same or limited size
            assert next_batch_size <= strategy.max_batch_size
            assert next_batch_size >= strategy.min_batch_size


def test_entity_type_batch_strategy():
    """Test the entity type batching strategy."""
    entities = create_test_entities(100)

    # Function to extract entity type
    def extract_type(entity: Dict[str, Any]) -> str:
        return entity["type"]

    strategy = EntityTypeBatchStrategy(type_extractor=extract_type)

    batches = strategy.create_batches(entities)

    # Verify that each batch contains entities of the same type
    for batch in batches:
        entity_types = set(extract_type(entity) for entity in batch)
        assert len(entity_types) == 1  # All entities in a batch have the same type

    # Verify that all entities are included
    entities_in_batches = [entity for batch in batches for entity in batch]
    assert len(entities_in_batches) == len(entities)


def test_similarity_batch_strategy():
    """Test the similarity-based batching strategy."""
    entities = create_test_entities(100)

    # Function to extract feature vector for similarity calculation
    def extract_features(entity: Dict[str, Any]) -> Tuple[float, float, float]:
        return (
            entity["complexity"],
            entity["steps_count"] / 20.0,  # Normalize to 0-1
            entity["size"] / 10.0,  # Normalize to 0-1
        )

    strategy = SimilarityBatchStrategy(
        feature_extractor=extract_features,
        similarity_threshold=0.8,
        max_batch_size=20
    )

    batches = strategy.create_batches(entities)

    # Verify that each batch respects the maximum size
    for batch in batches:
        assert len(batch) <= 20

    # Verify that all entities are included
    entities_in_batches = [entity for batch in batches for entity in batch]
    assert len(entities_in_batches) == len(entities)

    # Check that entities in the same batch have similar features
    # This is a probabilistic test, so we only check a sample of batches
    for batch in batches[:5]:
        if len(batch) < 2:
            continue

        # Check similarity between first entity and others
        first_features = extract_features(batch[0])
        for entity in batch[1:]:
            features = extract_features(entity)
            # Calculate Euclidean distance (simple similarity metric)
            squared_diffs = sum((a - b) ** 2 for a, b in zip(first_features, features))
            distance = squared_diffs ** 0.5
            # Convert to similarity (1 - normalized distance)
            # Max possible distance in 3D space with normalized 0-1 values is sqrt(3)
            similarity = 1 - distance / 3**0.5
            # This might fail occasionally due to randomness, but should be true most of the time
            assert similarity >= 0.5


def test_configure_optimal_batch_size():
    """Test the configure_optimal_batch_size function."""
    # Mock variables for testing
    entity_count = 1000
    available_memory = 1000  # MB
    entity_size = 0.1  # MB
    parallelism = 4

    # Test with memory constraint
    batch_size = configure_optimal_batch_size(
        entity_count=entity_count,
        available_memory=available_memory,
        entity_size_mb=entity_size,
        parallelism=parallelism,
        api_rate_limit=None
    )

    # Batch size should be constrained by available memory divided by parallelism
    # Each worker should have memory for its batch
    expected_max_batch_size = available_memory / entity_size / parallelism
    assert batch_size <= expected_max_batch_size

    # Test with API rate limit constraint
    batch_size = configure_optimal_batch_size(
        entity_count=entity_count,
        available_memory=10000,  # Large memory to not be the constraint
        entity_size_mb=entity_size,
        parallelism=parallelism,
        api_rate_limit=100  # 100 requests per minute
    )

    # With rate limit of 100/minute and 4 workers, each worker should handle 25/minute
    # Batch size should be lower to respect rate limits
    assert batch_size <= 25


def test_create_batches():
    """Test the create_batches utility function."""
    entities = create_test_entities(100)

    # Create fixed-size batches
    batches = create_batches(entities, batch_size=10)
    assert len(batches) == 10
    for batch in batches:
        assert len(batch) == 10

    # Create variable-size batches based on entity complexity
    def complexity_based_size(entities: List[Dict[str, Any]]) -> int:
        # More complex entities = smaller batches
        avg_complexity = sum(e["complexity"] for e in entities) / len(entities)
        return int(20 / avg_complexity)

    batches = create_batches(entities, size_calculator=complexity_based_size)
    assert len(batches) > 0

    # Entities should be sorted by size then batched
    entities_by_size = sorted(entities, key=lambda e: e["size"], reverse=True)
    batches = create_batches(entities, batch_size=10, sort_key=lambda e: e["size"], reverse=True)
    assert batches[0][0]["size"] >= batches[-1][-1]["size"]


def test_estimate_processing_time():
    """Test the estimate_processing_time function."""
    # Create a history of processing times
    history = [
        (10, 0.5),  # 10 entities took 0.5 seconds
        (15, 0.8),  # 15 entities took 0.8 seconds
        (20, 1.1),  # 20 entities took 1.1 seconds
        (25, 1.5),  # 25 entities took 1.5 seconds
    ]

    # Test estimation for exact batch size from history
    time_estimate = estimate_processing_time(15, history)
    assert time_estimate == 0.8  # Exact match should use that time

    # Test estimation for new batch size by interpolation
    time_estimate = estimate_processing_time(17, history)
    # Should be between 0.8 and 1.1, closer to 0.8
    assert 0.8 < time_estimate < 1.1
    assert abs(time_estimate - 0.92) < 0.1  # Approximately linear interpolation

    # Test extrapolation for batch size beyond history
    time_estimate = estimate_processing_time(30, history)
    # Should follow the trend that larger batches take more time
    assert time_estimate > 1.5

    # Test with empty history
    time_estimate = estimate_processing_time(10, [])
    assert time_estimate > 0  # Should return some default estimate


def test_combined_strategies():
    """Test combining multiple batching strategies."""
    entities = create_test_entities(100)

    # Mock time estimator function
    def mock_time_estimator(entity: Dict[str, Any]) -> float:
        return entity["complexity"] * 0.1 + entity["steps_count"] * 0.05

    # Function to extract entity type
    def extract_type(entity: Dict[str, Any]) -> str:
        return entity["type"]

    # Create batches first by type then by time
    type_strategy = EntityTypeBatchStrategy(type_extractor=extract_type)
    type_batches = type_strategy.create_batches(entities)

    time_strategy = TimeBatchStrategy(
        time_estimator=mock_time_estimator,
        max_batch_time=1.0
    )

    all_batches = []
    for type_batch in type_batches:
        time_sub_batches = time_strategy.create_batches(type_batch)
        all_batches.extend(time_sub_batches)

    # Check that all entities are included
    entities_in_batches = [entity for batch in all_batches for entity in batch]
    assert len(entities_in_batches) == len(entities)

    # Check that entities in each batch have the same type
    for batch in all_batches:
        if batch:
            entity_types = set(extract_type(entity) for entity in batch)
            assert len(entity_types) == 1

    # Check that estimated processing time for each batch doesn't exceed the limit
    # or contains only a single entity that exceeds the limit
    for batch in all_batches:
        if batch:
            estimated_time = sum(mock_time_estimator(entity) for entity in batch)
            if len(batch) == 1:
                # Single entity batches might exceed the limit if they can't be split further
                entity_time = mock_time_estimator(batch[0])
                if entity_time > 1.0:
                    # This is expected for large entities
                    continue
            assert estimated_time <= 1.0


def test_adaptive_learning_over_time():
    """Test that adaptive strategy learns and improves over time."""
    # Create a more predictable set of entities
    entities = []
    for i in range(100):
        complexity = (i // 10) + 1  # Creates groups with same complexity
        entities.append({
            "id": f"TC-{i}",
            "complexity": complexity,
            "steps_count": 5,
            "size": 5,
            "type": "functional",
        })

    random.shuffle(entities)  # Shuffle to ensure no inherent order

    strategy = AdaptiveBatchStrategy(
        initial_batch_size=10,
        min_batch_size=2,
        max_batch_size=50,
        target_processing_time=0.5,
        adaptation_rate=0.2
    )

    # Mock process function that simulates processing time based on complexity
    # Entities with higher complexity take longer to process
    def mock_process(batch: List[Dict[str, Any]]) -> float:
        total_complexity = sum(e["complexity"] for e in batch)
        return total_complexity * 0.05  # 0.05 seconds per complexity unit

    # Process several batches and track performance
    processing_metrics = []
    remaining = entities.copy()

    for _ in range(10):
        if not remaining:
            break

        batch_size = min(strategy.current_batch_size, len(remaining))
        batch = remaining[:batch_size]
        remaining = remaining[batch_size:]

        processing_time = mock_process(batch)
        throughput = len(batch) / processing_time if processing_time > 0 else 0

        processing_metrics.append({
            "batch_size": batch_size,
            "time": processing_time,
            "throughput": throughput,
        })

        strategy.adapt(processing_time)

    # As the strategy learns, throughput should generally improve or stabilize
    # We look at the last few iterations compared to the first few
    early_throughput = sum(m["throughput"] for m in processing_metrics[:3]) / 3
    late_throughput = sum(m["throughput"] for m in processing_metrics[-3:]) / 3

    # Throughput should be better or at least not significantly worse
    assert late_throughput >= early_throughput * 0.9


def test_performance_measurement():
    """Test performance measurement of different batch strategies."""
    entities = create_test_entities(200)
    batch_size = 20

    # Define multiple strategies to compare
    strategies = [
        ("fixed_size", lambda e: create_batches(e, batch_size=batch_size)),
        ("size_based", lambda e: SizeBatchStrategy(max_batch_size=100).create_batches(e)),
        ("type_based", lambda e: EntityTypeBatchStrategy(
            lambda entity: entity["type"]
        ).create_batches(e)),
    ]

    # Simple "processing" function that simulates workload
    def process_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
        # Simulate work - more complex entities take longer
        complexity_factor = entity["complexity"] / 5.0  # Normalize to 0-1
        time.sleep(0.001 * complexity_factor)  # Very short sleep to avoid long tests
        return {"processed": True, **entity}

    results = {}

    # Test each strategy
    for name, strategy_func in strategies:
        start_time = time.time()

        # Get batches using the strategy
        batches = strategy_func(entities)

        # Process each batch
        processed_entities = []
        for batch in batches:
            # Process entities in the batch
            batch_results = [process_entity(entity) for entity in batch]
            processed_entities.extend(batch_results)

        end_time = time.time()

        # Record metrics
        results[name] = {
            "time": end_time - start_time,
            "batches": len(batches),
            "entities": len(processed_entities),
        }

    # Verify that all strategies processed all entities
    for name, result in results.items():
        assert result["entities"] == len(entities), f"Strategy {name} missed some entities"

    # Just for visual checking during test runs (won't affect test)
    print("\nStrategy performance comparison:")
    for name, result in results.items():
        print(f"{name}: {result['time']:.4f}s, {result['batches']} batches")

    # No explicit assertions about which strategy is faster,
    # as that depends on the test environment and random data
