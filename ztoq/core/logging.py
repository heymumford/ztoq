"""
Copyright (c) 2025 Eric C.

Mumford (@heymumford) This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.

"""

"""Logging infrastructure with contextual error tracking.

This module provides a comprehensive logging system with structured logging,
contextual error tracking, correlation IDs, and sensitive data redaction.
"""

import json
import logging
import os
import re
import sys
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from re import Pattern
from typing import Any

# Import rich components for logging
try:
    from rich.logging import RichHandler
except ImportError:
    # Fallback if rich is not installed
    RichHandler = None

# Thread-local storage for context data
_context_local = threading.local()


# Create a class to hold the global state of correlation IDs
class CorrelationIdManager:
    """
    Manages correlation IDs across threads using thread-local storage.

    This class provides methods to get, set, and clear correlation IDs that are
    unique to each thread, allowing for proper tracking of operations across
    asynchronous code execution.

    """

    def __init__(self) -> None:
        """
        Initialize the correlation ID manager.
        """
        self.current_id: str | None = None

    def get_correlation_id(self) -> str:
        """
        Get the current correlation ID or generate a new one.
        """
        if not hasattr(_context_local, "correlation_id") or not _context_local.correlation_id:
            _context_local.correlation_id = f"ztoq-{uuid.uuid4()}"
        return _context_local.correlation_id

    def set_correlation_id(self, correlation_id: str) -> None:
        """
        Set the current correlation ID.
        """
        _context_local.correlation_id = correlation_id

    def clear_correlation_id(self) -> None:
        """
        Clear the current correlation ID.
        """
        if hasattr(_context_local, "correlation_id"):
            delattr(_context_local, "correlation_id")


# Global correlation ID manager instance
correlation_manager = CorrelationIdManager()


class LogRedactor:
    """
    Redacts sensitive information from log messages.
    """

    def __init__(self) -> None:
        """
        Initialize the log redactor with patterns for sensitive information.

        Sets up regex patterns to detect and redact sensitive information like
        API keys, passwords, tokens, credit card numbers, and email addresses.
        """
        self.patterns: dict[str, Pattern] = {
            "api_key": re.compile(
                r'(api[_-]?key|token)["\']?\s*[:=]\s*["\']?([^"\'&\s]{8,})', re.IGNORECASE
            ),
            "password": re.compile(
                r'(password|passwd|secret)["\']?\s*[:=]\s*["\']?([^"\'&\s]+)', re.IGNORECASE
            ),
            "bearer_token": re.compile(
                r'(Authorization|Bearer)["\']?\s*[:=]\s*["\']?([^"\'&\s]{8,})', re.IGNORECASE
            ),
            "credit_card": re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b"),
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        }

    def redact(self, message: str) -> str:
        """
        Redact sensitive information from the message.
        """
        if not isinstance(message, str):
            return message

        for field, pattern in self.patterns.items():
            if field in ("api_key", "password", "bearer_token"):
                # For key-value patterns, keep the key but redact the value
                message = pattern.sub(r"\1: [REDACTED]", message)
            else:
                # For standalone patterns, redact the entire match
                message = pattern.sub("[REDACTED]", message)
        return message


# Global redactor instance
redactor = LogRedactor()


def _log_record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
    """
    Create a custom LogRecord factory.

    This factory creates a basic LogRecord without additional attributes to avoid
    conflicts with attributes added later by the StructuredLogger.

    Args:
    ----
        *args: Positional arguments to pass to LogRecord constructor
        **kwargs: Keyword arguments to pass to LogRecord constructor

    Returns:
    -------
        A basic LogRecord instance

    """
    # Don't add any extra attributes here, just return the basic record
    # This avoids conflicts with attributes added later
    return logging.LogRecord(*args, **kwargs)


# Define as a class for backwards compatibility if needed
class StructuredLogRecord(logging.LogRecord):
    """
    Extended LogRecord class that supports additional context data.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize a structured log record with context support.

        Args:
        ----
            *args: Positional arguments to pass to LogRecord constructor
            **kwargs: Keyword arguments to pass to LogRecord constructor

        """
        super().__init__(*args, **kwargs)
        self.context: dict[str, Any] = {}
        self.log_correlation_id = correlation_manager.get_correlation_id()


