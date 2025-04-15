"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Configuration management for ZTOQ.

This module provides a central location for all configuration settings in ZTOQ.
It handles environment variables, default values, and validation of configuration
parameters for different components of the application.
"""

import logging
import os
from pathlib import Path
from typing import Any, ClassVar, Never

from pydantic import BaseModel, Field, field_validator, model_validator

# Configure logging
logger = logging.getLogger(__name__)


class BaseConfig(BaseModel):
    """Base configuration class with common functionality."""

    # Class variable to store environment variable prefixes
    ENV_PREFIX: ClassVar[str] = "ZTOQ_"

    @classmethod
    def from_env(cls, **overrides) -> Never:
        """
        Create a configuration instance from environment variables.

        Args:
        ----
            **overrides: Key-value pairs that override environment variables

        Returns:
        -------
            An instance of the configuration class

        """
        raise NotImplementedError("Subclasses must implement from_env method")

    @classmethod
    def get_env_var(cls, key: str, default: Any = None) -> Any:
        """
        Get an environment variable with the class prefix.

        Args:
        ----
            key: Key name without prefix
            default: Default value if environment variable is not found

        Returns:
        -------
            The environment variable value or default

        """
        env_key = f"{cls.ENV_PREFIX}{key.upper()}"
        return os.environ.get(env_key, default)


class LoggingConfig(BaseConfig):
    """Configuration for logging settings."""

    level: str = Field(
        default_factory=lambda: os.environ.get("ZTOQ_LOG_LEVEL", "INFO"),
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    format: str = Field(
        default="%(message)s",
        description="Logging format string",
    )
    date_format: str = Field(
        default="[%X]",
        description="Date format for logging timestamps",
    )
    use_rich: bool = Field(
        default=True,
        description="Whether to use rich for logging formatting",
    )
    log_file: str | None = Field(
        default=None,
        description="Path to the log file (None for console-only logging)",
    )
    json_format: bool = Field(
        default=False,
        description="Whether to use JSON format for logs",
    )
    include_correlation_id: bool = Field(
        default=True,
        description="Whether to include correlation IDs in logs",
    )

    # Environment variable names
    ENV_PREFIX: ClassVar[str] = "ZTOQ_"

    @field_validator("level")
    @classmethod
    def validate_level(cls, value):
        """Validate that the log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        value = value.upper()
        if value not in valid_levels:
            logger.warning(f"Invalid log level '{value}', defaulting to INFO")
            return "INFO"
        return value

    @classmethod
    def from_env(cls, **overrides) -> "LoggingConfig":
        """Create a logging configuration from environment variables."""
        config = {
            "level": cls.get_env_var("LOG_LEVEL", "INFO"),
            "format": cls.get_env_var("LOG_FORMAT", "%(message)s"),
            "date_format": cls.get_env_var("LOG_DATE_FORMAT", "[%X]"),
            "use_rich": cls.get_env_var("LOG_USE_RICH", "true").lower() == "true",
            "log_file": cls.get_env_var("LOG_FILE", None),
            "json_format": cls.get_env_var("LOG_JSON", "false").lower() == "true",
            "include_correlation_id": cls.get_env_var("LOG_CORRELATION_ID", "true").lower()
            == "true",
        }

        # Override with any directly provided values
        config.update(overrides)

        return cls(**config)

    def get_log_level_int(self) -> int:
        """Get the numeric logging level."""
        return getattr(logging, self.level)

    def configure_logging(self, debug: bool = False) -> None:
        """
        Configure logging based on the settings.

        Args:
        ----
            debug: Whether to force debug mode

        """
        # Import the contextual logging module
        from ztoq.core.logging import configure_logging as configure_contextual_logging

        # Use our new contextual logging system
        configure_contextual_logging(
            level=logging.DEBUG if debug else self.get_log_level_int(),
            log_file=self.log_file,
            json_format=self.json_format,
            include_timestamp=True,
            use_rich=self.use_rich,
            debug=debug,
        )

        logger.debug(
            f"Logging configured with level {logging.getLevelName(self.get_log_level_int() if not debug else logging.DEBUG)}",
        )


