"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for configuration management module.

These tests verify that the configuration module correctly handles environment variables,
validation, and default values for different components of the application.
"""

import logging
import os
from unittest.mock import patch

import pytest

from ztoq.core.config import (
    AppConfig,
    DatabaseConfig,
    LoggingConfig,
    QTestConfig,
    ZephyrConfig,
    get_app_config,
    init_app_config,
)


@pytest.mark.unit
class TestLoggingConfig:
    """Tests for the logging configuration."""

    def test_logging_config_defaults(self):
        """Test that logging config has sensible defaults."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.format == "%(message)s"
        assert config.date_format == "[%X]"
        assert config.use_rich is True

    def test_logging_config_validation(self):
        """Test that log level validation works."""
        # Valid log levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggingConfig(level=level)
            assert config.level == level

        # Invalid log level should default to INFO
        config = LoggingConfig(level="INVALID")
        assert config.level == "INFO"

    def test_get_log_level_int(self):
        """Test converting log level to int."""
        config = LoggingConfig(level="DEBUG")
        assert config.get_log_level_int() == logging.DEBUG

        config = LoggingConfig(level="INFO")
        assert config.get_log_level_int() == logging.INFO

    @patch("logging.basicConfig")
    def test_configure_logging(self, mock_basicConfig):
        """Test that logging configuration is applied correctly."""
        config = LoggingConfig(level="INFO", use_rich=True)
        config.configure_logging()

        # Should use INFO level by default
        mock_basicConfig.assert_called_once()
        args, kwargs = mock_basicConfig.call_args
        assert kwargs["level"] == logging.INFO

        # Test debug mode overrides level
        mock_basicConfig.reset_mock()
        config.configure_logging(debug=True)
        args, kwargs = mock_basicConfig.call_args
        assert kwargs["level"] == logging.DEBUG

    @patch.dict(os.environ, {"ZTOQ_LOG_LEVEL": "DEBUG", "ZTOQ_LOG_FORMAT": "%(levelname)s: %(message)s"})
    def test_from_env(self):
        """Test creating config from environment variables."""
        config = LoggingConfig.from_env()
        assert config.level == "DEBUG"
        assert config.format == "%(levelname)s: %(message)s"

        # Override with direct values
        config = LoggingConfig.from_env(level="ERROR")
        assert config.level == "ERROR"
        assert config.format == "%(levelname)s: %(message)s"  # Still from env


