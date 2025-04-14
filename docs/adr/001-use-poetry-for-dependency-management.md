# ADR-001: Use Poetry for Dependency Management

## Status

Accepted

## Context

We need a reliable and modern dependency management and packaging solution for the ZTOQ project. There are several options available in the Python ecosystem, including:

- pip with requirements.txt
- pipenv
- Poetry
- conda

We need a solution that provides:
- Reliable dependency resolution
- Lockfile support for reproducible builds
- Virtual environment management
- Easy publishing to PyPI (if needed)
- Development vs. production dependencies separation
- Easy integration with CI/CD pipelines

## Decision

We will use Poetry for dependency management and packaging for the ZTOQ project.

## Consequences

### Positive

- Poetry provides deterministic builds with its lock file (poetry.lock)
- Clear separation between development and production dependencies
- Single pyproject.toml file for both project metadata and dependencies
- Built-in virtual environment management
- Modern dependency resolver that handles conflicts well
- Support for defining project scripts
- Native support for publishing to PyPI
- Growing community adoption and support

### Negative

- Poetry has a steeper learning curve than pip + requirements.txt
- Some CI environments may require additional setup to use Poetry
- Poetry is still evolving, so occasional breaking changes in future versions might occur

## Implementation Details

We'll use a pyproject.toml file at the root of the project with this structure:

```toml
[tool.poetry]
name = "ztoq"
version = "0.1.0"
description = "Zephyr to qTest migration tool"
authors = ["Your Name <your.email@example.com>"]
readme = "README.md"
packages = [{include = "ztoq"}]

[tool.poetry.dependencies]
python = "^3.9"
pyyaml = "^6.0"
pydantic = "^2.0"
requests = "^2.30.0"
typer = "^0.9.0"
rich = "^13.5.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
pytest-cov = "^4.1"
black = "^23.0"
flake8 = "^6.0"
mypy = "^1.5"

[tool.poetry.scripts]
ztoq = "ztoq.cli:app"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

---
*Copyright (c) 2025 Eric C. Mumford (@heymumford) - Licensed under [MIT License](../../LICENSE)*