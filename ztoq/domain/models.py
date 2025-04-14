"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

from typing import Any
from pydantic import BaseModel

class OpenAPISpec(BaseModel):
    """OpenAPI specification model."""

    title: str
    version: str
    data: dict[str, Any]
    path: str | None = None

    class Config:
        allow_population_by_field_name = True
