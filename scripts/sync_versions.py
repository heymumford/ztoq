#!/usr/bin/env python3
"""
Utility script to synchronize version numbers across different files in the ZTOQ project.
This ensures that all version references (pyproject.toml, __init__.py, Sphinx conf.py) are consistent.
"""

import re
import sys
from pathlib import Path
from typing import Dict, Optional, List

# Constants
ROOT_DIR = Path(__file__).parent.parent.absolute()
VERSION_PATH = ROOT_DIR / "ztoq" / "__init__.py"
PYPROJECT_PATH = ROOT_DIR / "pyproject.toml"
SPHINX_CONF_PATH = ROOT_DIR / "docs" / "sphinx" / "source" / "conf.py"

def get_version_from_pyproject() -> Optional[str]:
    """Get version from pyproject.toml."""
    if not PYPROJECT_PATH.exists():
        return None
    
    with open(PYPROJECT_PATH, "r") as f:
        content = f.read()
        version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            return version_match.group(1)
    return None

def get_version_from_init() -> Optional[str]:
    """Get version from __init__.py."""
    if not VERSION_PATH.exists():
        return None
    
    with open(VERSION_PATH, "r") as f:
        content = f.read()
        version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            return version_match.group(1)
    return None

def get_version_from_sphinx() -> Optional[str]:
    """Get version from Sphinx conf.py."""
    if not SPHINX_CONF_PATH.exists():
        return None
    
    with open(SPHINX_CONF_PATH, "r") as f:
        content = f.read()
        version_match = re.search(r'release\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            return version_match.group(1)
    return None

def update_version_in_file(file_path: Path, pattern: str, replacement: str, version: str) -> bool:
    """Update version in a file with the given pattern and replacement template."""
    if not file_path.exists():
        print(f"Warning: {file_path} not found")
        return False
    
    with open(file_path, "r") as f:
        content = f.read()
    
    # Replace version using the provided pattern and replacement
    new_content = re.sub(pattern, replacement.format(version=version), content)
    
    if new_content != content:
        with open(file_path, "w") as f:
            f.write(new_content)
        print(f"Updated version in {file_path} to {version}")
        return True
    else:
        print(f"Version in {file_path} already set to {version}")
        return True

def synchronize_versions() -> bool:
    """Synchronize versions across all relevant files."""
    versions = {
        "pyproject": get_version_from_pyproject(),
        "init": get_version_from_init(),
        "sphinx": get_version_from_sphinx()
    }
    
    # Find the most common version
    version_counts: Dict[str, int] = {}
    for source, version in versions.items():
        if version:
            version_counts[version] = version_counts.get(version, 0) + 1
    
    if not version_counts:
        print("Error: No version found in any source file")
        return False
    
    # Use the most common version, or the pyproject version as the canonical one
    canonical_version = versions["pyproject"]
    if not canonical_version:
        # Find the most common version if pyproject version is not available
        canonical_version = max(version_counts.items(), key=lambda x: x[1])[0]
    
    print(f"Using {canonical_version} as the canonical version")
    
    # Update versions in all files
    success = True
    
    # Update __init__.py
    if versions["init"] != canonical_version:
        success = success and update_version_in_file(
            VERSION_PATH,
            r'__version__\s*=\s*["\']([^"\']+)["\']',
            r'__version__ = "{version}"',
            canonical_version
        )
    
    # Update pyproject.toml
    if versions["pyproject"] != canonical_version:
        success = success and update_version_in_file(
            PYPROJECT_PATH,
            r'version\s*=\s*["\']([^"\']+)["\']',
            r'version = "{version}"',
            canonical_version
        )
    
    # Update Sphinx conf.py
    if versions["sphinx"] != canonical_version:
        success = success and update_version_in_file(
            SPHINX_CONF_PATH,
            r'release\s*=\s*["\']([^"\']+)["\']',
            r'release = "{version}"',
            canonical_version
        )
    
    return success

def print_versions() -> None:
    """Print all version information for different files."""
    print("ZTOQ Version Information:")
    print(f"  pyproject.toml: {get_version_from_pyproject() or 'Not found'}")
    print(f"  __init__.py:    {get_version_from_init() or 'Not found'}")
    print(f"  Sphinx conf.py: {get_version_from_sphinx() or 'Not found'}")

def main() -> int:
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ZTOQ Version Synchronization Script")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check version consistency without making changes"
    )
    args = parser.parse_args()
    
    if args.check:
        print_versions()
        # Check if all versions are consistent
        versions = [
            v for v in [
                get_version_from_pyproject(),
                get_version_from_init(),
                get_version_from_sphinx()
            ] if v is not None
        ]
        
        if not versions:
            print("Error: No version found in any source file")
            return 1
        
        if len(set(versions)) == 1:
            print("\nAll versions are consistent!")
            return 0
        else:
            print("\nWarning: Versions are inconsistent across files")
            return 1
    else:
        print_versions()
        print("\nSynchronizing versions...")
        if synchronize_versions():
            print("\nVersion synchronization completed successfully")
            print_versions()
            return 0
        else:
            print("\nVersion synchronization failed")
            return 1

if __name__ == "__main__":
    sys.exit(main())