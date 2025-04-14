#!/usr/bin/env python3
"""
Script to fix f-strings that don't have placeholders.

This script searches for f-string instances that don't contain placeholders (F541 errors)
and converts them to regular strings.

Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import re
import sys
from pathlib import Path


def fix_fstrings_in_file(file_path):
    """Fix f-strings without placeholders in the given file."""
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        print(f"Error: File {file_path} not found")
        return False

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern to match f-strings without placeholders
    # This regex looks for f"..." or f'...' where there are no curly braces inside
    pattern = r'f(["\'])((?!\1).(?!{[^}]*}(?!\1)))*?\1'
    
    # Count matches before replacing
    matches = list(re.finditer(pattern, content))
    if not matches:
        print(f"No f-strings without placeholders found in {file_path}")
        return True

    # Replace f-strings without placeholders with regular strings
    modified_content = content
    offset = 0  # Track offset due to string length changes
    
    for match in matches:
        start, end = match.span()
        start += offset
        end += offset
        
        # Extract the original string
        original_str = modified_content[start:end]
        # Create the new string without the 'f' prefix
        new_str = original_str[1:]
        
        # Replace in the modified content
        modified_content = modified_content[:start] + new_str + modified_content[end:]
        
        # Update offset
        offset += len(new_str) - len(original_str)
    
    # Write the modified content back to the file
    with open(path, "w", encoding="utf-8") as f:
        f.write(modified_content)

    print(f"Fixed {len(matches)} f-strings without placeholders in {file_path}")
    return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: fix_fstring.py <file_path> [<file_path> ...]")
        return 1
    
    success = True
    for file_path in sys.argv[1:]:
        if not fix_fstrings_in_file(file_path):
            success = False
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())