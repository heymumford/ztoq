"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

"""
Version utilities for ZTOQ project.
Provides functions to manage and sync version numbers across the project.
"""

import os
import re

from .package_info import PYPROJECT_PATH, VERSION_PATH, get_version


def update_version(new_version: str, dry_run: bool = False) -> dict[str, bool]:
    """
    Update the version number in all relevant files.
    
    Args:
        new_version: New version string (e.g., "0.4.1")
        dry_run: If True, only check which files would be updated without modifying them
        
    Returns:
        Dict[str, bool]: Dictionary mapping file paths to whether they were updated

    """
    files_to_update = {
        str(VERSION_PATH): False,
        str(PYPROJECT_PATH): False,
    }

    # Update __init__.py
    if os.path.exists(VERSION_PATH):
        content = VERSION_PATH.read_text()
        updated_content = re.sub(
            r'__version__\s*=\s*["\']([^"\']*)["\']',
            f'__version__ = "{new_version}"',
            content,
        )

        if content != updated_content:
            if not dry_run:
                VERSION_PATH.write_text(updated_content)
            files_to_update[str(VERSION_PATH)] = True

    # Update pyproject.toml
    if os.path.exists(PYPROJECT_PATH):
        content = PYPROJECT_PATH.read_text()
        updated_content = re.sub(
            r'version\s*=\s*["\']([^"\']*)["\']',
            f'version = "{new_version}"',
            content,
        )

        if content != updated_content:
            if not dry_run:
                PYPROJECT_PATH.write_text(updated_content)
            files_to_update[str(PYPROJECT_PATH)] = True

    return files_to_update


def bump_version(version_part: str = "patch", dry_run: bool = False) -> tuple[str, dict[str, bool]]:
    """
    Bump the version number following semver conventions.
    
    Args:
        version_part: Which part of the version to bump ("major", "minor", or "patch")
        dry_run: If True, only check which files would be updated without modifying them
        
    Returns:
        Tuple[str, Dict[str, bool]]: New version string and dictionary of updated files

    """
    current_version = get_version()

    # Parse version
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", current_version)
    if not match:
        raise ValueError(f"Current version {current_version} does not follow semver format")

    major, minor, patch, suffix = match.groups()

    # Bump the appropriate part
    if version_part == "major":
        new_version = f"{int(major) + 1}.0.0{suffix}"
    elif version_part == "minor":
        new_version = f"{major}.{int(minor) + 1}.0{suffix}"
    elif version_part == "patch":
        new_version = f"{major}.{minor}.{int(patch) + 1}{suffix}"
    else:
        raise ValueError(f"Invalid version part: {version_part}. Must be major, minor, or patch")

    # Update files
    updated_files = update_version(new_version, dry_run)

    return new_version, updated_files


def get_version_parts() -> dict[str, str]:
    """
    Get the individual parts of the current version.
    
    Returns:
        Dict[str, str]: Dictionary with major, minor, patch, and suffix parts

    """
    current_version = get_version()

    # Parse version
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", current_version)
    if not match:
        raise ValueError(f"Current version {current_version} does not follow semver format")

    major, minor, patch, suffix = match.groups()

    return {
        "major": major,
        "minor": minor,
        "patch": patch,
        "suffix": suffix,
        "full": current_version,
    }


def check_version_consistency() -> list[str]:
    """
    Check if version numbers are consistent across the project.
    
    Returns:
        List[str]: List of files with inconsistent versions

    """
    inconsistent_files = []
    main_version = get_version()

    # Check __init__.py
    if os.path.exists(VERSION_PATH):
        content = VERSION_PATH.read_text()
        version_match = re.search(r'__version__\s*=\s*["\']([^"\']*)["\']', content)
        if version_match and version_match.group(1) != main_version:
            inconsistent_files.append(str(VERSION_PATH))

    # Check pyproject.toml
    if os.path.exists(PYPROJECT_PATH):
        content = PYPROJECT_PATH.read_text()
        version_match = re.search(r'version\s*=\s*["\']([^"\']*)["\']', content)
        if version_match and version_match.group(1) != main_version:
            inconsistent_files.append(str(PYPROJECT_PATH))

    return inconsistent_files
