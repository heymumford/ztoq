#!/usr/bin/env python3
"""
Build script for ZTOQ project that follows the test pyramid approach by Martin Fowler and Uncle Bob.
The test pyramid consists of:
- Many unit tests (fast, focused on single components)
- Some integration tests (test component interactions)
- Few system tests (slow, test the entire system end-to-end)
"""

import argparse
import subprocess
import sys
from typing import List, Dict, Any, Optional
from enum import Enum


class TestLevel(Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    SYSTEM = "system"
    ALL = "all"


class BuildCommand(Enum):
    CLEAN = "clean"
    LINT = "lint"
    TYPE_CHECK = "type-check"
    TEST = "test"
    DOCS = "docs"
    BUILD = "build"
    ALL = "all"


def run_command(cmd: List[str], env: Optional[Dict[str, Any]] = None) -> bool:
    """Run a command and return True if successful, False otherwise."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(result.stdout)
    return True


def run_poetry_command(cmd: List[str], env: Optional[Dict[str, Any]] = None) -> bool:
    """Run a poetry command and return True if successful, False otherwise."""
    return run_command(["poetry", "run"] + cmd, env=env)


def clean() -> bool:
    """Clean the project."""
    return run_command(["make", "clean"])


def lint() -> bool:
    """Run the linter."""
    return run_poetry_command(["flake8", "ztoq", "tests"])


def type_check() -> bool:
    """Run the type checker."""
    return run_poetry_command(["mypy", "ztoq"])


def test(level: TestLevel = TestLevel.ALL, with_docs: bool = False) -> bool:
    """Run tests for a specific level or all tests."""
    cmd = ["pytest", "-v"]
    if level != TestLevel.ALL:
        cmd.extend(["-m", level.value])
    # Add coverage for all tests
    if level == TestLevel.ALL:
        cmd.extend(["--cov=ztoq", "--cov-report=term", "--cov-report=html"])
    
    success = run_poetry_command(cmd)
    
    # Generate documentation after successful tests if requested
    if success and with_docs and level == TestLevel.ALL:
        success = generate_docs()
        
    return success


def generate_docs() -> bool:
    """Generate documentation."""
    # First, generate API documentation
    if not run_command(["sphinx-apidoc", "-o", "docs/sphinx/source/api", "ztoq", "--force"]):
        return False
    
    # Then build the documentation
    return run_command(["make", "-C", "docs/sphinx", "html"])

def build() -> bool:
    """Build the project."""
    return run_poetry_command(["poetry", "build"])


def run_all() -> bool:
    """Run all build steps."""
    steps = [
        ("Cleaning", clean),
        ("Linting", lint),
        ("Type checking", type_check),
        ("Running unit tests", lambda: test(TestLevel.UNIT)),
        ("Running integration tests", lambda: test(TestLevel.INTEGRATION)),
        ("Running system tests", lambda: test(TestLevel.SYSTEM)),
        ("Generating documentation", generate_docs),
        ("Building", build),
    ]
    success = True
    for step_name, step_func in steps:
        print(f"\n=== {step_name} ===")
        if not step_func():
            print(f"\n{step_name} failed!")
            success = False
            break
    if success:
        print("\n=== All steps completed successfully ===")
    return success


def main() -> int:
    """Main entry point for the build script."""
    parser = argparse.ArgumentParser(description="Build script for ZTOQ project")
    parser.add_argument(
        "command",
        type=str,
        choices=[cmd.value for cmd in BuildCommand],
        help="Build command to run",
    )
    parser.add_argument(
        "--test-level",
        type=str,
        choices=[level.value for level in TestLevel],
        default=TestLevel.ALL.value,
        help="Test level to run (only applicable for test command)",
    )
    parser.add_argument(
        "--with-docs",
        action="store_true",
        help="Generate documentation after running tests (only applicable for test command)",
    )
    args = parser.parse_args()
    command = BuildCommand(args.command)
    test_level = TestLevel(args.test_level)
    success = False
    if command == BuildCommand.CLEAN:
        success = clean()
    elif command == BuildCommand.LINT:
        success = lint()
    elif command == BuildCommand.TYPE_CHECK:
        success = type_check()
    elif command == BuildCommand.TEST:
        success = test(test_level, args.with_docs)
    elif command == BuildCommand.DOCS:
        success = generate_docs()
    elif command == BuildCommand.BUILD:
        success = build()
    elif command == BuildCommand.ALL:
        success = run_all()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
