# Project Structure

ZTOQ follows a well-organized file and directory structure to maintain code quality, readability, and maintainability. The project adheres to standard Python package organization practices with some enhancements to support the specific needs of a complex ETL tool.

## Directory Structure

```
ztoq/                 # Root Project Directory
├── config/           # Configuration files
│   ├── Dockerfile               # Main container definition
│   ├── Dockerfile.migration-report # Report generator container definition
│   ├── docker-compose.yml       # Docker Compose main configuration
│   ├── docker-compose.dashboard.yml # Dashboard service configuration
│   ├── docker-compose.migration.yml # Migration services configuration
│   ├── Makefile                 # Project task automation
│   ├── alembic.ini              # Database migration configuration
│   ├── setup.cfg                # Python package configuration
│   └── sonar-project.properties # SonarCloud analysis configuration
│
├── docs/             # Documentation
│   ├── adr/          # Architecture Decision Records
│   ├── badges/       # Build status badges
│   ├── specs/        # API specifications
│   ├── sphinx/       # Sphinx documentation source
│   └── *.md          # Markdown documentation files
│
├── utils/            # Utility scripts
│   ├── build.py                 # Build automation script
│   ├── test_install.py          # Installation verification
│   ├── run-migration.sh         # Migration execution script
│   ├── test_docs.sh             # Documentation testing script
│   └── ztoq_data.db             # Sample database for testing
│
├── scripts/          # Development scripts
│   ├── add_license_headers.py   # License header management
│   ├── fix_imports.py           # Import style corrections
│   ├── fix_spacing.py           # Code formatting helper
│   ├── init_db.py               # Database initialization
│   └── master_build.py          # CI/CD build script
│
├── migration-config/ # Migration configuration
│   ├── settings.json            # Global migration settings
│   └── projects.txt             # Project list for batch migrations
│
├── ztoq/             # Main package code
│   ├── core/         # Core functionality
│   ├── domain/       # Domain models and business logic
│   ├── __init__.py   # Package initialization
│   ├── cli.py        # Command-line interface
│   └── *.py          # Feature-specific modules
│
├── tests/            # Test suite
│   ├── unit/         # Unit tests
│   ├── integration/  # Integration tests
│   ├── system/       # System/E2E tests
│   ├── fixtures/     # Test fixtures and factories
│   └── generated/    # Generated test files
│
└── examples/         # Usage examples
```

## Rationale for this Structure

### Why separate `config/`, `docs/`, and `utils/` directories?

1. **Separation of Concerns**:
   - Code that runs the application is separate from code that configures, documents, or supports it
   - Makes the repository easier to navigate for new developers
   - Improves the signal-to-noise ratio in the main code directories

2. **Reduced Clutter**:
   - Keeps the root directory clean and focused
   - Makes important files like README.md and LICENSE stand out
   - Prevents root directory from becoming a "junk drawer"

3. **Conventional Practice**:
   - Follows standard practices in open-source projects
   - Aligns with expectations of experienced developers
   - Makes the project more approachable to new contributors

4. **Improved Maintainability**:
   - Configuration files are grouped by function rather than file type
   - Documentation is centralized for easier updates
   - Utility scripts are organized by purpose

### Benefits for Different Users

- **New Developers**: Clear organization helps understand the project faster
- **Maintainers**: Related files are grouped together for easier updates
- **End Users**: Documentation is easy to find and navigate
- **DevOps Engineers**: Configuration files are centralized for deployment

## Open Source Best Practices

This structure follows common open source Python project conventions:

- Main code in a package with the project name (`ztoq/`)
- Documentation in a dedicated directory (`docs/`)
- Clear separation between code and configuration
- Tests isolated in their own directory (`tests/`)
- Examples that demonstrate usage

By following these conventions, the project becomes more approachable to new contributors and easier to maintain over time. It also aligns with typical packaging and distribution patterns for Python projects.

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../LICENSE)*
