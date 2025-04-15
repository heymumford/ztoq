#!/usr/bin/env python3
"""
Utility script to synchronize version numbers across different files in the ZTOQ
project.

This ensures that all version references (pyproject.toml, __init__.py, Sphinx
conf.py) are consistent.

"""

import re
import sys
from pathlib import Path

# Constants
ROOT_DIR = Path(__file__).parent.parent.parent.absolute()  # Up to project root
VERSION_PATH = ROOT_DIR / "ztoq" / "__init__.py"
PYPROJECT_PATH = ROOT_DIR / "pyproject.toml"
SPHINX_CONF_PATH = ROOT_DIR / "docs" / "sphinx" / "source" / "conf.py"

# Additional version files to check - add more as discovered
ADDITIONAL_VERSION_PATHS = [
    # CLI file with version reference
    {"path": ROOT_DIR / "ztoq" / "cli.py", "pattern": r'__version__\s*=\s*["\']([^"\']+)["\']', "replacement": r'__version__ = "{version}"'},
]


def get_version_from_pyproject() -> str | None:
    """
    Get version from pyproject.toml.
    """
    if not PYPROJECT_PATH.exists():
        print(f"Warning: {PYPROJECT_PATH} not found")
        return None

    try:
        with open(PYPROJECT_PATH) as f:
            content = f.read()
        version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            return version_match.group(1)
        print(f"Warning: Version pattern not found in {PYPROJECT_PATH}")
    except Exception as e:
        print(f"Error reading {PYPROJECT_PATH}: {str(e)}")
    return None


def get_version_from_init() -> str | None:
    """
    Get version from __init__.py.
    """
    if not VERSION_PATH.exists():
        print(f"Warning: {VERSION_PATH} not found")
        return None

    try:
        with open(VERSION_PATH) as f:
            content = f.read()
        version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            return version_match.group(1)
        print(f"Warning: Version pattern not found in {VERSION_PATH}")
    except Exception as e:
        print(f"Error reading {VERSION_PATH}: {str(e)}")
    return None


