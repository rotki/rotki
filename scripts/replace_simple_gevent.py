#!/usr/bin/env python
"""Replace simple gevent imports with async equivalents

This script replaces straightforward gevent usage with asyncio equivalents.
It only handles simple cases that don't require logic changes.
"""
import re
from pathlib import Path


def get_simple_replacements() -> list[tuple[str, str]]:
    """Get list of simple string replacements"""
    return [
        # Import replacements
        ('from gevent import sleep', 'import asyncio'),
        ('from gevent.lock import Semaphore', 'import asyncio'),
        ('from gevent.event import Event', 'import asyncio'),
        ('import gevent\n', 'import asyncio\n'),
        
        # Usage replacements
        ('gevent.sleep(', 'asyncio.sleep('),
        ('Semaphore(', 'asyncio.Semaphore('),
        ('Event()', 'asyncio.Event()'),
        
        # Common patterns
        ('with semaphore:', 'async with semaphore:'),
        ('def ', 'async def '),  # This is too broad, skip
    ]


def get_import_mapping() -> dict[str, str]:
    """Get mapping of imports to replace"""
    return {
        'from gevent import sleep': 'from asyncio import sleep',
        'from gevent.lock import Semaphore': 'from asyncio import Semaphore', 
        'from gevent.event import Event': 'from asyncio import Event',
        'import gevent': 'import asyncio',
        'gevent.spawn': 'asyncio.create_task',
        'gevent.killall': '# TODO: Replace with task cancellation',
    }


def should_skip_file(filepath: Path) -> bool:
    """Check if file should be skipped"""
    skip_patterns = [
        'test_',
        '__pycache__',
        '.pyc',
        'scripts/',
        'tools/',
        'docs/',
        'async_',  # Skip already migrated files
        'unified.py',  # Skip unified interfaces
        'migration.py',  # Skip migration utilities
    ]
    
    filepath_str = str(filepath)
    return any(pattern in filepath_str for pattern in skip_patterns)


def create_compatibility_import(filepath: Path) -> str:
    """Create a compatibility import statement"""
    return """# Compatibility imports during migration
try:
    from rotkehlchen.api.feature_flags import async_features, AsyncFeature
    if async_features.is_enabled(AsyncFeature.TASK_MANAGER):
        import asyncio
        sleep = asyncio.sleep
        Semaphore = asyncio.Semaphore
        Event = asyncio.Event
    else:
        from gevent import sleep
        from gevent.lock import Semaphore
        from gevent.event import Event
except ImportError:
    # Fallback to gevent if feature flags not available
    from gevent import sleep
    from gevent.lock import Semaphore
    from gevent.event import Event

"""


def update_file(filepath: Path, dry_run: bool = True) -> tuple[bool, list[str]]:
    """Update a single file with compatibility imports"""
    if should_skip_file(filepath):
        return False, []
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        changes = []
        
        # Check if file uses gevent
        if 'gevent' not in content:
            return False, []
            
        # Don't modify files that already have compatibility imports
        if 'Compatibility imports during migration' in content:
            return False, []
            
        # Find gevent imports
        has_sleep = 'from gevent import sleep' in content or 'gevent.sleep' in content
        has_semaphore = 'from gevent.lock import Semaphore' in content
        has_event = 'from gevent.event import Event' in content
        has_gevent = any([has_sleep, has_semaphore, has_event])
        
        if not has_gevent:
            return False, []
            
        # Add compatibility import at the top after other imports
        lines = content.split('\n')
        insert_pos = 0
        
        # Find position after imports
        for i, line in enumerate(lines):
            if line.startswith(('import ', 'from ')) and 'gevent' not in line:
                insert_pos = i + 1
            elif line.strip() and not line.startswith(('#', 'import', 'from')):
                # Found first non-import line
                break
                
        # Remove existing gevent imports
        new_lines = []
        for line in lines:
            if ('from gevent import sleep' in line or
                'from gevent.lock import Semaphore' in line or  
                'from gevent.event import Event' in line):
                changes.append(f"Removed: {line.strip()}")
                continue
            new_lines.append(line)
            
        # Add compatibility imports
        compat_import = create_compatibility_import(filepath)
        new_lines.insert(insert_pos, compat_import)
        changes.append("Added compatibility imports")
        
        new_content = '\n'.join(new_lines)
        
        if new_content != original_content:
            if not dry_run:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            return True, changes
            
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        
    return False, []


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Replace simple gevent imports')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')
    parser.add_argument('--file', help='Process single file')
    args = parser.parse_args()
    
    if args.file:
        files = [Path(args.file)]
    else:
        # Get list of files with simple gevent usage
        simple_files = [
            'rotkehlchen/utils/mixins/lockable.py',
            'rotkehlchen/chain/aggregator.py',
            'rotkehlchen/chain/bitcoin/xpub.py',
            'rotkehlchen/chain/evm/transactions.py',
            'rotkehlchen/db/dbhandler.py',
            'rotkehlchen/globaldb/handler.py',
        ]
        files = [Path(f) for f in simple_files if Path(f).exists()]
        
    print(f"Processing {len(files)} files...")
    if args.dry_run:
        print("DRY RUN - No files will be modified\n")
        
    updated_count = 0
    for filepath in files:
        updated, changes = update_file(filepath, dry_run=args.dry_run)
        if updated:
            updated_count += 1
            print(f"\n{filepath}:")
            for change in changes:
                print(f"  - {change}")
                
    print(f"\n{'Would update' if args.dry_run else 'Updated'} {updated_count} files")
    
    if args.dry_run:
        print("\nRun without --dry-run to apply changes")


if __name__ == '__main__':
    main()