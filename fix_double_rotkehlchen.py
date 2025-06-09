#!/usr/bin/env python3
"""Script to fix double rotkehlchen references"""
import re
from pathlib import Path

def fix_double_references(file_path):
    """Fix double rotkehlchen references in a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix rotkehlchen.rotkehlchen -> rotkehlchen
    content = re.sub(r'\brotkehlchen\.rotkehlchen\.', 'rotkehlchen.', content)
    
    # Only write if changes were made
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Main function to fix all files"""
    api_v1_dir = Path('rotkehlchen/api/v1')
    fixed_files = []
    
    # Find all Python files in the directory
    for file_path in api_v1_dir.glob('*.py'):
        if fix_double_references(file_path):
            fixed_files.append(file_path)
    
    print(f"Fixed {len(fixed_files)} files:")
    for file_path in fixed_files:
        print(f"  - {file_path}")

if __name__ == '__main__':
    main()