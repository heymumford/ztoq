# ADR-009: Error Handling Strategy

## Status

Accepted

## Context

Effective error handling is critical for a data processing tool like ZTOQ that makes API calls, transforms data, and interacts with a database. We need a consistent approach to error handling that balances:

1. Graceful failure with meaningful error messages
2. Comprehensive logging for troubleshooting
3. Appropriate retry logic for transient failures
4. Clean error propagation through the call stack
5. User-friendly error reporting at the CLI level
6. Protection of data integrity during failures

There are several common patterns for error handling in Python:

- Using exceptions with try/except blocks
- Result objects that encapsulate success/failure states (Result[T, E] pattern)
- Monadic error handling with Option/Maybe types
- Global error handlers and middleware
- Callbacks and event-driven error notification

## Decision

We will implement a multi-layered error handling strategy that combines:

1. **Domain-specific exceptions hierarchy** for clear error classification
2. **Result objects for API operations** to encapsulate success/failure states
3. **Contextual logging** at appropriate levels
4. **Automated retry for transient errors** with exponential backoff
5. **Transaction rollback** for database operations on failure
6. **User-friendly CLI error messages** with debug options

### Exception Hierarchy

```python
class ZTOQError(Exception):
    """Base exception for all ZTOQ errors."""
    pass

class APIError(ZTOQError):
    """Errors related to API operations."""
    pass

class RateLimitError(APIError):
    """API rate limit exceeded."""
    pass

class AuthenticationError(APIError):
    """Authentication failed."""
    pass

class DataValidationError(ZTOQError):
    """Data validation failed."""
    pass

class StorageError(ZTOQError):
    """Storage operations error."""
    pass

class ConfigurationError(ZTOQError):
    """Configuration error."""
    pass
```

### Result Object Pattern

```python
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar, Union, List

T = TypeVar('T')

@dataclass
class Result(Generic[T]):
    """Encapsulates the result of an operation that might fail."""
    success: bool
    value: Optional[T] = None
    error: Optional[Exception] = None
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    @classmethod
    def success(cls, value: T) -> 'Result[T]':
        """Create a successful result."""
        return cls(success=True, value=value, warnings=[])
    
    @classmethod
    def failure(cls, error: Optional[Exception] = None, 
                error_message: Optional[str] = None) -> 'Result[T]':
        """Create a failed result."""
        return cls(
            success=False, 
            error=error, 
            error_message=error_message or (str(error) if error else "Unknown error"),
            warnings=[]
        )
    
    def with_warning(self, warning: str) -> 'Result[T]':
        """Add a warning message to the result."""
        if self.warnings is None:
            self.warnings = []
        self.warnings.append(warning)
        return self
```

### Retry Logic

```python
import time
from functools import wraps
from typing import Callable, TypeVar, Any, Dict, Optional

T = TypeVar('T')

def retry(
    max_attempts: int = 3, 
    delay_seconds: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: tuple = (APIError, ConnectionError)
) -> Callable:
    """Retry decorator with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            delay = delay_seconds
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        time.sleep(delay)
                        delay *= backoff_factor
            
            # All retries failed
            raise last_exception
        return wrapper
    return decorator
```

### CLI Error Display

```python
import typer
import logging
from typing import Optional

def handle_cli_error(error: Exception, verbose: bool = False) -> None:
    """Handle errors at the CLI level with appropriate messaging."""
    if isinstance(error, AuthenticationError):
        typer.secho("Authentication failed. Please check your API token.", fg=typer.colors.RED)
    elif isinstance(error, RateLimitError):
        typer.secho("API rate limit exceeded. Please try again later.", fg=typer.colors.RED)
    elif isinstance(error, ConfigurationError):
        typer.secho(f"Configuration error: {error}", fg=typer.colors.RED)
    elif isinstance(error, DataValidationError):
        typer.secho(f"Data validation error: {error}", fg=typer.colors.RED)
    elif isinstance(error, StorageError):
        typer.secho(f"Storage error: {error}", fg=typer.colors.RED) 
    else:
        typer.secho(f"An unexpected error occurred: {error.__class__.__name__}", fg=typer.colors.RED)
        
    if verbose:
        typer.secho(f"\nDebug details:\n{str(error)}\n", fg=typer.colors.YELLOW)
        # Log the full stack trace
        logging.exception("Detailed error information:")
```

## Consequences

### Positive

1. **Consistent Error Handling**: Uniform approach across the codebase
2. **Clear Error Classification**: Specific exception types for different failure modes
3. **Graceful Degradation**: Result objects allow partial success with warnings
4. **Improved Reliability**: Retry logic for transient failures
5. **Better Debugging**: Contextual error information and logging
6. **User-Friendly Messages**: Appropriate CLI error presentation
7. **Data Protection**: Proper transaction management prevents data corruption

### Negative

1. **Increased Complexity**: More code to manage error flows
2. **Risk of Over-Engineering**: Result objects add overhead if not needed
3. **Learning Curve**: Developers need to understand the patterns
4. **Potential Performance Impact**: Retry logic and logging add some overhead

## Implementation Notes

1. All public API methods should use the Result pattern or raise specific exceptions
2. Database operations should use transactions with proper rollback
3. Long-running operations should include progress reporting and partial results
4. The retry mechanism should be applied selectively to I/O-bound operations
5. Error messages should be user-focused at the CLI level
6. Detailed logs should be available but not overwhelming
7. Each component should document its error handling approach

## References

- [Railway Oriented Programming](https://fsharpforfunandprofit.com/rop/)
- [Python Exception Best Practices](https://docs.python-guide.org/writing/structure/#error-handling)
- [Functional Error Handling](https://medium.com/swlh/functional-error-handling-in-python-296c09d34b3c)