# ADR 020: Linting Strategy

## Status

Accepted (2025-04-15)

## Context

As the ZTOQ codebase grows, maintaining code quality and consistency becomes increasingly important. We were using multiple linting and formatting tools:

- black (code formatting)
- flake8 (linting)
- isort (import sorting)
- pydocstyle (docstring checking)
- docformatter (docstring formatting)
- pylint (comprehensive linting)
- mypy (type checking)

This led to several issues:
1. Running multiple tools was slow, especially in CI/CD pipelines
2. Configuration was spread across multiple files (.flake8, .isort.cfg, pyproject.toml)
3. Tools sometimes had conflicting rules
4. Developers needed to learn and run multiple tools

## Decision

We've decided to:

1. Consolidate on ruff as our primary linting and formatting tool
2. Update our pre-commit hooks to use ruff for both linting and formatting
3. Keep mypy for dedicated type checking as it offers more comprehensive type analysis
4. Create a comprehensive ruff configuration in pyproject.toml

The ruff configuration will include:
- Rules from all previously used tools (flake8, pylint, isort, etc.)
- Formatting rules compatible with Black's style
- Per-file ignores for different types of files (tests, examples, scripts)
- Documentation of rule selections and why certain rules are ignored

## Consequences

### Positive

- Faster linting (up to 100x faster than running multiple tools)
- Single source of truth for linting and formatting rules
- More auto-fixable issues with `--fix` option
- Better developer experience with a single tool
- Simplified CI/CD pipelines
- Improved code quality with more comprehensive checking

### Negative

- Migration effort to adjust to new combined tool
- May lose some specialized features of individual tools
- Need to train developers on the new tool and configuration

## Alternatives Considered

1. **Continue with multiple tools**: This would avoid migration costs but would not address speed, consistency, and usability issues.

2. **Use Black + Flake8 + isort**: This is a common combination but still requires managing multiple tools and configurations.

3. **Switch to a different language server (e.g., Pylance)**: While this would help IDE integration, it wouldn't solve the CI/CD and command-line tooling issues.

## Implementation Notes

1. We've created the following utility scripts to assist with the transition:
   - `scripts/remove_unused_imports.py`: Detects and suggests fixes for unused imports
   - `scripts/fix_logging.py`: Converts f-string logging to proper string interpolation

2. We've updated the pre-commit config to remove redundant tools and use ruff instead.

3. The ruff configuration in pyproject.toml includes:
   - Comprehensive rule selection covering all aspects of code quality
   - Per-file ignores for tests, examples, and scripts
   - Formatting rules compatible with Black

4. A prioritized plan for addressing remaining issues has been documented in `docs/LINTING_IMPROVEMENTS.md`.

## References

- [Ruff documentation](https://beta.ruff.rs/docs/)
- [Migration guides from other linters](https://beta.ruff.rs/docs/migration/)
- [Python code quality best practices](https://realpython.com/python-code-quality/)