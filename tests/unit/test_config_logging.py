"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Unit tests for configuration logging functions.

These tests verify that the logging configuration works correctly with debug mode.
"""

from unittest.mock import patch

import pytest

from ztoq.core.config import configure_logging


@pytest.mark.unit
class TestConfigLogging:
    """Tests for the logging configuration."""

    @patch("ztoq.core.logging.configure_logging")
    def test_configure_logging_debug(self, mock_configure_logging):
        """Test that debug mode sets correct log level."""
        # Test with debug=True
        with patch("logging.setLoggerClass"), patch("logging.setLogRecordFactory"):
            configure_logging(debug=True)

            # Check that logging was configured with DEBUG level
            mock_configure_logging.assert_called_once()
            args, kwargs = mock_configure_logging.call_args
            assert kwargs["debug"] is True

            # Test with debug=False (default)
            mock_configure_logging.reset_mock()
            configure_logging(debug=False)

            # Check that logging was configured with INFO level
            mock_configure_logging.assert_called_once()
            args, kwargs = mock_configure_logging.call_args
            assert kwargs["debug"] is False
