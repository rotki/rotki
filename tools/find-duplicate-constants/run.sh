#!/usr/bin/env bash
set -euo pipefail

# Find duplicate byte constants in the rotki codebase
# This script should be run from the project root or any subdirectory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Build if needed
BIN="$SCRIPT_DIR/target/release/find-duplicate-constants"
if [ ! -f "$BIN" ]; then
    echo "Building find-duplicate-constants tool..."
    cargo build --release
fi

# Run the tool
"$BIN"
