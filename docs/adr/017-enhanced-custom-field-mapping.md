# ADR-017: Enhanced Custom Field Mapping for Migration

## Status

Accepted

## Context

The migration process between Zephyr Scale and qTest involves transforming various entity types with custom fields. These custom fields can have complex structures including hierarchical data, tables, matrices, and specialized formats. The initial implementation of the custom field mapper handled basic transformations but was insufficient for complex field types.

Challenges with the existing implementation:
- Table-structured data wasn't formatted in a user-friendly way
- Hierarchical data structures (common in Zephyr) weren't properly transformed
- Date formats varied and required normalization
- Status and priority mappings were limited
- Validation for field transformations was missing
- Complex field types like user references and multi-select fields needed better handling

## Decision

We will enhance the custom field mapping implementation with the following improvements:

1. **Improved table formatting**: Create a specialized transformation function for table-structured data that handles various formats (dictionaries, matrices) and produces formatted output with headers and proper alignment.

2. **Hierarchical field support**: Add a dedicated transformer for hierarchical data that extracts meaningful information from complex nested structures.

3. **Comprehensive status and priority mappings**: Expand the status and priority mappings to handle a wider range of values and case/formatting variations.

4. **Improved date handling**: Add support for various date formats with better parsing and fallback options.

5. **Enhanced validation**: Create a custom field transformation validation rule that verifies transformations maintain data integrity.

6. **User field handling**: Improve handling of user references to extract meaningful user information regardless of the structure.

7. **Extract and map utility**: Add a helper function to extract and map fields with automatic type conversion.

## Consequences

### Positive

- More accurate and complete data transformation during migration
- Improved readability of complex field data in qTest
- Better handling of special cases and variations in field formats
- Reduced data loss during transformations
- Improved validation ensuring data quality
- More robust status and priority mapping with fallbacks

### Negative

- Increased complexity in the custom field mapper
- More test cases needed to verify all transformation scenarios
- Potential performance impact when transforming large datasets with complex fields

### Neutral

- The basic structure of the field mapper remains unchanged, only adding specialized functions for complex types
- The approach remains compatible with the existing migration workflow

## Implementation Details

1. The enhanced custom field mapper will use dedicated transformation functions for different field types.
2. A robust test suite will be created to verify all transformations.
3. The field mapper will be integrated with the validation framework to ensure data integrity during transformations.
4. Default mapping tables will be expanded to handle a wider range of field values.
5. Documentation will be updated to reflect the enhanced capabilities of the field mapper.

## References

- [Entity Mapping Documentation](../entity-mapping.md)
- ADR-013: ETL Migration Workflow