@pytest.mark.unit
class TestDatabaseConfig:
    """Tests for the database configuration."""

    def test_database_config_defaults(self):
        """Test that database config has sensible defaults."""
        config = DatabaseConfig()
        assert config.db_type == "sqlite"
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.echo is False

        # SQLite config should create a default path
        assert config.db_path is not None

    def test_database_config_validation(self):
        """Test validation for different database types."""
        # Valid SQLite config
        config = DatabaseConfig(db_type="sqlite", db_path="/path/to/db.sqlite")
        assert config.db_type == "sqlite"
        assert config.db_path == "/path/to/db.sqlite"

        # Valid PostgreSQL config
        config = DatabaseConfig(
            db_type="postgresql",
            host="localhost",
            port=5432,
            username="postgres",
            password="postgres",
            database="ztoq",
        )
        assert config.db_type == "postgresql"
        assert config.host == "localhost"

        # Valid Snowflake config
        config = DatabaseConfig(
            db_type="snowflake",
            account="testaccount",
            username="testuser",
            password="testpass",
            database="testdb",
            warehouse="testwh",
            schema="testschema",
            role="testrole",
        )
        assert config.db_type == "snowflake"
        assert config.account == "testaccount"

        # Invalid PostgreSQL config (missing required fields)
        with pytest.raises(ValueError):
            DatabaseConfig(db_type="postgresql", host="", username="postgres", database="ztoq")

        # Invalid Snowflake config (missing required fields)
        with pytest.raises(ValueError):
            DatabaseConfig(db_type="snowflake", account="", username="testuser")

        # Invalid database type
        with pytest.raises(ValueError):
            DatabaseConfig(db_type="unknown")

    def test_get_connection_string(self):
        """Test generating connection strings for different database types."""
        # SQLite - mock the path creation to avoid file system access
        with patch("pathlib.Path.mkdir"):
            config = DatabaseConfig(db_type="sqlite", db_path="/path/to/db.sqlite")
            assert config.get_connection_string() == "sqlite:////path/to/db.sqlite"

        # PostgreSQL
        config = DatabaseConfig(
            db_type="postgresql",
            host="localhost",
            port=5432,
            username="postgres",
            password="postgres",
            database="ztoq",
        )
        assert config.get_connection_string() == "postgresql://postgres:postgres@localhost:5432/ztoq"

        # Snowflake
        config = DatabaseConfig(
            db_type="snowflake",
            account="testaccount",
            username="testuser",
            password="testpass",
            database="testdb",
            warehouse="testwh",
            schema="testschema",
            role="testrole",
        )
        conn_str = config.get_connection_string()
        assert conn_str.startswith("snowflake://testuser:testpass@testaccount/testdb")
        assert "warehouse=testwh" in conn_str
        assert "schema=testschema" in conn_str
        assert "role=testrole" in conn_str

    @patch.dict(os.environ, {
        "ZTOQ_DB_TYPE": "postgresql",
        "ZTOQ_PG_HOST": "test-host",
        "ZTOQ_PG_PORT": "5433",
        "ZTOQ_PG_USER": "test-user",
        "ZTOQ_PG_PASSWORD": "test-pass",
        "ZTOQ_PG_DATABASE": "test-db",
    })
    def test_from_env_postgresql(self):
        """Test creating PostgreSQL config from environment variables."""
        config = DatabaseConfig.from_env()
        assert config.db_type == "postgresql"
        assert config.host == "test-host"
        assert config.port == 5433
        assert config.username == "test-user"
        assert config.password == "test-pass"
        assert config.database == "test-db"

    @patch.dict(os.environ, {
        "ZTOQ_DB_TYPE": "snowflake",
        "ZTOQ_SF_ACCOUNT": "test-account",
        "ZTOQ_SF_USER": "test-user",
        "ZTOQ_SF_PASSWORD": "test-pass",
        "ZTOQ_SF_DATABASE": "test-db",
        "ZTOQ_SF_WAREHOUSE": "test-wh",
        "ZTOQ_SF_SCHEMA": "test-schema",
        "ZTOQ_SF_ROLE": "test-role",
    })
    def test_from_env_snowflake(self):
        """Test creating Snowflake config from environment variables."""
        config = DatabaseConfig.from_env()
        assert config.db_type == "snowflake"
        assert config.account == "test-account"
        assert config.username == "test-user"
        assert config.password == "test-pass"
        assert config.database == "test-db"
        assert config.warehouse == "test-wh"
        assert config.schema == "test-schema"
        assert config.role == "test-role"


@pytest.mark.unit
class TestZephyrConfig:
    """Tests for the Zephyr Scale API configuration."""

    def test_zephyr_config_validation(self):
        """Test that ZephyrConfig validates input correctly."""
        # Valid config
        config = ZephyrConfig(
            base_url="https://api.example.com",
            api_token="valid-token",
            project_key="TEST",
        )
        assert config.base_url == "https://api.example.com"
        assert config.api_token == "valid-token"
        assert config.project_key == "TEST"

        # Missing URL protocol should add https://
        config = ZephyrConfig(
            base_url="api.example.com",
            api_token="valid-token",
            project_key="TEST",
        )
        assert config.base_url == "https://api.example.com"

        # Invalid config - missing required fields
        with pytest.raises(ValueError):
            ZephyrConfig(base_url="", api_token="valid-token", project_key="TEST")

        with pytest.raises(ValueError):
            ZephyrConfig(base_url="https://api.example.com", api_token="", project_key="TEST")

    @patch.dict(os.environ, {
        "ZTOQ_ZEPHYR_BASE_URL": "api.test.com",
        "ZTOQ_ZEPHYR_API_TOKEN": "env-token",
        "ZTOQ_ZEPHYR_PROJECT_KEY": "ENV-TEST",
    })
    def test_from_env(self):
        """Test creating config from environment variables."""
        config = ZephyrConfig.from_env()
        assert config.base_url == "https://api.test.com"
        assert config.api_token == "env-token"
        assert config.project_key == "ENV-TEST"

        # Override with direct values
        config = ZephyrConfig.from_env(project_key="OVERRIDE")
        assert config.base_url == "https://api.test.com"
        assert config.api_token == "env-token"
        assert config.project_key == "OVERRIDE"


