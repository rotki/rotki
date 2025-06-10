#!/usr/bin/env python
"""Script to convert GlobalDBHandler methods from sync to async"""

import re
from pathlib import Path

def convert_to_async(content: str) -> str:
    """Convert GlobalDBHandler methods to async"""
    
    # Pattern to match method definitions (both static and instance methods)
    method_pattern = re.compile(
        r'^(\s*)(@staticmethod\s+)?def\s+(\w+)\s*\(',
        re.MULTILINE
    )
    
    # Methods that should NOT be converted (dunder methods, already async, etc)
    skip_methods = {
        '__new__', '__init__', '__del__', '__repr__', '__str__',
        'filepath', 'cleanup', '_prioritize_manual_balances_query',
        # Already converted methods:
        'packaged_db_conn', 'get_schema_version', 'get_setting_value',
        'add_setting_value', 'add_asset', 'retrieve_assets', 
        'get_assets_mappings', 'search_assets', 'get_all_asset_data',
        'get_asset_data', 'fetch_underlying_tokens', '_add_underlying_tokens',
        'get_evm_token_identifier', 'check_asset_exists'
    }
    
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        match = method_pattern.match(line)
        
        if match and match.group(3) not in skip_methods:
            indent = match.group(1)
            is_static = match.group(2) is not None
            method_name = match.group(3)
            
            # Check if it's already async
            if 'async def' in line:
                new_lines.append(line)
                i += 1
                continue
                
            # Convert to async
            if is_static:
                new_line = f"{indent}@staticmethod\n{indent}async def {method_name}("
                new_lines.append(f"{indent}@staticmethod")
                # Find the actual def line (might be on next line)
                i += 1
                if i < len(lines) and 'def ' in lines[i]:
                    new_lines.append(lines[i].replace('def ', 'async def '))
                else:
                    new_lines.append(new_line)
            else:
                new_lines.append(line.replace('def ', 'async def '))
        else:
            new_lines.append(line)
        i += 1
    
    content = '\n'.join(new_lines)
    
    # Convert context managers
    content = re.sub(
        r'(\s+)with (self\.conn|GlobalDBHandler\(\)\.conn|conn)\.(read_ctx|write_ctx)\(\) as (\w+):',
        r'\1async with \2.\3() as \4:',
        content
    )
    
    # Convert packaged_db_conn context managers
    content = re.sub(
        r'(\s+)with (GlobalDBHandler\.packaged_db_conn\(\)|GlobalDBHandler\(\)\.packaged_db_conn\(\)) as (\w+):',
        r'\1async with await \2 as \3:',
        content
    )
    
    # Convert cursor operations
    # cursor.execute
    content = re.sub(
        r'(\s+)(\w+)\.execute\(',
        lambda m: f'{m.group(1)}await {m.group(2)}.execute(' if m.group(2) in ['cursor', 'write_cursor', 'read_cursor'] else m.group(0),
        content
    )
    
    # cursor.fetchone/fetchall
    content = re.sub(
        r'(\s+)(\w+)\.(fetchone|fetchall)\(\)',
        lambda m: f'{m.group(1)}await {m.group(2)}.{m.group(3)}()' if m.group(2) in ['cursor', 'write_cursor', 'read_cursor', 'result', 'query'] else m.group(0),
        content
    )
    
    # for entry in cursor
    content = re.sub(
        r'(\s+)for (\w+) in (cursor|write_cursor|read_cursor):',
        r'\1async for \2 in \3:',
        content
    )
    
    # Handle specific method calls that need await
    globaldb_methods = [
        'get_evm_token_identifier', 'add_evm_token_data', 'check_asset_exists',
        'get_evm_token', 'fetch_underlying_tokens', '_add_underlying_tokens',
        'get_asset_data', 'get_all_asset_data', 'add_asset', 'edit_evm_token',
        'edit_user_asset', 'add_user_owned_assets', 'get_assets_with_symbol',
        'get_historical_price', 'get_historical_prices', 'add_historical_prices',
        'add_single_historical_price', 'add_manual_latest_price', 'get_manual_current_price',
        'get_all_manual_latest_prices', 'delete_manual_latest_price', 'get_manual_prices',
        'edit_manual_price', 'delete_manual_price', 'delete_historical_prices',
        'get_historical_price_range', 'get_historical_price_data', 'hard_reset_assets_list',
        'get_user_added_assets', 'resolve_asset', 'get_asset_type', 'asset_id_exists',
        'get_collection_main_asset', 'asset_in_collection', 'get_or_write_abi',
        'get_assets_in_same_collection', 'get_assetid_from_exchange_name',
        'query_asset_mappings_by_type', '_execute_mapping_operation',
        'add_location_asset_mappings', '_location_asset_mapping_null_precheck',
        'update_location_asset_mappings', 'delete_location_asset_mappings',
        'add_counterparty_asset_mappings', 'update_counterparty_asset_mappings',
        'delete_counterparty_asset_mappings', 'get_protocol_for_asset',
        'packaged_db_conn', 'get_schema_version', 'get_setting_value', 'add_setting_value',
        'retrieve_assets', 'get_assets_mappings', 'search_assets'
    ]
    
    for method in globaldb_methods:
        # Handle GlobalDBHandler.method() calls
        content = re.sub(
            rf'(\s+)(?<!await )GlobalDBHandler\.{method}\(',
            rf'\1await GlobalDBHandler.{method}(',
            content
        )
        # Handle GlobalDBHandler().method() calls
        content = re.sub(
            rf'(\s+)(?<!await )GlobalDBHandler\(\)\.{method}\(',
            rf'\1await GlobalDBHandler().{method}(',
            content
        )
    
    # Handle db method calls that might need await
    db_methods = ['get_settings', 'get_ignored_asset_ids']
    for method in db_methods:
        content = re.sub(
            rf'(\s+)(?<!await )(\w+)\.{method}\(',
            lambda m: f'{m.group(1)}await {m.group(2)}.{method}(' if m.group(2) in ['db', 'userdb', 'self'] else m.group(0),
            content
        )
    
    # Handle globaldb_get_setting_value calls
    content = re.sub(
        r'(\s+)(?<!await )globaldb_get_setting_value\(',
        r'\1await globaldb_get_setting_value(',
        content
    )
    
    return content


def main():
    """Main function to convert the GlobalDBHandler file"""
    file_path = Path('/Users/banteg/dev/rotki/rotki/rotkehlchen/globaldb/handler.py')
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Convert to async
    new_content = convert_to_async(content)
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Converted {file_path} to async")


if __name__ == '__main__':
    main()