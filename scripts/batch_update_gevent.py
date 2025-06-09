#!/usr/bin/env python
"""Batch update gevent imports to use compatibility layer"""
import re
from pathlib import Path


def update_simple_gevent_imports(filepath: Path) -> tuple[bool, list[str]]:
    """Update a file that uses simple gevent imports"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Skip if already using compat module
        if 'from rotkehlchen.utils.gevent_compat import' in content:
            return False, []
            
        original_content = content
        changes = []
        imports_needed = set()
        
        # Find what gevent features are used
        if re.search(r'\bgevent\.sleep\b', content):
            imports_needed.add('sleep')
            content = re.sub(r'\bgevent\.sleep\b', 'sleep', content)
            changes.append("Replaced gevent.sleep with sleep")
            
        if re.search(r'\bgevent\.spawn\b', content):
            imports_needed.add('spawn')
            content = re.sub(r'\bgevent\.spawn\b', 'spawn', content)
            changes.append("Replaced gevent.spawn with spawn")
            
        if re.search(r'\bgevent\.killall\b', content):
            imports_needed.add('kill_all')
            content = re.sub(r'\bgevent\.killall\b', 'kill_all', content)
            changes.append("Replaced gevent.killall with kill_all")
            
        # Check for Semaphore usage
        if 'from gevent.lock import Semaphore' in content:
            imports_needed.add('Semaphore')
            content = content.replace('from gevent.lock import Semaphore\n', '')
            changes.append("Removed gevent.lock.Semaphore import")
            
        # Check for Event usage
        if 'from gevent.event import Event' in content:
            imports_needed.add('Event')
            content = content.replace('from gevent.event import Event\n', '')
            changes.append("Removed gevent.event.Event import")
            
        if not imports_needed and 'import gevent' not in content:
            return False, []
            
        # Find where to insert compat import
        lines = content.split('\n')
        insert_pos = 0
        import_gevent_line = -1
        
        for i, line in enumerate(lines):
            if line.strip() == 'import gevent':
                import_gevent_line = i
            elif line.startswith(('import ', 'from ')) and 'gevent' not in line:
                if 'rotkehlchen' in line:
                    insert_pos = i + 1
                    
        # If we found import gevent and have replacements, remove it
        if import_gevent_line >= 0 and imports_needed:
            lines.pop(import_gevent_line)
            if insert_pos > import_gevent_line:
                insert_pos -= 1
            changes.append("Removed import gevent")
            
        # Add compat import if we have imports needed
        if imports_needed:
            imports = sorted(imports_needed)
            import_line = f"from rotkehlchen.utils.gevent_compat import {', '.join(imports)}"
            
            if insert_pos == 0:
                # Find first non-comment, non-docstring line after imports
                in_docstring = False
                for i, line in enumerate(lines):
                    if line.strip().startswith('"""') or line.strip().startswith("'''"):
                        in_docstring = not in_docstring
                    elif not in_docstring and not line.strip().startswith('#') and line.strip():
                        if line.startswith(('import ', 'from ')):
                            insert_pos = i + 1
                        else:
                            break
                            
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
    """Update multiple files"""
    # List of files to update
    files_to_update = [
        'rotkehlchen/exchanges/bybit.py',
        'rotkehlchen/exchanges/kraken.py',
        'rotkehlchen/exchanges/poloniex.py',
        'rotkehlchen/exchanges/gemini.py',
        'rotkehlchen/exchanges/coinbase.py',
        'rotkehlchen/exchanges/kucoin.py',
        'rotkehlchen/exchanges/bitpanda.py',
        'rotkehlchen/exchanges/independentreserve.py',
        'rotkehlchen/exchanges/binance.py',
        'rotkehlchen/utils/network.py',
        'rotkehlchen/chain/substrate/manager.py',
        'rotkehlchen/chain/zksync_lite/manager.py',
        'rotkehlchen/chain/ethereum/graph.py',
        'rotkehlchen/chain/ethereum/modules/eth2/eth2.py',
        'rotkehlchen/chain/evm/decoding/decoder.py',
        'rotkehlchen/externalapis/blockscout.py',
        'rotkehlchen/externalapis/cryptocompare.py',
        'rotkehlchen/externalapis/opensea.py',
        'rotkehlchen/externalapis/etherscan.py',
        'rotkehlchen/externalapis/beaconchain/service.py',
    ]
    
    print(f"Updating {len(files_to_update)} files...")
    updated_count = 0
    
    for filepath in files_to_update:
        path = Path(filepath)
        if not path.exists():
            print(f"File not found: {filepath}")
            continue
            
        updated, changes = update_simple_gevent_imports(path)
        if updated:
            updated_count += 1
            print(f"\n✓ Updated {filepath}:")
            for change in changes:
                print(f"  - {change}")
        else:
            if changes:  # Error occurred
                print(f"\n✗ Failed to update {filepath}:")
                for change in changes:
                    print(f"  - {change}")
                    
    print(f"\nSuccessfully updated {updated_count} files")


if __name__ == '__main__':
    main()