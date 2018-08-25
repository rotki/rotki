#!/usr/bin/env bash

# Get SCRIPT_DIR, the directory the script is located even if there are symlinks involved
FILE_SOURCE="${BASH_SOURCE[0]}"
# resolve $FILE_SOURCE until the file is no longer a symlink
while [ -h "$FILE_SOURCE" ]; do
    SCRIPT_DIR="$( cd -P "$( dirname "$FILE_SOURCE" )" && pwd )"
    FILE_SOURCE="$(readlink "$FILE_SOURCE")"
    # if $FILE_SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
    [[ $FILE_SOURCE != /* ]] && FILE_SOURCE="$SCRIPT_DIR/$FILE_SOURCE"
done
SCRIPT_DIR="$( cd -P "$( dirname "$FILE_SOURCE" )" && pwd )"


# This is a remnant from when we had different code during wrapping that prepared the LD_PATH
if [[ "$OSTYPE" == "linux-gnu" ]]; then
    $SCRIPT_DIR/unwrapped_executable
else
    $SCRIPT_DIR/rotkehlchen.app/Contents/MacOS/rotkehlchen
fi
