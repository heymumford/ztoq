#!/usr/bin/env python3
"""
Build and host Sphinx documentation for ZTOQ.

This script builds the Sphinx documentation and starts a local web server
to host the docs, making them accessible to users via a web browser.
"""

import argparse
import http.server
import importlib.util
import logging
import os
import socketserver
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("doc_server")

def check_dependencies():
    """Check if required dependencies are installed."""
    dependencies = ["sphinx", "sphinx_rtd_theme", "recommonmark", "myst_parser"]
    missing = []

    for dep in dependencies:
        if importlib.util.find_spec(dep) is None:
            missing.append(dep)

    if missing:
        logger.error(f"Missing dependencies: {', '.join(missing)}")
        logger.info("Installing missing dependencies...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            logger.info("Dependencies installed successfully.")
        except subprocess.CalledProcessError:
            logger.error("Failed to install dependencies. Please install them manually:")
            logger.error(f"pip install {' '.join(missing)}")
            return False

    return True

def build_sphinx_docs(docs_path, output_format="html"):
    """Build Sphinx documentation."""
    sphinx_dir = Path(docs_path) / "sphinx"
    build_dir = sphinx_dir / "build"
    source_dir = sphinx_dir / "source"

    if not sphinx_dir.exists():
        logger.error(f"Sphinx directory not found: {sphinx_dir}")
        return False

    logger.info(f"Building {output_format} documentation...")
    try:
        result = subprocess.run(
            ["make", "-C", str(sphinx_dir), output_format],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(f"Sphinx build output:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"Sphinx build warnings:\n{result.stderr}")

        html_dir = build_dir / output_format
        if not html_dir.exists():
            logger.error(f"Build directory not found: {html_dir}")
            return False

        return html_dir
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to build documentation: {e}")
        logger.error(f"Command output:\n{e.stdout}\n{e.stderr}")
        return False

class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """A quieter HTTP request handler that doesn't print to stdout."""

    def log_message(self, format, *args):
        """Override to log to our logger instead of stderr."""
        logger.debug(f"{self.address_string()} - {format%args}")

def host_docs(doc_dir, port=8000):
    """Host documentation using a simple HTTP server."""
    # Verify the directory exists
    if not os.path.isdir(doc_dir):
        logger.error(f"Documentation directory not found: {doc_dir}")
        return None, port

    # Change to the documentation directory
    try:
        os.chdir(doc_dir)
    except Exception as e:
        logger.error(f"Failed to change to documentation directory: {e}")
        return None, port

    handler = QuietHTTPRequestHandler

    # Try up to 10 different ports
    max_attempts = 10
    attempts = 0

    while attempts < max_attempts:
        try:
            httpd = socketserver.TCPServer(("", port), handler)
            logger.info(f"Serving documentation at http://localhost:{port}/")
            return httpd, port
        except OSError as e:
            logger.warning(f"Port {port} is in use, trying {port+1}... ({e})")
            port += 1
            attempts += 1

    logger.error(f"Failed to find an available port after {max_attempts} attempts")
    return None, port

def open_browser(url, delay=1.0):
    """Open a web browser after a short delay."""
    def _open_browser():
        time.sleep(delay)
        webbrowser.open(url)

    threading.Thread(target=_open_browser).start()

def main():
    """Main function to build and host the documentation."""
    parser = argparse.ArgumentParser(description="Build and host ZTOQ documentation")
    parser.add_argument(
        "--port", type=int, default=8000,
        help="Port to host the documentation server on (default: 8000)",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Don't automatically open the documentation in a web browser",
    )
    parser.add_argument(
        "--format", default="html", choices=["html", "dirhtml", "singlehtml"],
        help="Output format for the documentation (default: html)",
    )
    args = parser.parse_args()

    # Find the project root directory
    project_root = Path(__file__).resolve().parent.parent
    docs_path = project_root / "docs"

    if not check_dependencies():
        sys.exit(1)

    html_dir = build_sphinx_docs(docs_path, args.format)
    if not html_dir:
        sys.exit(1)

    httpd, actual_port = host_docs(html_dir, args.port)
    if not httpd:
        logger.error("Failed to start documentation server. Try accessing the documentation directly:")
        logger.info(f"File: {html_dir}/index.html")
        sys.exit(1)

    if not args.no_browser:
        open_browser(f"http://localhost:{actual_port}/")

    try:
        logger.info("Press Ctrl+C to stop the server")
        httpd.serve_forever()
    except (KeyboardInterrupt, ValueError, OSError) as e:
        if isinstance(e, KeyboardInterrupt):
            logger.info("Server stopped by user")
        else:
            logger.error(f"Server error: {e}")

        # Show how to access the documentation directly
        logger.info(f"You can view the documentation directly by opening: {html_dir}/index.html")

if __name__ == "__main__":
    main()
