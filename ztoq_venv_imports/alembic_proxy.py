"""
Proxy to load alembic modules from the virtualenv rather than local directory.
"""
import os
import sys
import subprocess
from pathlib import Path

def get_venv_site_packages():
    """Get the site-packages directory of the Poetry virtualenv."""
    result = subprocess.run(
        ["poetry", "env", "info", "--path"], 
        capture_output=True, 
        text=True,
        check=True
    )
    venv_path = result.stdout.strip()
    python_version = subprocess.run(
        ["poetry", "run", "python", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
        capture_output=True,
        text=True,
        check=True
    ).stdout.strip()
    
    site_packages = Path(venv_path) / "lib" / f"python{python_version}" / "site-packages"
    return str(site_packages)

# Execute the get_venv_site_packages function to get the site-packages path
SITE_PACKAGES = get_venv_site_packages()

# Temporarily modify sys.path to prioritize the virtualenv's site-packages
if SITE_PACKAGES not in sys.path:
    sys.path.insert(0, SITE_PACKAGES)

# Force Python to look in the virtualenv first for imports
original_path = list(sys.path)

# Import the real alembic modules
import alembic
import alembic.command
import alembic.config

# Restore the original path
sys.path = original_path