# Testing Custom Fields and Attachments in ZTOQ

This document outlines the approach to testing custom fields and binary attachments in the ZTOQ (Zephyr to qTest) tool.

## Custom Fields in Zephyr Scale

Zephyr Scale supports various types of custom fields for test cases, test cycles, test plans, and test executions:

1. **Basic Types**:
   - Text - Single line text
   - Paragraph - Multi-line text
   - Checkbox - Boolean value
   - Radio - Single choice from options
   - Dropdown - Single choice from dropdown
   - Multiple Select - Multiple choices

2. **Advanced Types**:
   - Date - Date value
   - Datetime - Date and time value
   - Numeric - Number value
   - URL - Web link
   - Table - Tabular data
   - File - Attached file

3. **Enterprise-specific Types**:
   - Hierarchical Select
   - User Group
   - Label
   - Sprint
   - Version
   - Component

## Testing Approach for Custom Fields

Our testing approach covers:

1. **Type Validation**: Ensure each custom field type is properly validated, especially:
   - Checkbox fields must be boolean
   - Numeric fields must be numbers
   - Table fields must be arrays/lists
   - Multiple Select fields must be arrays/lists

2. **Entity Integration**: Verify custom fields for each entity type:
   - Test Case custom fields
   - Test Cycle custom fields
   - Test Plan custom fields
   - Test Execution custom fields

3. **Mock Data Generation**: Generate realistic custom fields for testing with:
   - Varied field types
   - Valid and invalid values
   - Different combinations of fields

4. **API Validation**: Check API validation of:
   - Required fields
   - Field type constraints
   - Value constraints

## Binary Attachments

Attachments can be associated with:

1. Test cases
2. Test steps (both in test cases and executions)
3. Test executions

Our attachment testing strategy ensures:

1. **File Types**: Support for various file types:
   - Text files (.txt, .log)
   - Images (.png, .jpg)
   - Documents (.pdf, .doc)
   - Binary data

2. **Entity Association**: Correct attachment to:
   - Test cases
   - Test steps
   - Test executions

3. **Upload and Download**: Complete lifecycle testing:
   - Uploading attachments
   - Retrieving attachment metadata
   - Downloading attachment content

4. **Binary Integrity**: Ensuring binary content is preserved:
   - Base64 encoding/decoding
   - Content type preservation
   - File size accuracy

## Test Generation

The `ZephyrTestGenerator` class automatically generates tests for:

1. **Custom Field Tests**:
   - Valid fields of each type
   - Invalid field values
   - Missing field types
   - Field associations with entities

2. **Attachment Tests**:
   - File upload tests for various file types
   - Attachment association tests
   - Binary content integrity tests
   - Error case testing

## Implementation Details

### Custom Field Handling

```python
# Creating a custom field for testing
field = {
    "id": "cf-numeric-1",
    "name": "Numeric Field",
    "type": "numeric",
    "value": 123.45
}

# Validating a custom field
def validate_custom_field(field, expected_type):
    assert field["type"] == expected_type
    
    # Type-specific validation
    if expected_type == "checkbox":
        assert isinstance(field["value"], bool)
    elif expected_type == "numeric":
        assert isinstance(field["value"], (int, float))
    elif expected_type == "table":
        assert isinstance(field["value"], list)
```

### Attachment Handling

```python
# Creating an attachment from binary data
def create_attachment(filename, content_type, binary_data):
    encoded = base64.b64encode(binary_data).decode('utf-8')
    return {
        "filename": filename,
        "contentType": content_type,
        "size": len(binary_data),
        "content": encoded
    }

# Uploading an attachment
def upload_attachment(client, entity_type, entity_id, file_path):
    return client.upload_attachment(
        entity_type=entity_type,
        entity_id=entity_id,
        file_path=file_path
    )
```

## Usage Examples

Running custom field and attachment tests:

```bash
# Generate and run custom field tests
python examples/custom_fields_test.py

# Run generated tests
poetry run pytest tests/generated/test_custom_fields.py
poetry run pytest tests/generated/test_attachments.py
```

## Key Test Scenarios

1. Test a custom field of each type on each entity type
2. Test invalid values for each custom field type
3. Test attachment uploads for each supported file type
4. Test binary content preservation throughout the API lifecycle
5. Test step-specific attachments in test cases and executions

These tests ensure that the ZTOQ tool correctly handles all custom field types and binary attachments for a comprehensive data extraction from Zephyr Scale and migration to qTest.

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../../LICENSE)*