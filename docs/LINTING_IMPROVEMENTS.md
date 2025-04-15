# Linting Improvements Plan

## Progress Report

We've made significant improvements to the project's linting configuration and code quality:

1. **Consolidated linting tools**: Removed redundant linters and standardized on ruff as the primary linting tool
   - Removed: black, flake8, isort, pydocstyle, docformatter, pylint
   - Updated pre-commit hooks to use ruff for both linting and formatting

2. **Updated ruff configuration**:
   - Added more rule sets (PL, RUF, INP, PIE, COM, etc.)
   - Improved per-file ignores for test files and examples
   - Added format configuration for consistent code style

3. **Fixed thousands of issues automatically**:
   - Fixed 7481+ issues with `ruff --fix`
   - Created proper `__init__.py` files for alembic namespace packages
   - Fixed unused variables and imports
   - Improved code formatting and style consistency

4. **Created utility scripts**:
   - `scripts/remove_unused_imports.py`: Tool to locate and fix unused imports
   - `scripts/fix_logging.py`: Tool to fix logging f-string issues

## Remaining Issues

The most common issues remaining in the codebase are:

1. **Logging Format Issues (G004)**: 865 instances of logging with f-strings
2. **Pytest Assertion Style (PT009)**: 450 instances of unittest-style assertions in pytest
3. **Type Annotation Issues**: 510+ instances of missing type annotations
4. **Code Complexity (C901)**: 88 functions that are too complex
5. **Namespace Package Issues (INP001)**: 46 implicit namespace packages without `__init__.py`

## Improvement Plan

### Short-term Actions

1. **Fix logging format issues**:
   - Improve `scripts/fix_logging.py` to handle more patterns
   - Gradually update logging calls to use proper string interpolation

2. **Fix remaining unused imports and variables**:
   - Run `ruff --fix --select=F401,F841` on targeted directories
   - Review and manually fix remaining issues

3. **Add missing `__init__.py` files**:
   - Identify and create missing init files in all packages

### Medium-term Actions

1. **Improve pytest assertions**:
   - Gradually convert unittest-style assertions to pytest style
   - Focus on test files updated for new features first

2. **Add type annotations to public APIs**:
   - Prioritize `ztoq/core/` and other key modules
   - Start with return type annotations for public functions

### Long-term Actions

1. **Address code complexity**:
   - Refactor complex functions into smaller, more focused functions
   - Add better documentation for complex functions

2. **Fix miscellaneous security and style issues**:
   - Handle subprocess security issues (S603)
   - Improve random number generation (S311)
   - Fix string concatenation in logging (G003)

## Usage Instructions

### Running Ruff Checks

```bash
# Run basic checks
python -m ruff check .

# Fix auto-fixable issues
python -m ruff check --fix .

# Fix specific category of issues
python -m ruff check --fix --select=F,E,W .

# Run with unsafe fixes (use with caution)
python -m ruff check --fix --unsafe-fixes .
```

### Running the Utility Scripts

```bash
# Find unused imports
python scripts/remove_unused_imports.py ztoq

# Fix logging format issues
python scripts/fix_logging.py ztoq
```

## Benefits

Consolidating on ruff as our primary linting tool provides several benefits:

1. **Faster linting**: Ruff is significantly faster than the combination of separate tools
2. **Consistent rules**: Single source of truth for coding standards
3. **Automatic fixing**: More issues can be fixed automatically
4. **Comprehensive analysis**: Covers style, security, performance, and maintainability
5. **Lower maintenance**: Easier to update and maintain one tool than many

The improvements made will help make the codebase more consistent, maintainable, and easier to understand for new contributors.