# Documentation Contribution Guide

This guide outlines the standards and best practices for contributing to the ZTOQ project documentation.

## Documentation Structure

All documentation is organized in the `docs/` directory with the following structure:

```
docs/
├── adr/                 # Architecture Decision Records
├── specs/               # API specifications
├── sphinx/              # Sphinx documentation
│   ├── source/          # Source files for Sphinx
│   └── build/           # Generated documentation
├── *.md                 # Core documentation files
└── upload/              # Reference materials
```

## Naming Conventions

1. **Use kebab-case for all documentation files**: All documentation files should use kebab-case (lowercase with hyphens). For example:
   - `openapi-integration.md` ✓
   - `custom-fields-attachments.md` ✓
   - `OPENAPI_INTEGRATION.md` ✗
   - `CustomFieldsAttachments.md` ✗

2. **ADR naming**: Architecture Decision Records should follow the pattern `NNN-title-in-kebab-case.md` where NNN is a sequential number.

3. **Sphinx RST files**: RST files should match the kebab-case pattern of their corresponding markdown files.

## Documentation Standards

1. **Headers**: Use ATX-style headers (with `#` symbols)
   - Use one `#` for the main title
   - Use `##` for section headings
   - Use `###` for subsections
   - Use `####` for sub-subsections

2. **Code examples**: Use fenced code blocks with language identifiers
   ```python
   def example_function():
       return "This is example code"
   ```

3. **Lists**: Use `-` for unordered lists and `1.` for ordered lists

4. **Links**: Use reference-style links for external resources and inline links for internal documentation

5. **Images**: Store images in `docs/images/` and use relative paths to reference them

## Documentation Types

1. **Architectural Documentation**: System design, data flows, and component interactions
2. **API Documentation**: API usage, endpoints, and schemas
3. **User Guides**: End-user instructions for using the application
4. **Developer Guides**: Information for developers extending or modifying the application
5. **ADRs**: Records of significant architectural decisions

## Documentation Integration

Our documentation is integrated with Sphinx to generate a comprehensive documentation website:

1. Markdown files are included in RST files using the `myst_parser` extension
2. API documentation is auto-generated from docstrings
3. C4 diagrams provide visual representations of the architecture

## Contribution Process

1. Write documentation following these guidelines
2. Test documentation generation with `make docs` or `python build.py docs`
3. Review the generated documentation to ensure proper formatting
4. Submit changes through the standard pull request process

## Documentation Testing

Before submitting documentation changes:

1. Run `make docs` to build the documentation
2. Run `make docs-serve` to preview the documentation locally
3. Check for broken links, formatting issues, and content accuracy

## Tips for Effective Documentation

1. Write clear, concise explanations
2. Provide examples where appropriate
3. Consider the audience (users, developers, administrators)
4. Update documentation when the corresponding code changes
5. Cross-reference related documentation sections

## Documentation Maintenance

As the project evolves:

1. Regularly review documentation for accuracy
2. Archive outdated documentation (don't delete it)
3. Mark experimental features as such
4. Note version compatibility where relevant

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../../LICENSE)*