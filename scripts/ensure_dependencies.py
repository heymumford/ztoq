#!/usr/bin/env python3
"""
Ensure all dependencies are properly installed.

This script verifies that all required dependencies are installed correctly
and properly accessible by the Python interpreter. It's designed to be run
during the build process to catch dependency issues early.
"""

import importlib
import subprocess
import sys
from pathlib import Path


def print_status(message: str, status: str = "INFO", indent: int = 0) -> None:
    """Print a status message with appropriate coloring."""
    colors = {
        "INFO": "\033[94m",  # Blue
        "SUCCESS": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
    }
    reset = "\033[0m"
    indent_str = " " * indent
    print(f"{indent_str}{colors.get(status, '')}{message}{reset}")


def check_import(module_name: str) -> bool:
    """Check if a module can be imported."""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def check_critical_imports() -> list[str]:
    """Check critical imports and return a list of missing modules."""
    critical_modules = [
        "psutil",
        "sqlalchemy",
        "pydantic",
        "typer",
        "pytest",
        "alembic",
        "pandas",
        "numpy",
        "requests",
        "fastapi",
        "ruff",
        "mypy",
    ]

    missing = []
    for module in critical_modules:
        if not check_import(module):
            missing.append(module)

    return missing


def get_module_version(module_name: str) -> str | None:
    """Get the version of an installed module."""
    try:
        module = importlib.import_module(module_name)
        if hasattr(module, "__version__"):
            return module.__version__
        if hasattr(module, "version"):
            return module.version
        # Try using pip to get the version
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", module_name],
            text=True,
            capture_output=True,
            check=False,
        )
        for line in result.stdout.splitlines():
            if line.startswith("Version: "):
                return line.replace("Version: ", "").strip()
        return None
    except (ImportError, subprocess.SubprocessError):
        return None


def check_all_dependencies() -> tuple[dict[str, str], list[str]]:
    """Check all dependencies in pyproject.toml and return versions and missing modules."""
    project_root = Path(__file__).parent.parent
    pyproject_path = project_root / "pyproject.toml"

    # Parse pyproject.toml to extract dependencies
    dependencies = []
    in_deps_section = False

    try:
        with open(pyproject_path) as f:
            for line in f:
                line = line.strip()
                if line == "[tool.poetry.dependencies]":
                    in_deps_section = True
                    continue
                if line.startswith("[") and line.endswith("]"):
                    in_deps_section = False
                    continue

                if in_deps_section and "=" in line and not line.startswith("#"):
                    package_name = line.split("=")[0].strip()
                    if package_name == "python":
                        continue
                    dependencies.append(package_name)
    except Exception as e:
        print_status(f"Error parsing pyproject.toml: {e}", "ERROR")
        return {}, []

    # Check each dependency
    versions = {}
    missing = []

    for package in dependencies:
        # Convert package name to import name (e.g., psycopg2-binary -> psycopg2)
        import_name = package.replace("-binary", "").replace("-", "_")

        version = get_module_version(import_name)
        if version:
            versions[package] = version
        else:
            missing.append(package)

    return versions, missing


def main() -> int:
    """Check if all critical dependencies are properly installed."""
    print_status("Checking critical dependencies...", "INFO")
    missing_critical = check_critical_imports()

    # Define maximum allowed missing dependencies
    MAX_ALLOWED_MISSING = 5

    if missing_critical:
        print_status("Missing critical dependencies:", "ERROR")
        for module in missing_critical:
            print_status(f"- {module}", "ERROR", indent=2)
        print_status("\nPlease install missing dependencies and try again:", "INFO")
        print_status("poetry install", "INFO", indent=2)
        sys.exit(1)
    else:
        print_status("All critical dependencies are available.", "SUCCESS")

    print_status("\nChecking all dependencies from pyproject.toml...", "INFO")
    versions, missing = check_all_dependencies()

    if versions:
        print_status("Installed dependencies:", "SUCCESS")
        for package, version in versions.items():
            print_status(f"- {package}: {version}", "SUCCESS", indent=2)

    if missing:
        print_status("\nMissing dependencies:", "WARNING")
        for package in missing:
            print_status(f"- {package}", "WARNING", indent=2)
        print_status(
            "\nSome dependencies might be optional or have different import names.",
            "INFO",
        )
        print_status("Consider installing missing dependencies if needed:", "INFO")
        print_status("poetry add <package-name>", "INFO", indent=2)

    if not missing or len(missing) < MAX_ALLOWED_MISSING:  # Allow some missing dependencies
        print_status("\nDependency check completed successfully!", "SUCCESS")
        return 0
    print_status("\nToo many missing dependencies. Please fix the issues and try again.", "ERROR")
    return 1


if __name__ == "__main__":
    sys.exit(main())
