#!/usr/bin/env python3
"""Linting tool to ensure all EVM addresses in the codebase are properly checksummed."""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from eth_utils import is_checksum_address, to_checksum_address
from eth_utils.exceptions import ValidationError

if TYPE_CHECKING:
    from collections.abc import Sequence


class AddressViolation(NamedTuple):
    """Represents a non-checksummed address found in the code."""
    file: Path
    line: int
    column: int
    address: str
    checksummed: str
    context: str


def is_valid_evm_address(address: str) -> bool:
    """Check if a string is a valid EVM address format (0x followed by 40 hex chars)."""
    if not address.startswith('0x'):
        return False
    if len(address) != 42:
        return False
    try:
        int(address, base=0)
    except ValueError:
        return False
    else:
        return True


def find_addresses_in_string(content: str) -> list[tuple[str, int]]:
    """Find all potential EVM addresses in a string using regex."""
    # Pattern for 0x followed by 40 hexadecimal characters
    pattern = r'0x[a-fA-F0-9]{40}'
    matches = []

    for match in re.finditer(pattern, content):
        address = match.group(0)
        if is_valid_evm_address(address):
            matches.append((address, match.start()))

    return matches


def check_python_file(file_path: Path) -> list[AddressViolation]:
    """Check a Python file for non-checksummed addresses."""
    violations = []

    try:
        content = file_path.read_text()
        lines = content.splitlines()

        # Parse the AST to find string literals
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # If we can't parse the file, fall back to regex search
            for line_num, line in enumerate(lines, 1):
                for address, col in find_addresses_in_string(line):
                    if not is_checksum_address(address):
                        try:
                            checksummed = to_checksum_address(address)
                            violations.append(AddressViolation(
                                file=file_path,
                                line=line_num,
                                column=col + 1,
                                address=address,
                                checksummed=checksummed,
                                context=line.strip(),
                            ))
                        except ValidationError:
                            # Not a valid address, skip
                            pass
            return violations

        # Walk the AST to find string literals
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                address_str = node.value
                if is_valid_evm_address(address_str) and not is_checksum_address(address_str):
                    try:
                        checksummed = to_checksum_address(address_str)
                        # Find the line content
                        line_content = lines[node.lineno - 1] if node.lineno <= len(lines) else ''

                        violations.append(AddressViolation(
                            file=file_path,
                            line=node.lineno,
                            column=node.col_offset + 1,
                            address=address_str,
                            checksummed=checksummed,
                            context=line_content.strip(),
                        ))
                    except ValidationError:
                        # Not a valid address, skip
                        pass

    except Exception as e:
        print(f'Error processing {file_path}: {e}')

    return violations


def check_json_file(file_path: Path) -> list[AddressViolation]:
    """Check a JSON file for non-checksummed addresses."""
    violations = []

    try:
        content = file_path.read_text()
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
            for address, col in find_addresses_in_string(line):
                if not is_checksum_address(address):
                    try:
                        checksummed = to_checksum_address(address)
                        violations.append(AddressViolation(
                            file=file_path,
                            line=line_num,
                            column=col + 1,
                            address=address,
                            checksummed=checksummed,
                            context=line.strip(),
                        ))
                    except ValidationError:
                        # Not a valid address, skip
                        pass
    except Exception as e:
        print(f'Error processing {file_path}: {e}')

    return violations


def should_skip_file(file_path: Path, skip_tests: bool) -> bool:
    """Determine if a file should be skipped based on configuration."""
    # Skip test files if requested
    if skip_tests and ('test' in file_path.parts or 'tests' in file_path.parts):
        return True

    # Skip node_modules, venv, etc.
    skip_dirs = {'.git', 'node_modules', 'venv', '.venv', '__pycache__', 'build', 'dist'}
    return any(part in skip_dirs for part in file_path.parts)


def main() -> int:
    """Main entry point for the linting tool."""
    parser = argparse.ArgumentParser(
        description='Check for non-checksummed EVM addresses in the codebase',
    )
    parser.add_argument(
        'paths',
        nargs='*',
        default=['.'],
        help='Paths to check (default: current directory)',
    )
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip test files',
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Automatically fix non-checksummed addresses (use with caution)',
    )
    parser.add_argument(
        '--exclude',
        action='append',
        default=[],
        help='Additional patterns to exclude',
    )

    args = parser.parse_args()

    violations: list[AddressViolation] = []
    files_checked = 0

    for path_str in args.paths:
        path = Path(path_str)

        if path.is_file():
            files_to_check: Sequence[Path] = [path]
        else:
            # Find all Python and JSON files
            files_to_check = [*path.rglob('*.py'), *path.rglob('*.json')]

        for file_path in files_to_check:
            if should_skip_file(file_path, args.skip_tests):
                continue

            # Check additional exclude patterns
            if any(pattern in str(file_path) for pattern in args.exclude):
                continue

            files_checked += 1

            if file_path.suffix == '.py':
                file_violations = check_python_file(file_path)
            elif file_path.suffix == '.json':
                file_violations = check_json_file(file_path)
            else:
                continue

            violations.extend(file_violations)

    # Report results
    if len(violations) == 0:
        print(f'✅ Checked {files_checked} files - all EVM addresses are properly checksummed!')
        return 0

    print(f'❌ Found {len(violations)} non-checksummed addresses in {files_checked} files:\n')

    for violation in violations:
        print(f'{violation.file}:{violation.line}:{violation.column}')
        print(f'  Found:     {violation.address}')
        print(f'  Should be: {violation.checksummed}')
        print(f'  Context:   {violation.context}')
        print()

    if args.fix:
        print('--fix option not implemented yet. Please fix addresses manually.')
        print('Consider using string_to_evm_address() for address constants.')

    return 1


if __name__ == '__main__':
    sys.exit(main())
