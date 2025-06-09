#!/usr/bin/env python3
"""Rename all async_*.py files to their standard names"""
import os
import shutil
from pathlib import Path

# Base directory
base_dir = Path("/Users/banteg/dev/rotki/rotki/rotkehlchen")

# Find all async files
async_files = list(base_dir.rglob("async_*.py")) + list(base_dir.rglob("*_async.py"))

# Filter out test files and __pycache__
async_files = [f for f in async_files if "__pycache__" not in str(f) and "test" not in str(f)]

print(f"Found {len(async_files)} async files to rename")

# Group by what needs to be done
renames = []
for file in async_files:
    if file.name.startswith("async_"):
        new_name = file.name[6:]  # Remove "async_" prefix
    elif file.name.endswith("_async.py"):
        new_name = file.name[:-9] + ".py"  # Remove "_async" suffix
    else:
        continue
        
    new_path = file.parent / new_name
    
    # Check if target exists
    if new_path.exists():
        print(f"⚠️  Target exists, will replace: {new_path}")
        
    renames.append((file, new_path))

# Perform renames
for old_path, new_path in renames:
    print(f"Renaming: {old_path.relative_to(base_dir)} -> {new_path.name}")
    
    # If target exists, remove it first (we're replacing with async version)
    if new_path.exists():
        os.remove(new_path)
        
    shutil.move(str(old_path), str(new_path))

print(f"\n✅ Renamed {len(renames)} files")

# Also handle special cases
special_renames = [
    (base_dir / "api" / "async_server.py", base_dir / "api" / "server.py"),
    (base_dir / "async_rotkehlchen.py", base_dir / "rotkehlchen.py"),
]

for old_path, new_path in special_renames:
    if old_path.exists():
        print(f"\nSpecial rename: {old_path.name} -> {new_path.name}")
        if new_path.exists():
            print(f"⚠️  Replacing existing {new_path.name}")
            os.remove(new_path)
        shutil.move(str(old_path), str(new_path))