"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Package information utilities for ZTOQ project.
Provides access to version information and other package metadata.
"""

import re
import sys
from importlib import metadata
from pathlib import Path

# Constants
PACKAGE_NAME = "ztoq"
ROOT_DIR = Path(__file__).parent.parent.parent.absolute()
VERSION_PATH = ROOT_DIR / "ztoq" / "__init__.py"
PYPROJECT_PATH = ROOT_DIR / "pyproject.toml"


def get_version() -> str:
    """
    Get the package version from multiple possible sources.
    
    Returns:
        str: The package version

    """
    # First try to get it from the installed package
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        pass

    # Fall back to reading from __init__.py
    try:
        with open(VERSION_PATH) as f:
            content = f.read()
        version_match = re.search(r'__version__\s*=\s*["\']([\d\.]+)["\']', content)
        if version_match:
            return version_match.group(1)
    except Exception:
        pass

    # Fall back to pyproject.toml
    try:
        with open(PYPROJECT_PATH) as f:
            content = f.read()
        version_match = re.search(r'version\s*=\s*["\']([\d\.]+)["\']', content)
        if version_match:
            return version_match.group(1)
    except Exception:
        pass

    # If all else fails
    return "unknown"


def get_python_version() -> tuple[int, int, int]:
    """
    Get the current Python version.
    
    Returns:
        Tuple[int, int, int]: Major, minor, and patch version numbers

    """
    return (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)


def get_package_metadata() -> dict[str, str]:
    """
    Get package metadata from pyproject.toml.
    
    Returns:
        Dict[str, str]: Package metadata including name, version, description, etc.

    """
    metadata_dict = {
        "name": PACKAGE_NAME,
        "version": get_version(),
        "python_version": ".".join(map(str, get_python_version())),
    }

    # Try to get additional metadata from pyproject.toml
    try:
        with open(PYPROJECT_PATH) as f:
            content = f.read()

        # Extract description
        desc_match = re.search(r'description\s*=\s*["\'](.*?)["\']', content)
        if desc_match:
            metadata_dict["description"] = desc_match.group(1)

        # Extract authors
        authors_match = re.search(r"authors\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if authors_match:
            authors_str = authors_match.group(1)
            authors = re.findall(r'["\'](.*?)["\']', authors_str)
            metadata_dict["authors"] = ", ".join(authors)

    except Exception:
        pass

    return metadata_dict


def is_dev_environment() -> bool:
    """
    Check if currently running in a development environment.
    
    Returns:
        bool: True if in a development environment, False otherwise

    """
    # Check for presence of dev dependencies
    dev_indicators = ["pytest", "black", "flake8", "mypy"]
    for indicator in dev_indicators:
        try:
            metadata.version(indicator)
            return True
        except metadata.PackageNotFoundError:
            continue

    # Check for common dev environment indicators
    return any([
        # Is the package installed in development mode
        "site-packages" not in str(ROOT_DIR),
        # Are we running from the project directory
        Path.cwd().is_relative_to(ROOT_DIR),
    ])


def get_requirements() -> list[str]:
    """
    Get the package dependencies.
    
    Returns:
        List[str]: List of package dependencies

    """
    try:
        with open(PYPROJECT_PATH) as f:
            content = f.read()

        # Find the dependencies section
        deps_section = re.search(r"\[tool\.poetry\.dependencies\](.*?)(?=\[tool\.poetry\.group|$)",
                               content, re.DOTALL)
        if not deps_section:
            return []

        deps_content = deps_section.group(1)

        # Extract dependencies, excluding python requirement
        deps = []
        for line in deps_content.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("python"):
                # Extract package name by removing version constraint
                match = re.match(r"([a-zA-Z0-9_-]+)\s*=", line)
                if match:
                    deps.append(match.group(1))

        return deps
    except Exception:
        return []
