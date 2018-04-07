#!/usr/bin/env bash

set -e
set -x

# mkdir -p $HOME/.bin
# export PATH=$PATH:$HOME/.bin

if [[ "${TRAVIS_OS_NAME}" == "linux" ]]; then
    apt-get install -y libsqlcipher-dev libzmq-dev libssl-dev
else
    brew update && brew install sqlcipher
    git clone https://github.com/MacPython/terryfy.git
    # Avoid printing the lines from the script below.
fi

.travis/download_geth.sh
