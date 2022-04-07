#!/usr/bin/env bash

# the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# the temp directory used, within $DIR
# omit the -p parameter to create a temporal directory in the default location
WORK_DIR=$(mktemp -d -p "$DIR")

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


# Only use this option if you can't install libsqlcipher
# through your system's package manager
# NOTE: This will add the lib to /usr/local/lib so make sure
# that ldconfig also searches that directory for libraries by editing
# /etc/ld.so.conf
SQLCIPHER_EXISTS=$(ldconfig -p | grep libsqlcipher)

echo "SQLCIPHER_EXISTS: $SQLCIPHER_EXISTS";
# Installing sqlcipher if it wasn't previously installed or user provided flag --upgrade
if [[ $SQLCIPHER_EXISTS == "" || $1 == "--upgrade" ]]; then
    echo "Downloading and compiling sqlcipher";
    # Go into the directory and build sqlcipher
    cd "$WORK_DIR" || exit 1
    git clone https://github.com/sqlcipher/sqlcipher
    cd sqlcipher || exit 1
    git checkout v4.5.0
    ./configure \
	--enable-tempstore=yes \
	CFLAGS="-DSQLITE_HAS_CODEC -DSQLITE_ENABLE_FTS3 -DSQLITE_ENABLE_FTS3_PARENTHESIS" \
	LDFLAGS="-lcrypto"
    make
    sudo make install

    cd "$DIR" || exit 1
fi
