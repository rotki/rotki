#!/usr/bin/env python
"""Update gevent imports to use compatibility layer

This script updates files to use the centralized compatibility module
instead of directly importing from gevent.
"""
import ast
import re
from pathlib import Path


class GeventImportUpdater(ast.NodeTransformer):
    """AST transformer to update gevent imports"""
    
    def __init__(self):
        self.imports_to_add = set()
        self.modified = False
        
    def visit_ImportFrom(self, node):
        """Update from imports"""
        if node.module == 'gevent':
            for alias in node.names:
                if alias.name in ['sleep', 'spawn']:
                    self.imports_to_add.add(alias.name)
                    self.modified = True
                    return None  # Remove this import
        elif node.module == 'gevent.lock':
            for alias in node.names:
                if alias.name == 'Semaphore':
                    self.imports_to_add.add('Semaphore')
                    self.modified = True
                    return None
        elif node.module == 'gevent.event':
            for alias in node.names:
                if alias.name == 'Event':
                    self.imports_to_add.add('Event')
                    self.modified = True
                    return None
        return node


def update_file(filepath: Path) -> bool:
    """Update a single file to use compat imports"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Skip if already using compat module
        if 'from rotkehlchen.utils.gevent_compat import' in content:
            return False
            
        # Parse and transform AST
        tree = ast.parse(content)
        updater = GeventImportUpdater()
        new_tree = updater.visit(tree)
        
        if not updater.modified:
            return False
            
        # Find where to insert the compat import
        lines = content.split('\n')
        insert_pos = 0
        last_import = 0
        
        for i, line in enumerate(lines):
            if line.startswith(('import ', 'from ')):
                last_import = i
                if 'from rotkehlchen' in line:
                    insert_pos = i + 1
                    
        if insert_pos == 0:
            insert_pos = last_import + 1
            
        # Insert compat import
        imports = sorted(updater.imports_to_add)
        import_line = f"from rotkehlchen.utils.gevent_compat import {', '.join(imports)}"
        lines.insert(insert_pos, import_line)
        
        # Remove old imports
        new_lines = []
        for line in lines:
            if ('from gevent import' in line or 
                'from gevent.lock import Semaphore' in line or
                'from gevent.event import Event' in line):
                # Check if it's one we handle
                if any(imp in line for imp in ['sleep', 'spawn', 'Semaphore', 'Event']):
                    continue
            new_lines.append(line)
            
        new_content = '\n'.join(new_lines)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return True
        
    except Exception as e:
        print(f"Error updating {filepath}: {e}")
        return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update gevent imports to use compat layer')
    parser.add_argument('--file', help='Update single file')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed')
    args = parser.parse_args()
    
    if args.file:
        files = [Path(args.file)]
    else:
        # Files with simple gevent usage from the analysis
        files = [
            'rotkehlchen/exchanges/bitfinex.py',
            'rotkehlchen/chain/ethereum/modules/makerdao/vaults.py', 
            'rotkehlchen/chain/ethereum/modules/makerdao/dsr.py',
            'rotkehlchen/api/rest.py',
        ]
        files = [Path(f) for f in files if Path(f).exists()]
        
    updated = 0
    for filepath in files:
        if args.dry_run:
            print(f"Would update: {filepath}")
        else:
            if update_file(filepath):
                updated += 1
                print(f"Updated: {filepath}")
                
    print(f"\n{'Would update' if args.dry_run else 'Updated'} {updated} files")
    

if __name__ == '__main__':
    main()