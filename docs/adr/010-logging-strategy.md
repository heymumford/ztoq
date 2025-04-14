# ADR-010: Logging Strategy

## Status

Accepted

## Context

Effective logging is essential for monitoring, debugging, and understanding the behavior of ZTOQ, especially as a data processing tool that makes API calls and performs database operations. A well-designed logging system should provide visibility into application behavior while avoiding information overload or security risks.

Key considerations include:

1. Log levels and appropriate usage
2. Structured vs. unstructured logging
3. Performance impact
4. Sensitive data protection
5. Log destination configuration
6. Integration with CLI output
7. Log formatting and contextual information

## Decision

We will implement a comprehensive logging strategy using Python's built-in `logging` module with structured logs and contextual information. The logging system will follow these principles:

### 1. Log Levels and Usage

We will use the standard Python log levels with clear guidelines:

- **CRITICAL (50)**: Application is unusable, immediate attention required
- **ERROR (40)**: Error that prevents a specific operation but allows the application to continue
- **WARNING (30)**: Potentially problematic situations that don't prevent operation
- **INFO (20)**: Confirmation that things are working as expected, major state changes
- **DEBUG (10)**: Detailed information useful for diagnosing problems

Default log level will be INFO for production use, with command-line options to adjust.

### 2. Structured Logging

We will use structured logging to make logs machine-readable and easily searchable:

```python
import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional

class StructuredLogRecord(logging.LogRecord):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = {}  # Additional context data

class StructuredLogger(logging.Logger):
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, **kwargs):
        # Extract context from kwargs if present
        context = kwargs.pop('context', {}) if kwargs else {}
        if extra is None:
            extra = {}
        extra['context'] = context
        super()._log(level, msg, args, exc_info, extra, stack_info)

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add context if available
        if hasattr(record, 'context') and record.context:
            log_data['context'] = record.context
            
        # Add exception info if available
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
            
        return json.dumps(log_data)
```

### 3. Context Managers for Operation Logging

We will provide context managers for logging operations with timing and context:

```python
import logging
import time
from contextlib import contextmanager
from typing import Optional, Dict, Any

@contextmanager
def log_operation(logger, operation_name: str, level: int = logging.INFO, context: Optional[Dict[str, Any]] = None):
    """Context manager for logging operations with timing."""
    start_time = time.time()
    context = context or {}
    
    logger.log(level, f"Starting {operation_name}", context=context)
    
    try:
        yield
        duration = time.time() - start_time
        logger.log(level, f"Completed {operation_name} in {duration:.2f}s", context=context)
    except Exception as e:
        duration = time.time() - start_time
        error_context = {**context, 'error_type': type(e).__name__, 'error': str(e)}
        logger.log(logging.ERROR, f"Failed {operation_name} after {duration:.2f}s", 
                   context=error_context, exc_info=True)
        raise
```

### 4. Configuration

We will provide multiple logging configuration options:

```python
import logging
import logging.config
import os
import sys
from typing import Optional, Dict, Any

def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    json_format: bool = False,
    include_timestamp: bool = True
) -> None:
    """Configure application logging."""
    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stderr,
            'formatter': 'json' if json_format else 'standard',
        }
    }
    
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers['file'] = {
            'class': 'logging.FileHandler',
            'filename': log_file,
            'formatter': 'json' if json_format else 'standard',
        }
    
    formatters = {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s' if include_timestamp 
                     else '[%(levelname)s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'json': {
            'class': 'ztoq.logging.JSONFormatter',
        }
    }
    
    logging.config.dictConfig({
        'version': 1,
        'formatters': formatters,
        'handlers': handlers,
        'loggers': {
            'ztoq': {
                'level': level,
                'handlers': list(handlers.keys()),
                'propagate': False,
            }
        },
        'root': {
            'level': max(level, logging.WARNING),  # Root logger should be at least WARNING
            'handlers': list(handlers.keys()),
        }
    })
    
    # Register custom logger class
    logging.setLoggerClass(StructuredLogger)
```

### 5. CLI Integration

We will integrate with Typer for CLI output:

```python
import typer
import logging
from typing import Optional

def setup_cli_logging(verbose: bool = False, quiet: bool = False, 
                      log_file: Optional[str] = None) -> None:
    """Configure logging based on CLI parameters."""
    # Determine log level
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO
        
    # Configure logging
    configure_logging(
        level=level,
        log_file=log_file,
        json_format=False,  # Use text format for CLI
        include_timestamp=True
    )
    
    # Set up logger
    logger = logging.getLogger('ztoq.cli')
    
    # Add a Typer callback handler for critical/error logs
    class TyperLogHandler(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.ERROR:
                typer.secho(self.format(record), fg=typer.colors.RED, err=True)
                
    handler = TyperLogHandler()
    handler.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter('%(message)s'))  # Simplified for CLI
    logger.addHandler(handler)
```

### 6. Log Redaction for Sensitive Data

We will implement log redaction for sensitive data:

```python
import re
from typing import Dict, List, Pattern

class LogRedactor:
    """Redacts sensitive information from log messages."""
    
    def __init__(self):
        self.patterns: Dict[str, Pattern] = {
            'api_key': re.compile(r'(api[_-]?key|token)["\']?\s*[:=]\s*["\']?([^"\'&\s]{8,})', re.IGNORECASE),
            'password': re.compile(r'(password|passwd)["\']?\s*[:=]\s*["\']?([^"\'&\s]+)', re.IGNORECASE),
            'credit_card': re.compile(r'\b(?:\d{4}[- ]?){3}\d{4}\b'),
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        }
        
    def redact(self, message: str) -> str:
        """Redact sensitive information from the message."""
        for field, pattern in self.patterns.items():
            if field in ('api_key', 'password'):
                # For key-value patterns, keep the key but redact the value
                message = pattern.sub(r'\1: [REDACTED]', message)
            else:
                # For standalone patterns, redact the entire match
                message = pattern.sub('[REDACTED]', message)
        return message
```

## Consequences

### Positive

1. **Improved Observability**: Structured logs provide better insight into application behavior
2. **Easier Debugging**: Contextual information and operation timing aid in troubleshooting
3. **Flexible Configuration**: Multiple options for log levels, formats, and destinations
4. **Security**: Sensitive data redaction protects against accidental exposure
5. **Performance Monitoring**: Built-in timing for operations helps identify bottlenecks
6. **User Experience**: Integration with CLI provides appropriate feedback
7. **Scalability**: JSON logs can be easily consumed by log aggregation tools

### Negative

1. **Implementation Overhead**: More complex logging system to maintain
2. **Performance Considerations**: Structured logging adds some CPU and memory overhead
3. **Learning Curve**: Developers need to understand when and how to use different log levels
4. **Potential Verbosity**: Risk of generating too much log data if not configured properly

## Implementation Notes

1. Create a dedicated `logging.py` module for logging utilities
2. Initialize logging early in application startup
3. Use descriptive logger names following module hierarchy
4. Limit DEBUG logs to information useful for troubleshooting
5. Always redact sensitive information before logging
6. Include request IDs for tracking operations across log entries
7. Implement log rotation for file-based logs to manage size

## References

- [Python Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html)
- [Structured Logging Best Practices](https://www.datadoghq.com/blog/python-logging-best-practices/)
- [12-Factor App: Logs](https://12factor.net/logs)