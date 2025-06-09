#!/usr/bin/env python3
"""Script to update RestAPI references to use get_rotkehlchen dependency"""
import os
import re
from pathlib import Path

def update_file(file_path):
    """Update all RestAPI references in a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = False
    
    # Check if get_rotkehlchen is already imported
    has_get_rotkehlchen_import = 'from rotkehlchen.api.v1.dependencies import get_rotkehlchen' in content
    
    # Update any remaining RestAPI imports (if get_rotkehlchen not already imported)
    if not has_get_rotkehlchen_import and 'RestAPI' in content:
        # Check if there are other imports from rotkehlchen.api.rest
        if 'from rotkehlchen.api.rest import' in content:
            # Add get_rotkehlchen to existing import
            content = re.sub(
                r'from rotkehlchen\.api\.rest import ([^;\n]+)',
                lambda m: f'from rotkehlchen.api.v1.dependencies import get_rotkehlchen',
                content
            )
            changes_made = True
    
    # Update the get_rest_api function definition
    if 'async def get_rest_api() -> RestAPI:' in content:
        content = re.sub(
            r'async def get_rest_api\(\) -> RestAPI:',
            'async def get_rotkehlchen() -> "Rotkehlchen":',
            content
        )
        # Also update the docstring
        content = re.sub(
            r'"""Get RestAPI instance - will be injected by the app"""',
            '"""Get Rotkehlchen instance - will be injected by the app"""',
            content
        )
        # Update the error message
        content = re.sub(
            r"raise NotImplementedError\('RestAPI injection not configured'\)",
            "raise NotImplementedError('Rotkehlchen injection not configured')",
            content
        )
        changes_made = True
    
    # Update all Depends(get_rest_api) to Depends(get_rotkehlchen)
    if 'Depends(get_rest_api)' in content:
        content = re.sub(
            r'Depends\(get_rest_api\)',
            'Depends(get_rotkehlchen)',
            content
        )
        changes_made = True
    
    # Update parameter names from rest_api to rotkehlchen
    if 'rest_api: RestAPI' in content:
        content = re.sub(
            r'rest_api: RestAPI',
            'rotkehlchen: "Rotkehlchen"',
            content
        )
        changes_made = True
    
    # Update all rest_api. usages to rotkehlchen.
    if 'rest_api.' in content:
        content = re.sub(
            r'\brest_api\.',
            'rotkehlchen.',
            content
        )
        changes_made = True
    
    # Add TYPE_CHECKING import if needed
    if '"Rotkehlchen"' in content and 'from typing import TYPE_CHECKING' not in content:
        # Find the imports section
        import_match = re.search(r'(^import .+?\n|^from .+?\n)+', content, re.MULTILINE)
        if import_match:
            import_end = import_match.end()
            # Add TYPE_CHECKING import after other imports
            content = content[:import_end] + '\nfrom typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from rotkehlchen.rotkehlchen import Rotkehlchen\n' + content[import_end:]
            changes_made = True
    
    # Only write if changes were made
    if changes_made:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    """Main function to update all files"""
    api_v1_dir = Path('rotkehlchen/api/v1')
    updated_files = []
    
    # Find all Python files in the directory
    for file_path in api_v1_dir.glob('*.py'):
        if file_path.name == 'dependencies.py':
            continue  # Skip the dependencies file itself
            
        if update_file(file_path):
            updated_files.append(file_path)
    
    print(f"Updated {len(updated_files)} files:")
    for file_path in updated_files:
        print(f"  - {file_path}")

if __name__ == '__main__':
    main()