def get_version_from_sphinx() -> str | None:
    """
    Get version from Sphinx conf.py.
    """
    if not SPHINX_CONF_PATH.exists():
        print(f"Warning: {SPHINX_CONF_PATH} not found")
        return None

    try:
        with open(SPHINX_CONF_PATH) as f:
            content = f.read()
        version_match = re.search(r'release\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            return version_match.group(1)
        print(f"Warning: Version pattern not found in {SPHINX_CONF_PATH}")
    except Exception as e:
        print(f"Error reading {SPHINX_CONF_PATH}: {str(e)}")
    return None


def is_valid_version(version: str) -> bool:
    """
    Check if the string is a valid semantic version.

    Args:
        version: The version string to check

    Returns:
        bool: True if the version is valid, False otherwise

    """
    # Simple check for common placeholders
    placeholders = ["{", "}", "<", ">", "version", "new_version"]
    for ph in placeholders:
        if ph in version:
            return False

    # Basic semver check - more restrictive than full semver but catches most cases
    semver_pattern = r"^\d+\.\d+\.\d+(?:[-+].+)?$"
    if re.match(semver_pattern, version):
        return True

    return False


def get_version_from_file(file_info: dict) -> str | None:
    """
    Get version from an arbitrary file using a pattern.

    Args:
        file_info: Dict with 'path' and 'pattern' keys

    Returns:
        Version string or None if not found or invalid

    """
    path = file_info["path"]
    pattern = file_info["pattern"]

    if not path.exists():
        print(f"Warning: {path} not found")
        return None

    try:
        with open(path) as f:
            content = f.read()
        version_match = re.search(pattern, content)
        if version_match:
            version = version_match.group(1)
            # Check if it's a valid version and not a placeholder
            if is_valid_version(version):
                return version
            return None
        print(f"Warning: Version pattern not found in {path}")
    except Exception as e:
        print(f"Error reading {path}: {str(e)}")
    return None


def find_potential_version_files() -> list:
    """
    Scan project for files likely to contain version information.
    """
    potential_files = []
    common_patterns = [
        r'version\s*=\s*["\']([^"\']+)["\']',
        r'__version__\s*=\s*["\']([^"\']+)["\']',
        r'VERSION\s*=\s*["\']([^"\']+)["\']',
        r'release\s*=\s*["\']([^"\']+)["\']',
    ]

    # Look in common locations for version references
    locations = [
        ROOT_DIR / "setup.py",
        ROOT_DIR / "setup.cfg",
        ROOT_DIR / "docs",
        ROOT_DIR / "scripts",
        ROOT_DIR / "ztoq",
    ]

    for location in locations:
        if not location.exists():
            continue

        if location.is_file():
            for pattern in common_patterns:
                try:
                    with open(location) as f:
                        content = f.read()
                    if re.search(pattern, content):
                        potential_files.append(
                            {
                                "path": location,
                                "pattern": pattern,
                                "replacement": pattern.replace(r'([^"\']+)', r"{version}"),
                            }
                        )
                except Exception:
                    pass
        elif location.is_dir():
            # Look for Python files in the directory
            for py_file in location.glob("**/*.py"):
                for pattern in common_patterns:
                    try:
                        with open(py_file) as f:
                            content = f.read()
                        if re.search(pattern, content):
                            potential_files.append(
                                {
                                    "path": py_file,
                                    "pattern": pattern,
                                    "replacement": pattern.replace(r'([^"\']+)', r"{version}"),
                                }
                            )
                            break  # Only add the file once with the first matching pattern
                    except Exception:
                        pass

    return potential_files


def update_version_in_file(file_path: Path, pattern: str, replacement: str, version: str) -> bool:
    """
    Update version in a file with the given pattern and replacement template.
    """
    if not file_path.exists():
        print(f"Warning: {file_path} not found")
        return False

    try:
        with open(file_path) as f:
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
    except Exception as e:
        print(f"Error updating {file_path}: {str(e)}")
        return False


def synchronize_versions(scan_for_version_files: bool = False, verbose: bool = False) -> bool:
    """
    Synchronize versions across all relevant files.

    Args:
        scan_for_version_files: Whether to scan the project for additional version files
        verbose: Whether to print verbose output

    Returns:
        bool: True if synchronization succeeded, False otherwise

    """
    # Start with our known version files
    versions = {
        "pyproject": get_version_from_pyproject(),
        "init": get_version_from_init(),
        "sphinx": get_version_from_sphinx(),
    }

    # Keep track of all version files for updating
    version_files = [
        {
            "path": VERSION_PATH,
            "pattern": r'__version__\s*=\s*["\']([^"\']+)["\']',
            "replacement": r'__version__ = "{version}"',
        },
        {
            "path": PYPROJECT_PATH,
            "pattern": r'version\s*=\s*["\']([^"\']+)["\']',
            "replacement": r'version = "{version}"',
        },
        {
            "path": SPHINX_CONF_PATH,
            "pattern": r'release\s*=\s*["\']([^"\']+)["\']',
            "replacement": r'release = "{version}"',
        },
    ]

    # Add our predefined additional version paths
    for file_info in ADDITIONAL_VERSION_PATHS:
        file_name = file_info["path"].name
        versions[file_name] = get_version_from_file(file_info)
        version_files.append(file_info)

    # Optionally scan for other version files
    if scan_for_version_files:
        print("Scanning for additional version files...")
        potential_files = find_potential_version_files()

        # Filter out files we already know about
        known_paths = set(
            [str(VERSION_PATH), str(PYPROJECT_PATH), str(SPHINX_CONF_PATH)]
            + [str(file_info["path"]) for file_info in ADDITIONAL_VERSION_PATHS]
        )
        new_files = [f for f in potential_files if str(f["path"]) not in known_paths]

        if verbose:
            print(f"Found {len(new_files)} additional files with potential version references:")
            for file_info in new_files:
                print(f"  - {file_info['path']}")

        # Add versions from additional files
        for file_info in new_files:
            file_name = file_info["path"].name
            version = get_version_from_file(file_info)
            if version:
                versions[file_name] = version
                version_files.append(file_info)
                if verbose:
                    print(f"  - {file_info['path']} contains version {version}")

    # Find the most common version
    version_counts: dict[str, int] = {}
    for source, version in versions.items():
        if version:
            version_counts[version] = version_counts.get(version, 0) + 1
        else:
            print(f"Warning: No version found in {source}")

    if not version_counts:
        print("Error: No version found in any source file")
        return False

    # Use the pyproject version as canonical, falling back to the most common version
    canonical_version = versions["pyproject"]
    if not canonical_version:
        # Find the most common version if pyproject version is not available
        try:
            canonical_version = max(version_counts.items(), key=lambda x: x[1])[0]
        except ValueError:
            print("Error: Could not determine a canonical version")
            return False

    if not canonical_version:
        print("Error: No valid version found to use as canonical version")
        return False

    print(f"Using {canonical_version} as the canonical version")

    # Update versions in all files
    success = True

    for file_info in version_files:
        path = file_info["path"]
        pattern = file_info["pattern"]
        replacement = file_info["replacement"]

        # Only update files that exist and have a different version
        if path.exists():
            file_version = get_version_from_file(file_info)
            if file_version != canonical_version:
                success = success and update_version_in_file(
                    path, pattern, replacement, canonical_version
                )

    return success


def print_versions(scan_for_version_files: bool = False, verbose: bool = False) -> dict:
    """
    Print all version information for different files.

    Args:
        scan_for_version_files: Whether to scan for additional version files
        verbose: Whether to print verbose output

    Returns:
        dict: Dictionary of versions keyed by file name

    """
    print("ZTOQ Version Information:")

    # Known versions
    versions = {
        "pyproject.toml": get_version_from_pyproject(),
        "__init__.py": get_version_from_init(),
        "Sphinx conf.py": get_version_from_sphinx(),
    }

    # Print known versions
    for file_name, version in versions.items():
        print(f"  {file_name:<15} {version or 'Not found'}")

    # Additional predefined version files
    for file_info in ADDITIONAL_VERSION_PATHS:
        file_name = file_info["path"].name
        version = get_version_from_file(file_info)
        versions[file_name] = version
        print(f"  {file_name:<15} {version or 'Not found'}")

    # Optionally scan for other version files
    if scan_for_version_files:
        print("\nScanning for additional version files...")
        potential_files = find_potential_version_files()

        # Filter out files we already know about
        known_paths = set(
            [str(VERSION_PATH), str(PYPROJECT_PATH), str(SPHINX_CONF_PATH)]
            + [str(file_info["path"]) for file_info in ADDITIONAL_VERSION_PATHS]
        )
        new_files = [f for f in potential_files if str(f["path"]) not in known_paths]

        if new_files:
            print("\nAdditional files with version information:")
            for file_info in new_files:
                path = file_info["path"]
                file_version = get_version_from_file(file_info)
                versions[path.name] = file_version
                # Only show path relative to project root
                rel_path = path.relative_to(ROOT_DIR)
                print(f"  {str(rel_path):<30} {file_version or 'Not found'}")
        elif verbose:
            print("  No additional version files found")

    return versions


def bump_version(current_version: str, bump_type: str = "patch") -> str:
    """
    Bump the version according to semantic versioning.

    Args:
        current_version: Current version string
        bump_type: Type of bump ('major', 'minor', or 'patch')

    Returns:
        str: New version string

    """
    if not current_version:
        return "0.1.0"  # Default for new projects

    try:
        # Parse the version
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:[-+](.+))?$", current_version)
        if not match:
            print(f"Warning: Could not parse version '{current_version}'. Using default bump.")
            return "0.1.0"

        major, minor, patch, suffix = match.groups()
        major, minor, patch = int(major), int(minor), int(patch)

        # Bump according to type
        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        else:  # patch (default)
            patch += 1

        # Build the new version
        new_version = f"{major}.{minor}.{patch}"
        if suffix:
            new_version += f"-{suffix}"

        return new_version
    except Exception as e:
        print(f"Error bumping version: {str(e)}")
        return current_version


