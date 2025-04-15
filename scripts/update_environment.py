#!/usr/bin/env python3
"""
Update the development environment.

This script updates all dependencies and tools, ensuring everything is in sync.
It's particularly useful after pulling new changes from the repository.
"""

import os
import subprocess
import sys
from pathlib import Path


def execute_command(cmd: str, description: str | None = None, exit_on_error: bool = True) -> bool:
    """
    Execute a shell command and handle errors.

    Args:
        cmd: The command to execute
        description: Optional description of the command
        exit_on_error: Whether to exit the program if the command fails

    Returns:
        True if the command was successful, False otherwise

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
        print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"\033[91mError executing command: {cmd}\033[0m")
        print(f"\033[91mStderr: {e.stderr}\033[0m")
        if exit_on_error:
            sys.exit(1)
        return False


def update_environment() -> None:
    """Update the development environment with the latest dependencies and tools."""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Step 1: Update Poetry dependencies
    execute_command("poetry update", description="Updating Poetry dependencies")

    # Step 2: Update pre-commit hooks
    execute_command("pre-commit autoupdate", description="Updating pre-commit hooks")

    # Step 3: Ensure Ruff and pre-commit config versions match
    ruff_version = None
    with open("pyproject.toml") as f:
        for line in f:
            if "ruff" in line and "=" in line:
                ruff_version = line.split("=")[-1].strip().strip('"^')
                break

    if ruff_version:
        with open(".pre-commit-config.yaml") as f:
            content = f.read()

        # Update Ruff version in pre-commit config
        if "repo: https://github.com/astral-sh/ruff-pre-commit" in content:
            print(f"\033[94mUpdating Ruff version in pre-commit config to {ruff_version}...\033[0m")
            with open(".pre-commit-config.yaml") as f:
                lines = f.readlines()

            with open(".pre-commit-config.yaml", "w") as f:
                for line in lines:
                    if "repo: https://github.com/astral-sh/ruff-pre-commit" in line:
                        found_ruff_repo = True
                    elif found_ruff_repo and "rev:" in line:
                        line = f"    rev: v{ruff_version}  # Same version as in pyproject.toml\n"
                        found_ruff_repo = False
                    f.write(line)

    # Step 4: Install updated dependencies
    execute_command("poetry install", description="Installing updated dependencies")

    # Step 5: Install pre-commit hooks
    execute_command("pre-commit install", description="Installing pre-commit hooks")

    # Step 6: Install husky hooks
    husky_dir = project_root / ".husky"
    git_hooks_dir = project_root / ".git" / "hooks"

    if husky_dir.exists():
        print("\033[94mInstalling husky hooks...\033[0m")
        for hook_file in husky_dir.glob("*"):
            if hook_file.is_file() and not hook_file.name.startswith("."):
                target_path = git_hooks_dir / hook_file.name
                try:
                    # Create a symlink to the husky hook
                    if target_path.exists():
                        target_path.unlink()

                    # Copy the hook file to .git/hooks and make it executable
                    with open(hook_file) as src, open(target_path, "w") as dst:
                        dst.write(src.read())
                    os.chmod(target_path, 0o755)

                    print(f"Installed hook: {hook_file.name}")
                except Exception as e:
                    print(f"\033[91mError installing hook {hook_file.name}: {e}\033[0m")

    # Step 7: Verify everything is working
    execute_command(
        "pre-commit run --all-files",
        description="Running pre-commit checks",
        exit_on_error=False,
    )

    # Step 8: Run the dependency check
    execute_command("python scripts/ensure_dependencies.py", description="Verifying dependencies")

    print("\n\033[92m✓ Environment updated successfully!\033[0m")


if __name__ == "__main__":
    update_environment()
