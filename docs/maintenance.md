# ZTOQ Maintenance and Development Guidelines

## Project Status

The ZTOQ project is currently being expanded to include qTest integration capabilities. This enhancement involves:

1. Implementing a unified qTest client for all four qTest APIs
2. Creating a mock server for testing qTest integration
3. Building an ETL-based migration workflow
4. Developing entity mapping between Zephyr and qTest

## Recent Changes

1. **Code Formatting**:
   - Applied Black formatting to all Python files
   - Fixed code style inconsistencies

2. **Documentation Updates**:
   - Created ADR-011: qTest Integration Architecture
   - Created ADR-012: Test-Driven Development Approach
   - Created ADR-013: ETL-Based Migration Workflow
   - Updated C4 diagrams to include qTest integration components

3. **Testing Infrastructure**:
   - Added unit tests for qTest client
   - Added unit tests for qTest mock server
   - Added unit tests for qTest models

4. **Project Organization**:
   - Updated Kanban board with TDD approach (write tests first)
   - Reorganized tasks into logical phases

## Current Issues

1. **Type Checking Errors**:
   - Multiple type errors in qtest_mock_server.py:
     - Parameter type mismatches
     - Object iteration issues
   - Type errors in openapi_parser.py:
     - Tuple/string key issues in dictionaries
     - Missing base64 imports
   - Type errors in test_generator.py:
     - Type annotation issues
     - Missing base64 imports

2. **Import Issues**:
   - QTest models not imported correctly in qtest_client.py

## Next Steps

1. **Fix Type Checking Issues**:
   - Annotate function parameters correctly
   - Add proper imports
   - Fix dictionary key type issues
   - Add proper nullable type handling

2. **Resolve Import Issues**:
   - Move qTest models to proper location
   - Update import statements

3. **Continue Implementation**:
   - Complete qTest client unit tests
   - Add integration tests for ETL workflow
   - Implement entity mapping with test-first approach

## Development Guidelines

1. **Test-Driven Development**:
   - Always write tests before implementation
   - Follow the Red-Green-Refactor cycle
   - Aim for high test coverage

2. **Code Quality**:
   - Run formatting tools regularly (Black)
   - Use type annotations consistently
   - Follow existing project patterns

3. **Documentation**:
   - Update ADRs for significant decisions
   - Keep C4 diagrams in sync with code
   - Document public APIs

4. **Performance Considerations**:
   - Use connection pooling
   - Implement batching for large datasets
   - Consider memory usage for large migrations

## Linting and Validation

Run these commands before submitting changes:

```bash
# Format code
black .

# Type checking
mypy ztoq/

# Run tests
pytest tests/
```

## Maintenance Tasks

Regular maintenance tasks include:

1. Updating dependencies
2. Reviewing and resolving linting issues
3. Maintaining test coverage
4. Updating documentation as needed
5. Reviewing error logs for patterns

## Troubleshooting

If you encounter issues:

1. Check the logs with appropriate verbosity
2. Verify configuration settings
3. Run tests to isolate the problem
4. Check for recent changes that might have introduced the issue

## Contact

If you have questions or need assistance:

- Project Lead: Evan Mumford
- GitHub Issues: [ZTOQ Issues](https://github.com/username/ztoq/issues)

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../../LICENSE)*