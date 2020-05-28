#!/usr/bin/env bash

set -e
set -x

COVERAGE_ARGS='--cov=./ --travis-fold=always'
if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then
    # source terryfy/test_tools.sh;
    COVERAGE_ARGS=''
fi


if [[ "$TESTS_TYPE" == "UI" ]]; then
    cd frontend/app
    npm ci
    npm run test:integration-ci
else
    python pytestgeventwrapper.py $COVERAGE_ARGS rotkehlchen/tests
fi

set +e
set +x
