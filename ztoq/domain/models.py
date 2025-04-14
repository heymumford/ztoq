"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional

class OpenAPISpec(BaseModel):
    """OpenAPI specification model."""

    title: str
    version: str
    data: Dict[str, Any]
    path: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
