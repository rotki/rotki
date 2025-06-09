#!/usr/bin/env python3
"""Verify feature parity between Flask resources and FastAPI endpoints"""

import ast
import re
from pathlib import Path
from collections import defaultdict

def get_flask_resources(resources_file):
    """Extract Flask resources and their HTTP methods"""
    resources = {}
    
    with open(resources_file, 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.endswith('Resource'):
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in ['get', 'post', 'put', 'patch', 'delete']:
                    methods.append(item.name.upper())
            
            if methods:
                resources[node.name] = methods
            else:
                # Some resources might not have explicit methods defined in the class
                resources[node.name] = ['UNKNOWN']
    
    return resources


def get_fastapi_endpoints(api_dir):
    """Extract FastAPI endpoints from async files"""
    endpoints = defaultdict(list)
    
    for file in Path(api_dir).glob('async_*.py'):
        with open(file, 'r') as f:
            content = f.read()
        
        # Find all router decorators with their paths and methods
        pattern = r'@router\.(get|post|put|patch|delete)\("([^"]+)"'
        matches = re.findall(pattern, content)
        
        for method, path in matches:
            endpoints[file.name].append((method.upper(), path))
    
    return endpoints


def analyze_parity():
    """Analyze feature parity between Flask and FastAPI"""
    resources_file = Path(__file__).parent.parent / 'rotkehlchen/api/v1/resources.py'
    api_dir = Path(__file__).parent.parent / 'rotkehlchen/api/v1'
    
    # Get Flask resources
    flask_resources = get_flask_resources(resources_file)
    print(f"\n📊 Flask Resources Analysis:")
    print(f"Total resource classes: {len(flask_resources)}")
    
    # Count total HTTP methods in Flask
    total_flask_methods = 0
    for resource, methods in flask_resources.items():
        if 'UNKNOWN' not in methods:
            total_flask_methods += len(methods)
        else:
            total_flask_methods += 1  # Assume at least 1 method
    
    print(f"Total HTTP methods: {total_flask_methods}")
    
    # Show resources with multiple methods
    print("\n🔍 Flask Resources with Multiple HTTP Methods:")
    multi_method_resources = {k: v for k, v in flask_resources.items() if len(v) > 1 and 'UNKNOWN' not in v}
    for resource, methods in sorted(multi_method_resources.items()):
        print(f"  {resource}: {', '.join(methods)} ({len(methods)} methods)")
    
    # Get FastAPI endpoints
    fastapi_endpoints = get_fastapi_endpoints(api_dir)
    print(f"\n📊 FastAPI Endpoints Analysis:")
    
    total_fastapi = 0
    endpoint_breakdown = {}
    
    for file, endpoints in sorted(fastapi_endpoints.items()):
        count = len(endpoints)
        total_fastapi += count
        endpoint_breakdown[file] = count
        print(f"  {file}: {count} endpoints")
    
    print(f"\nTotal FastAPI endpoints: {total_fastapi}")
    
    # Show detailed endpoint paths
    print("\n🔍 FastAPI Endpoint Details:")
    all_paths = defaultdict(list)
    
    for file, endpoints in sorted(fastapi_endpoints.items()):
        for method, path in endpoints:
            all_paths[path].append((method, file))
    
    # Show paths with multiple methods
    print("\nPaths with multiple HTTP methods:")
    for path, methods in sorted(all_paths.items()):
        if len(methods) > 1:
            print(f"  {path}:")
            for method, file in methods:
                print(f"    {method} ({file})")
    
    # Summary
    print(f"\n📈 Summary:")
    print(f"Flask resource classes: {len(flask_resources)}")
    print(f"Flask total HTTP methods (estimated): {total_flask_methods}")
    print(f"FastAPI endpoints: {total_fastapi}")
    print(f"Difference: {total_fastapi - total_flask_methods}")
    
    # Try to map Flask resources to FastAPI files
    print("\n🔗 Potential Mapping (Flask → FastAPI):")
    print("(This is approximate based on naming patterns)")
    
    mappings = {
        'Settings': 'async_base.py',
        'AsyncTasks': 'async_base.py',
        'Exchanges': 'async_exchanges.py',
        'Balances': 'async_balances.py',
        'Blockchain': 'async_blockchain.py',
        'Transaction': 'async_transactions.py',
        'NFT': 'async_nfts.py',
        'Eth2': 'async_eth2.py',
        'Asset': 'async_assets.py, async_assets_extended.py',
        'Database': 'async_database.py',
        'History': 'async_history.py',
        'User': 'async_users.py',
        'Statistics': 'async_statistics.py',
        'Accounting': 'async_accounting.py',
        'Liquity': 'async_defi.py',
        'Loopring': 'async_defi.py',
        'Uniswap': 'async_defi.py',
        'RpcNodes': 'async_utils.py',
        'Messages': 'async_utils.py',
        'Oracle': 'async_utils.py',
    }
    
    for flask_name, methods in sorted(flask_resources.items()):
        fastapi_file = 'Unknown'
        for pattern, file in mappings.items():
            if pattern in flask_name:
                fastapi_file = file
                break
        print(f"  {flask_name} ({len(methods)} methods) → {fastapi_file}")


if __name__ == '__main__':
    analyze_parity()