class DatabaseConfig(BaseConfig):
    """Configuration for database connections."""

    db_type: str = Field(
        default="sqlite",
        description="Database type (sqlite, postgresql, snowflake)",
    )
    db_path: str | None = Field(
        default=None,
        description="Path to SQLite database file (for SQLite)",
    )
    host: str | None = Field(
        default=None,
        description="Database host (for PostgreSQL/Snowflake)",
    )
    port: int | None = Field(
        default=None,
        description="Database port (for PostgreSQL/Snowflake)",
    )
    username: str | None = Field(
        default=None,
        description="Database username (for PostgreSQL/Snowflake)",
    )
    password: str | None = Field(
        default=None,
        description="Database password (for PostgreSQL/Snowflake)",
    )
    database: str | None = Field(
        default=None,
        description="Database name (for PostgreSQL/Snowflake)",
    )
    schema: str | None = Field(
        default=None,
        description="Database schema (for Snowflake)",
    )
    warehouse: str | None = Field(
        default=None,
        description="Warehouse (for Snowflake)",
    )
    role: str | None = Field(
        default=None,
        description="Role (for Snowflake)",
    )
    account: str | None = Field(
        default=None,
        description="Account (for Snowflake)",
    )
    pool_size: int = Field(
        default=5,
        description="Connection pool size",
    )
    max_overflow: int = Field(
        default=10,
        description="Maximum number of connections to overflow",
    )
    echo: bool = Field(
        default=False,
        description="Whether to echo SQL statements",
    )

    # Environment variable names
    ENV_PREFIX: ClassVar[str] = "ZTOQ_"

    @model_validator(mode="after")
    def validate_db_config(self):
        """Validate database configuration based on the database type."""
        # Create default path for SQLite if not provided
        if self.db_type == "sqlite" and not self.db_path:
            self.db_path = os.path.join(os.getcwd(), "ztoq_data.db")

        # Validate required PostgreSQL parameters
        elif self.db_type == "postgresql":
            if not all([self.host, self.username, self.database]):
                raise ValueError("Host, username, and database name are required for PostgreSQL")

        # Validate required Snowflake parameters
        elif self.db_type == "snowflake":
            if not all([self.account, self.username, self.database, self.warehouse]):
                raise ValueError(
                    "Account, username, database, and warehouse are required for Snowflake",
                )

        # Check for unsupported database types
        elif self.db_type not in ["sqlite", "postgresql", "snowflake"]:
            raise ValueError(f"Unsupported database type: {self.db_type}")

        return self

    @classmethod
    def from_env(cls, **overrides) -> "DatabaseConfig":
        """Create a database configuration from environment variables."""
        # Get database type from environment or use default
        db_type = cls.get_env_var("DB_TYPE", "sqlite").lower()

        # Base configuration with common settings
        config = {
            "db_type": db_type,
            "pool_size": int(cls.get_env_var("DB_POOL_SIZE", "5")),
            "max_overflow": int(cls.get_env_var("DB_MAX_OVERFLOW", "10")),
            "echo": cls.get_env_var("DB_ECHO", "false").lower() == "true",
        }

        # Add type-specific configuration
        if db_type == "sqlite":
            config["db_path"] = cls.get_env_var("DB_PATH")
        elif db_type == "postgresql":
            config.update(
                {
                    "host": cls.get_env_var("PG_HOST"),
                    "port": int(cls.get_env_var("PG_PORT", "5432")),
                    "username": cls.get_env_var("PG_USER"),
                    "password": cls.get_env_var("PG_PASSWORD"),
                    "database": cls.get_env_var("PG_DATABASE"),
                },
            )
        elif db_type == "snowflake":
            config.update(
                {
                    "account": cls.get_env_var("SF_ACCOUNT"),
                    "username": cls.get_env_var("SF_USER"),
                    "password": cls.get_env_var("SF_PASSWORD"),
                    "database": cls.get_env_var("SF_DATABASE"),
                    "warehouse": cls.get_env_var("SF_WAREHOUSE"),
                    "schema": cls.get_env_var("SF_SCHEMA"),
                    "role": cls.get_env_var("SF_ROLE"),
                },
            )

        # Override with any directly provided values
        config.update(overrides)

        return cls(**config)

    def get_connection_string(self) -> str:
        """
        Get the database connection string based on the configuration.

        Returns
        -------
            Database connection string for SQLAlchemy

        """
        if self.db_type == "sqlite":
            db_path = Path(self.db_path) if self.db_path else Path("ztoq_data.db")
            # Ensure parent directory exists
            db_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{db_path}"
        if self.db_type == "postgresql":
            # Validate required PostgreSQL parameters
            if not all([self.host, self.username, self.database]):
                raise ValueError("Host, username, and database name are required for PostgreSQL")
            port = self.port or 5432
            password_part = f":{self.password}" if self.password else ""
            return f"postgresql://{self.username}{password_part}@{self.host}:{port}/{self.database}"
        if self.db_type == "snowflake":
            # Validate required Snowflake parameters
            if not all([self.account, self.username, self.database, self.warehouse]):
                raise ValueError(
                    "Account, username, database, and warehouse are required for Snowflake",
                )
            password_part = f":{self.password}" if self.password else ""
            conn_str = f"snowflake://{self.username}{password_part}@{self.account}/{self.database}"

            # Add optional parameters
            params = []
            if self.warehouse:
                params.append(f"warehouse={self.warehouse}")
            if self.schema:
                params.append(f"schema={self.schema}")
            if self.role:
                params.append(f"role={self.role}")

            if params:
                conn_str += "?" + "&".join(params)

            return conn_str
        raise ValueError(f"Unsupported database type: {self.db_type}")