class StructuredLogger(logging.Logger):
    """
    Logger that supports structured logging with context data.
    """

    def _log(
        self,
        level: int,
        msg: Any,
        args: tuple,
        exc_info: bool | tuple | None = None,
        extra: dict[str, Any] | None = None,
        stack_info: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Log a message with the specified level and optional context.

        Args:
        ----
            level: The log level (DEBUG, INFO, etc.)
            msg: The message to log
            args: Arguments for string formatting
            exc_info: Exception info for traceback
            extra: Extra attributes to add to the LogRecord
            stack_info: Whether to include stack info
            **kwargs: Additional keyword arguments, which may include 'context'

        """
        # Extract context from kwargs if present
        context = kwargs.pop("context", {}) if kwargs else {}

        # Create extra dict if it doesn't exist
        if extra is None:
            extra = {}

        # Handle context properly
        # Store additional context in a new field that won't conflict with LogRecord
        if context:
            # Use context_data instead of context to avoid conflict
            extra["context_data"] = context

        # Add correlation ID
        extra["correlation_id"] = correlation_manager.get_correlation_id()

        # Redact sensitive information from the message
        if isinstance(msg, str):
            msg = redactor.redact(msg)

        # Call parent's _log method
        super()._log(level, msg, args, exc_info, extra, stack_info)

    def with_context(self, **context: Any) -> "StructuredLogger":
        """
        Return a logger with added context data.

        Args:
        ----
            **context: Arbitrary context key-value pairs to include in logs

        Returns:
        -------
            A StructuredLogger instance with the specified context

        """
        logger = self.manager.getLogger(self.name)
        # Store context in a different name to avoid collision
        logger._log_context = context
        return logger

    def info(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """
        Override info method to add context from with_context if available.

        Args:
        ----
            msg: The message to log
            *args: Arguments for string formatting
            **kwargs: Additional keyword arguments, may include 'context'

        """
        if hasattr(self, "_log_context") and "context" not in kwargs:
            kwargs["context"] = self._log_context
        return super().info(msg, *args, **kwargs)

    def debug(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """
        Override debug method to add context from with_context if available.

        Args:
        ----
            msg: The message to log
            *args: Arguments for string formatting
            **kwargs: Additional keyword arguments, may include 'context'

        """
        if hasattr(self, "_log_context") and "context" not in kwargs:
            kwargs["context"] = self._log_context
        return super().debug(msg, *args, **kwargs)

    def warning(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """
        Override warning method to add context from with_context if available.

        Args:
        ----
            msg: The message to log
            *args: Arguments for string formatting
            **kwargs: Additional keyword arguments, may include 'context'

        """
        if hasattr(self, "_log_context") and "context" not in kwargs:
            kwargs["context"] = self._log_context
        return super().warning(msg, *args, **kwargs)

    def error(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """
        Override error method to add context from with_context if available.

        Args:
        ----
            msg: The message to log
            *args: Arguments for string formatting
            **kwargs: Additional keyword arguments, may include 'context'

        """
        if hasattr(self, "_log_context") and "context" not in kwargs:
            kwargs["context"] = self._log_context
        return super().error(msg, *args, **kwargs)

    def critical(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """
        Override critical method to add context from with_context if available.

        Args:
        ----
            msg: The message to log
            *args: Arguments for string formatting
            **kwargs: Additional keyword arguments, may include 'context'

        """
        if hasattr(self, "_log_context") and "context" not in kwargs:
            kwargs["context"] = self._log_context
        return super().critical(msg, *args, **kwargs)


class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs log records as JSON.
    """

    def format_record(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.

        Args:
        ----
            record: The LogRecord to format

        Returns:
        -------
            A JSON string representation of the log record

        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),  # using now() instead of deprecated utcnow()
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation_id if it exists
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        # Add context data if it exists
        if hasattr(record, "context_data") and record.context_data:
            log_data["context"] = record.context_data

        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_data)

    def format(self, record: logging.LogRecord) -> str:
        """Forward logging format calls to format_record."""
        return self.format_record(record)


