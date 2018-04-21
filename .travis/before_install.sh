#!/usr/bin/env bash

set -e
set -x

# mkdir -p $HOME/.bin
# export PATH=$PATH:$HOME/.bin

if [[ "${TRAVIS_OS_NAME}" == "linux" ]]; then
    apt-get install -y libsqlcipher-dev libzmq3 libzmq3-dev
    sudo ldconfig
else
    brew update && brew install sqlcipher
    brew install zmq
    git clone https://github.com/MacPython/terryfy.git
    # Avoid printing the lines from the script below.
fi

.travis/download_geth.sh
