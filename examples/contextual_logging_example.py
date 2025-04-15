#!/usr/bin/env python3
"""
Example script demonstrating how to use the contextual logging system in ZTOQ.
"""
import sys
import time
from pathlib import Path

# Add parent directory to path if running as script
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

from ztoq.core.logging import (
    ErrorTracker,
    configure_logging,
    correlation_id,
    get_logger,
    log_operation,
)


def simulate_api_call(logger, success=True, delay=0.5):
    """Simulate an API call that might fail."""
    logger.info("Making API request", context={"endpoint": "/api/test", "method": "GET"})
    time.sleep(delay)  # Simulate network delay

    if not success:
        logger.warning("API request experiencing slowness", context={"response_time": f"{delay*2}s"})
        time.sleep(delay)  # More delay
        raise ConnectionError("API request timed out")

    logger.info("API request successful", context={"status_code": 200})
    return {"status": "success", "data": {"id": 123, "name": "Test Item"}}


def process_item(logger, item_id, should_fail=False):
    """Process an item with contextual logging."""
    # Create a new logger with item context
    item_logger = logger.with_context(item_id=item_id, process_type="standard")

    # Use the context manager to track the operation
    with log_operation(item_logger, f"Processing item {item_id}", context={"priority": "high"}):
        item_logger.info("Starting item processing")

        # Simulate some processing steps
        item_logger.debug("Validating item data")
        time.sleep(0.2)

        item_logger.debug("Transforming item data")
        time.sleep(0.3)

        # Simulate an API call that might fail
        result = simulate_api_call(item_logger, success=not should_fail)

        item_logger.info("Item processing completed", context={"result_status": result["status"]})
        return result


def batch_process_with_error_tracking(items):
    """Demonstrate batch processing with error tracking."""
    logger = get_logger(__name__)
    logger.info("Starting batch processing", context={"batch_size": len(items)})

    error_tracker = ErrorTracker(logger)
    results = []

    for i, item_id in enumerate(items):
        # Use a new correlation ID for each item
        with correlation_id(f"batch-{i}-{item_id}"):
            try:
                # Process the item (with potential errors)
                should_fail = (i % 3 == 0)  # Make every third item fail
                result = process_item(logger, item_id, should_fail=should_fail)
                results.append(result)
            except Exception as e:
                # Track the error but continue processing
                error_tracker.add_error(e, context={"item_id": item_id, "attempt": i+1})
                logger.error(f"Failed to process item {item_id}: {e!s}")

    # Summarize processing results
    success_count = len(results)
    error_count = len(error_tracker.errors)
    logger.info(
        "Batch processing completed",
        context={
            "successful_items": success_count,
            "failed_items": error_count,
            "total_items": len(items),
        },
    )

    # Report errors if any occurred
    if error_tracker.has_errors():
        error_summary = error_tracker.get_error_summary()
        logger.warning(
            "Errors occurred during batch processing",
            context={
                "total_errors": error_summary["total_errors"],
                "error_types": error_summary["error_types"],
            },
        )

    return results, error_tracker.errors


def main():
    """Main entry point for example."""
    # Configure logging with rich output
    configure_logging(level="DEBUG", use_rich=True)

    logger = get_logger(__name__)
    logger.info("Starting contextual logging example")

    try:
        # Example 1: Simple contextual logging
        logger.info("Example 1: Simple contextual logging")
        with correlation_id():
            logger.info("This log message has a correlation ID")
            logger.info("This shares the same correlation ID", context={"example": "context data"})

        # Example 2: Operation tracking
        logger.info("Example 2: Operation tracking")
        with log_operation(logger, "Example operation", context={"example_id": "op-123"}):
            logger.info("Inside the operation")
            time.sleep(0.5)
            logger.info("Still inside the operation")

        # Example 3: Error tracking in batch processing
        logger.info("Example 3: Batch processing with error tracking")
        items = ["item-1", "item-2", "item-3", "item-4", "item-5"]
        results, errors = batch_process_with_error_tracking(items)

        # Example 4: Demonstrate correlation ID inheritance
        logger.info("Example 4: Correlation ID inheritance")
        with correlation_id("parent-correlation-id"):
            logger.info("Parent operation")

            # These will inherit the parent correlation ID
            logger.debug("Child operation 1")
            logger.debug("Child operation 2")

            # This creates a new correlation ID for its scope
            with correlation_id():
                logger.debug("Nested operation with new correlation ID")

            # Back to parent correlation ID
            logger.info("Back to parent correlation ID")

        logger.info("Contextual logging example completed successfully")

    except Exception as e:
        logger.error(f"Example failed with error: {e!s}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
