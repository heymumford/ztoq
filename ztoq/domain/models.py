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
