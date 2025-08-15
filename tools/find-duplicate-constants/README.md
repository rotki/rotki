# Find Duplicate Constants Tool

A fast Rust-based tool to find duplicate byte constants in the rotki Python codebase.

## Purpose

This tool scans all Python files in the rotki project to find byte constants (like `b'...'`) that have the same value but are defined multiple times with different names. This helps identify opportunities to consolidate duplicate constants.

## Installation

From the `tools/find-duplicate-constants` directory:

```bash
cargo build --release
```

## Usage

From the `tools/find-duplicate-constants` directory:

```bash
./target/release/find-duplicate-constants
```

Or using cargo:

```bash
cargo run --release
```

## Output

The tool will:
1. Scan all Python files in the project (excluding virtual environments and build directories)
2. Extract all byte constants defined with patterns like `CONSTANT_NAME: Final = b'...'`
3. Group constants by their byte value
4. Report any duplicates found, showing:
   - The byte value in both raw and hex format
   - All file locations and constant names for each duplicate

## Exit Codes

- `0`: No duplicates found
- `1`: Duplicates found (useful for CI/CD integration)

## Example Output

```
================================================================================
DUPLICATE FOUND: 2 occurrences
Byte value: [249, 67, 207, 16, ...]
Hex representation: f943cf10ef4d1e32...
--------------------------------------------------------------------------------
  rotkehlchen/chain/optimism/modules/walletconnect/decoder.py:39 - STAKING_DEPOSIT
  rotkehlchen/chain/evm/decoding/curve/lend/constants.py:13 - LEVERAGE_ZAP_DEPOSIT_TOPIC
```

## Integration with CI

This tool can be integrated into CI pipelines as a lint step to prevent introduction of duplicate constants.