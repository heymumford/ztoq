"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

from functools import lru_cache
from pathlib import Path
from ztoq.domain.models import OpenAPISpec
from ztoq.openapi_parser import load_openapi_spec

@lru_cache(maxsize=1)


def get_openapi_spec() -> OpenAPISpec:
    """Load and cache the OpenAPI specification."""
    spec_path = Path(__file__).parent.parent.parent / "docs" / "specs" / "z-openapi.yml"
    data = load_openapi_spec(spec_path)

    return OpenAPISpec(
        title=data.get("info", {}).get("title", "Unknown API"),
            version=data.get("info", {}).get("version", "0.0.0"),
            data=data,
            path=str(spec_path),
        )
