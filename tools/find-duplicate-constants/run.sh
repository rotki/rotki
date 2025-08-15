#!/bin/bash

# Find duplicate byte constants in the rotki codebase
# This script should be run from the project root or any subdirectory

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Build if needed
if [ ! -f "$SCRIPT_DIR/target/release/find-duplicate-constants" ]; then
    echo "Building find-duplicate-constants tool..."
    cd "$SCRIPT_DIR" && cargo build --release
fi

# Run the tool
cd "$SCRIPT_DIR" && ./target/release/find-duplicate-constants