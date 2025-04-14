"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import yaml
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging
import random
import string
import base64
from datetime import datetime, date

# Set up module logger
logger = logging.getLogger("ztoq.openapi_parser")

def load_openapi_spec(spec_path: Path) -> Dict[str, Any]:
    """Load and parse an OpenAPI specification file.

    Args:
        spec_path: Path to the OpenAPI YAML file

    Returns:
        Parsed OpenAPI specification as dictionary
    """
    logger.info(f"Loading OpenAPI spec from {spec_path}")

    if not spec_path.exists():
        logger.error(f"OpenAPI spec file not found: {spec_path}")
        raise FileNotFoundError(f"OpenAPI spec file not found at {spec_path}")

    try:
        with open(spec_path, "r") as f:
            spec = yaml.safe_load(f)

        # Validate the spec
        if validate_zephyr_spec(spec):
            logger.info("Successfully loaded and validated Zephyr Scale OpenAPI spec")
        else:
            logger.warning("Loaded OpenAPI spec but it may not be for Zephyr Scale API")

        # Log some basic info about the spec
        logger.debug(f"OpenAPI version: {spec.get('openapi', 'unknown')}")
        info = spec.get("info", {})
        logger.debug(f"API title: {info.get('title', 'unknown')}")
        logger.debug(f"API version: {info.get('version', 'unknown')}")

        # Log endpoint count
        paths = spec.get("paths", {})
        endpoint_count = sum(1 for _ in paths.items())
        logger.debug(f"Found {endpoint_count} endpoints in spec")

        return spec

    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML file: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading OpenAPI spec: {e}")
        raise

def validate_zephyr_spec(spec: Dict[str, Any]) -> bool:
    """Validate that the OpenAPI spec is for Zephyr Scale API.

    Args:
        spec: Parsed OpenAPI specification

    Returns:
        True if valid, False otherwise
    """
    # Check if it's an OpenAPI spec
    if "openapi" not in spec:
        logger.warning("Not a valid OpenAPI spec (missing 'openapi' field)")
        return False

    # Check if it's for Zephyr Scale
    info = spec.get("info", {})
    title = info.get("title", "").lower()
    description = info.get("description", "").lower()

    is_zephyr = "zephyr" in title or "zephyr" in description

    if not is_zephyr:
        logger.warning(f"Spec may not be for Zephyr Scale API. Title: '{info.get('title', '')}'")

    return is_zephyr

