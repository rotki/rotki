#!/usr/bin/env bash

set -e
set -x


if [[ "${TRAVIS_OS_NAME}" == "linux" ]]; then
    sudo apt-get update
    sudo apt-get install -y libssl-dev libzmq5 libzmq3-dev python3-setuptools
    # Unfortunately Ubuntu does not have sqlcipher v4, so we have to compile and install manually
    ./install_deps.sh
    sudo ldconfig
    # export DISPLAY=:99.0;
    # Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
else
    # Thankfully OSX has sqlcipher v4 in homebrew: https://formulae.brew.sh/formula/sqlcipher
    brew update && brew install sqlcipher
    brew install zmq
    brew install nvm
    # Moved to travis.yml since environment was not properly built here
    # git clone https://github.com/MacPython/terryfy.git
    # source terryfy/travis_tools.sh
    # get_python_environment $INSTALL_TYPE $VERSION $VENV
fi

.travis/download_geth.sh
