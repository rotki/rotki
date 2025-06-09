#!/usr/bin/env python
"""Verify which files still use direct gevent imports"""
import os
import re
from pathlib import Path

def check_file_for_gevent(filepath):
    """Check if a file has direct gevent imports"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Skip if it's the compat file itself
        if 'gevent_compat.py' in str(filepath):
            return None
            
        # Check for direct gevent imports
        patterns = [
            r'^from gevent import',
            r'^import gevent',
            r'from gevent\.',
            r'gevent\.'
        ]
        
        issues = []
        for i, line in enumerate(content.split('\n'), 1):
            for pattern in patterns:
                if re.search(pattern, line):
                    # Check if it's importing from compat
                    if 'gevent_compat' not in line:
                        issues.append((i, line.strip()))
        
        return issues if issues else None
    except Exception as e:
        return f"Error: {e}"

def main():
    """Main function"""
    project_root = Path(__file__).parent.parent
    
    # Files that are expected to still use gevent directly
    expected_gevent_files = {
        'greenlets/manager.py',  # Will be replaced with AsyncTaskManager
        'db/drivers/gevent.py',  # Will be replaced with async driver
        '__main__.py',  # Monkey patching, TODO comment present
        'pytestgeventwrapper.py',  # Test wrapper needs monkey patching
        'tools/profiling/cpu.py',  # Profiling tool, specific to gevent
        'tools/assets_database/main.py',  # Has monkey patching
        'rotkehlchen_mock/__main__.py',  # Mock server has monkey patching
        'scripts/benchmark_async_migration.py',  # Benchmarking script
    }
    
    unexpected_files = []
    expected_files = []
    migrated_files = []
    
    # Walk through all Python files
    for root, dirs, files in os.walk(project_root):
        # Skip __pycache__ and .git directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.venv', 'venv']]
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                relative_path = filepath.relative_to(project_root)
                
                issues = check_file_for_gevent(filepath)
                
                if issues:
                    # Check if this was expected
                    is_expected = False
                    for expected in expected_gevent_files:
                        if str(relative_path).endswith(expected):
                            is_expected = True
                            expected_files.append(str(relative_path))
                            break
                    
                    if not is_expected:
                        unexpected_files.append((str(relative_path), issues))
                else:
                    # Check if file imports from compat
                    try:
                        with open(filepath, 'r') as f:
                            if 'gevent_compat' in f.read():
                                migrated_files.append(str(relative_path))
                    except:
                        pass
    
    # Print results
    print("=" * 80)
    print("GEVENT MIGRATION STATUS REPORT")
    print("=" * 80)
    
    print(f"\n✅ Files successfully migrated to compat layer: {len(migrated_files)}")
    if len(migrated_files) < 10:
        for f in sorted(migrated_files):
            print(f"   - {f}")
    else:
        print(f"   (showing first 10 of {len(migrated_files)})")
        for f in sorted(migrated_files)[:10]:
            print(f"   - {f}")
    
    print(f"\n✅ Expected files still using gevent directly: {len(expected_files)}")
    for f in sorted(expected_files):
        print(f"   - {f}")
    
    if unexpected_files:
        print(f"\n❌ UNEXPECTED files still using gevent directly: {len(unexpected_files)}")
        for filepath, issues in unexpected_files:
            print(f"\n   {filepath}:")
            for line_no, line in issues[:3]:  # Show first 3 issues
                print(f"      Line {line_no}: {line}")
            if len(issues) > 3:
                print(f"      ... and {len(issues) - 3} more")
    else:
        print("\n✅ No unexpected files using gevent directly!")
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"- Total migrated files: {len(migrated_files)}")
    print(f"- Expected gevent files: {len(expected_files)}")
    print(f"- Unexpected gevent files: {len(unexpected_files)}")
    print(f"- Migration {'COMPLETE' if not unexpected_files else 'IN PROGRESS'}")
    print("=" * 80)

if __name__ == '__main__':
    main()