#!/usr/bin/env python3
"""Wrapper script to integrate EVM address checksum checking into the lint workflow."""

import subprocess  # noqa: S404
import sys
from pathlib import Path

# Paths to check - matching the Makefile's COMMON_LINT_PATHS
PATHS_TO_CHECK = [
    'rotkehlchen/',
    'rotkehlchen_mock/',
    'package.py',
    'docs/conf.py',
    'packaging/docker/entrypoint.py',
    'tools/',
]

# Additional paths to exclude
EXCLUDE_PATTERNS = [
]


def main() -> None:
    """Run the checksum linting tool on the codebase."""
    script_path = Path(__file__).parent / 'checksum_evm_addresses.py'

    cmd = [sys.executable, str(script_path)]

    # Add paths to check
    cmd.extend(PATHS_TO_CHECK)

    # Add exclusions
    for pattern in EXCLUDE_PATTERNS:
        cmd.extend(['--exclude', pattern])

    # Skip test files by default (can be overridden with command line args)
    if '--include-tests' not in sys.argv:
        cmd.append('--skip-tests')

    # Pass through any additional arguments
    extra_args = [arg for arg in sys.argv[1:] if arg != '--include-tests']
    cmd.extend(extra_args)

    # Run the linting tool
    result = subprocess.run(cmd, check=False)  # noqa: S603

    # Exit with the same code as the linting tool
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
