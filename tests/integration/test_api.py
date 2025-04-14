"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from ztoq.api.app import create_app
from ztoq.domain.models import OpenAPISpec

@pytest.mark.integration


class TestAPIRoutes:
    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI application."""
        return TestClient(create_app())

    @pytest.fixture
    def mock_openapi_spec(self):
        """Mock the OpenAPI spec for testing."""
        with patch("ztoq.core.services.get_openapi_spec") as mock:
            mock.return_value = OpenAPISpec(
                title="Test API",
                    version="1.0.0",
                    data={"info": {"title": "Test API", "version": "1.0.0"}, "paths": {}},
                    path="/test/path.yml",
                )
            yield mock

    def test_root_endpoint(self, client):
        """Test the root endpoint returns the expected message."""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()

    def test_api_root_endpoint(self, client):
        """Test the API root endpoint returns the expected message."""
        response = client.get("/api/")
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to ZTOQ API"}

    def test_spec_endpoint(self, client, mock_openapi_spec):
        """Test the spec endpoint returns the OpenAPI specification."""
        response = client.get("/api/spec")
        assert response.status_code == 200
        assert "info" in response.json()
        assert response.json()["info"]["title"] == "Test API"
        assert response.json()["info"]["version"] == "1.0.0"
