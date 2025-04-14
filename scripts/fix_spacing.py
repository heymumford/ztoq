#!/usr/bin/env python3
"""
Script to fix class and function spacing issues in Python files.

This script adds proper blank lines before class and function definitions
to match PEP 8 style guidelines, addressing E302 flake8 errors.

Copyright (c) 2025 Eric C. Mumford (@heymumford)
This file is part of ZTOQ, licensed under the MIT License.
See LICENSE file for details.
"""

import os
import re
import sys

def fix_class_and_function_spacing(file_path):
    """Fix class and function spacing in a Python file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to find class and function definitions with incorrect spacing
    # This looks for class or def at the start of a line that doesn't have 
    # two blank lines before it, unless it's part of a nested class/function
    pattern = re.compile(r'(?<!\n\n\n)(?<!\n\n)(^(?:class|def)\s+[a-zA-Z_])', re.MULTILINE)
    
    # Replace with two blank lines
    new_content = pattern.sub(r'\n\n\1', content)
    
    # If changes were made, write back to file
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Fixed class/function spacing in {file_path}")
        return True
    
    return False

def fix_trailing_whitespace(file_path):
    """Remove trailing whitespace from lines."""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    fixed_lines = [line.rstrip() + '\n' for line in lines]
    
    # Check if any changes were made
    if lines != fixed_lines:
        with open(file_path, 'w') as f:
            f.writelines(fixed_lines)
        print(f"Fixed trailing whitespace in {file_path}")
        return True
    
    return False

def fix_continuation_indentation(file_path):
    """Fix continuation line indentation issues."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # This is a simplified approach and might not catch all cases or might over-fix some
    # For better results, consider using black formatter
    
    # Pattern for common continuation indentation errors in lists, dicts, etc.
    pattern = re.compile(r',\n(\s+)([^\s])', re.MULTILINE)
    
    # Replace with proper indentation (4 spaces more than the line above)
    def replacement(match):
        spaces = match.group(1)
        item = match.group(2)
        proper_indent = ' ' * (len(spaces) + 4)
        return f',\n{proper_indent}{item}'
    
    new_content = pattern.sub(replacement, content)
    
    # If changes were made, write back to file
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Fixed continuation indentation in {file_path}")
        return True
    
    return False

def main():
    """Process all Python files to fix spacing issues."""
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
    
    # Fix spacing issues in each file
    for file_path in python_files:
        any_changes = False
        any_changes |= fix_class_and_function_spacing(file_path)
        any_changes |= fix_trailing_whitespace(file_path)
        any_changes |= fix_continuation_indentation(file_path)
        
        if not any_changes:
            print(f"No spacing issues found in {file_path}")
    
    print(f"Processed {len(python_files)} Python files.")

if __name__ == "__main__":
    main()