#!/usr/bin/env python
"""Script to fix remaining async issues in GlobalDBHandler"""

import re
from pathlib import Path

def fix_remaining_async(content: str) -> str:
    """Fix remaining async issues"""
    
    # Fix executemany
    content = re.sub(
        r'(\s+)(\w+)\.executemany\(',
        lambda m: f'{m.group(1)}await {m.group(2)}.executemany(' if m.group(2) in ['cursor', 'write_cursor', 'read_cursor'] else m.group(0),
        content
    )
    
    # Fix cursor.execute(...).fetchone() patterns
    content = re.sub(
        r'= (\w+)\.execute\((.*?)\)\.fetchone\(\)',
        lambda m: f'= (await {m.group(1)}.execute({m.group(2)})).fetchone()' if m.group(1) in ['cursor', 'write_cursor', 'read_cursor'] else m.group(0),
        content,
        flags=re.DOTALL
    )
    
    # Fix cursor.execute(...).fetchall() patterns
    content = re.sub(
        r'= (\w+)\.execute\((.*?)\)\.fetchall\(\)',
        lambda m: f'= (await {m.group(1)}.execute({m.group(2)})).fetchall()' if m.group(1) in ['cursor', 'write_cursor', 'read_cursor'] else m.group(0),
        content,
        flags=re.DOTALL
    )
    
    # Fix return cursor.execute(...).fetchone/fetchall patterns
    content = re.sub(
        r'return (\w+)\.execute\((.*?)\)\.(fetchone|fetchall)\(\)',
        lambda m: f'return (await {m.group(1)}.execute({m.group(2)})).{m.group(3)}()' if m.group(1) in ['cursor', 'write_cursor', 'read_cursor'] else m.group(0),
        content,
        flags=re.DOTALL
    )
    
    # Fix if cursor.execute(...).fetchone() patterns
    content = re.sub(
        r'if (\w+)\.execute\((.*?)\)\.fetchone\(\)',
        lambda m: f'if (await {m.group(1)}.execute({m.group(2)})).fetchone()' if m.group(1) in ['cursor', 'write_cursor', 'read_cursor'] else m.group(0),
        content,
        flags=re.DOTALL
    )
    
    # Fix transaction lock patterns
    content = re.sub(
        r'(\s+)with (self\.conn|conn)\.(critical_section_and_transaction_lock|transaction_lock)\(\):',
        r'\1async with \2.\3():',
        content
    )
    
    # Fix specific cases where await is needed before fetchone/fetchall
    content = re.sub(
        r'result = await (query|result)\.(fetchone|fetchall)\(\)',
        r'result = await \1.\2()',
        content
    )
    
    # Fix cases where we have await cursor.execute but then .fetchone() without await
    content = re.sub(
        r'(await \w+\.execute\([^)]+\))\.fetchone\(\)',
        r'(await \1.fetchone())',
        content
    )
    
    content = re.sub(
        r'(await \w+\.execute\([^)]+\))\.fetchall\(\)',
        r'(await \1.fetchall())',
        content
    )
    
    return content


def main():
    """Main function to fix remaining async issues"""
    file_path = Path('/Users/banteg/dev/rotki/rotki/rotkehlchen/globaldb/handler.py')
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix remaining async issues
    new_content = fix_remaining_async(content)
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print(f"Fixed remaining async issues in {file_path}")


if __name__ == '__main__':
    main()