class RichContextFormatter(logging.Formatter):
    """
    Formatter for Rich console output with context data.
    """

    def format_record(self, record: logging.LogRecord) -> str:
        """
        Format the log record for Rich console output.

        Args:
        ----
            record: The LogRecord to format

        Returns:
        -------
            A formatted string with context data and correlation ID

        """
        message = super().format(record)

        # Add context data if it exists
        if hasattr(record, "context_data") and record.context_data:
            context_str = " ".join(f"[{k}={v}]" for k, v in record.context_data.items())
            if context_str:
                message = f"{message} {context_str}"

        # Add correlation ID
        if hasattr(record, "correlation_id"):
            message = f"{message} [correlation_id={record.correlation_id}]"

        return message

    def format(self, record: logging.LogRecord) -> str:
        """Forward logging format calls to format_record."""
        return self.format_record(record)


@contextmanager
def log_operation(
    logger: logging.Logger,
    operation_name: str,
    level: int = logging.INFO,
    context: dict[str, Any] | None = None,
) -> Any:
    """
    Context manager for logging operations with timing and context tracking.

    Args:
    ----
        logger: The logger instance to use
        operation_name: Name of the operation being performed
        level: Log level to use
        context: Additional context data to include in the logs

    Yields:
    ------
        None: This context manager doesn't yield a value

    Raises:
    ------
        Exception: Re-raises any exception that occurs within the context

    """
    start_time = time.time()
    operation_id = str(uuid.uuid4())[:8]
    context = context or {}
    context["operation_id"] = operation_id

    logger.log(level, f"Starting {operation_name}", context=context)

    try:
        yield
        duration = time.time() - start_time
        logger.log(level, f"Completed {operation_name} in {duration:.2f}s", context=context)
    except Exception as e:
        duration = time.time() - start_time
        error_context = {
            **context,
            "error_type": type(e).__name__,
            "error": str(e),
            "duration": f"{duration:.2f}s",
        }
        logger.log(
            logging.ERROR,
            f"Failed {operation_name} after {duration:.2f}s",
            context=error_context,
            exc_info=True,
        )
        raise


@contextmanager
def correlation_id(correlation_id: str | None = None) -> Iterator[str]:
    """
    Context manager for setting a correlation ID for the current context.

    Args:
    ----
        correlation_id: ID to use, or None to generate a new one

    Yields:
    ------
        str: The current correlation ID (either provided or generated)

    """
    previous_id = (
        correlation_manager.get_correlation_id()
        if hasattr(_context_local, "correlation_id")
        else None
    )

    # Set new correlation ID
    if correlation_id:
        correlation_manager.set_correlation_id(correlation_id)
    else:
        correlation_manager.set_correlation_id(f"ztoq-{uuid.uuid4()}")

    try:
        yield correlation_manager.get_correlation_id()
    finally:
        # Restore previous correlation ID
        if previous_id:
            correlation_manager.set_correlation_id(previous_id)
        else:
            correlation_manager.clear_correlation_id()