@pytest.mark.unit
class TestQTestConfig:
    """Tests for the qTest API configuration."""

    def test_qtest_config_validation(self):
        """Test that QTestConfig validates input correctly."""
        # Valid config with username/password
        config = QTestConfig(
            base_url="https://qtest.example.com",
            username="user@example.com",
            password="password123",
            project_id=123,
        )
        assert config.base_url == "https://qtest.example.com"
        assert config.username == "user@example.com"
        assert config.password == "password123"
        assert config.project_id == 123

        # Valid config with bearer token
        config = QTestConfig(
            base_url="https://qtest.example.com",
            bearer_token="valid-token",
            project_id=123,
        )
        assert config.base_url == "https://qtest.example.com"
        assert config.bearer_token == "valid-token"
        assert config.project_id == 123

        # Invalid config - missing auth methods
        with pytest.raises(ValueError):
            QTestConfig(
                base_url="https://qtest.example.com",
                username="",
                password="",
                bearer_token="",
                project_id=123,
            )

        # Invalid project ID (negative)
        with pytest.raises(ValueError):
            QTestConfig(
                base_url="https://qtest.example.com",
                username="user@example.com",
                password="password123",
                project_id=-1,
            )

    @patch.dict(os.environ, {
        "ZTOQ_QTEST_BASE_URL": "qtest.test.com",
        "ZTOQ_QTEST_BEARER_TOKEN": "env-token",
        "ZTOQ_QTEST_PROJECT_ID": "456",
    })
    def test_from_env(self):
        """Test creating config from environment variables."""
        config = QTestConfig.from_env()
        assert config.base_url == "https://qtest.test.com"
        assert config.bearer_token == "env-token"
        assert config.project_id == 456

        # Override with direct values
        config = QTestConfig.from_env(project_id=789)
        assert config.base_url == "https://qtest.test.com"
        assert config.bearer_token == "env-token"
        assert config.project_id == 789


@pytest.mark.unit
class TestAppConfig:
    """Tests for the application configuration."""

    def test_app_config_defaults(self):
        """Test that app config has sensible defaults."""
        config = AppConfig()
        assert config.debug is False
        assert config.app_name == "ZTOQ"
        assert isinstance(config.logging, LoggingConfig)
        assert config.database is None
        assert config.zephyr is None
        assert config.qtest is None

    def test_configure_logging(self):
        """Test that configure_logging passes debug flag correctly."""
        with patch.object(LoggingConfig, "configure_logging") as mock_configure:
            # Without debug
            config = AppConfig(debug=False)
            config.configure_logging()
            mock_configure.assert_called_with(debug=False)

            # With debug
            mock_configure.reset_mock()
            config = AppConfig(debug=True)
            config.configure_logging()
            mock_configure.assert_called_with(debug=True)

    def test_from_env(self):
        """Test creating app config from environment."""
        with patch.dict(os.environ, {"ZTOQ_DEBUG": "true", "ZTOQ_APP_VERSION": "1.2.3"}):
            config = AppConfig.from_env()
            assert config.debug is True
            assert config.app_version == "1.2.3"


@pytest.mark.unit
class TestGlobalConfig:
    """Tests for global configuration functions."""

    def test_get_app_config(self):
        """Test that get_app_config initializes config if needed."""
        # Reset global config
        from ztoq.core.config import _app_config
        _app_config = None

        # First call should initialize
        config = get_app_config()
        assert config is not None
        assert isinstance(config, AppConfig)

        # Second call should return the same instance
        config2 = get_app_config()
        assert config2 is config

    def test_init_app_config(self):
        """Test that init_app_config sets the global config."""
        # Initialize with an instance
        test_config = AppConfig(app_name="TEST")
        result = init_app_config(config=test_config)
        assert result is test_config
        assert get_app_config() is test_config

        # Initialize with kwargs
        result = init_app_config(app_name="NEW")
        assert result.app_name == "NEW"
        assert get_app_config().app_name == "NEW"