def main() -> int:
    """
    Main entry point for the script.
    """
    import argparse

    try:
        parser = argparse.ArgumentParser(description="ZTOQ Version Synchronization Script")
        parser.add_argument(
            "--check",
            action="store_true",
            help="Only check version consistency without making changes",
        )
        parser.add_argument(
            "--scan", action="store_true", help="Scan the project for additional version files"
        )
        parser.add_argument("--verbose", action="store_true", help="Show more detailed output")
        parser.add_argument(
            "--update", type=str, metavar="VERSION", help="Update to a specific version"
        )
        parser.add_argument(
            "--bump",
            choices=["major", "minor", "patch"],
            help="Bump version according to semantic versioning",
        )
        args = parser.parse_args()

        scan_mode = args.scan
        verbose_mode = args.verbose

        if args.bump:
            # Get current version and bump it
            current_version = (
                get_version_from_pyproject() or get_version_from_init() or get_version_from_sphinx()
            )
            if not current_version:
                print("Error: No current version found to bump")
                return 1

            new_version = bump_version(current_version, args.bump)
            print(f"Bumping {args.bump} version: {current_version} -> {new_version}")

            # Update main version files
            success = True

            # Update __init__.py
            success = success and update_version_in_file(
                VERSION_PATH,
                r'__version__\s*=\s*["\']([^"\']+)["\']',
                r'__version__ = "{version}"',
                new_version,
            )

            # Update pyproject.toml
            success = success and update_version_in_file(
                PYPROJECT_PATH,
                r'version\s*=\s*["\']([^"\']+)["\']',
                r'version = "{version}"',
                new_version,
            )

            # Update Sphinx conf.py
            success = success and update_version_in_file(
                SPHINX_CONF_PATH,
                r'release\s*=\s*["\']([^"\']+)["\']',
                r'release = "{version}"',
                new_version,
            )

            # Update additional versions if requested
            if scan_mode:
                print("\nSynchronizing additional files...")
                success = success and synchronize_versions(
                    scan_for_version_files=True, verbose=verbose_mode
                )

            if success:
                print(f"\nSuccessfully bumped version to {new_version}")
                print_versions(scan_for_version_files=scan_mode, verbose=verbose_mode)
                return 0
            else:
                print("\nVersion bump failed")
                return 1
        elif args.check:
            # Print versions and check consistency
            versions = print_versions(scan_for_version_files=scan_mode, verbose=verbose_mode)

            # Get unique versions
            unique_versions = set(v for v in versions.values() if v is not None)

            if not unique_versions:
                print("\nError: No version found in any source file")
                return 1

            if len(unique_versions) == 1:
                print(f"\nAll versions are consistent! ({next(iter(unique_versions))})")
                return 0
            else:
                print("\nWarning: Versions are inconsistent across files")
                print(
                    f"Found {len(unique_versions)} different versions: {', '.join(unique_versions)}"
                )
                return 1
        elif args.update:
            # Update to a specific version
            print(f"Updating to version {args.update}")

            # Create a temporary versions dictionary with the key files
            temp_versions = {"pyproject": args.update, "init": args.update, "sphinx": args.update}

            # Update main version files
            success = True

            # Update __init__.py
            success = success and update_version_in_file(
                VERSION_PATH,
                r'__version__\s*=\s*["\']([^"\']+)["\']',
                r'__version__ = "{version}"',
                args.update,
            )

            # Update pyproject.toml
            success = success and update_version_in_file(
                PYPROJECT_PATH,
                r'version\s*=\s*["\']([^"\']+)["\']',
                r'version = "{version}"',
                args.update,
            )

            # Update Sphinx conf.py
            success = success and update_version_in_file(
                SPHINX_CONF_PATH,
                r'release\s*=\s*["\']([^"\']+)["\']',
                r'release = "{version}"',
                args.update,
            )

            # Update additional versions
            if scan_mode:
                print("\nSynchronizing additional files...")
                # Additional synchronization is handled by the synchronize_versions function
                success = success and synchronize_versions(
                    scan_for_version_files=True, verbose=verbose_mode
                )

            if success:
                print("\nVersion update completed successfully")
                print_versions(scan_for_version_files=scan_mode, verbose=verbose_mode)
                return 0
            else:
                print("\nVersion update failed")
                return 1
        else:
            # Default behavior: synchronize versions
            print_versions(scan_for_version_files=scan_mode, verbose=verbose_mode)
            print("\nSynchronizing versions...")
            if synchronize_versions(scan_for_version_files=scan_mode, verbose=verbose_mode):
                print("\nVersion synchronization completed successfully")
                print_versions(scan_for_version_files=scan_mode, verbose=verbose_mode)
                return 0
            else:
                print("\nVersion synchronization failed")
                return 1
    except Exception as e:
        print(f"Error: An unexpected error occurred: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
