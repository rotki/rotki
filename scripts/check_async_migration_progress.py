#!/usr/bin/env python
"""Check the progress of the gevent to asyncio migration

This script analyzes the codebase to show:
1. Migration progress by module
2. Remaining work
3. Feature flag usage
4. Async endpoint implementation status
"""
import ast
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'


def check_file_imports(filepath: Path) -> dict[str, Any]:
    """Check a Python file for gevent/async patterns"""
    result = {
        'uses_gevent_direct': False,
        'uses_compat_layer': False,
        'uses_asyncio': False,
        'has_async_functions': False,
        'has_sync_functions': False,
        'gevent_imports': [],
        'compat_imports': [],
        'asyncio_imports': [],
        'async_functions': [],
        'sync_functions': [],
        'feature_flags': [],
    }
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Check for direct gevent imports
        gevent_pattern = r'(?:from gevent|import gevent)'
        if re.search(gevent_pattern, content):
            result['uses_gevent_direct'] = True
            result['gevent_imports'] = re.findall(r'from gevent[.\w]* import [\w, ]+|import gevent[.\w]*', content)
            
        # Check for compat layer usage
        if 'gevent_compat' in content:
            result['uses_compat_layer'] = True
            result['compat_imports'] = re.findall(r'from rotkehlchen\.utils\.gevent_compat import [\w, ]+', content)
            
        # Check for asyncio usage
        asyncio_pattern = r'(?:import asyncio|from asyncio|async def|await )'
        if re.search(asyncio_pattern, content):
            result['uses_asyncio'] = True
            result['asyncio_imports'] = re.findall(r'from asyncio[.\w]* import [\w, ]+|import asyncio[.\w]*', content)
            
        # Parse AST for function analysis
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    result['has_async_functions'] = True
                    result['async_functions'].append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    result['has_sync_functions'] = True
                    result['sync_functions'].append(node.name)
                    
        except SyntaxError:
            pass
            
        # Check for feature flag usage
        if 'AsyncFeature' in content:
            result['feature_flags'] = re.findall(r'AsyncFeature\.(\w+)', content)
            
    except Exception as e:
        result['error'] = str(e)
        
    return result


def analyze_module(module_path: Path) -> dict[str, Any]:
    """Analyze a module directory"""
    stats = {
        'total_files': 0,
        'gevent_direct': 0,
        'using_compat': 0,
        'using_asyncio': 0,
        'fully_async': 0,
        'mixed_async_sync': 0,
        'files': {},
    }
    
    for py_file in module_path.rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue
            
        stats['total_files'] += 1
        file_info = check_file_imports(py_file)
        rel_path = py_file.relative_to(module_path.parent.parent)
        stats['files'][str(rel_path)] = file_info
        
        if file_info['uses_gevent_direct']:
            stats['gevent_direct'] += 1
        if file_info['uses_compat_layer']:
            stats['using_compat'] += 1
        if file_info['uses_asyncio']:
            stats['using_asyncio'] += 1
        if file_info['has_async_functions'] and not file_info['has_sync_functions']:
            stats['fully_async'] += 1
        elif file_info['has_async_functions'] and file_info['has_sync_functions']:
            stats['mixed_async_sync'] += 1
            
    return stats


def check_endpoint_migration() -> dict[str, Any]:
    """Check which endpoints have been migrated to FastAPI"""
    project_root = Path(__file__).parent.parent
    v1_dir = project_root / 'rotkehlchen' / 'api' / 'v1'
    
    # Find all Flask resources
    flask_endpoints = set()
    resources_file = v1_dir / 'resources.py'
    if resources_file.exists():
        with open(resources_file, 'r') as f:
            content = f.read()
            # Extract resource class names
            flask_endpoints = set(re.findall(r'class (\w+Resource)\(', content))
    
    # Find all FastAPI routers
    fastapi_endpoints = set()
    async_files = list(v1_dir.glob('async_*.py'))
    for async_file in async_files:
        with open(async_file, 'r') as f:
            content = f.read()
            # Look for router definitions
            if 'router = APIRouter' in content:
                fastapi_endpoints.add(async_file.stem)
                
    return {
        'flask_endpoints': len(flask_endpoints),
        'fastapi_endpoints': len(fastapi_endpoints),
        'migration_percentage': (len(fastapi_endpoints) / len(flask_endpoints) * 100) if flask_endpoints else 0,
        'async_files': [f.name for f in async_files],
    }