def extract_api_endpoints(spec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extract API endpoints from the OpenAPI spec.

    Args:
        spec: Parsed OpenAPI specification

    Returns:
        Dictionary of endpoints with their details
    """
    logger.info("Extracting API endpoints from OpenAPI spec")

    endpoints = {}
    paths = spec.get("paths", {})

    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ["get", "post", "put", "delete"]:
                endpoint_id = f"{method.upper()} {path}"
                endpoints[endpoint_id] = {
                    "path": path,
                    "method": method,
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "parameters": details.get("parameters", []),
                    "responses": details.get("responses", {}),
                }
                logger.debug(f"Found endpoint: {endpoint_id} - {details.get('summary', '')}")

    logger.info(f"Extracted {len(endpoints)} endpoints from OpenAPI spec")
    return endpoints

class ZephyrApiSpecWrapper:
    """A wrapper class for the Zephyr Scale OpenAPI specification.

    This class provides utilities for working with the OpenAPI spec, including:
    - Endpoint validation and discovery
    - Request/response schema validation
    - Parameter validation
    - Mock data generation for testing
    """

    def __init__(self, spec: Dict[str, Any]):
        """Initialize the spec wrapper.

        Args:
            spec: Parsed OpenAPI specification
        """
        self.spec = spec
        self.endpoints = self._extract_endpoints()
        self.schemas = spec.get("components", {}).get("schemas", {})

        logger.info(f"Initialized ZephyrApiSpecWrapper with {len(self.endpoints)} endpoints")

    def _extract_endpoints(self) -> Dict[str, Dict[str, Any]]:
        """Extract detailed endpoint information from the spec.

        Returns:
            Dictionary mapping endpoint paths to their details
        """
        endpoints = {}
        paths = self.spec.get("paths", {})

        for path, path_info in paths.items():
            for method, method_info in path_info.items():
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    key = (path, method.lower())
                    endpoints[key] = {
                        "path": path,
                        "method": method.lower(),
                        "operation_id": method_info.get("operationId"),
                        "summary": method_info.get("summary", ""),
                        "description": method_info.get("description", ""),
                        "parameters": method_info.get("parameters", []),
                        "request_body": method_info.get("requestBody", {}),
                        "responses": method_info.get("responses", {}),
                        "tags": method_info.get("tags", []),
                        "security": method_info.get("security", []),
                    }

        return endpoints

    def get_endpoint_info(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific endpoint.

        Args:
            path: The endpoint path
            method: The HTTP method

        Returns:
            Endpoint details or None if not found
        """
        key = (path, method.lower())
        return self.endpoints.get(key)

    def find_endpoints_by_tag(self, tag: str) -> List[Tuple[str, str]]:
        """Find all endpoints with a specific tag.

        Args:
            tag: The tag to search for

        Returns:
            List of (path, method) tuples for matching endpoints
        """
        matches = []
        for (path, method), info in self.endpoints.items():
            if tag in info.get("tags", []):
                matches.append((path, method))
        return matches

    def find_endpoints_by_operation_id(self, operation_id: str) -> Optional[Tuple[str, str]]:
        """Find an endpoint by its operationId.

        Args:
            operation_id: The operationId to search for

        Returns:
            Tuple of (path, method) or None if not found
        """
        for (path, method), info in self.endpoints.items():
            if info.get("operation_id") == operation_id:
                return (path, method)
        return None

    def find_endpoints_by_pattern(self, pattern: str) -> List[Tuple[str, str]]:
        """Find endpoints with paths matching a pattern.

        Args:
            pattern: Regular expression pattern for paths

        Returns:
            List of (path, method) tuples for matching endpoints
        """
        matches = []
        regex = re.compile(pattern)
        for (path, method), _ in self.endpoints.items():
            if regex.search(path):
                matches.append((path, method))
        return matches

    def get_request_schema(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """Get the request body schema for an endpoint.

        Args:
            path: The endpoint path
            method: The HTTP method

        Returns:
            JSON Schema for the request body or None
        """
        endpoint_info = self.get_endpoint_info(path, method)
        if not endpoint_info:
            return None

        request_body = endpoint_info.get("request_body", {})
        content = request_body.get("content", {})

        for content_type, content_schema in content.items():
            if content_type.lower() == "application/json":
                return content_schema.get("schema", {})

        return None

    def get_response_schema(
        self, path: str, method: str, status_code: str = "200"
    ) -> Optional[Dict[str, Any]]:
        """Get the response schema for an endpoint.

        Args:
            path: The endpoint path
            method: The HTTP method
            status_code: The HTTP status code as a string

        Returns:
            JSON Schema for the response or None
        """
        endpoint_info = self.get_endpoint_info(path, method)
        if not endpoint_info:
            return None

        responses = endpoint_info.get("responses", {})
        response = responses.get(status_code, {})
        content = response.get("content", {})

        for content_type, content_schema in content.items():
            if content_type.lower() == "application/json":
                return content_schema.get("schema", {})

        return None

    def validate_request(
        self, path: str, method: str, data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate a request body against the schema.

        Args:
            path: The endpoint path
            method: The HTTP method
            data: The request body data

        Returns:
            Tuple of (valid, error_message)
        """
        schema = self.get_request_schema(path, method)
        if not schema:
            logger.warning(f"No request schema found for {method.upper()} {path}")
            return True, None

        try:
            # Resolve schema references
            schema = self._resolve_schema_refs(schema)
            jsonschema.validate(data, schema)
            return True, None
        except jsonschema.exceptions.ValidationError as e:
            error_message = f"Request validation error: {e.message}"
            logger.error(error_message)
            return False, error_message

    def validate_response(
        self, path: str, method: str, status_code: str, data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate a response against the schema.

        Args:
            path: The endpoint path
            method: The HTTP method
            status_code: The HTTP status code as a string
            data: The response data

        Returns:
            Tuple of (valid, error_message)
        """
        schema = self.get_response_schema(path, method, status_code)
        if not schema:
            logger.warning(
                f"No response schema found for {method.upper()} {path} (status {status_code})"
            )
            return True, None

        try:
            # Resolve schema references
            schema = self._resolve_schema_refs(schema)
            jsonschema.validate(data, schema)
            return True, None
        except jsonschema.exceptions.ValidationError as e:
            error_message = f"Response validation error: {e.message}"
            logger.error(error_message)
            return False, error_message

    def _resolve_schema_refs(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively resolve $ref references in a schema.

        This is a simplified implementation that only handles basic references.
        A more complete implementation would handle nested and circular references.

        Args:
            schema: The schema with references

        Returns:
            Schema with resolved references
        """
        if not isinstance(schema, dict):
            return schema

        result = {}
        for key, value in schema.items():
            if (
                key == "$ref"
                and isinstance(value, str)
                and value.startswith("#/components/schemas/")
            ):
                # Get the referenced schema
                schema_name = value.split("/")[-1]
                referenced_schema = self.schemas.get(schema_name, {})
                # Recursively resolve references in the referenced schema
                return self._resolve_schema_refs(referenced_schema)
            elif isinstance(value, dict):
                result[key] = self._resolve_schema_refs(value)
            elif isinstance(value, list):
                result[key] = [
                    self._resolve_schema_refs(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value

        return result

    def generate_mock_data(self, schema: Dict[str, Any]) -> Any:
        """Generate mock data based on a schema.

        Args:
            schema: JSON Schema definition

        Returns:
            Mock data matching the schema
        """
        # Handle basic types
        schema_type = schema.get("type")

        if schema_type == "object":
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            result = {}

            for prop_name, prop_schema in properties.items():
                # Always include required properties, randomly include optional ones
                if prop_name in required or random.random() > 0.3:
                    result[prop_name] = self.generate_mock_data(prop_schema)

            # Special handling for Zephyr API specific fields
            # If this looks like a Zephyr object (has key, name, id properties)
            is_zephyr_object = "key" in properties and "name" in properties and "id" in properties

            # Special handling for custom fields
            if is_zephyr_object and "customFields" in properties and "customFields" not in result:
                result["customFields"] = self._generate_mock_custom_fields()

            # Special handling for attachments
            if is_zephyr_object and "attachments" in properties and "attachments" not in result:
                result["attachments"] = self._generate_mock_attachments()

            # Special handling for steps (test cases and executions)
            if is_zephyr_object and "steps" in properties and "steps" not in result:
                result["steps"] = self._generate_mock_steps()

            return result

        elif schema_type == "array":
            items_schema = schema.get("items", {})
            # Generate 1-5 items
            count = random.randint(1, 5)
            return [self.generate_mock_data(items_schema) for _ in range(count)]

        elif schema_type == "string":
            if schema.get("format") == "date-time":
                return datetime.now().isoformat()
            elif schema.get("format") == "date":
                return date.today().isoformat()
            elif schema.get("format") == "email":
                return f"user{random.randint(1, 1000)}@example.com"
            elif schema.get("format") == "uri":
                return f"https://example.com/{random.randint(1, 1000)}"
            elif "enum" in schema:
                return random.choice(schema["enum"])
            elif schema.get("contentEncoding") == "base64":
                # Generate mock base64 content for binary data
                return base64.b64encode(f"Mock binary data for {schema}".encode("utf-8")).decode(
                    "utf-8"
                )
            else:
                # Generate random string based on pattern or length
                pattern = schema.get("pattern")
                if pattern:
                    # For simplicity, just return a basic string for patterns
                    return f"pattern-{random.randint(1, 1000)}"
                else:
                    min_length = schema.get("minLength", 5)
                    max_length = schema.get("maxLength", 20)
                    length = random.randint(min_length, max(min_length, min(max_length, 20)))
                    return "".join(random.choices(string.ascii_letters, k=length))

        elif schema_type == "number" or schema_type == "integer":
            min_val = schema.get("minimum", 0)
            max_val = schema.get("maximum", 1000)
            if schema_type == "integer":
                return random.randint(min_val, max_val)
            else:
                return round(random.uniform(min_val, max_val), 2)

        elif schema_type == "boolean":
            return random.choice([True, False])

        elif schema_type == "null":
            return None

        # Handle case where $ref is directly in the schema
        if "$ref" in schema:
            ref_schema = self._resolve_schema_refs(schema)
            return self.generate_mock_data(ref_schema)

        # Handle oneOf, anyOf, allOf
        if "oneOf" in schema:
            chosen_schema = random.choice(schema["oneOf"])
            return self.generate_mock_data(chosen_schema)

        if "anyOf" in schema:
            chosen_schema = random.choice(schema["anyOf"])
            return self.generate_mock_data(chosen_schema)

        if "allOf" in schema:
            # Combine all schemas (simplified implementation)
            combined = {}
            for sub_schema in schema["allOf"]:
                resolved = self._resolve_schema_refs(sub_schema)
                if isinstance(resolved, dict):
                    combined.update(resolved)
            return self.generate_mock_data(combined)

        # Default case
        logger.warning(f"Cannot generate mock data for schema: {schema}")
        return "mock_data"

    def _generate_mock_custom_fields(self) -> List[Dict[str, Any]]:
        """Generate a list of mock custom fields with different types.

        Returns:
            List of custom field dictionaries
        """
        # Create a variety of custom field types based on the CustomFieldType enum
        custom_fields = [
            # Text field
            {"id": "cf-text-1", "name": "Text Field", "type": "text", "value": "Sample text value"},
            # Paragraph field
            {
                "id": "cf-paragraph-1",
                "name": "Paragraph Field",
                "type": "paragraph",
                "value": "This is a longer paragraph value that spans multiple lines\nand contains more detailed information.",
            },
            # Checkbox field
            {"id": "cf-checkbox-1", "name": "Checkbox Field", "type": "checkbox", "value": True},
            # Dropdown field
            {
                "id": "cf-dropdown-1",
                "name": "Dropdown Field",
                "type": "dropdown",
                "value": "Option 2",
            },
            # Numeric field
            {"id": "cf-numeric-1", "name": "Numeric Field", "type": "numeric", "value": 123.45},
            # Multiple select
            {
                "id": "cf-multiselect-1",
                "name": "Multi-Select Field",
                "type": "multipleSelect",
                "value": ["Option A", "Option C"],
            },
            # Table field
            {
                "id": "cf-table-1",
                "name": "Table Field",
                "type": "table",
                "value": [
                    {"Column 1": "Row 1 Value 1", "Column 2": "Row 1 Value 2"},
                    {"Column 1": "Row 2 Value 1", "Column 2": "Row 2 Value 2"},
                ],
            },
            # File field (with base64 encoded content)
            {
                "id": "cf-file-1",
                "name": "File Field",
                "type": "file",
                "value": {
                    "id": "att-1",
                    "filename": "test_file.txt",
                    "contentType": "text/plain",
                    "size": 1024,
                    "content": base64.b64encode(b"Mock file content").decode("utf-8"),
                },
            },
        ]

        # Randomly select 3-5 custom fields
        num_fields = min(5, len(custom_fields))
        return random.sample(custom_fields, random.randint(2, num_fields))

    def _generate_mock_attachments(self) -> List[Dict[str, Any]]:
        """Generate a list of mock attachments.

        Returns:
            List of attachment dictionaries
        """
        attachment_types = [
            # Text file
            {
                "id": "att-text-1",
                "filename": "document.txt",
                "contentType": "text/plain",
                "size": 2048,
                "createdOn": datetime.now().isoformat(),
                "createdBy": "tester1",
                "content": base64.b64encode(b"Sample text file content").decode("utf-8"),
            },
            # Image file
            {
                "id": "att-img-1",
                "filename": "screenshot.png",
                "contentType": "image/png",
                "size": 24576,
                "createdOn": datetime.now().isoformat(),
                "createdBy": "tester2",
                "content": base64.b64encode(b"Mock image binary data").decode("utf-8"),
            },
            # PDF file
            {
                "id": "att-pdf-1",
                "filename": "report.pdf",
                "contentType": "application/pdf",
                "size": 102400,
                "createdOn": datetime.now().isoformat(),
                "createdBy": "tester1",
                "content": base64.b64encode(b"Mock PDF binary data").decode("utf-8"),
            },
            # CSV file
            {
                "id": "att-csv-1",
                "filename": "data.csv",
                "contentType": "text/csv",
                "size": 5120,
                "createdOn": datetime.now().isoformat(),
                "createdBy": "tester3",
                "content": base64.b64encode(b"id,name,value\n1,test1,100\n2,test2,200").decode(
                    "utf-8"
                ),
            },
        ]

        # Randomly select 1-3 attachments
        num_attachments = min(3, len(attachment_types))
        return random.sample(attachment_types, random.randint(1, num_attachments))

    def _generate_mock_steps(self) -> List[Dict[str, Any]]:
        """Generate a list of mock test steps with attachments.

        Returns:
            List of test step dictionaries
        """
        steps = []

        # Generate between 2 and 5 steps
        for i in range(random.randint(2, 5)):
            # Randomly decide if this step has attachments
            has_attachments = random.random() > 0.5

            step = {
                "id": f"step-{i+1}",
                "index": i,
                "description": f"Test step {i+1}: Perform action {random.choice(['A', 'B', 'C'])}",
                "expectedResult": f"Expected result for step {i+1}",
                "data": f"Test data for step {i+1}",
                "status": random.choice(["PASS", "FAIL", "BLOCKED", "NOT_EXECUTED", None]),
            }

            # Add actual result for executed steps
            if step["status"] in ["PASS", "FAIL", "BLOCKED"]:
                step["actualResult"] = f"Actual result for step {i+1}"

            # Add attachments for some steps
            if has_attachments:
                step["attachments"] = self._generate_mock_attachments()

            steps.append(step)

        return steps

    def generate_mock_request(self, path: str, method: str) -> Dict[str, Any]:
        """Generate a mock request body for an endpoint.

        Args:
            path: The endpoint path
            method: The HTTP method

        Returns:
            Mock request data
        """
        schema = self.get_request_schema(path, method)
        if not schema:
            return {}

        return self.generate_mock_data(schema)

    def generate_mock_response(
        self, path: str, method: str, status_code: str = "200"
    ) -> Dict[str, Any]:
        """Generate a mock response for an endpoint.

        Args:
            path: The endpoint path
            method: The HTTP method
            status_code: The HTTP status code as a string

        Returns:
            Mock response data
        """
        schema = self.get_response_schema(path, method, status_code)
        if not schema:
            return {}

        return self.generate_mock_data(schema)

    def get_parameters(self, path: str, method: str) -> Dict[str, Dict[str, Any]]:
        """Get parameter definitions for an endpoint.

        Args:
            path: The endpoint path
            method: The HTTP method

        Returns:
            Dictionary of parameters keyed by name
        """
        endpoint_info = self.get_endpoint_info(path, method)
        if not endpoint_info:
            return {}

        parameters = {}
        for param in endpoint_info.get("parameters", []):
            param_name = param.get("name")
            if param_name:
                parameters[param_name] = param

        return parameters

    def validate_parameters(
        self,
        path: str,
        method: str,
        query_params: Dict[str, Any],
        path_params: Dict[str, Any] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate request parameters against the schema.

        Args:
            path: The endpoint path
            method: The HTTP method
            query_params: The query parameters
            path_params: The path parameters

        Returns:
            Tuple of (valid, error_message)
        """
        path_params = path_params or {}
        endpoint_info = self.get_endpoint_info(path, method)
        if not endpoint_info:
            return True, None

        parameter_defs = endpoint_info.get("parameters", [])

        # Check for missing required parameters
        for param_def in parameter_defs:
            param_name = param_def.get("name")
            param_in = param_def.get("in")  # 'query', 'path', 'header', 'cookie'
            required = param_def.get("required", False)

            if required:
                if param_in == "query" and param_name not in query_params:
                    return False, f"Missing required query parameter: {param_name}"
                elif param_in == "path" and param_name not in path_params:
                    return False, f"Missing required path parameter: {param_name}"

        # Validate parameter values
        for param_def in parameter_defs:
            param_name = param_def.get("name")
            param_in = param_def.get("in")
            param_schema = param_def.get("schema", {})

            # Check query parameters
            if param_in == "query" and param_name in query_params:
                value = query_params[param_name]
                try:
                    jsonschema.validate(
                        {"value": value}, {"type": "object", "properties": {"value": param_schema}}
                    )
                except jsonschema.exceptions.ValidationError as e:
                    return False, f"Invalid query parameter '{param_name}': {e.message}"

            # Check path parameters
            elif param_in == "path" and param_name in path_params:
                value = path_params[param_name]
                try:
                    jsonschema.validate(
                        {"value": value}, {"type": "object", "properties": {"value": param_schema}}
                    )
                except jsonschema.exceptions.ValidationError as e:
                    return False, f"Invalid path parameter '{param_name}': {e.message}"

        return True, None

    def generate_pydantic_model_string(self, schema_name: str) -> str:
        """Generate a Pydantic model string from a schema definition.

        Args:
            schema_name: The name of the schema in the components/schemas section

        Returns:
            String representation of a Pydantic model class
        """
        schema = self.schemas.get(schema_name)
        if not schema:
            return f"# Schema '{schema_name}' not found"

        output = [
            f"class {schema_name}(BaseModel):",
            f'    """Generated model for {schema_name}."""',
            "",
        ]

        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for prop_name, prop_schema in properties.items():
            prop_type = self._get_python_type(prop_schema)
            optional = prop_name not in required

            # Add field definition
            if optional:
                output.append(f"    {prop_name}: Optional[{prop_type}] = None")
            else:
                output.append(f"    {prop_name}: {prop_type}")

        # Add config class if needed
        if output[-1] != "":
            output.append("")
        output.append('    model_config = {"populate_by_name": True}')

        return "\n".join(output)

    def _get_python_type(self, schema: Dict[str, Any]) -> str:
        """Convert a JSON Schema type to a Python type annotation.

        Args:
            schema: JSON Schema definition

        Returns:
            Python type annotation as string
        """
        if "$ref" in schema:
            # Extract the model name from the reference
            ref = schema["$ref"]
            if ref.startswith("#/components/schemas/"):
                return ref.split("/")[-1]
            return "Any"  # Default for unknown references

        schema_type = schema.get("type")

        if schema_type == "object":
            return "Dict[str, Any]"

        elif schema_type == "array":
            items_schema = schema.get("items", {})
            items_type = self._get_python_type(items_schema)
            return f"List[{items_type}]"

        elif schema_type == "string":
            if schema.get("format") == "date-time":
                return "datetime"
            elif schema.get("format") == "date":
                return "date"
            return "str"

        elif schema_type == "integer":
            return "int"

        elif schema_type == "number":
            return "float"

        elif schema_type == "boolean":
            return "bool"

        elif schema_type == "null":
            return "None"

        # Handle oneOf, anyOf, allOf
        if "oneOf" in schema or "anyOf" in schema:
            return "Any"  # Use Any for union types for simplicity

        return "Any"  # Default catchall

    def get_method_signature(self, path: str, method: str) -> str:
        """Generate a Python method signature for an endpoint.

        Args:
            path: The endpoint path
            method: The HTTP method

        Returns:
            Method signature as string
        """
        endpoint_info = self.get_endpoint_info(path, method)
        if not endpoint_info:
            return f"def {method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}() -> Dict[str, Any]:"

        # Get operation ID or generate a method name
        operation_id = endpoint_info.get("operation_id")
        if not operation_id:
            operation_id = (
                f"{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
            )

        # Start building the method signature
        params = []

        # Add parameters
        for param_def in endpoint_info.get("parameters", []):
            param_name = param_def.get("name", "").replace("-", "_")
            param_in = param_def.get("in")
            required = param_def.get("required", False)
            schema = param_def.get("schema", {})
            python_type = self._get_python_type(schema)

            if required:
                params.append(f"{param_name}: {python_type}")
            else:
                default = "None"
                params.append(f"{param_name}: Optional[{python_type}] = {default}")

        # Add request body if needed
        request_schema = self.get_request_schema(path, method)
        if request_schema:
            params.append("body: Dict[str, Any]")

        # Build the full signature
        signature = f"def {operation_id}({', '.join(params)}) -> Dict[str, Any]:"

        return signature
