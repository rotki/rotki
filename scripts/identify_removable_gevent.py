#!/usr/bin/env python
"""Identify gevent components that can be safely removed

This script analyzes the codebase to find gevent components that have
complete async replacements and can be removed.
"""
import ast
import os
from collections import defaultdict
from pathlib import Path
from typing import Any


class GeventUsageAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze gevent usage"""
    
    def __init__(self):
        self.gevent_imports = []
        self.gevent_usage = []
        self.classes_using_gevent = []
        
    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            if alias.name.startswith('gevent'):
                self.gevent_imports.append({
                    'module': alias.name,
                    'alias': alias.asname,
                    'line': node.lineno,
                })
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        if node.module and node.module.startswith('gevent'):
            for alias in node.names:
                self.gevent_imports.append({
                    'module': node.module,
                    'name': alias.name,
                    'alias': alias.asname,
                    'line': node.lineno,
                })
        self.generic_visit(node)
        
    def visit_Attribute(self, node: ast.Attribute) -> Any:
        if isinstance(node.value, ast.Name) and node.value.id == 'gevent':
            self.gevent_usage.append({
                'attribute': node.attr,
                'line': node.lineno,
            })
        self.generic_visit(node)


def analyze_file(filepath: Path) -> dict[str, Any]:
    """Analyze a Python file for gevent usage"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = ast.parse(content, filename=str(filepath))
        analyzer = GeventUsageAnalyzer()
        analyzer.visit(tree)
        
        return {
            'file': str(filepath),
            'imports': analyzer.gevent_imports,
            'usage': analyzer.gevent_usage,
            'has_gevent': bool(analyzer.gevent_imports),
        }
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return {
            'file': str(filepath),
            'error': str(e),
            'has_gevent': False,
        }


def find_async_replacements() -> dict[str, str]:
    """Map of gevent components to their async replacements"""
    return {
        'rotkehlchen/api/websockets/notifier.py': 'rotkehlchen/api/websockets/async_notifier.py',
        'rotkehlchen/greenlets/manager.py': 'rotkehlchen/tasks/async_manager.py',
        'rotkehlchen/db/drivers/gevent.py': 'rotkehlchen/db/drivers/async_sqlcipher.py',
        'gevent.spawn': 'asyncio.create_task',
        'gevent.sleep': 'asyncio.sleep',
        'gevent.lock.Semaphore': 'asyncio.Semaphore',
        'gevent.event.Event': 'asyncio.Event',
        'geventwebsocket': 'websockets',
    }


def analyze_removability(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze which files can have gevent removed"""
    replacements = find_async_replacements()
    
    removable = []
    requires_update = []
    complex_migration = []
    
    for result in results:
        if not result.get('has_gevent'):
            continue
            
        filepath = result['file']
        imports = result.get('imports', [])
        
        # Check if this is a file we've already replaced
        if filepath in replacements:
            removable.append({
                'file': filepath,
                'replacement': replacements[filepath],
                'reason': 'Complete async replacement exists',
            })
            continue
            
        # Analyze imports
        simple_imports = True
        for imp in imports:
            module = imp.get('module', '')
            if module in ['gevent', 'gevent.event', 'gevent.lock']:
                # These have simple replacements
                pass
            elif module == 'geventwebsocket':
                # WebSocket has async replacement
                pass
            else:
                simple_imports = False
                
        if simple_imports:
            requires_update.append({
                'file': filepath,
                'imports': imports,
                'action': 'Update imports to use async equivalents',
            })
        else:
            complex_migration.append({
                'file': filepath,
                'imports': imports,
                'action': 'Requires deeper analysis',
            })
            
    return {
        'removable': removable,
        'requires_update': requires_update,
        'complex_migration': complex_migration,
    }


def main():
    """Main entry point"""
    # Find all Python files
    rotki_path = Path('rotkehlchen')
    python_files = list(rotki_path.rglob('*.py'))
    
    # Skip test files for now
    python_files = [f for f in python_files if 'test' not in str(f)]
    
    print(f"Analyzing {len(python_files)} Python files...")
    
    # Analyze each file
    results = []
    for filepath in python_files:
        result = analyze_file(filepath)
        if result.get('has_gevent'):
            results.append(result)
            
    print(f"\nFound {len(results)} files using gevent")
    
    # Analyze removability
    analysis = analyze_removability(results)
    
    print("\n=== REMOVABLE FILES ===")
    for item in analysis['removable']:
        print(f"- {item['file']}")
        print(f"  Replacement: {item['replacement']}")
        print(f"  Reason: {item['reason']}")
        print()
        
    print("\n=== FILES REQUIRING SIMPLE UPDATES ===")
    for item in analysis['requires_update']:
        print(f"- {item['file']}")
        print(f"  Imports to update:")
        for imp in item['imports']:
            print(f"    - {imp.get('module', '')} ({imp.get('name', '')})")
        print()
        
    print("\n=== FILES REQUIRING COMPLEX MIGRATION ===")
    for item in analysis['complex_migration']:
        print(f"- {item['file']}")
        print(f"  Complex imports:")
        for imp in item['imports']:
            print(f"    - {imp.get('module', '')} ({imp.get('name', '')})")
        print()
        
    # Summary
    print("\n=== SUMMARY ===")
    print(f"Removable files: {len(analysis['removable'])}")
    print(f"Simple updates needed: {len(analysis['requires_update'])}")
    print(f"Complex migrations: {len(analysis['complex_migration'])}")
    
    # Feature flag check
    print("\n=== FEATURE FLAG COVERAGE ===")
    print("The following features have async implementations:")
    print("- WebSockets (AsyncRotkiNotifier)")
    print("- Task Manager (AsyncTaskManager)")
    print("- Database (AsyncDBHandler)")
    print("- Endpoints: ping, info, settings, history, transactions, assets")
    print("\nTo remove gevent components, enable feature flags:")
    print("export ASYNC_MODE=full")


if __name__ == '__main__':
    main()