def print_progress_bar(percentage: float, width: int = 50) -> str:
    """Create a progress bar string"""
    filled = int(width * percentage / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f'[{bar}] {percentage:.1f}%'


def main():
    """Main function to check migration progress"""
    project_root = Path(__file__).parent.parent
    
    print(f"\n{BOLD}🚀 Rotki Async Migration Progress Report{RESET}")
    print("=" * 80)
    
    # Key modules to analyze
    modules = {
        'API': project_root / 'rotkehlchen' / 'api',
        'Tasks': project_root / 'rotkehlchen' / 'tasks',
        'Chain': project_root / 'rotkehlchen' / 'chain',
        'Exchanges': project_root / 'rotkehlchen' / 'exchanges',
        'Database': project_root / 'rotkehlchen' / 'db',
        'Greenlets': project_root / 'rotkehlchen' / 'greenlets',
    }
    
    overall_stats = {
        'total_files': 0,
        'migrated_to_compat': 0,
        'using_asyncio': 0,
        'still_gevent_direct': 0,
    }
    
    module_results = {}
    
    # Analyze each module
    for module_name, module_path in modules.items():
        if module_path.exists():
            stats = analyze_module(module_path)
            module_results[module_name] = stats
            
            overall_stats['total_files'] += stats['total_files']
            overall_stats['migrated_to_compat'] += stats['using_compat']
            overall_stats['using_asyncio'] += stats['using_asyncio']
            overall_stats['still_gevent_direct'] += stats['gevent_direct']
    
    # Print module-by-module progress
    print(f"\n{BOLD}📊 Module Migration Status:{RESET}")
    for module_name, stats in module_results.items():
        total = stats['total_files']
        if total == 0:
            continue
            
        compat_pct = (stats['using_compat'] / total * 100) if total else 0
        async_pct = (stats['using_asyncio'] / total * 100) if total else 0
        gevent_pct = (stats['gevent_direct'] / total * 100) if total else 0
        
        print(f"\n{BLUE}{module_name}:{RESET}")
        print(f"  Total files: {total}")
        print(f"  {GREEN}Using compat layer:{RESET} {stats['using_compat']:3d} files {print_progress_bar(compat_pct, 30)}")
        print(f"  {YELLOW}Using asyncio:{RESET}      {stats['using_asyncio']:3d} files {print_progress_bar(async_pct, 30)}")
        print(f"  {RED}Direct gevent:{RESET}      {stats['gevent_direct']:3d} files {print_progress_bar(gevent_pct, 30)}")
        
        if stats['fully_async'] > 0:
            print(f"  {GREEN}Fully async:{RESET}        {stats['fully_async']:3d} files")
        if stats['mixed_async_sync'] > 0:
            print(f"  {YELLOW}Mixed async/sync:{RESET}   {stats['mixed_async_sync']:3d} files")
    
    # Overall progress
    print(f"\n{BOLD}📈 Overall Progress:{RESET}")
    total = overall_stats['total_files']
    if total > 0:
        compat_pct = (overall_stats['migrated_to_compat'] / total * 100)
        async_pct = (overall_stats['using_asyncio'] / total * 100)
        remaining_pct = (overall_stats['still_gevent_direct'] / total * 100)
        
        print(f"\nTotal Python files analyzed: {total}")
        print(f"\n{GREEN}Migrated to compat layer:{RESET} {overall_stats['migrated_to_compat']:3d} files")
        print(print_progress_bar(compat_pct))
        print(f"\n{YELLOW}Using asyncio:{RESET}            {overall_stats['using_asyncio']:3d} files")
        print(print_progress_bar(async_pct))
        print(f"\n{RED}Still using gevent directly:{RESET} {overall_stats['still_gevent_direct']:3d} files")
        print(print_progress_bar(remaining_pct))
    
    # Check endpoint migration
    print(f"\n{BOLD}🌐 API Endpoint Migration:{RESET}")
    endpoint_stats = check_endpoint_migration()
    print(f"Flask endpoints: {endpoint_stats['flask_endpoints']}")
    print(f"FastAPI endpoints: {endpoint_stats['fastapi_endpoints']}")
    print(f"Migration progress: {print_progress_bar(endpoint_stats['migration_percentage'])}")
    if endpoint_stats['async_files']:
        print(f"Async endpoint files: {', '.join(endpoint_stats['async_files'])}")
    
    # Find files still needing attention
    print(f"\n{BOLD}⚠️  Files Still Using Direct Gevent:{RESET}")
    critical_files = []
    for module_name, stats in module_results.items():
        for filepath, file_info in stats['files'].items():
            if file_info['uses_gevent_direct'] and not file_info['uses_compat_layer']:
                critical_files.append(filepath)
    
    if critical_files:
        # Group by directory
        by_dir = defaultdict(list)
        for filepath in sorted(critical_files):
            parts = Path(filepath).parts
            if len(parts) > 2:
                dir_key = '/'.join(parts[:3])
            else:
                dir_key = '/'.join(parts[:2])
            by_dir[dir_key].append(filepath)
        
        for dir_key, files in sorted(by_dir.items()):
            print(f"\n  {YELLOW}{dir_key}:{RESET}")
            for filepath in files[:5]:  # Show max 5 per directory
                print(f"    - {filepath}")
            if len(files) > 5:
                print(f"    ... and {len(files) - 5} more")
    else:
        print(f"  {GREEN}None! All files use the compat layer.{RESET}")
    
    # Feature flag usage
    print(f"\n{BOLD}🚩 Feature Flag Usage:{RESET}")
    feature_flags = defaultdict(int)
    for module_name, stats in module_results.items():
        for filepath, file_info in stats['files'].items():
            for flag in file_info['feature_flags']:
                feature_flags[flag] += 1
    
    if feature_flags:
        for flag, count in sorted(feature_flags.items()):
            print(f"  AsyncFeature.{flag}: {count} files")
    else:
        print("  No feature flags found in use yet")
    
    # Summary and next steps
    print(f"\n{BOLD}📋 Summary:{RESET}")
    if overall_stats['still_gevent_direct'] == 0:
        print(f"  {GREEN}✅ All files migrated to compat layer!{RESET}")
    else:
        print(f"  {YELLOW}⏳ {overall_stats['still_gevent_direct']} files still need migration{RESET}")
    
    if endpoint_stats['migration_percentage'] < 100:
        print(f"  {YELLOW}⏳ {endpoint_stats['flask_endpoints'] - endpoint_stats['fastapi_endpoints']} endpoints need FastAPI migration{RESET}")
    
    print(f"\n{BOLD}🎯 Next Steps:{RESET}")
    if overall_stats['still_gevent_direct'] > 0:
        print("  1. Complete migration of remaining files to compat layer")
    print("  2. Implement AsyncTaskManager to replace GreenletManager")
    print("  3. Create async database driver")
    print("  4. Migrate more endpoints to FastAPI")
    print("  5. Enable feature flags and convert code to async/await")
    print("  6. Remove gevent dependencies")
    
    print("\n" + "=" * 80)
    print(f"{GREEN}Migration is {compat_pct:.1f}% complete!{RESET}\n")


if __name__ == '__main__':
    main()