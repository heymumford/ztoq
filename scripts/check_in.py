#!/usr/bin/env python3
"""
Check-in script for ZTOQ (Zephyr to qTest) - handles versioning, commits, and git tags.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

# Constants
ROOT_DIR = Path(__file__).parent.parent.absolute()
VERSION_PATH = ROOT_DIR / "ztoq" / "__init__.py"
BUILD_INFO_PATH = ROOT_DIR / ".build_info.json"
PYPROJECT_PATH = ROOT_DIR / "pyproject.toml"


def run_command(cmd: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
    """Run a command and return the return code, stdout, and stderr."""
    print(f"Running: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd
    )
    stdout, stderr = proc.communicate()
    return proc.returncode, stdout, stderr


def get_current_version() -> str:
    """Get the current version from the __init__.py file."""
    if not VERSION_PATH.exists():
        return "0.0.0"
    
    with open(VERSION_PATH, "r") as f:
        content = f.read()
        version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if version_match:
            return version_match.group(1)
        else:
            return "0.0.0"


def get_next_build_number() -> int:
    """Get the next build number."""
    if BUILD_INFO_PATH.exists():
        try:
            with open(BUILD_INFO_PATH, "r") as f:
                build_info = json.load(f)
                return build_info.get("build_number", 0) + 1
        except (json.JSONDecodeError, KeyError):
            pass
    return 1


def update_version(new_version: str) -> bool:
    """Update the version in the __init__.py file and pyproject.toml."""
    # Update __init__.py
    if VERSION_PATH.exists():
        with open(VERSION_PATH, "r") as f:
            content = f.read()
        
        # Replace version in __init__.py
        new_content = re.sub(
            r'__version__\s*=\s*["\']([^"\']+)["\']',
            f'__version__ = "{new_version}"',
            content
        )
        
        if new_content != content:
            with open(VERSION_PATH, "w") as f:
                f.write(new_content)
            print(f"Updated version in {VERSION_PATH} to {new_version}")
        else:
            print(f"Version in {VERSION_PATH} already set to {new_version}")
    else:
        print(f"Warning: {VERSION_PATH} not found, cannot update version")
    
    # Update pyproject.toml
    if PYPROJECT_PATH.exists():
        with open(PYPROJECT_PATH, "r") as f:
            content = f.read()
        
        # Replace version in pyproject.toml
        new_content = re.sub(
            r'version\s*=\s*["\']([^"\']+)["\']',
            f'version = "{new_version}"',
            content
        )
        
        if new_content != content:
            with open(PYPROJECT_PATH, "w") as f:
                f.write(new_content)
            print(f"Updated version in {PYPROJECT_PATH} to {new_version}")
            return True
        else:
            print(f"Version in {PYPROJECT_PATH} already set to {new_version}")
            return True
    else:
        print(f"Warning: {PYPROJECT_PATH} not found, cannot update version")
        return False


def clean_commit_message(message: str) -> str:
    """Clean the commit message to remove Claude references."""
    # Remove any "🤖 Generated with [Claude Code]..." lines
    message_lines = message.strip().split("\n")
    clean_lines = []
    
    for line in message_lines:
        if "🤖 Generated with [Claude Code]" in line:
            continue
        if "Co-Authored-By: Claude <noreply@anthropic.com>" in line:
            continue
        clean_lines.append(line)
    
    return "\n".join(clean_lines)


def increment_version(version_type: str = "patch") -> str:
    """Increment the version number based on the version type."""
    current_version = get_current_version()
    current_build = get_next_build_number()
    
    # Parse the version
    match = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-b(\d+))?", current_version)
    if not match:
        # If version doesn't match the pattern, start with 0.0.1
        major, minor, patch, build = 0, 0, 1, current_build
    else:
        major, minor, patch, build = match.groups()
        major, minor, patch = int(major), int(minor), int(patch)
        build = int(build) if build else current_build
    
    # Increment the version based on the type
    if version_type == "major":
        major += 1
        minor, patch = 0, 0
    elif version_type == "minor":
        minor += 1
        patch = 0
    elif version_type == "patch":
        patch += 1
    
    # Create the new version string
    return f"{major:02d}.{minor:02d}.{patch:04d}-b{build}"


def commit_changes(message: str, version: str) -> bool:
    """Commit changes to the repository and create a tag."""
    # Check if there are changes to commit
    returncode, stdout, stderr = run_command(["git", "status", "--porcelain"], ROOT_DIR)
    if returncode != 0:
        print(f"Error checking git status: {stderr}")
        return False
    
    if not stdout.strip():
        print("No changes to commit")
        return False
    
    # Clean the commit message
    clean_message = clean_commit_message(message)
    
    # Add all changes
    returncode, stdout, stderr = run_command(["git", "add", "."], ROOT_DIR)
    if returncode != 0:
        print(f"Error adding changes: {stderr}")
        return False
    
    # Commit changes
    commit_cmd = ["git", "commit", "-m", f"{clean_message}\n\nVersion: {version}"]
    returncode, stdout, stderr = run_command(commit_cmd, ROOT_DIR)
    if returncode != 0:
        print(f"Error committing changes: {stderr}")
        return False
    
    # Create a tag
    tag_name = f"v{version}"
    tag_cmd = ["git", "tag", "-a", tag_name, "-m", f"Version {version}"]
    returncode, stdout, stderr = run_command(tag_cmd, ROOT_DIR)
    if returncode != 0:
        print(f"Error creating tag: {stderr}")
        return False
    
    print(f"Changes committed and tagged as {tag_name}")
    return True


def save_build_info(version: str) -> None:
    """Save information about the current build."""
    # Get the current git hash
    returncode, stdout, stderr = run_command(["git", "rev-parse", "--short", "HEAD"], ROOT_DIR)
    git_hash = stdout.strip() if returncode == 0 else "unknown"
    
    # Extract build number from version
    build_match = re.search(r"-b(\d+)$", version)
    build_number = int(build_match.group(1)) if build_match else 1
    
    # Create build info
    build_info = {
        "version": version,
        "git_hash": git_hash,
        "timestamp": datetime.now().isoformat(),
        "build_number": build_number
    }
    
    # Save build info
    with open(BUILD_INFO_PATH, "w") as f:
        json.dump(build_info, f, indent=2)
    
    print(f"Build info saved: v{version} (build {build_number}, {git_hash})")


def main() -> int:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="ZTOQ Check-in Script")
    parser.add_argument(
        "message",
        help="Commit message"
    )
    parser.add_argument(
        "--version-type",
        choices=["major", "minor", "patch"],
        default="patch",
        help="Version type to increment (default: patch)"
    )
    parser.add_argument(
        "--skip-commit",
        action="store_true",
        help="Skip committing changes, just update version"
    )
    args = parser.parse_args()
    
    # Increment version
    new_version = increment_version(args.version_type)
    print(f"Incrementing to version: {new_version}")
    
    # Update version files
    if not update_version(new_version):
        print("Failed to update version files")
        return 1
    
    if args.skip_commit:
        print("Skipping commit as requested")
        save_build_info(new_version)
        return 0
    
    # Commit changes
    if not commit_changes(args.message, new_version):
        print("Failed to commit changes")
        return 1
    
    # Save build info
    save_build_info(new_version)
    
    print("\nCheck-in completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())