#!/usr/bin/env python3
"""
Script to fix import ordering issues in Python files.

This script modifies Python files to ensure imports come after the license header
but before any other code, fixing E402 flake8 errors.

Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import os
import re
import sys

LICENSE_HEADER = '''"""
Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""'''

def fix_imports(file_path):
    """Fix import ordering in a Python file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # If no license header, skip
    if LICENSE_HEADER not in content:
        print(f"No license header in {file_path}, skipping.")
        return
    
    # Find module docstring after license header
    after_license = content.split(LICENSE_HEADER)[1].lstrip()
    
    module_docstring = ""
    code_remainder = after_license
    
    # Extract module docstring if it exists
    if after_license.startswith('"""'):
        docstring_end = after_license.find('"""', 3)
        if docstring_end != -1:
            docstring_end += 3  # Include the closing quotes
            module_docstring = after_license[:docstring_end]
            code_remainder = after_license[docstring_end:].lstrip()
    
    # Find all import statements
    import_pattern = re.compile(r'^(?:from\s+[\w.]+\s+import\s+.*|import\s+.*)$', re.MULTILINE)
    imports = import_pattern.findall(code_remainder)
    
    # Remove the imports from the remainder
    for imp in imports:
        code_remainder = code_remainder.replace(imp, '', 1)
    
    # Clean up any empty lines at the beginning of remainder
    code_remainder = code_remainder.lstrip()
    
    # Build the new content
    new_content = LICENSE_HEADER + "\n\n"
    
    # Add module docstring if it exists
    if module_docstring:
        new_content += module_docstring + "\n\n"
    
    # Add imports
    new_content += "\n".join(imports) + "\n\n"
    
    # Add the rest of the code
    new_content += code_remainder
    
    # Write back to file
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Fixed imports in {file_path}")

def main():
    """Process all Python files to fix imports."""
    # Get all Python files from the ztoq directory
    ztoq_dir = os.path.join(os.getcwd(), 'ztoq')
    tests_dir = os.path.join(os.getcwd(), 'tests')
    
    python_files = []
    
    # Walk through the ztoq directory
    for root, _, files in os.walk(ztoq_dir):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    # Walk through the tests directory
    for root, _, files in os.walk(tests_dir):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    # Fix imports in each file
    for file_path in python_files:
        fix_imports(file_path)
    
    print(f"Processed {len(python_files)} Python files.")

if __name__ == "__main__":
    main()