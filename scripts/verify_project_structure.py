#!/usr/bin/env python3
"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Project structure verification script.

This script checks that the project follows the defined structure and
ensures version consistency across files. It can be used as a pre-commit
hook or in CI/CD pipelines.
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path to allow importing from ztoq
script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

try:
    from ztoq.utils import dependency_manager, package_info, version_utils
except ImportError:
    print("Error: Could not import utility modules. Please ensure you're running from the project root.")
    sys.exit(1)


def check_project_structure():
    """Check that the project structure follows the conventions."""
    required_dirs = [
        "ztoq",
        "ztoq/core",
        "ztoq/domain",
        "ztoq/utils",
        "tests",
        "tests/unit",
        "tests/integration",
        "tests/system",
        "docs",
        "scripts",
    ]

    required_files = [
        "ztoq/__init__.py",
        "ztoq/core/__init__.py",
        "ztoq/domain/__init__.py",
        "ztoq/utils/__init__.py",
        "pyproject.toml",
        "README.md",
    ]

    missing_dirs = []
    missing_files = []

    # Check required directories
    for directory in required_dirs:
        path = project_root / directory
        if not path.exists() or not path.is_dir():
            missing_dirs.append(directory)

    # Check required files
    for file in required_files:
        path = project_root / file
        if not path.exists() or not path.is_file():
            missing_files.append(file)

    return missing_dirs, missing_files


def check_version_consistency():
    """Check version consistency across files."""
    inconsistent_files = version_utils.check_version_consistency()
    return inconsistent_files


def check_dependency_imports():
    """Check that all dependencies are properly imported."""
    required_deps, missing_deps = dependency_manager.check_all_project_dependencies()
    return required_deps, missing_deps


def main():
    parser = argparse.ArgumentParser(
        description="Verify project structure and dependencies.",
    )
    parser.add_argument(
        "--fix", action="store_true", help="Fix version inconsistencies automatically",
    )
    args = parser.parse_args()

    errors = 0
    warnings = 0

    # Check project structure
    print("Checking project structure...")
    missing_dirs, missing_files = check_project_structure()
    if missing_dirs:
        errors += 1
        print("Error: Missing directories:")
        for directory in missing_dirs:
            print(f"  - {directory}")
    if missing_files:
        errors += 1
        print("Error: Missing files:")
        for file in missing_files:
            print(f"  - {file}")
    if not missing_dirs and not missing_files:
        print("✅ Project structure is correct.")

    # Check version consistency
    print("\nChecking version consistency...")
    inconsistent_files = check_version_consistency()
    if inconsistent_files:
        warnings += 1
        print("Warning: Version inconsistencies found in these files:")
        for file in inconsistent_files:
            print(f"  - {file}")

        if args.fix:
            print("Fixing version inconsistencies...")
            current_version = package_info.get_version()
            version_utils.update_version(current_version)
            print(f"Updated all files to version {current_version}")
    else:
        print("✅ Version numbers are consistent.")

    # Check dependencies
    print("\nChecking project dependencies...")
    all_installed, missing_deps = dependency_manager.check_all_project_dependencies()
    if not all_installed:
        warnings += 1
        print("Warning: Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\nRun 'poetry install' to install missing dependencies.")
    else:
        print("✅ All required dependencies are installed.")

    # Print summary
    print("\nVerification complete:")
    print(f"  - {errors} errors")
    print(f"  - {warnings} warnings")

    # Exit with error code if there are errors
    if errors > 0:
        sys.exit(1)
    elif warnings > 0 and not args.fix:
        print("Run with --fix to automatically fix issues.")
        sys.exit(1)
    else:
        print("Project structure verification passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
