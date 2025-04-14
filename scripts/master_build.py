#!/usr/bin/env python3
"""
Master build script for ZTOQ (Zephyr to qTest) - handles testing, documentation, and badge generation.
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Constants
ROOT_DIR = Path(__file__).parent.parent.absolute()
README_PATH = ROOT_DIR / "README.md"
BADGE_PATH = ROOT_DIR / "docs" / "badges"
VERSION_PATH = ROOT_DIR / "ztoq" / "__init__.py"
TESTS_DIR = ROOT_DIR / "tests"
UNIT_TESTS_DIR = TESTS_DIR / "unit"
INTEGRATION_TESTS_DIR = TESTS_DIR / "integration"
E2E_TESTS_DIR = TESTS_DIR / "e2e"
BUILD_INFO_PATH = ROOT_DIR / ".build_info.json"


@dataclass
class TestResults:
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0


@dataclass
class TestSuiteResults:
    unit: TestResults = field(default_factory=TestResults)
    integration: TestResults = field(default_factory=TestResults)
    e2e: TestResults = field(default_factory=TestResults)

    @property
    def total(self) -> TestResults:
        return TestResults(
            total=self.unit.total + self.integration.total + self.e2e.total,
            passed=self.unit.passed + self.integration.passed + self.e2e.passed,
            failed=self.unit.failed + self.integration.failed + self.e2e.failed,
            skipped=self.unit.skipped + self.integration.skipped + self.e2e.skipped,
        )


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a command and return the return code, stdout, and stderr."""
    print(f"Running: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd)
    stdout, stderr = proc.communicate()
    return proc.returncode, stdout, stderr


def count_tests_by_type() -> dict[str, int]:
    """Count the number of test files by type."""
    counts = {"unit": 0, "integration": 0, "e2e": 0}

    # Count unit tests
    if UNIT_TESTS_DIR.exists():
        counts["unit"] = len(list(UNIT_TESTS_DIR.glob("test_*.py")))

    # Count integration tests
    if INTEGRATION_TESTS_DIR.exists():
        counts["integration"] = len(list(INTEGRATION_TESTS_DIR.glob("test_*.py")))

    # Count e2e tests
    if E2E_TESTS_DIR.exists():
        counts["e2e"] = len(list(E2E_TESTS_DIR.glob("test_*.py")))

    return counts


def run_tests() -> TestSuiteResults:
    """Run all tests and return the results."""
    results = TestSuiteResults()

    # Run unit tests
    returncode, stdout, stderr = run_command(
        ["poetry", "run", "pytest", "tests/unit", "-v"], ROOT_DIR
    )
    parse_test_results(stdout, results.unit)

    # Run integration tests
    returncode, stdout, stderr = run_command(
        ["poetry", "run", "pytest", "tests/integration", "-v"], ROOT_DIR
    )
    parse_test_results(stdout, results.integration)

    # Run e2e tests if they exist
    if (TESTS_DIR / "e2e").exists():
        returncode, stdout, stderr = run_command(
            ["poetry", "run", "pytest", "tests/e2e", "-v"], ROOT_DIR
        )
        parse_test_results(stdout, results.e2e)

    return results


def parse_test_results(output: str, results: TestResults) -> None:
    """Parse pytest output and update the results object."""
    # Sample line: "collected 42 items"
    total_match = re.search(r"collected (\d+) items", output)
    if total_match:
        results.total = int(total_match.group(1))

    # Count passed tests (each line with PASSED)
    results.passed = output.count("PASSED")

    # Count failed tests (each line with FAILED)
    results.failed = output.count("FAILED")

    # Count skipped tests (each line with SKIPPED)
    results.skipped = output.count("SKIPPED")


def create_test_pyramid_ascii(results: TestSuiteResults, test_counts: dict[str, int]) -> str:
    """Create ASCII art representation of the test pyramid."""
    e2e_width = 20
    integration_width = 40
    unit_width = 60

    # Calculate proportions for the pyramid
    test_counts["e2e"]
    test_counts["integration"]
    test_counts["unit"]

    # Create the pyramid
    pyramid = []

    # E2E Tests (top)
    e2e_line = f"    {'^':^{e2e_width}}    "
    pyramid.append(e2e_line)
    e2e_label = f"    {'E2E Tests':^{e2e_width}}    "
    pyramid.append(e2e_label)
    e2e_counts = f"    {f'{results.e2e.passed}/{results.e2e.total} passed':^{e2e_width}}    "
    pyramid.append(e2e_counts)

    # Integration Tests (middle)
    int_line = f"  {'/':^{integration_width}}  "
    pyramid.append(int_line)
    int_label = f"  {'Integration Tests':^{integration_width}}  "
    pyramid.append(int_label)
    int_counts = f"  {f'{results.integration.passed}/{results.integration.total} passed':^{integration_width}}  "
    pyramid.append(int_counts)

    # Unit Tests (bottom)
    unit_line = f"{'/':^{unit_width}}"
    pyramid.append(unit_line)
    unit_label = f"{'Unit Tests':^{unit_width}}"
    pyramid.append(unit_label)
    unit_counts = f"{f'{results.unit.passed}/{results.unit.total} passed':^{unit_width}}"
    pyramid.append(unit_counts)

    # Add bottom line
    pyramid.append(f"{'=' * unit_width}")

    # Add summary
    total_results = results.total
    summary = f"Total: {total_results.passed}/{total_results.total} tests passed ({total_results.failed} failed, {total_results.skipped} skipped)"
    pyramid.append(f"{summary:^{unit_width}}")

    return "\n".join(pyramid)


def generate_badges(results: TestSuiteResults) -> None:
    """Generate badge information for the README."""
    # Create badges directory if it doesn't exist
    BADGE_PATH.mkdir(exist_ok=True, parents=True)

    # Calculate pass percentage
    total = results.total
    pass_pct = total.passed / total.total * 100 if total.total > 0 else 0

    # Determine coverage badge color
    if pass_pct >= 90:
        color = "brightgreen"
    elif pass_pct >= 80:
        color = "green"
    elif pass_pct >= 70:
        color = "yellowgreen"
    elif pass_pct >= 60:
        color = "yellow"
    else:
        color = "red"

    # Save test results badge info
    with open(BADGE_PATH / "test_results.json", "w") as f:
        json.dump(
            {
                "schemaVersion": 1,
                "label": "tests",
                "message": f"{pass_pct:.1f}% ({total.passed}/{total.total})",
                "color": color,
            },
            f,
        )

    # Save unit test badge info
    with open(BADGE_PATH / "unit_tests.json", "w") as f:
        unit_pct = (results.unit.passed / results.unit.total) * 100 if results.unit.total > 0 else 0
        json.dump(
            {
                "schemaVersion": 1,
                "label": "unit tests",
                "message": f"{unit_pct:.1f}% ({results.unit.passed}/{results.unit.total})",
                "color": "blue",
            },
            f,
        )

    # Save integration test badge info
    with open(BADGE_PATH / "integration_tests.json", "w") as f:
        int_pct = (
            (results.integration.passed / results.integration.total) * 100
            if results.integration.total > 0
            else 0
        )
        json.dump(
            {
                "schemaVersion": 1,
                "label": "integration tests",
                "message": f"{int_pct:.1f}% ({results.integration.passed}/{results.integration.total})",
                "color": "blue",
            },
            f,
        )

    # Save e2e test badge info
    with open(BADGE_PATH / "e2e_tests.json", "w") as f:
        e2e_pct = (results.e2e.passed / results.e2e.total) * 100 if results.e2e.total > 0 else 0
        json.dump(
            {
                "schemaVersion": 1,
                "label": "e2e tests",
                "message": f"{e2e_pct:.1f}% ({results.e2e.passed}/{results.e2e.total})",
                "color": "blue",
            },
            f,
        )


def update_readme(results: TestSuiteResults, test_counts: dict[str, int]) -> None:
    """Update the README with test pyramid and badges."""
    if not README_PATH.exists():
        print(f"Error: README not found at {README_PATH}")
        return

    with open(README_PATH) as f:
        content = f.read()

    # Create new badge section
    badges = (
        "[![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/yourusername/ztoq/main/docs/badges/test_results.json)]"
        "(https://github.com/yourusername/ztoq/actions)\n"
        "[![Unit Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/yourusername/ztoq/main/docs/badges/unit_tests.json)]"
        "(https://github.com/yourusername/ztoq/actions)\n"
        "[![Integration Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/yourusername/ztoq/main/docs/badges/integration_tests.json)]"
        "(https://github.com/yourusername/ztoq/actions)\n"
        "[![E2E Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/yourusername/ztoq/main/docs/badges/e2e_tests.json)]"
        "(https://github.com/yourusername/ztoq/actions)\n"
    )

    # Create pyramid ASCII art
    test_pyramid = create_test_pyramid_ascii(results, test_counts)

    # Prepare the test pyramid section
    test_pyramid_section = f"""
## Test Pyramid

```
{test_pyramid}
```

*Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
"""

    # Replace or add badges section
    if "![Tests]" in content:
        # Replace existing badges
        content = re.sub(r"(\[!\[Tests\].+\n)+", badges, content)
    else:
        # Add badges after the title
        title_match = re.search(r"^#\s+.*$", content, re.MULTILINE)
        if title_match:
            title_end = title_match.end()
            content = content[:title_end] + "\n\n" + badges + content[title_end:]

    # Replace or add test pyramid section
    if "## Test Pyramid" in content:
        # Replace existing section
        content = re.sub(
            r"## Test Pyramid\s+```[\s\S]+?```\s+\*Updated:.*\*",
            test_pyramid_section.strip(),
            content,
        )
    else:
        # Add section before Features
        if "## Features" in content:
            content = content.replace("## Features", test_pyramid_section + "\n## Features")
        else:
            # Append to the end if Features section not found
            content += "\n" + test_pyramid_section

    # Write updated content
    with open(README_PATH, "w") as f:
        f.write(content)

    print(f"Updated README at {README_PATH}")


def build_project() -> int:
    """Build the project, run tests, and update documentation."""
    # Get test counts
    test_counts = count_tests_by_type()
    print(
        f"Found tests: {test_counts['unit']} unit, {test_counts['integration']} integration, {test_counts['e2e']} e2e"
    )

    # Run linting
    returncode, stdout, stderr = run_command(["poetry", "run", "flake8", "ztoq", "tests"], ROOT_DIR)
    if returncode != 0:
        print(f"Linting failed:\n{stderr}")

    # Run type checking
    returncode, stdout, stderr = run_command(["poetry", "run", "mypy", "ztoq"], ROOT_DIR)
    if returncode != 0:
        print(f"Type checking failed:\n{stderr}")

    # Run tests
    results = run_tests()

    # Generate badges
    generate_badges(results)

    # Update README
    update_readme(results, test_counts)

    # Build documentation
    returncode, stdout, stderr = run_command(
        ["poetry", "run", "python", "utils/build.py", "docs"], ROOT_DIR
    )
    if returncode != 0:
        print(f"Documentation build failed:\n{stderr}")

    # Save build info
    save_build_info()

    # Report results
    total = results.total
    print("\nTest Results Summary:")
    print(f"  Total: {total.total} tests")
    print(f"  Passed: {total.passed} tests")
    print(f"  Failed: {total.failed} tests")
    print(f"  Skipped: {total.skipped} tests")

    if total.failed > 0:
        print(f"\nBuild completed with {total.failed} test failures")
        return 1
    else:
        print("\nBuild completed successfully")
        return 0


def save_build_info() -> None:
    """Save information about the current build."""
    # Get the current version
    version = "0.0.0"
    if VERSION_PATH.exists():
        with open(VERSION_PATH) as f:
            version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', f.read())
            if version_match:
                version = version_match.group(1)

    # Get the current git hash
    returncode, stdout, stderr = run_command(["git", "rev-parse", "--short", "HEAD"], ROOT_DIR)
    git_hash = stdout.strip() if returncode == 0 else "unknown"

    # Create build info
    build_info = {
        "version": version,
        "git_hash": git_hash,
        "timestamp": datetime.now().isoformat(),
        "build_number": 1,
    }

    # Load previous build info if it exists
    if BUILD_INFO_PATH.exists():
        try:
            with open(BUILD_INFO_PATH) as f:
                prev_info = json.load(f)
                if prev_info.get("version") == version:
                    build_info["build_number"] = prev_info.get("build_number", 0) + 1
        except (json.JSONDecodeError, KeyError):
            pass

    # Save build info
    with open(BUILD_INFO_PATH, "w") as f:
        json.dump(build_info, f, indent=2)

    print(f"Build info saved: v{version} (build {build_info['build_number']}, {git_hash})")


def main() -> int:
    """Main entry point for the build script."""
    parser = argparse.ArgumentParser(description="ZTOQ Master Build Script")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    args = parser.parse_args()

    if args.skip_tests:
        print("Skipping tests as requested")
        # Just update the build info
        save_build_info()
        return 0
    else:
        return build_project()


if __name__ == "__main__":
    sys.exit(main())
