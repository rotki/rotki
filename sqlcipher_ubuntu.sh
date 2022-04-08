#!/usr/bin/env bash

# the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# the temp directory used, within $DIR
# omit the -p parameter to create a temporal directory in the default location
WORK_DIR=$(mktemp -d -p "$DIR")
SQLCIPHER_DIR="$DIR/.sqlcipher"

# check if tmp dir was created
if [[ ! "$WORK_DIR" || ! -d "$WORK_DIR" ]]; then
  echo "Could not create temp dir"
  exit 1
fi

# deletes the temp directory
function cleanup {
  rm -rf "$WORK_DIR"
  echo "Deleted temp working directory $WORK_DIR"
}

# register the cleanup function to be called on the EXIT signal
trap cleanup EXIT

# check if SQLCIPHER_DIR exists
[ -d "$SQLCIPHER_DIR" ] && SQLCIPHER_EXISTS=true || SQLCIPHER_EXISTS=false

# Ask user what to do if directory exists
if [[ $SQLCIPHER_EXISTS == true ]]; then
    echo "Looks like you already have sqlcipher installed (in $SQLCIPHER_DIR directory). Would you like to reinstall it (yes/no)?"
    read -r WANTS_TO_REINSTALL
    if [[ $WANTS_TO_REINSTALL == "yes" ]]; then
      sudo rm -r "$SQLCIPHER_DIR"
    else
      exit 1
    fi
fi

echo "Downloading and compiling sqlcipher";
# Go into the directory and build sqlcipher
cd "$WORK_DIR" || exit 1
git clone https://github.com/sqlcipher/sqlcipher
cd sqlcipher || exit 1
git checkout v4.5.0
./configure \
--enable-tempstore=yes \
CFLAGS="-DSQLITE_HAS_CODEC -DSQLITE_ENABLE_FTS3 -DSQLITE_ENABLE_FTS3_PARENTHESIS" \
LDFLAGS="-lcrypto" \
prefix="$SQLCIPHER_DIR"
make
sudo make install

cd "$DIR" || exit 1

# We need to set LD_LIBRARY_PATH to use local version of sqlcipher
echo "LD_LIBRARY_PATH=$SQLCIPHER_DIR/lib" > "$DIR/sqlcipher.env"