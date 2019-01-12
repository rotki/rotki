#!/usr/bin/env bash

set -e
set -x

COVERAGE_ARGS='--cov=./ --travis-fold=always'
if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then
    # source terryfy/test_tools.sh;
    COVERAGE_ARGS=''
fi

python -m pytest $COVERAGE_ARGS rotkehlchen/

npm install
npm rebuild zeromq --runtime=electron --target=3.0.0
PYTHON=/usr/bin/python2.7 ./node_modules/.bin/electron-rebuild
npm test

set +e
set +x
