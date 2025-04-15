"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for CLI debug mode flag.

These tests verify that the debug mode flag works correctly.
"""

from unittest.mock import MagicMock, patch

import pytest

# Create mocks to avoid circular imports
typer_mock = MagicMock()
config_mock = MagicMock()

# Create a mock CLI app
with patch.dict("sys.modules", {
    "typer": typer_mock,
    "ztoq.core.config": config_mock,
}):
    # Now import our CLI module with mocked dependencies
    from ztoq.cli import callback, configure_app


@pytest.mark.unit
class TestCLIDebugMode:
    """Tests for CLI debug mode flag."""

    def test_callback_debug_flag(self):
        """Test that the callback passes debug flag correctly."""
        with patch("ztoq.cli.configure_app") as mock_configure:
            # Call the callback with debug=True
            callback(debug=True, version=False)
            # Verify the call
            mock_configure.assert_called_with(debug=True)

            # Call the callback with debug=False
            mock_configure.reset_mock()
            callback(debug=False, version=False)
            # Verify the call
            mock_configure.assert_called_with(debug=False)

    def test_configure_app(self):
        """Test that configure_app initializes app with debug mode."""
        with patch("ztoq.cli.init_app_config") as mock_init_config:
            # Set up mocked return value
            mock_config = MagicMock()
            mock_init_config.return_value = mock_config

            # Call with debug=True
            result = configure_app(debug=True)

            # Verify app initialized with debug=True
            mock_init_config.assert_called_with(debug=True, app_version=pytest.approx(any))
            mock_config.configure_logging.assert_called_once()
            assert result == mock_config
