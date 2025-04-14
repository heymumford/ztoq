"""
Test generation utilities for Zephyr Scale API testing.

This module provides tools for generating test cases based on OpenAPI specifications.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from pathlib import Path

from ztoq.openapi_parser import ZephyrApiSpecWrapper, load_openapi_spec

# Set up module logger
logger = logging.getLogger("ztoq.test_generator")


class ZephyrTestGenerator:
    """Generator for test cases based on the Zephyr Scale OpenAPI spec."""

    def __init__(self, spec_wrapper: ZephyrApiSpecWrapper):
        """Initialize the test generator.

        Args:
            spec_wrapper: An initialized ZephyrApiSpecWrapper
        """
        self.spec_wrapper = spec_wrapper
        logger.info("Initialized ZephyrTestGenerator")

    @classmethod
    def from_spec_path(cls, spec_path: Path) -> "ZephyrTestGenerator":
        """Create a test generator from an OpenAPI spec file.

        Args:
            spec_path: Path to the OpenAPI spec file

        Returns:
            Configured ZephyrTestGenerator
        """
        logger.info(f"Creating test generator from OpenAPI spec: {spec_path}")
        spec = load_openapi_spec(spec_path)
        spec_wrapper = ZephyrApiSpecWrapper(spec)
        return cls(spec_wrapper)

    def generate_endpoint_tests(self, path: str, method: str) -> List[Dict[str, Any]]:
        """Generate test cases for a specific endpoint.

        Args:
            path: The endpoint path
            method: The HTTP method

        Returns:
            List of test case definitions
        """
        logger.info(f"Generating tests for {method.upper()} {path}")
        tests = []

        # Get endpoint information
        endpoint_info = self.spec_wrapper.get_endpoint_info(path, method)
        if not endpoint_info:
            logger.warning(f"Endpoint not found: {method.upper()} {path}")
            return []

        # Generate happy path test
        tests.append(self._generate_happy_path_test(path, method))

        # Generate parameter tests
        parameter_tests = self._generate_parameter_tests(path, method)
        tests.extend(parameter_tests)

        # Generate response tests
        response_tests = self._generate_response_tests(path, method)
        tests.extend(response_tests)

        # Generate schema validation tests
        if method.lower() in ["post", "put", "patch"] and self.spec_wrapper.get_request_schema(
            path, method
        ):
            schema_tests = self._generate_schema_validation_tests(path, method)
            tests.extend(schema_tests)

        # Generate custom field tests
        if self._is_entity_endpoint(path):
            custom_field_tests = self._generate_custom_field_tests(path, method)
            tests.extend(custom_field_tests)

        # Generate attachment tests
        if self._supports_attachments(path):
            attachment_tests = self._generate_attachment_tests(path, method)
            tests.extend(attachment_tests)

        logger.info(f"Generated {len(tests)} tests for {method.upper()} {path}")
        return tests

    def _is_entity_endpoint(self, path: str) -> bool:
        """Check if this endpoint returns a Zephyr entity that could have custom fields.

        Args:
            path: The endpoint path

        Returns:
            True if endpoint likely returns a Zephyr entity
        """
        # These endpoints typically return entities with custom fields
        entity_patterns = [
            "/testcases",
            "/testexecutions",
            "/testcycles",
            "/testplans",
            "/testcase",
            "/testexecution",
            "/testcycle",
            "/testplan",
        ]

        # Check if path appears to be an entity endpoint
        return any(pattern in path.lower() for pattern in entity_patterns)

    def _supports_attachments(self, path: str) -> bool:
        """Check if this endpoint supports attachments.

        Args:
            path: The endpoint path

        Returns:
            True if endpoint likely supports attachments
        """
        # These endpoints typically support attachments
        attachment_patterns = [
            "/attachment",
            "/attachments",
            "/testcases/",
            "/testexecutions/",
            "/teststeps/",
        ]

        # Check if path appears to support attachments
        return any(pattern in path.lower() for pattern in attachment_patterns)

    def _generate_custom_field_tests(self, path: str, method: str) -> List[Dict[str, Any]]:
        """Generate tests for custom field handling.

        Args:
            path: The endpoint path
            method: The HTTP method

        Returns:
            List of custom field test definitions
        """
        tests = []
        endpoint_info = self.spec_wrapper.get_endpoint_info(path, method)
        operation_id = endpoint_info.get("operation_id", f"{method.lower()}_{path}")

        # Only generate custom field tests for POST/PUT endpoints
        if method.lower() not in ["post", "put", "patch"]:
            return tests

        request_schema = self.spec_wrapper.get_request_schema(path, method)
        if not request_schema:
            return tests

        # Check if schema has customFields property
        properties = request_schema.get("properties", {})
        if "customFields" not in properties:
            return tests

        # Create mock data as base
        base_data = self.spec_wrapper.generate_mock_data(request_schema)

        # Generate tests for each custom field type
        field_types = [
            "text",
            "paragraph",
            "checkbox",
            "radio",
            "dropdown",
            "multipleSelect",
            "date",
            "datetime",
            "numeric",
            "table",
        ]

        for field_type in field_types:
            # Create valid custom field test
            valid_cf = self._create_custom_field(field_type, valid=True)
            valid_test_data = base_data.copy()
            valid_test_data["customFields"] = [valid_cf]

            valid_test = {
                "name": f"test_{operation_id}_valid_{field_type}_customfield",
                "description": f"Test {method.upper()} {path} with valid {field_type} custom field",
                "path": path,
                "method": method,
                "request_data": valid_test_data,
                "expected_status": 200 if method.lower() == "get" else 201,
                "validate_schema": True,
            }
            tests.append(valid_test)

            # Create invalid custom field test (for types with validation)
            if field_type in ["checkbox", "numeric", "table", "multipleSelect"]:
                invalid_cf = self._create_custom_field(field_type, valid=False)
                invalid_test_data = base_data.copy()
                invalid_test_data["customFields"] = [invalid_cf]

                invalid_test = {
                    "name": f"test_{operation_id}_invalid_{field_type}_customfield",
                    "description": f"Test {method.upper()} {path} with invalid {field_type} custom field",
                    "path": path,
                    "method": method,
                    "request_data": invalid_test_data,
                    "expected_status": 400,
                    "validate_schema": False,
                }
                tests.append(invalid_test)

        # Test for missing custom field type
        missing_type_cf = {
            "id": "cf-missing-type",
            "name": "Missing Type Field",
            # missing "type" field
            "value": "Some value",
        }
        missing_type_data = base_data.copy()
        missing_type_data["customFields"] = [missing_type_cf]

        missing_type_test = {
            "name": f"test_{operation_id}_missing_customfield_type",
            "description": f"Test {method.upper()} {path} with missing custom field type",
            "path": path,
            "method": method,
            "request_data": missing_type_data,
            "expected_status": 400,
            "validate_schema": False,
        }
        tests.append(missing_type_test)

        return tests

    def _create_custom_field(self, field_type: str, valid: bool = True) -> Dict[str, Any]:
        """Create a custom field of the specified type.

        Args:
            field_type: The custom field type
            valid: Whether to create a valid (True) or invalid (False) field

        Returns:
            Custom field dictionary
        """
        field = {
            "id": f"cf-{field_type}-1",
            "name": f"{field_type.capitalize()} Field",
            "type": field_type,
        }

        # Set valid or invalid value based on type
        if field_type == "text" or field_type == "paragraph":
            field["value"] = "Sample text value" if valid else 12345
        elif field_type == "checkbox":
            field["value"] = True if valid else "not-a-boolean"
        elif field_type == "radio" or field_type == "dropdown":
            field["value"] = "Option A" if valid else 12345
        elif field_type == "multipleSelect":
            field["value"] = ["Option A", "Option B"] if valid else "not-a-list"
        elif field_type == "date":
            field["value"] = "2023-01-15" if valid else "invalid-date"
        elif field_type == "datetime":
            field["value"] = "2023-01-15T14:30:00Z" if valid else "invalid-datetime"
        elif field_type == "numeric":
            field["value"] = 123.45 if valid else "not-a-number"
        elif field_type == "table":
            field["value"] = [{"col1": "val1", "col2": "val2"}] if valid else "not-a-table"
        else:
            field["value"] = "Default value"

        return field

    def _generate_attachment_tests(self, path: str, method: str) -> List[Dict[str, Any]]:
        """Generate tests for attachment handling.

        Args:
            path: The endpoint path
            method: The HTTP method

        Returns:
            List of attachment test definitions
        """
        tests = []
        endpoint_info = self.spec_wrapper.get_endpoint_info(path, method)
        operation_id = endpoint_info.get("operation_id", f"{method.lower()}_{path}")

        # Only generate attachment tests for specific endpoints
        if not (
            ("/attachments" in path) or (method.lower() == "post" and path.endswith("/attachments"))
        ):
            return tests

        # Test uploading different file types
        file_types = [
            {"name": "text", "filename": "test.txt", "content_type": "text/plain"},
            {"name": "image", "filename": "test.png", "content_type": "image/png"},
            {"name": "pdf", "filename": "test.pdf", "content_type": "application/pdf"},
            {"name": "binary", "filename": "test.bin", "content_type": "application/octet-stream"},
        ]

        for file_type in file_types:
            attachment_test = {
                "name": f"test_{operation_id}_upload_{file_type['name']}_attachment",
                "description": f"Test {method.upper()} {path} with {file_type['name']} attachment",
                "path": path,
                "method": method,
                "file_upload": {
                    "filename": file_type["filename"],
                    "content_type": file_type["content_type"],
                    "content": base64.b64encode(
                        f"Mock {file_type['name']} content".encode("utf-8")
                    ).decode("utf-8"),
                },
                "expected_status": 201 if method.lower() == "post" else 200,
                "validate_schema": True,
            }
            tests.append(attachment_test)

        # Test uploading with invalid content type
        invalid_type_test = {
            "name": f"test_{operation_id}_invalid_content_type",
            "description": f"Test {method.upper()} {path} with invalid content type",
            "path": path,
            "method": method,
            "file_upload": {
                "filename": "test.txt",
                "content_type": "invalid/content-type",
                "content": base64.b64encode(b"Invalid content type test").decode("utf-8"),
            },
            "expected_status": 400,
            "validate_schema": False,
        }
        tests.append(invalid_type_test)

        # Test uploading empty file
        empty_file_test = {
            "name": f"test_{operation_id}_empty_file",
            "description": f"Test {method.upper()} {path} with empty file",
            "path": path,
            "method": method,
            "file_upload": {"filename": "empty.txt", "content_type": "text/plain", "content": ""},
            "expected_status": 400,
            "validate_schema": False,
        }
        tests.append(empty_file_test)

        # Test attachment on test step if it's a test step endpoint
        if "/teststeps/" in path or "/steps/" in path:
            step_attachment_test = {
                "name": f"test_{operation_id}_step_attachment",
                "description": f"Test {method.upper()} {path} with step attachment",
                "path": path,
                "method": method,
                "file_upload": {
                    "filename": "step_attachment.png",
                    "content_type": "image/png",
                    "content": base64.b64encode(b"Step attachment content").decode("utf-8"),
                    "step_id": "step-1",  # Assuming step ID is needed
                },
                "expected_status": 201 if method.lower() == "post" else 200,
                "validate_schema": True,
            }
            tests.append(step_attachment_test)

        return tests

    def _generate_happy_path_test(self, path: str, method: str) -> Dict[str, Any]:
        """Generate a happy path test for an endpoint.

        Args:
            path: The endpoint path
            method: The HTTP method

        Returns:
            Test case definition
        """
        endpoint_info = self.spec_wrapper.get_endpoint_info(path, method)
        operation_id = endpoint_info.get("operation_id", f"{method.lower()}_{path}")

        # Generate mock request data
        request_data = {}
        if method.lower() in ["post", "put", "patch"]:
            request_schema = self.spec_wrapper.get_request_schema(path, method)
            if request_schema:
                request_data = self.spec_wrapper.generate_mock_data(request_schema)

        # Generate mock parameters
        params = {}
        for param in endpoint_info.get("parameters", []):
            if param.get("required", False) and param.get("in") == "query":
                param_name = param.get("name")
                param_schema = param.get("schema", {})
                params[param_name] = self.spec_wrapper.generate_mock_data(param_schema)

        # Generate expected response
        expected_response = self.spec_wrapper.generate_mock_response(path, method)

        return {
            "name": f"test_{operation_id}_happy_path",
            "description": f"Test happy path for {method.upper()} {path}",
            "path": path,
            "method": method,
            "request_data": request_data,
            "params": params,
            "expected_status": 200,
            "validate_schema": True,
        }

    def _generate_parameter_tests(self, path: str, method: str) -> List[Dict[str, Any]]:
        """Generate tests for endpoint parameters.

        Args:
            path: The endpoint path
            method: The HTTP method

        Returns:
            List of parameter test definitions
        """
        tests = []
        endpoint_info = self.spec_wrapper.get_endpoint_info(path, method)
        operation_id = endpoint_info.get("operation_id", f"{method.lower()}_{path}")

        # Get required parameters
        required_params = [
            p
            for p in endpoint_info.get("parameters", [])
            if p.get("required", False) and p.get("in") == "query"
        ]

        # For each required parameter, generate a test without it
        for param in required_params:
            param_name = param.get("name")
            test = {
                "name": f"test_{operation_id}_missing_{param_name}",
                "description": f"Test {method.upper()} {path} with missing required parameter: {param_name}",
                "path": path,
                "method": method,
                "params": {},  # Will populate with all except the missing one
                "expected_status": 400,  # Assuming 400 for missing required param
                "validate_schema": False,
            }

            # Add all other required parameters
            for other_param in required_params:
                other_name = other_param.get("name")
                if other_name != param_name:
                    other_schema = other_param.get("schema", {})
                    test["params"][other_name] = self.spec_wrapper.generate_mock_data(other_schema)

            tests.append(test)

        # Generate tests for invalid parameter values
        for param in endpoint_info.get("parameters", []):
            param_name = param.get("name")
            param_schema = param.get("schema", {})
            param_type = param_schema.get("type")

            # Skip if no type information
            if not param_type:
                continue

            if param_type == "string" and "enum" in param_schema:
                # Test with invalid enum value
                test = {
                    "name": f"test_{operation_id}_invalid_{param_name}",
                    "description": f"Test {method.upper()} {path} with invalid enum value for {param_name}",
                    "path": path,
                    "method": method,
                    "params": {param_name: "INVALID_VALUE"},
                    "expected_status": 400,
                    "validate_schema": False,
                }
                tests.append(test)

            elif param_type in ["integer", "number"]:
                # Test with out-of-range values if min/max specified
                if "minimum" in param_schema:
                    min_val = param_schema["minimum"]
                    test = {
                        "name": f"test_{operation_id}_{param_name}_below_minimum",
                        "description": f"Test {method.upper()} {path} with {param_name} below minimum",
                        "path": path,
                        "method": method,
                        "params": {param_name: min_val - 1},
                        "expected_status": 400,
                        "validate_schema": False,
                    }
                    tests.append(test)

                if "maximum" in param_schema:
                    max_val = param_schema["maximum"]
                    test = {
                        "name": f"test_{operation_id}_{param_name}_above_maximum",
                        "description": f"Test {method.upper()} {path} with {param_name} above maximum",
                        "path": path,
                        "method": method,
                        "params": {param_name: max_val + 1},
                        "expected_status": 400,
                        "validate_schema": False,
                    }
                    tests.append(test)

        return tests

    def _generate_response_tests(self, path: str, method: str) -> List[Dict[str, Any]]:
        """Generate tests for different response codes.

        Args:
            path: The endpoint path
            method: The HTTP method

        Returns:
            List of response test definitions
        """
        tests = []
        endpoint_info = self.spec_wrapper.get_endpoint_info(path, method)
        operation_id = endpoint_info.get("operation_id", f"{method.lower()}_{path}")

        # Get all defined response codes
        responses = endpoint_info.get("responses", {})

        # Skip the 200 response as it's covered by the happy path test
        for status_code in responses:
            if status_code == "200":
                continue

            response = responses[status_code]
            test = {
                "name": f"test_{operation_id}_response_{status_code}",
                "description": f"Test {method.upper()} {path} with {status_code} response: {response.get('description', '')}",
                "path": path,
                "method": method,
                "expected_status": int(status_code),
                "validate_schema": True,
            }

            # Add specific test setup based on status code
            if status_code.startswith("4"):
                # For 4xx responses, set up invalid request
                if status_code == "401":
                    test["auth"] = False  # No auth
                elif status_code == "403":
                    test["auth"] = "invalid"  # Invalid auth
                elif status_code == "404":
                    test["path"] = f"{path}/nonexistent"  # Nonexistent resource

            tests.append(test)

        return tests

    def _generate_schema_validation_tests(self, path: str, method: str) -> List[Dict[str, Any]]:
        """Generate tests for request schema validation.

        Args:
            path: The endpoint path
            method: The HTTP method

        Returns:
            List of schema validation test definitions
        """
        tests = []
        endpoint_info = self.spec_wrapper.get_endpoint_info(path, method)
        operation_id = endpoint_info.get("operation_id", f"{method.lower()}_{path}")

        # Get request schema
        request_schema = self.spec_wrapper.get_request_schema(path, method)
        if not request_schema:
            return []

        # Generate valid request data as base
        valid_data = self.spec_wrapper.generate_mock_data(request_schema)

        # If it's an object type schema
        if request_schema.get("type") == "object":
            # Get required properties
            required = request_schema.get("required", [])
            properties = request_schema.get("properties", {})

            # For each required property, generate a test without it
            for prop in required:
                if prop in valid_data:
                    invalid_data = valid_data.copy()
                    del invalid_data[prop]

                    test = {
                        "name": f"test_{operation_id}_missing_{prop}",
                        "description": f"Test {method.upper()} {path} with missing required property: {prop}",
                        "path": path,
                        "method": method,
                        "request_data": invalid_data,
                        "expected_status": 400,
                        "validate_schema": False,
                    }
                    tests.append(test)

            # For each property, generate tests with invalid types
            for prop, prop_schema in properties.items():
                prop_type = prop_schema.get("type")
                if not prop_type:
                    continue

                invalid_data = valid_data.copy()

                # Set invalid type based on property type
                if prop_type == "string":
                    invalid_data[prop] = 123  # Number instead of string
                elif prop_type in ["integer", "number"]:
                    invalid_data[prop] = "not-a-number"  # String instead of number
                elif prop_type == "boolean":
                    invalid_data[prop] = "not-a-boolean"  # String instead of boolean
                elif prop_type == "array":
                    invalid_data[prop] = "not-an-array"  # String instead of array
                elif prop_type == "object":
                    invalid_data[prop] = "not-an-object"  # String instead of object

                test = {
                    "name": f"test_{operation_id}_invalid_{prop}_type",
                    "description": f"Test {method.upper()} {path} with invalid type for {prop}",
                    "path": path,
                    "method": method,
                    "request_data": invalid_data,
                    "expected_status": 400,
                    "validate_schema": False,
                }
                tests.append(test)

        return tests

    def generate_test_suite(self, tag: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Generate a complete test suite for all endpoints or filtered by tag.

        Args:
            tag: Optional tag to filter endpoints

        Returns:
            Dictionary mapping endpoint identifiers to test definitions
        """
        logger.info(f"Generating test suite" + (f" for tag: {tag}" if tag else ""))

        # Get endpoints to test
        endpoints = []
        if tag:
            endpoints = self.spec_wrapper.find_endpoints_by_tag(tag)
        else:
            endpoints = [(path, method) for (path, method) in self.spec_wrapper.endpoints.keys()]

        # Generate tests for each endpoint
        test_suite = {}
        for path, method in endpoints:
            endpoint_id = f"{method.upper()} {path}"
            tests = self.generate_endpoint_tests(path, method)
            test_suite[endpoint_id] = tests

        total_tests = sum(len(tests) for tests in test_suite.values())
        logger.info(f"Generated {total_tests} tests for {len(test_suite)} endpoints")

        return test_suite

    def export_test_suite_to_json(self, output_path: Path, tag: Optional[str] = None) -> None:
        """Generate and export a test suite to a JSON file.

        Args:
            output_path: Path to save the test suite
            tag: Optional tag to filter endpoints
        """
        test_suite = self.generate_test_suite(tag)

        with open(output_path, "w") as f:
            json.dump(test_suite, f, indent=2)

        logger.info(f"Exported test suite to {output_path}")

    def generate_test_function(self, test: Dict[str, Any]) -> str:
        """Generate a pytest function for a test case.

        Args:
            test: Test case definition

        Returns:
            Python code for the test function
        """
        name = test["name"]
        path = test["path"]
        method = test["method"]
        description = test.get("description", "")

        lines = [f"def {name}(zephyr_client):"]
        lines.append(f'    """')
        lines.append(f"    {description}")
        lines.append(f'    """')

        # Set up request parameters
        if "params" in test and test["params"]:
            params_str = json.dumps(test["params"], indent=4).replace("\n", "\n    ")
            lines.append(f"    params = {params_str}")
        else:
            lines.append(f"    params = {{}}")

        # Set up request data if needed
        if "request_data" in test and test["request_data"]:
            data_str = json.dumps(test["request_data"], indent=4).replace("\n", "\n    ")
            lines.append(f"    data = {data_str}")

        # Set up file upload if needed
        if "file_upload" in test:
            file_upload = test["file_upload"]
            lines.append(f"    # Prepare file upload")
            lines.append(f"    filename = '{file_upload['filename']}'")
            lines.append(f"    content_type = '{file_upload['content_type']}'")

            # For base64 content, decode it to binary
            if "content" in file_upload:
                lines.append(f"    # Base64 encoded content")
                lines.append(f"    import base64")
                lines.append(f"    content = base64.b64decode('{file_upload['content']}')")

            # Set up multipart files dict
            lines.append(f"    files = {{'file': (filename, content, content_type)}}")

            # Add step_id if provided (for test step attachments)
            if "step_id" in file_upload:
                lines.append(f"    # This is a test step attachment")
                lines.append(f"    params['stepId'] = '{file_upload['step_id']}'")

        # Handle authentication setup
        if "auth" in test:
            if test["auth"] == False:
                lines.append(f"    # Test without authentication")
                lines.append(f"    saved_token = zephyr_client.headers['Authorization']")
                lines.append(f"    zephyr_client.headers['Authorization'] = ''")
            elif test["auth"] == "invalid":
                lines.append(f"    # Test with invalid authentication")
                lines.append(f"    saved_token = zephyr_client.headers['Authorization']")
                lines.append(f"    zephyr_client.headers['Authorization'] = 'Bearer invalid_token'")

        # Set up the expected status code
        expected_status = test.get("expected_status", 200)

        # Add expectations based on status code
        if expected_status < 400:
            # Success case
            lines.append(f"    try:")
            lines.append(f"        # Make API request")
            lines.append(f"        response = zephyr_client._make_request(")
            lines.append(f"            '{method.upper()}',")
            lines.append(f"            '{path}',")
            lines.append(f"            params=params,")

            # Add appropriate parameters based on what's in the test
            if "request_data" in test and test["request_data"]:
                lines.append(f"            json_data=data,")
            if "file_upload" in test:
                lines.append(f"            files=files,")
                # For file uploads, use multipart header
                lines.append(
                    f"            headers={{'Authorization': zephyr_client.headers['Authorization']}},"
                )

            lines.append(f"            validate={test.get('validate_schema', True)}")
            lines.append(f"        )")
            lines.append(f"        # Check response")
            lines.append(f"        assert response is not None")

            # Add response validation for specific test types
            if "file_upload" in test:
                lines.append(f"        # Validate attachment response")
                lines.append(f"        assert 'id' in response")
                lines.append(f"        assert 'filename' in response")
                lines.append(f"        assert response['filename'] == filename")

            # Add custom field validation if relevant
            if "request_data" in test and "customFields" in test["request_data"]:
                lines.append(f"        # Validate custom fields in response if present")
                lines.append(f"        if 'customFields' in response:")
                lines.append(f"            assert len(response['customFields']) > 0")

            lines.append(f"    except Exception as e:")
            lines.append(
                f"        pytest.fail(f'Expected successful response but got error: {{e}}')"
            )
        else:
            # Error case
            lines.append(f"    with pytest.raises(requests.exceptions.HTTPError) as excinfo:")
            lines.append(f"        # Make API request expecting {expected_status} error")
            lines.append(f"        zephyr_client._make_request(")
            lines.append(f"            '{method.upper()}',")
            lines.append(f"            '{path}',")
            lines.append(f"            params=params,")

            # Add appropriate parameters based on what's in the test
            if "request_data" in test and test["request_data"]:
                lines.append(f"            json_data=data,")
            if "file_upload" in test:
                lines.append(f"            files=files,")
                # For file uploads, use multipart header
                lines.append(
                    f"            headers={{'Authorization': zephyr_client.headers['Authorization']}},"
                )

            lines.append(f"            validate={test.get('validate_schema', False)}")
            lines.append(f"        )")
            lines.append(f"    # Verify expected status code")
            lines.append(f"    assert excinfo.value.response.status_code == {expected_status}")

        # Restore auth if needed
        if "auth" in test:
            lines.append(f"    # Restore authentication")
            lines.append(f"    zephyr_client.headers['Authorization'] = saved_token")

        return "\n".join(lines)

    def generate_pytest_file(self, output_path: Path, tag: Optional[str] = None) -> None:
        """Generate a pytest file with test functions.

        Args:
            output_path: Path to save the pytest file
            tag: Optional tag to filter endpoints
        """
        logger.info(f"Generating pytest file for" + (f" tag: {tag}" if tag else " all endpoints"))

        test_suite = self.generate_test_suite(tag)

        # Start with imports and fixtures
        lines = [
            "import pytest",
            "import requests",
            "from pathlib import Path",
            "from typing import Dict, Any, List",
            "",
            "from ztoq.models import ZephyrConfig",
            "from ztoq.zephyr_client import ZephyrClient",
            "",
            "",
            "@pytest.fixture",
            "def zephyr_client():",
            '    """Create a Zephyr client for testing."""',
            "    config = ZephyrConfig(",
            "        base_url='https://api.zephyrscale.smartbear.com/v2',",
            "        api_token='test-token',",
            "        project_key='TEST'",
            "    )",
            "    client = ZephyrClient.from_openapi_spec(",
            "        Path('docs/specs/z-openapi.yml'),",
            "        config,",
            "        log_level='DEBUG'",
            "    )",
            "    return client",
            "",
        ]

        # Add test functions
        for endpoint_id, tests in test_suite.items():
            lines.append(f"# Tests for {endpoint_id}")
            for test in tests:
                lines.append(self.generate_test_function(test))
                lines.append("")  # Empty line between functions

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        logger.info(f"Generated pytest file at {output_path}")