class ErrorTracker:
    """
    Tracks errors and their context for later analysis.

    This class is useful for collecting errors during batch operations so they
    can be reported together at the end.

    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """
        Initialize an error tracker.

        Args:
        ----
            logger: Optional logger to use for logging errors. If not provided,
                a default logger will be used.

        """
        self.errors: list[dict[str, Any]] = []
        self.logger = logger or logging.getLogger("ztoq.error_tracker")

    def add_error(
        self, error: Exception, context: dict[str, Any] | None = None, log: bool = True
    ) -> None:
        """
        Add an error to the tracker.

        Args:
        ----
            error: The exception that occurred
            context: Additional context information
            log: Whether to log the error as well as tracking it

        """
        error_info = {
            "error_type": type(error).__name__,
            "message": str(error),
            "timestamp": datetime.now().isoformat(),
            "correlation_id": correlation_manager.get_correlation_id(),
            "context": context or {},
        }
        self.errors.append(error_info)

        if log:
            self.logger.error(
                f"Error tracked: {error_info['error_type']}: {error_info['message']}",
                context=context,
                exc_info=error,
            )

    @contextmanager
    def track_errors(
        self, context: dict[str, Any] | None = None, log: bool = True
    ) -> Iterator["ErrorTracker"]:
        """
        Context manager to track errors that occur during execution.

        Args:
        ----
            context: Additional context information
            log: Whether to log the error as well as tracking it

        Yields:
        ------
            ErrorTracker: The error tracker instance

        """
        try:
            yield self
        except Exception as e:
            self.add_error(e, context=context, log=log)
            raise

    def has_errors(self) -> bool:
        """
        Check if any errors have been tracked.
        """
        return len(self.errors) > 0

    def get_error_summary(self) -> dict[str, Any]:
        """
        Get a summary of tracked errors.

        Returns
        -------
            A dictionary containing error statistics including:
            - total_errors: Total count of tracked errors
            - error_types: Count of each error type
            - first_error: The first error that occurred
            - last_error: The most recent error

        """
        error_types: dict[str, int] = {}
        for error in self.errors:
            error_type = error["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "total_errors": len(self.errors),
            "error_types": error_types,
            "first_error": self.errors[0] if self.errors else None,
            "last_error": self.errors[-1] if self.errors else None,
        }

    def clear(self) -> None:
        """
        Clear all tracked errors.
        """
        self.errors = []


def configure_logging(
    level: int | str = logging.INFO,
    log_file: str | None = None,
    json_format: bool = False,
    include_timestamp: bool = True,
    use_rich: bool = True,
    debug: bool = False,
) -> None:
    """
    Configure application logging.

    Args:
    ----
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL or integer)
        log_file: Optional path to log file
        json_format: Whether to use JSON format for logs
        include_timestamp: Whether to include timestamps in logs
        use_rich: Whether to use Rich for console output
        debug: Whether to force debug mode

    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper())

    # Override with debug level if debug flag is set
    if debug:
        level = logging.DEBUG

    # Register custom logger class and record factory
    logging.setLoggerClass(StructuredLogger)
    logging.setLogRecordFactory(_log_record_factory)

    # Set up handlers
    handlers = []

    # Console handler
    if use_rich and RichHandler is not None:
        # Rich handler with custom formatter
        rich_handler = RichHandler(rich_tracebacks=True, markup=True, show_time=include_timestamp)
        rich_formatter = RichContextFormatter("%(message)s")
        rich_handler.setFormatter(rich_formatter)
        handlers.append(rich_handler)
    elif use_rich:
        # Fallback if RichHandler is not available
        console_handler = logging.StreamHandler(sys.stderr)
        format_str = (
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            if include_timestamp
            else "[%(levelname)s] %(name)s: %(message)s"
        )
        console_handler.setFormatter(logging.Formatter(format_str))
        handlers.append(console_handler)
    else:
        # Standard console handler
        console_handler = logging.StreamHandler(sys.stderr)
        if json_format:
            console_handler.setFormatter(JSONFormatter())
        else:
            format_str = (
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                if include_timestamp
                else "[%(levelname)s] %(name)s: %(message)s"
            )
            console_handler.setFormatter(logging.Formatter(format_str))
        handlers.append(console_handler)

    # File handler if requested
    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        if json_format:
            file_handler.setFormatter(JSONFormatter())
        else:
            format_str = (
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                if include_timestamp
                else "[%(levelname)s] %(name)s: %(message)s"
            )
            file_handler.setFormatter(logging.Formatter(format_str))
        handlers.append(file_handler)

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(max(level, logging.WARNING))  # Root logger should be at least WARNING

    # Remove existing handlers and add our configured ones
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for handler in handlers:
        root.addHandler(handler)

    # Configure ztoq logger
    logger = logging.getLogger("ztoq")
    logger.setLevel(level)
    logger.propagate = False

    # Remove existing handlers and add our configured ones
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    for handler in handlers:
        logger.addHandler(handler)

    # Log directly with Python's logging module to avoid structured logging issues during setup
    # Create a basic message that shows the configuration
    init_message = f"Logging configured with level {logging.getLevelName(level)}"

    # Configure a temporary basic handler to log this message
    temp_handler = logging.StreamHandler(sys.stderr)
    temp_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    # Use Python's logging without our structured logger for this one initial message
    current_logger_factory = logging.getLoggerClass()
    logging.setLoggerClass(logging.Logger)  # Temporarily set back to standard logger

    basic_logger = logging.getLogger("logging_setup")
    basic_logger.setLevel(level)
    basic_logger.addHandler(temp_handler)
    basic_logger.propagate = False

    # Log the initialization message
    basic_logger.info(init_message)

    # Cleanup: remove the temporary handler and restore our logger class
    basic_logger.removeHandler(temp_handler)
    logging.setLoggerClass(current_logger_factory)


# Helper function to get a logger with the standard configuration
def get_logger(name: str) -> StructuredLogger:
    """
    Get a logger with the standard configuration.

    Args:
    ----
        name: Name of the logger, typically __name__

    Returns:
    -------
        A structured logger instance

    """
    return logging.getLogger(name)
