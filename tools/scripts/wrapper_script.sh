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


if [[ "$OSTYPE" == "linux-gnu" ]]; then
    # TODO: Add this check also for OSX
    LDD_RESULT=`LD_LIBRARY_PATH=$SCRIPT_DIR ldd $SCRIPT_DIR/resources/app/node_modules/zmq/bin/*/zmq.node | grep "not found" | awk '/ => / {print $1 }'`
    if [[ $LDD_RESULT != '' ]]; then
	echo "Failed to start Rotkehlchen. Dynamic library '$LDD_RESULT' not found";
	exit 1
    fi
    LD_LIBRARY_PATH=$SCRIPT_DIR $SCRIPT_DIR/unwrapped_executable
else
    LD_LIBRARY_PATH=$SCRIPT_DIR $SCRIPT_DIR/rotkehlchen.app/Contents/MacOS/rotkehlchen
fi
