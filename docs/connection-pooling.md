# Connection Pooling

ZTOQ implements HTTP connection pooling to optimize performance when making high-volume API requests to Zephyr and qTest. Connection pooling provides significant performance benefits for ETL processes by efficiently reusing existing HTTP connections instead of creating new ones for each request.

## Overview

Connection pooling helps solve several issues commonly encountered in high-throughput ETL scenarios:

1. **Connection Establishment Overhead**: Creating new TCP connections is expensive (DNS lookups, SSL handshakes, TCP handshakes)
2. **TCP Slow Start**: New connections initially have limited throughput due to TCP congestion control
3. **Limited Resource Utilization**: Without pooling, connections are often underutilized
4. **Rate Limiting**: Properly managing and reusing connections helps prevent API rate limits
5. **Memory Usage**: Creating many new connections can lead to high memory consumption

## Implementation

ZTOQ's connection pooling is implemented in `ztoq/connection_pool.py` with the following key components:

### Synchronous Connection Pooling

The main `ConnectionPool` class manages connection pools for different base URLs, with features including:

- **Pool Management**: Maintains separate connection pools per base URL
- **Connection Reuse**: Efficiently reuses connections with keep-alive
- **Automatic Retries**: Built-in retry mechanisms with configurable backoff
- **Resource Limits**: Controls maximum connections per pool
- **Graceful Failover**: Handles connection failures with proper cleanup
- **Automatic Cleanup**: Periodic cleanup of idle connections
- **Performance Metrics**: Tracks connection statistics for monitoring
- **Thread Safety**: Thread-safe implementation for concurrent usage

### Asynchronous Connection Pooling (optional)

The `AsyncConnectionPool` class provides similar functionality for asynchronous workloads:

- **Support for httpx/aiohttp**: Works with popular async HTTP libraries
- **Client Management**: Maintains stateful async clients per base URL
- **Resource Management**: Controls max connections and timeouts
- **Metrics Tracking**: Monitors client usage statistics

## Integration with Clients

Both the Zephyr and qTest clients have been updated to use connection pooling:

```python
# In _make_request method:
from ztoq.connection_pool import connection_pool

# Use connection pool to get a session and make the request
with connection_pool.get_session(url) as session:
    response = session.request(
        method=method,
        url=url,
        headers=request_headers,
        params=params,
        json=json_data,
        files=files,
        timeout=timeout,
    )
```

## Configuration

The connection pool is configured with sensible defaults but can be customized:

```python
from ztoq.connection_pool import ConnectionPool, connection_pool

# Get the default singleton instance
pool = connection_pool

# Or create a custom pool (not typically needed)
custom_pool = ConnectionPool(
    max_pool_size=20,          # Maximum connections per base URL
    connection_timeout=5.0,    # Connection timeout in seconds
    read_timeout=30.0,         # Read timeout in seconds
    max_retries=3,             # Maximum number of retries
    retry_backoff_factor=0.5,  # Backoff factor for retries
    retry_status_codes=[429, 500, 502, 503, 504]  # Status codes to retry
)
```

## Performance Benefits

Connection pooling provides several performance benefits:

1. **Reduced Latency**: Reusing connections eliminates TCP and SSL handshake time
2. **Higher Throughput**: Established connections bypass TCP slow start
3. **Better Resource Utilization**: Connections remain active between requests
4. **Improved Stability**: Automatic retries and failure handling
5. **Memory Efficiency**: Controlled connection usage reduces memory overhead

## Metrics and Monitoring

The connection pool provides metrics for monitoring:

```python
from ztoq.connection_pool import connection_pool

# Get metrics
metrics = connection_pool.get_metrics()

# Example metrics
# {
#   "created_connections": 25,
#   "reused_connections": 475,
#   "failed_connections": 3,
#   "active_pools": 2,
#   "last_cleanup": 1649937600,
#   "pools": {
#     "https://api.zephyrscale.com": 5,
#     "https://api.qtest.com": 5
#   }
# }
```

## Cleanup and Shutdown

For applications with long-running processes, proper cleanup is important:

```python
from ztoq.connection_pool import connection_pool, close_connection_pools

# At application shutdown
close_connection_pools()
```

## Testing

Comprehensive test coverage is provided in `tests/integration/test_connection_pooling.py`, including:

- Connection reuse verification
- Pool size limits
- Concurrent request handling
- Cleanup mechanisms
- Error handling
- Performance metrics tracking

## Use with Work Queues

Connection pooling integrates seamlessly with ZTOQ's work queue system, allowing for optimized parallel processing:

```python
from ztoq.work_queue import WorkQueue
from ztoq.connection_pool import connection_pool

# WorkQueue will use the connection pool automatically when processing HTTP requests
queue = WorkQueue(max_workers=10)
```

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../LICENSE)*
