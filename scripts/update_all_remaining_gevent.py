#!/usr/bin/env python
"""Update all remaining files to use gevent compatibility layer"""
import re
from pathlib import Path


def update_file_for_gevent_compat(filepath: Path) -> tuple[bool, list[str]]:
    """Update a file to use gevent compat layer"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Skip if already using compat module
        if 'from rotkehlchen.utils.gevent_compat import' in content:
            return False, ["Already using compat module"]
            
        original_content = content
        changes = []
        imports_needed = set()
        
        # Handle different patterns
        patterns = [
            # gevent.spawn usage
            (r'\bgevent\.spawn\b', 'spawn', 'spawn'),
            # gevent.sleep usage
            (r'\bgevent\.sleep\b', 'sleep', 'sleep'),
            # gevent.killall usage
            (r'\bgevent\.killall\b', 'kill_all', 'kill_all'),
            # gevent.kill usage
            (r'\bgevent\.kill\b', 'kill', 'kill'),
            # gevent.joinall usage
            (r'\bgevent\.joinall\b', 'joinall', 'joinall'),
            # gevent.wait usage
            (r'\bgevent\.wait\b', 'wait', 'wait'),
            # gevent.Timeout usage
            (r'\bgevent\.Timeout\b', 'Timeout', 'Timeout'),
            # gevent.pool usage
            (r'\bgevent\.pool\b', 'pool', 'pool'),
        ]
        
        for pattern, replacement, import_name in patterns:
            if re.search(pattern, content):
                imports_needed.add(import_name)
                content = re.sub(pattern, replacement, content)
                changes.append(f"Replaced {pattern} with {replacement}")
        
        # Check for specific imports
        if 'from gevent.lock import Semaphore' in content:
            imports_needed.add('Semaphore')
            content = content.replace('from gevent.lock import Semaphore\n', '')
            changes.append("Removed gevent.lock.Semaphore import")
            
        if 'from gevent.event import Event' in content:
            imports_needed.add('Event')
            content = content.replace('from gevent.event import Event\n', '')
            changes.append("Removed gevent.event.Event import")
            
        if 'from gevent import Greenlet' in content:
            imports_needed.add('Greenlet')
            content = content.replace('from gevent import Greenlet\n', '')
            changes.append("Removed gevent.Greenlet import")
            
        # Handle gevent.socket
        if 'gevent.socket' in content:
            # This is more complex, needs special handling
            changes.append("WARNING: gevent.socket usage detected - needs manual review")
            
        # Remove import gevent if we have replacements
        if imports_needed and 'import gevent' in content:
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                if line.strip() == 'import gevent':
                    continue
                new_lines.append(line)
            content = '\n'.join(new_lines)
            changes.append("Removed import gevent")
            
        if not imports_needed:
            return False, ["No gevent usage found"]
            
        # Add compat imports
        lines = content.split('\n')
        insert_pos = 0
        
        # Find import section
        for i, line in enumerate(lines):
            if line.startswith(('import ', 'from ')) and 'gevent' not in line:
                if 'rotkehlchen' in line:
                    insert_pos = i + 1
                    
        if insert_pos == 0:
            # Find first import
            for i, line in enumerate(lines):
                if line.startswith(('import ', 'from ')):
                    insert_pos = i + 1
                    break
                    
        # Insert compat import
        imports = sorted(imports_needed)
        import_line = f"from rotkehlchen.utils.gevent_compat import {', '.join(imports)}"
        lines.insert(insert_pos, import_line)
        changes.append(f"Added compat import: {import_line}")
        
        new_content = '\n'.join(lines)
        
        if new_content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True, changes
            
    except Exception as e:
        return False, [f"Error: {e}"]
        
    return False, []


def main():
    """Update all remaining files"""
    # List of all files that still need updating
    files_to_update = [
        # Core files
        'rotkehlchen/logging.py',
        'rotkehlchen/server.py',
        'rotkehlchen/accounting/accountant.py',
        'rotkehlchen/tasks/unified.py',
        'rotkehlchen/tasks/manager.py',
        'rotkehlchen/greenlets/utils.py',
        'rotkehlchen/premium/sync.py',
        
        # Test files (important to update for consistency)
        'rotkehlchen/tests/fixtures/greenlets.py',
        'rotkehlchen/tests/utils/api.py',
        'rotkehlchen/tests/utils/ethereum.py',
        'rotkehlchen/tests/utils/substrate.py',
        'rotkehlchen/tests/unit/test_tokens.py',
        'rotkehlchen/tests/unit/test_tasks_manager.py',
        'rotkehlchen/tests/unit/test_search.py',
        'rotkehlchen/tests/integration/test_premium.py',
        'rotkehlchen/tests/integration/test_blockchain.py',
        'rotkehlchen/tests/integration/test_backend.py',
        'rotkehlchen/tests/websocketsapi/test_misc.py',
        'rotkehlchen/tests/db/test_savepoints.py',
        'rotkehlchen/tests/db/test_async.py',
        'rotkehlchen/tests/api/test_async.py',
        'rotkehlchen/tests/api/test_balances.py',
        'rotkehlchen/tests/api/test_bitcoin.py',
        'rotkehlchen/tests/api/test_ethereum_transactions.py',
        'rotkehlchen/tests/api/test_users.py',
        'rotkehlchen/tests/api/blockchain/test_base.py',
        'rotkehlchen/tests/api/blockchain/test_evm.py',
        'rotkehlchen/tests/fixtures/websockets.py',
        'rotkehlchen/tests/external_apis/test_gnosispay.py',
        'rotkehlchen/tests/external_apis/test_monerium.py',
        'rotkehlchen/tests/exchanges/test_kraken.py',
        
        # Data migration tests
        'rotkehlchen/tests/data_migrations/test_migrations.py',
    ]
    
    print(f"Updating {len(files_to_update)} files...")
    updated_count = 0
    failed_count = 0
    
    for filepath in files_to_update:
        path = Path(filepath)
        if not path.exists():
            print(f"⚠️  File not found: {filepath}")
            continue
            
        updated, changes = update_file_for_gevent_compat(path)
        if updated:
            updated_count += 1
            print(f"\n✅ Updated {filepath}:")
            for change in changes:
                print(f"  - {change}")
        elif "Error" in str(changes):
            failed_count += 1
            print(f"\n❌ Failed to update {filepath}:")
            for change in changes:
                print(f"  - {change}")
                
    print(f"\n📊 Summary: Updated {updated_count} files, {failed_count} failures")
    
    # Also handle special cases
    print("\n🔧 Handling special cases...")
    
    # Handle __main__.py separately due to monkey patching
    handle_main_py()
    
    # Handle files with gevent.pool, gevent.Timeout etc
    handle_complex_files()


def handle_main_py():
    """Special handling for __main__.py due to monkey patching"""
    filepath = Path('rotkehlchen/__main__.py')
    print(f"\n🔧 Special handling for {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Add comment about monkey patching
        if '# TODO: Remove monkey patching' not in content:
            content = content.replace(
                'from gevent import monkey  # isort:skip',
                '# TODO: Remove monkey patching when fully migrated to asyncio\nfrom gevent import monkey  # isort:skip'
            )
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print("  - Added TODO comment for monkey patching removal")
    except Exception as e:
        print(f"  - Error: {e}")


def handle_complex_files():
    """Handle files with more complex gevent usage"""
    complex_patterns = {
        'rotkehlchen/greenlets/manager.py': handle_greenlet_manager,
        'rotkehlchen/tasks/manager.py': handle_task_manager,
        'rotkehlchen/chain/substrate/manager.py': handle_substrate_timeout,
    }
    
    for filepath, handler in complex_patterns.items():
        if Path(filepath).exists():
            print(f"\n🔧 Special handling for {filepath}")
            handler(filepath)


def handle_greenlet_manager(filepath: str):
    """Handle GreenletManager which uses gevent heavily"""
    # This is complex and uses many gevent features
    # For now, just add a TODO comment
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if '# TODO: Replace with AsyncTaskManager' not in content:
            lines = content.split('\n')
            lines.insert(0, '# TODO: Replace with AsyncTaskManager when migrating to asyncio')
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
                
            print("  - Added TODO comment for AsyncTaskManager replacement")
    except Exception as e:
        print(f"  - Error: {e}")


def handle_task_manager(filepath: str):
    """Handle TaskManager which coordinates greenlets"""
    try:
        path = Path(filepath)
        updated, changes = update_file_for_gevent_compat(path)
        if updated:
            print("  - Updated basic gevent usage")
            for change in changes:
                print(f"    {change}")
    except Exception as e:
        print(f"  - Error: {e}")


def handle_substrate_timeout(filepath: str):
    """Handle substrate manager with gevent.Timeout"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Add Timeout to compat imports if needed
        if 'gevent.Timeout' in content and 'from rotkehlchen.utils.gevent_compat import' not in content:
            # Update to use compat
            content = content.replace('with gevent.Timeout(', 'with Timeout(')
            
            # Add import
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'from rotkehlchen.utils.gevent_compat import' in line:
                    # Add Timeout to existing import
                    if 'Timeout' not in line:
                        lines[i] = line.rstrip(')') + ', Timeout)'
                    break
            else:
                # No compat import found, add it
                for i, line in enumerate(lines):
                    if line.startswith('from rotkehlchen'):
                        lines.insert(i, 'from rotkehlchen.utils.gevent_compat import Timeout, sleep')
                        break
                        
            content = '\n'.join(lines)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print("  - Updated gevent.Timeout usage")
    except Exception as e:
        print(f"  - Error: {e}")


if __name__ == '__main__':
    main()