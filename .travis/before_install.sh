#!/usr/bin/env bash

set -e
set -x


if [[ "${TRAVIS_OS_NAME}" == "linux" ]]; then
    sudo apt-get update
    sudo apt-get install -y libsqlcipher-dev libzmq5 libzmq3-dev python3-setuptools
    sudo ldconfig
    # export DISPLAY=:99.0;
    # Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
else
    brew update && brew install sqlcipher
    brew install zmq
    # Moved to travis.yml since environment was not properly built here
    # git clone https://github.com/MacPython/terryfy.git
    # source terryfy/travis_tools.sh
    # get_python_environment $INSTALL_TYPE $VERSION $VENV
fi

.travis/download_geth.sh
