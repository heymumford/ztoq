#!/usr/bin/env python3
"""
Post-installation script for ZTOQ.

This script is executed after ZTOQ is installed to perform final setup
steps and show the user how to access the documentation.
"""

import subprocess
import sys


def print_welcome_message():
    """Print a welcome message after installation."""
    print("\n" + "="*80)
    print("ZTOQ Installation Complete!")
    print("="*80)
    print("""
Thank you for installing ZTOQ - the Zephyr to qTest migration tool.

To view the documentation in your web browser, run:
    ztoq docs serve

This will build the Sphinx documentation and open it in your default browser.

For more information on how to use ZTOQ, you can also run:
    ztoq --help

Happy migrating!
""")


def setup_docs():
    """Check if documentation dependencies are installed."""
    try:
        # Check if Sphinx and required packages are installed
        dependencies = ["sphinx", "sphinx_rtd_theme", "recommonmark", "myst_parser"]
        for dep in dependencies:
            try:
                __import__(dep)
            except ImportError:
                print(f"Installing documentation dependency: {dep}")
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
    except Exception as e:
        print(f"Warning: Could not set up documentation dependencies: {e}")
        print("You can install them manually with: pip install sphinx sphinx_rtd_theme recommonmark myst_parser")


def main():
    """Main function for post-installation script."""
    # Set up documentation dependencies
    setup_docs()

    # Print welcome message
    print_welcome_message()

    # In a post-install hook context, we shouldn't block with input
    # Instead, provide clear instructions
    print("To view the documentation now, run: ztoq docs serve")

    # Return success
    return 0


if __name__ == "__main__":
    main()
