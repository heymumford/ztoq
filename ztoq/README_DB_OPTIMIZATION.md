# Database Optimization Module

This module provides optimized database access patterns for handling large test management migration datasets. It's designed to significantly improve performance when working with thousands of test cases, cycles, and executions.

## Quick Start

### Using the Optimized Database Manager

```python
# Option 1: From factory directly
from ztoq.database_factory import DatabaseFactory, DatabaseType

manager = DatabaseFactory.create_database_manager(
    db_type=DatabaseType.OPTIMIZED,
    db_path="/path/to/db.sqlite"
)

# Option 2: With the optimize flag
manager = DatabaseFactory.create_database_manager(
    db_type=DatabaseType.SQLITE,
    db_path="/path/to/db.sqlite",
    optimize=True
)

# Option 3: Using helper function
from ztoq.db_optimization_helpers import get_optimized_database_manager

manager = get_optimized_database_manager(
    db_type=DatabaseType.SQLITE,
    db_path="/path/to/db.sqlite"
)

# Option 4: Environment variable approach
# Set ZTOQ_OPTIMIZE_DB=true in your environment
# Then use the standard get_database_manager
from ztoq.database_factory import get_database_manager
manager = get_database_manager()
```

### Batch Operations

For optimal performance with large datasets, use the batch operations:

```python
# Batch save test cases
manager.batch_save_test_cases(test_cases_list, project_key="PROJECT1")

# Batch save test cycles
manager.batch_save_test_cycles(test_cycles_list, project_key="PROJECT1")

# Batch save test executions
manager.batch_save_test_executions(test_executions_list, project_key="PROJECT1")
```

### Keyset Pagination

For efficiently traversing large result sets:

```python
# Initial query - get first page
test_cases = manager.get_test_cases(project_key="PROJECT1", page_size=100)

# Get subsequent pages
last_id = test_cases[-1].id if test_cases else None
next_page = manager.get_test_cases(
    project_key="PROJECT1",
    page_size=100,
    last_id=last_id
)
```

### Performance Monitoring

To check database performance:

```python
from ztoq.db_optimization_helpers import get_database_performance_report

# Get performance report
report = get_database_performance_report()

# Print summary
print(f"Total operations: {report['summary']['total_operations']}")
print(f"Average time: {report['summary']['avg_operation_time']*1000:.2f}ms")
print(f"Error rate: {report['summary']['error_rate']*100:.2f}%")

# Check slowest operations
for op in report.get('slow_operations', [])[:3]:
    print(f"Slow operation: {op['operation']} - {op['avg_time']*1000:.2f}ms")
```

### Optimization Configuration

Adjust optimization settings based on your workload:

```python
from ztoq.db_optimization_helpers import optimize_for_reads, optimize_for_writes

# For migration phases with mostly reading operations
optimize_for_reads()  # Increases cache TTL to 10 minutes

# For migration phases with heavy writing
optimize_for_writes()  # Reduces cache TTL to 1 minute

# Reset all performance statistics and clear cache
from ztoq.db_optimization_helpers import reset_performance_tracking
reset_performance_tracking()
```

## Migration Context

This optimization module is specifically designed for the following migration scenarios:

1. **Test Case Migration**: When migrating thousands of test cases from Zephyr to qTest
   - Efficiently batch process test case data
   - Cache project and folder lookups
   - Optimize relationship handling

2. **Test Cycle Migration**: When migrating complex test cycle hierarchies
   - Handle parent-child relationships efficiently
   - Process cycle assignments in batches
   - Maintain relationship integrity

3. **Test Execution Migration**: When migrating test execution history and results
   - Process large volumes of execution data
   - Efficiently handle attachments and evidence
   - Maintain execution context and history

## Performance Tips

1. **Use Appropriate Batch Sizes**: The default batch size is 100, but can be adjusted based on your dataset complexity
2. **Monitor Performance**: Regularly check the performance report during migration
3. **Tune Cache TTL**: Adjust cache TTL based on your data volatility
4. **Transaction Scope**: Use transaction_scope for critical operations
5. **Connection Pooling**: Set pool size based on available resources

## Further Documentation

For detailed implementation information and background, see:
- [Database Optimization Strategy](../docs/database-optimization.md)
- [Performance Optimization Phase](../docs/kanban.md#phase-9-performance-optimization)

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../LICENSE)*