class ZephyrConfig(BaseConfig):
    """Configuration for Zephyr Scale API."""

    base_url: str = Field(
        ...,
        description="Base URL for Zephyr Scale API",
    )
    api_token: str = Field(
        ...,
        description="API token for Zephyr Scale authentication",
    )
    project_key: str = Field(
        ...,
        description="JIRA project key",
    )
    timeout: float = Field(
        default=30.0,
        description="API request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed API requests",
    )

    # Environment variable names
    ENV_PREFIX: ClassVar[str] = "ZTOQ_"

    @field_validator("base_url")
    def validate_base_url(self, value):
        """Validate base URL format."""
        if not value:
            raise ValueError("base_url must be provided")

        # Ensure base URL has proper prefix, adding https:// if missing
        if not value.startswith(("http://", "https://")):
            value = f"https://{value}"
        return value

    @field_validator("api_token")
    def validate_api_token(self, value):
        """Validate API token."""
        if not value:
            raise ValueError("api_token must be provided")
        return value

    @classmethod
    def from_env(cls, **overrides) -> "ZephyrConfig":
        """Create a Zephyr configuration from environment variables."""
        config = {
            "base_url": cls.get_env_var("ZEPHYR_BASE_URL", ""),
            "api_token": cls.get_env_var("ZEPHYR_API_TOKEN", ""),
            "project_key": cls.get_env_var("ZEPHYR_PROJECT_KEY", ""),
            "timeout": float(cls.get_env_var("ZEPHYR_TIMEOUT", "30.0")),
            "max_retries": int(cls.get_env_var("ZEPHYR_MAX_RETRIES", "3")),
        }

        # Override with any directly provided values
        config.update(overrides)

        return cls(**config)


class QTestConfig(BaseConfig):
    """Configuration for qTest API."""

    base_url: str = Field(
        default_factory=lambda: os.environ.get("ZTOQ_QTEST_BASE_URL", ""),
        description="Base URL for qTest API (e.g., https://example.qtest.com)",
    )
    username: str = Field(
        default="",
        description="Username for qTest authentication (not needed with bearer token)",
    )
    password: str = Field(
        default="",
        description="Password for qTest authentication (not needed with bearer token)",
    )
    project_id: int = Field(
        ...,
        description="Project ID to work with",
        gt=0,
    )
    bearer_token: str = Field(
        default_factory=lambda: os.environ.get("ZTOQ_QTEST_BEARER_TOKEN", ""),
        description="Bearer token for qTest authentication",
    )
    timeout: float = Field(
        default=30.0,
        description="API request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed API requests",
    )

    # Environment variable names
    ENV_PREFIX: ClassVar[str] = "ZTOQ_"

    @field_validator("base_url")
    def validate_base_url(self, value):
        """Validate base URL format."""
        if not value:
            raise ValueError("base_url must be provided")

        # Ensure base URL has proper prefix, adding https:// if missing
        if not value.startswith(("http://", "https://")):
            value = f"https://{value}"
        return value

    @model_validator(mode="after")
    def validate_auth_method(self):
        """Validate that either username/password or bearer token is provided."""
        username = self.username
        password = self.password
        bearer_token = self.bearer_token

        if not bearer_token and not (username and password):
            raise ValueError(
                "Either bearer_token or username/password combination must be provided.",
            )

        return self

    @classmethod
    def from_env(cls, **overrides) -> "QTestConfig":
        """Create a qTest configuration from environment variables."""
        config = {
            "base_url": cls.get_env_var("QTEST_BASE_URL", ""),
            "username": cls.get_env_var("QTEST_USERNAME", ""),
            "password": cls.get_env_var("QTEST_PASSWORD", ""),
            "bearer_token": cls.get_env_var("QTEST_BEARER_TOKEN", ""),
            "project_id": int(cls.get_env_var("QTEST_PROJECT_ID", "0")),
            "timeout": float(cls.get_env_var("QTEST_TIMEOUT", "30.0")),
            "max_retries": int(cls.get_env_var("QTEST_MAX_RETRIES", "3")),
        }

        # Override with any directly provided values
        config.update(overrides)

        return cls(**config)


