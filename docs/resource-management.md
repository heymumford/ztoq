# Resource Management Best Practices

## Overview

ZTOQ is designed to handle large-scale migrations with parallel and asynchronous processing. This requires careful management of resources like connections, memory, and file handles. This document outlines best practices for resource management when using ZTOQ.

## Automatic Resource Management

ZTOQ implements several automatic resource management features:

### Connection Pooling

- HTTP connections are pooled for both synchronous and asynchronous clients
- Idle connections are automatically closed after a configurable period (default: 60 seconds)
- Connection pools are thread-safe and periodically cleaned up
- A global cleanup function is registered to release connection pools at shutdown

```python
# Import the cleanup function
from ztoq.connection_pool import close_connection_pools

# Call at application shutdown
close_connection_pools()
```

### Database Sessions

- Database sessions are managed with context managers to ensure proper closure
- Thread-local sessions are tracked and automatically cleaned up when threads exit
- Sessions include proper error handling to ensure resources are released
- Transactions are properly committed or rolled back in all cases

```python
# Using the session context manager
with database_manager.session() as session:
    # Session is automatically closed after this block
    results = session.query(Model).all()
```

### Work Queue Memory Management

- Work queues limit the number of completed items stored in memory
- Oldest completed items are automatically cleaned up when the limit is reached
- Configurable cleanup intervals ensure regular memory usage optimization
- All async tasks include timeouts to prevent resource leaks

```python
# Configure the work queue with memory management settings
queue = WorkQueue(
    max_completed_items=1000,  # Store up to 1000 completed items
    cleanup_interval=100       # Clean up every 100 completions
)
```

### Circuit Breakers

- Circuit breakers track failing API endpoints to prevent cascading failures
- Idle circuit breakers are periodically removed from memory
- Explicit cleanup methods are provided for application shutdown

```python
# Cleanup idle circuit breakers
CircuitBreaker.cleanup_idle_circuits()
```

## Client Resource Management

Client classes in ZTOQ provide explicit cleanup methods:

### ZephyrClient

```python
client = ZephyrClient(config)
try:
    # Use the client
    projects = client.get_projects()
finally:
    # Clean up resources
    client.cleanup()
```

### QTestClient

```python
client = QTestClient(config)
try:
    # Use the client
    projects = client.get_projects()
finally:
    # Clean up resources
    client.cleanup()
```

## Thread and Process Management

When using parallel processing:

1. Always use context managers for thread and process pools:

```python
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    # Submit work
    futures = [executor.submit(task, item) for item in items]
    # Process results
    for future in concurrent.futures.as_completed(futures):
        result = future.result()
```

2. Set appropriate timeouts for tasks:

```python
# Set a timeout to prevent hanging tasks
try:
    result = future.result(timeout=60)  # 60-second timeout
except concurrent.futures.TimeoutError:
    # Handle timeout
    pass
```

3. Handle exceptions to ensure resource cleanup:

```python
try:
    result = future.result()
except Exception as e:
    # Handle exception and ensure cleanup
    pass
```

## Memory Usage Optimization

For large migrations, optimize memory usage:

1. Process data in batches:

```python
# Use batch processing to limit memory usage
for batch in ztoq.utils.batch_processor(items, batch_size=1000):
    process_batch(batch)
```

2. Use generators for large datasets:

```python
# Use generators to avoid loading everything into memory
for item in client.get_test_cases():  # Returns a generator
    process_item(item)
```

3. Explicitly clean up large objects when done:

```python
# Process a large object
result = process_large_object(large_object)
# Explicitly clean up
large_object = None
```

## Best Practices Summary

1. **Use Context Managers**: Always use `with` statements for resource management
2. **Set Timeouts**: Provide timeouts for network operations and async tasks
3. **Cleanup Clients**: Call `cleanup()` on client objects when done
4. **Handle Exceptions**: Always include exception handling for proper cleanup
5. **Process in Batches**: Avoid loading entire datasets into memory
6. **Close Connections**: Explicitly close connections when appropriate
7. **Monitor Resources**: Watch memory and connection usage during large operations
8. **Use Dedicated Thread Pools**: Use separate thread pools for different operations

By following these practices, you can ensure efficient resource usage even during large-scale migrations with high concurrency.