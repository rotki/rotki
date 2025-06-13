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


def fix_addresses_in_file(file_path: Path, violations: list[AddressViolation]) -> bool:
    """Fix non-checksummed addresses in a file."""
    if not violations:
        return True

    try:
        content = file_path.read_text()

        # Sort violations by position in reverse order to avoid offset issues
        sorted_violations = sorted(violations, key=lambda v: (v.line, v.column), reverse=True)

        lines = content.splitlines(keepends=True)

        for violation in sorted_violations:
            # Find the line (0-indexed)
            line_idx = violation.line - 1
            if line_idx >= len(lines):
                continue

            line = lines[line_idx]
            # Replace the address in the line
            # We need to be careful to only replace the exact occurrence
            col_idx = violation.column - 1

            # Verify the address is at the expected position
            if line[col_idx:col_idx + len(violation.address)] == violation.address:
                lines[line_idx] = (
                    line[:col_idx] +
                    violation.checksummed +
                    line[col_idx + len(violation.address):]
                )
            else:
                # Fallback: replace the address anywhere in the line
                lines[line_idx] = line.replace(violation.address, violation.checksummed)

        # Write back the fixed content
        file_path.write_text(''.join(lines))

    except Exception as e:
        print(f'Error fixing {file_path}: {e}')
        return False
    else:
        return True


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
        help='Automatically fix non-checksummed addresses',
    )
    parser.add_argument(
        '--exclude',
        action='append',
        default=[],
        help='Additional patterns to exclude',
    )

    args = parser.parse_args()

    violations_by_file: dict[Path, list[AddressViolation]] = {}
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

            if file_violations:
                violations_by_file[file_path] = file_violations

    # Get total violations count
    total_violations = sum(len(v) for v in violations_by_file.values())

    # Report results
    if total_violations == 0:
        print(f'✅ Checked {files_checked} files - all EVM addresses are properly checksummed!')
        return 0

    if args.fix:
        # Fix the violations
        print(
            f'🔧 Fixing {total_violations} non-checksummed addresses '
            f'in {len(violations_by_file)} files...\n',
        )

        fixed_count = 0
        for file_path, violations in violations_by_file.items():
            if fix_addresses_in_file(file_path, violations):
                fixed_count += len(violations)
                print(f'✅ Fixed {len(violations)} addresses in {file_path}')
            else:
                print(f'❌ Failed to fix addresses in {file_path}')

        if fixed_count == total_violations:
            print(f'\n✅ Successfully fixed all {fixed_count} addresses!')
            return 0
        else:
            print(f'\n⚠️  Fixed {fixed_count}/{total_violations} addresses')
            return 1
    else:
        # Just report the violations
        print(f'❌ Found {total_violations} non-checksummed addresses in {files_checked} files:\n')

        for violations in violations_by_file.values():
            for violation in violations:
                print(f'{violation.file}:{violation.line}:{violation.column}')
                print(f'  Found:     {violation.address}')
                print(f'  Should be: {violation.checksummed}')
                print(f'  Context:   {violation.context}')
                print()

        print('💡 Run with --fix to automatically fix these addresses')

    return 1


if __name__ == '__main__':
    sys.exit(main())
