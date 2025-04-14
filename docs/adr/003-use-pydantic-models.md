# ADR-003: Use Pydantic for Data Modeling

## Status

Accepted

## Context

The ZTOQ application needs to handle complex data structures from the Zephyr Scale API and ensure proper type validation. Options for data modeling and validation include:

1. Plain Python classes or dictionaries
2. dataclasses (standard library)
3. attrs library
4. Pydantic models
5. Marshmallow schemas

Requirements for our data models:
- Automatic validation of incoming data
- Type hints and IDE autocompletion
- JSON serialization/deserialization
- Support for nested models and complex types
- Handling of camelCase to snake_case field name conversions (API uses camelCase)
- Optional fields and default values

## Decision

We will use Pydantic for all data models in the ZTOQ application.

## Consequences

### Positive

- Pydantic provides runtime validation with good error messages
- Native integration with FastAPI (if we add APIs later)
- Excellent type hint support for IDE autocompletion
- JSON serialization/deserialization is built-in
- Support for field aliases to handle camelCase API fields
- Automatic conversion between Python and JSON types
- Good performance characteristics
- Active development and community support

### Negative

- Steeper learning curve than plain classes or dataclasses
- Additional dependency in the project
- Can be more verbose for simpler data structures
- Runtime overhead compared to plain dictionaries (though this is minimal)

## Implementation Details

We'll create Pydantic models for all key data structures from the Zephyr Scale API:

```python
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class TestStep(BaseModel):
    """Represents a test step in a test case or execution."""
    id: Optional[str] = None
    index: int
    description: str
    expected_result: Optional[str] = Field(None, alias="expectedResult")
    data: Optional[str] = None
    actual_result: Optional[str] = Field(None, alias="actualResult")
    status: Optional[str] = None
    
    class Config:
        allow_population_by_field_name = True

class TestCase(BaseModel):
    """Represents a Zephyr test case."""
    id: str
    key: str
    name: str
    objective: Optional[str] = None
    precondition: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    # ... other fields
    steps: List[TestStep] = Field(default_factory=list)
    
    class Config:
        allow_population_by_field_name = True
```

This approach will ensure consistent validation and serialization across the application.

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../../LICENSE)*