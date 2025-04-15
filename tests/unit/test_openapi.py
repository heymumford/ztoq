"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ztoq.core.services import get_openapi_spec
from ztoq.domain.models import OpenAPISpec
from ztoq.openapi_parser import load_openapi_spec


@pytest.mark.unit
class TestOpenAPILoader:
    def test_load_openapi_spec_missing_file(self):
        """Test that loading a missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_openapi_spec(Path("nonexistent.yml"))

    @patch("ztoq.openapi_parser.open", create=True)
    @patch("ztoq.openapi_parser.yaml.safe_load")
    @patch("ztoq.openapi_parser.Path.exists")
    def test_load_openapi_spec_success(self, mock_exists, mock_yaml_load, mock_open):
        """Test successful loading of OpenAPI spec."""
        # Setup mocks
        mock_exists.return_value = True
        mock_yaml_load.return_value = {"info": {"title": "Test API", "version": "1.0.0"}}
        mock_open.return_value.__enter__.return_value = MagicMock()

        # Call function
        result = load_openapi_spec(Path("test.yml"))

        # Verify results
        assert result == {"info": {"title": "Test API", "version": "1.0.0"}}
        mock_exists.assert_called_once()
        mock_open.assert_called_once()
        mock_yaml_load.assert_called_once()


@pytest.mark.unit
class TestOpenAPIService:
    @patch("ztoq.core.services.load_openapi_spec")
    def test_get_openapi_spec(self, mock_load_spec):
        """Test that the service correctly creates an OpenAPISpec object."""
        # Setup mock
        mock_load_spec.return_value = {
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {},
        }

        # Call function
        result = get_openapi_spec()

        # Verify result
        assert isinstance(result, OpenAPISpec)
        assert result.title == "Test API"
        assert result.version == "1.0.0"
        assert "info" in result.data
        assert "paths" in result.data
