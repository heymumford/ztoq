"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Dependency management utilities for ZTOQ project.
Provides functions to check for required dependencies and optional dependencies.
"""

import importlib.util
import re
from pathlib import Path

from .package_info import get_requirements


def is_dependency_installed(package_name: str) -> bool:
    """
    Check if a dependency is installed.
    
    Args:
        package_name: Name of the package to check
        
    Returns:
        bool: True if the package is installed, False otherwise

    """
    return importlib.util.find_spec(package_name) is not None


def check_dependencies(required_deps: list[str]) -> tuple[bool, list[str]]:
    """
    Check if all required dependencies are installed.
    
    Args:
        required_deps: List of required dependencies
        
    Returns:
        Tuple[bool, List[str]]: Tuple of (all_installed, missing_deps)

    """
    missing_deps = []

    for dep in required_deps:
        if not is_dependency_installed(dep):
            missing_deps.append(dep)

    return len(missing_deps) == 0, missing_deps


def check_all_project_dependencies() -> tuple[bool, list[str]]:
    """
    Check if all project dependencies defined in pyproject.toml are installed.
    
    Returns:
        Tuple[bool, List[str]]: Tuple of (all_installed, missing_deps)

    """
    required_deps = get_requirements()
    return check_dependencies(required_deps)


def get_optional_dependencies() -> dict[str, list[str]]:
    """
    Get optional dependency groups from pyproject.toml.
    
    Returns:
        Dict[str, List[str]]: Dictionary mapping group names to lists of package names

    """
    optional_deps = {}

    try:
        # Get the path to pyproject.toml
        root_dir = Path(__file__).parent.parent.parent.absolute()
        pyproject_path = root_dir / "pyproject.toml"

        with open(pyproject_path) as f:
            content = f.read()

        # Find all optional dependency groups
        # Example: [tool.poetry.group.dev.dependencies]
        group_pattern = r"\[tool\.poetry\.group\.([a-zA-Z0-9_-]+)\.dependencies\](.*?)(?=\[|\Z)"

        for match in re.finditer(group_pattern, content, re.DOTALL):
            group_name = match.group(1)
            deps_content = match.group(2)

            # Parse dependencies in this group
            deps = []
            for line in deps_content.strip().split("\n"):
                line = line.strip()
                if line:
                    # Extract package name
                    pkg_match = re.match(r"([a-zA-Z0-9_-]+)\s*=", line)
                    if pkg_match:
                        deps.append(pkg_match.group(1))

            if deps:
                optional_deps[group_name] = deps

    except Exception as e:
        print(f"Error parsing optional dependencies: {e}")

    return optional_deps


def check_optional_dependency_group(group_name: str) -> tuple[bool, set[str]]:
    """
    Check if all dependencies in an optional group are installed.
    
    Args:
        group_name: Name of the optional dependency group
        
    Returns:
        Tuple[bool, Set[str]]: Tuple of (all_installed, missing_deps)

    """
    optional_groups = get_optional_dependencies()

    if group_name not in optional_groups:
        return False, set([f"Group '{group_name}' not found"])

    missing = set()
    for dep in optional_groups[group_name]:
        if not is_dependency_installed(dep):
            missing.add(dep)

    return len(missing) == 0, missing
