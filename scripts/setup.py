#!/usr/bin/env python3
"""
Setup script for the ztoq project.

This script ensures all dependencies are properly installed and the project is ready for development.
It performs the following tasks:
1. Installs all dependencies using Poetry
2. Sets up pre-commit hooks
3. Verifies that all required dependencies are installed correctly
4. Creates necessary directories and configuration files if they don't exist
"""

import os
import subprocess
import sys
from pathlib import Path


def execute_command(
    cmd: str, description: str | None = None, exit_on_error: bool = True
) -> str | None:
    """
    Execute a shell command and handle errors.

    Args:
        cmd: The command to execute
        description: Optional description of the command
        exit_on_error: Whether to exit the program if the command fails

    Returns:
        Command output or None if the command failed

    """
    if description:
        print(f"\033[94m{description}...\033[0m")

    try:
        # NOTE: shell=True is used because we're executing commands in a controlled environment
        # with predefined strings, not user input
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            text=True,
            capture_output=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"\033[91mError executing command: {cmd}\033[0m")
        print(f"\033[91mStderr: {e.stderr}\033[0m")
        if exit_on_error:
            sys.exit(1)
        return None


def verify_dependency(module_name: str, package_name: str | None = None) -> bool:
    """
    Verify that a Python module can be imported.

    Args:
        module_name: The name of the module to import
        package_name: The name of the package to install if different from module_name

    Returns:
        True if the module can be imported, False otherwise

    """
    if package_name is None:
        package_name = module_name

    try:
        __import__(module_name)
        return True
    except ImportError:
        print(
            f"\033[93mWarning: Could not import {module_name}. Installing {package_name}...\033[0m",
        )
        execute_command(f"poetry add {package_name}", description=f"Installing {package_name}")
        try:
            __import__(module_name)
            return True
        except ImportError:
            print(f"\033[91mError: Failed to import {module_name} even after installation.\033[0m")
            return False


def setup_project() -> None:
    """Main setup function to prepare the project for development."""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Step 1: Ensure Poetry is installed
    try:
        execute_command("poetry --version", description="Checking Poetry installation")
    except FileNotFoundError:
        print(
            "\033[91mPoetry is not installed. Please install Poetry first: https://python-poetry.org/docs/#installation\033[0m",
        )
        sys.exit(1)

    # Step 2: Install dependencies
    execute_command("poetry install", description="Installing project dependencies")

    # Step 3: Setup pre-commit hooks
    execute_command("poetry run pre-commit install", description="Setting up pre-commit hooks")

    # Step 4: Install husky hooks
    husky_dir = project_root / ".husky"
    git_hooks_dir = project_root / ".git" / "hooks"

    if husky_dir.exists():
        print("\033[94mInstalling husky hooks...\033[0m")
        for hook_file in husky_dir.glob("*"):
            if hook_file.is_file() and not hook_file.name.startswith("."):
                target_path = git_hooks_dir / hook_file.name
                try:
                    # Create a symlink or copy the husky hook
                    if target_path.exists():
                        target_path.unlink()

                    # Copy the hook file to .git/hooks and make it executable
                    with open(hook_file) as src, open(target_path, "w") as dst:
                        dst.write(src.read())
                    os.chmod(target_path, 0o755)

                    print(f"Installed hook: {hook_file.name}")
                except Exception as e:
                    print(f"\033[91mError installing hook {hook_file.name}: {e}\033[0m")

    # Step 5: Verify critical dependencies
    dependencies = [
        ("sqlalchemy", None),
        ("pydantic", None),
        ("typer", None),
        ("pytest", None),
        ("ruff", None),
        ("mypy", None),
    ]

    all_deps_ok = True
    for module_name, package_name in dependencies:
        if not verify_dependency(module_name, package_name):
            all_deps_ok = False

    if not all_deps_ok:
        print(
            "\033[91mSome dependencies could not be verified. Please check the errors above.\033[0m",
        )
        sys.exit(1)

    # Step 6: Create necessary directories if they don't exist
    for directory in ["temp_site_packages"]:
        dir_path = project_root / directory
        if not dir_path.exists():
            dir_path.mkdir(parents=True)
            print(f"\033[92mCreated directory: {directory}\033[0m")

    # Step 7: Run a test command to verify the setup
    execute_command(
        "poetry run python -c \"import sys; print('Python version:', sys.version)\"",
        description="Verifying Python environment",
    )

    # Step 8: Success message
    print("\n\033[92m✓ Project setup completed successfully!\033[0m")
    print("\033[92m✓ All dependencies are installed and verified.\033[0m")
    print("\033[92m✓ Pre-commit hooks are installed.\033[0m")
    print(
        "\n\033[94mYou can now use the project. Run 'make help' to see available commands.\033[0m",
    )


if __name__ == "__main__":
    setup_project()
