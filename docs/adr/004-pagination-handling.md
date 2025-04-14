# ADR-004: Strategy for Handling Paginated API Responses

## Status

Accepted

## Context

The Zephyr Scale API uses pagination for endpoints that can return large amounts of data (e.g., test cases, test executions). This means we need a reliable strategy to handle paginated responses without overloading the API or the client application.

Pagination in the Zephyr Scale API works by providing:
- `startAt` parameter to specify the starting index
- `maxResults` parameter to limit results per page (default and max is usually 100)
- Response includes `totalCount`, `startAt`, `maxResults`, and `isLast` flags

We considered several approaches:
1. Manual pagination handling in each API call
2. A unified pagination helper function
3. A dedicated iterator class for paginated responses
4. Automatic retrieval of all pages at once
5. Asynchronous loading of pages

## Decision

We will implement a generic `PaginatedIterator` class that:
- Is parameterized by the model type being returned
- Lazily fetches pages as needed when iterating
- Handles pagination details transparently
- Supports type hinting for IDE assistance

## Consequences

### Positive

- Clean API for consuming paginated resources
- Lazy loading means we only fetch what's needed
- Type safety through generic typing
- Consistent pagination handling across all API endpoints
- Simplifies client code that needs to process large datasets
- Memory-efficient by not loading all data at once

### Negative

- More complex implementation than simple helper functions
- Requires understanding of Python's iterator protocol
- May be more difficult for new contributors to understand
- Potential for multiple API calls when iterating (though this is also a feature)

## Implementation Details

We'll create a `PaginatedIterator` class with this structure:

```python
from typing import TypeVar, Generic, Type, cast, Optional, Dict, Any

T = TypeVar("T")

class PaginatedIterator(Generic[T]):
    """Iterator for paginated API responses."""
    
    def __init__(
        self, 
        client: "ZephyrClient", 
        endpoint: str,
        model_class: Type[T],
        params: Optional[Dict[str, Any]] = None,
        page_size: int = 100
    ):
        """Initialize the paginated iterator."""
        self.client = client
        self.endpoint = endpoint
        self.model_class = model_class
        self.params = params or {}
        self.params["maxResults"] = page_size
        self.current_page = None
        self.item_index = 0
        
    def __iter__(self):
        return self
    
    def __next__(self) -> T:
        # Fetch first page if needed
        if not self.current_page:
            self._fetch_next_page()
        
        # Check if we need to fetch the next page
        if self.item_index >= len(self.current_page.values):
            if self.current_page.is_last:
                raise StopIteration
            
            self._fetch_next_page()
            
        # Return the next item
        item = cast(T, self.model_class(**self.current_page.values[self.item_index]))
        self.item_index += 1
        return item
    
    def _fetch_next_page(self):
        """Fetch the next page of results."""
        if self.current_page:
            self.params["startAt"] = self.current_page.start_at + len(self.current_page.values)
        else:
            self.params["startAt"] = 0
            
        response = self.client._make_request("GET", self.endpoint, params=self.params)
        self.current_page = PaginatedResponse(**response)
        self.item_index = 0
```

This will be used by client methods like `get_test_cases()` to provide a consistent interface:

```python
def get_test_cases(self, project_key: Optional[str] = None) -> PaginatedIterator[TestCase]:
    params = {}
    if project_key:
        params["projectKey"] = project_key
        
    return PaginatedIterator[TestCase](
        client=self,
        endpoint="/testcases",
        model_class=TestCase,
        params=params
    )
```

The caller can then use this iterator like any standard Python iterator:

```python
# Lazy iteration - fetches pages as needed
for test_case in client.get_test_cases():
    process_test_case(test_case)
    
# Convert to list - fetches all pages immediately
all_test_cases = list(client.get_test_cases())
```

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../../LICENSE)*