class AppConfig(BaseConfig):
    """Main application configuration that aggregates all other configurations."""

    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration",
    )
    database: DatabaseConfig | None = Field(
        default=None,
        description="Database configuration",
    )
    zephyr: ZephyrConfig | None = Field(
        default=None,
        description="Zephyr Scale API configuration",
    )
    qtest: QTestConfig | None = Field(
        default=None,
        description="qTest API configuration",
    )
    debug: bool = Field(
        default=False,
        description="Debug mode flag",
    )
    app_name: str = Field(
        default="ZTOQ",
        description="Application name",
    )
    app_version: str = Field(
        default="0.0.0",
        description="Application version",
    )

    # Environment variable names
    ENV_PREFIX: ClassVar[str] = "ZTOQ_"

    @classmethod
    def from_env(cls, **overrides) -> "AppConfig":
        """Create an application configuration from environment variables."""
        config = {
            "logging": LoggingConfig.from_env(),
            "debug": cls.get_env_var("DEBUG", "false").lower() == "true",
            "app_name": cls.get_env_var("APP_NAME", "ZTOQ"),
            "app_version": cls.get_env_var("APP_VERSION", "0.0.0"),
        }

        # Add optional configurations if their environment variables are present
        if any(key.startswith(("DB_", "PG_", "SF_")) for key in os.environ):
            config["database"] = DatabaseConfig.from_env()

        if any(key.startswith("ZEPHYR_") for key in os.environ):
            config["zephyr"] = ZephyrConfig.from_env()

        if any(key.startswith("QTEST_") for key in os.environ):
            config["qtest"] = QTestConfig.from_env()

        # Override with any directly provided values
        for key, value in overrides.items():
            if key in ["logging", "database", "zephyr", "qtest"] and value is not None:
                # For nested configs, accept either raw dict or instantiated objects
                if isinstance(value, dict):
                    config_class = globals()[key.capitalize() + "Config"]
                    config[key] = config_class(**value)
                else:
                    config[key] = value
            else:
                config[key] = value

        return cls(**config)

    def configure_logging(self) -> None:
        """Configure logging based on the settings."""
        self.logging.configure_logging(debug=self.debug)


# Global app configuration
_app_config = None


def get_app_config() -> AppConfig:
    """
    Get the global application configuration.

    Returns
    -------
        The application configuration instance

    """
    global _app_config
    if _app_config is None:
        _app_config = AppConfig.from_env()
    return _app_config


def init_app_config(config: AppConfig = None, **kwargs) -> AppConfig:
    """
    Initialize the global application configuration.

    Args:
    ----
        config: An existing AppConfig instance
        **kwargs: Key-value pairs for creating a new AppConfig

    Returns:
    -------
        The application configuration instance

    """
    global _app_config
    _app_config = config if config is not None else AppConfig.from_env(**kwargs)
    return _app_config


# Function to configure logging directly with debug flag
def configure_logging(debug: bool = False) -> None:
    """
    Configure logging with optional debug mode.

    Args:
    ----
        debug: Whether to force debug mode

    """
    from ztoq.core.logging import configure_logging as configure_contextual_logging

    # Use our new contextual logging system
    configure_contextual_logging(
        level="DEBUG" if debug else "INFO",
        use_rich=True,
        include_timestamp=True,
        debug=debug,
    )
