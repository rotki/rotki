#!/usr/bin/env python3
"""Simple test to verify async infrastructure"""
import asyncio
import tempfile
from pathlib import Path

from rotkehlchen.globaldb.handler import GlobalDBHandler


async def test_globaldb_init():
    """Test that GlobalDB can be initialized in async context"""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        print(f"Testing GlobalDB init with data_dir: {data_dir}")
        
        # This should work in async context
        globaldb = GlobalDBHandler(
            data_dir=data_dir,
            sql_vm_instructions_cb=0,  # No callback for simple test
        )
        print(f"GlobalDB initialized: {globaldb}")
        
        # Test a simple query
        version = await globaldb.get_schema_version()
        print(f"Schema version: {version}")
        
        return True


if __name__ == "__main__":
    # Run in async context
    result = asyncio.run(test_globaldb_init())
    print(f"Test result: {result}")