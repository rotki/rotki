#!/usr/bin/env bash

set -ex


INSTALL_OPT=""
PIP_CMD="pip"
if [[ "${TRAVIS_OS_NAME}" == "osx" ]]; then
    # install into user dir on macos to avoid sudo
    # INSTALL_OPT="--user"
    PIP_CMD="pip"
fi

# Temporary pinning of pip < 19 due to pyinstaller bug
# https://github.com/pypa/pip/issues/6163
$PIP_CMD install ${INSTALL_OPT} --upgrade "pip<19.0.0" wheel

if [[ "${TRAVIS_JOB_NAME}" != "Deploy Job" ]]; then
    # For non deploy jobs we install the venv here
    $PIP_CMD install ${INSTALL_OPT} pytest-travis-fold codecov pytest-cov
    $PIP_CMD install ${INSTALL_OPT} -r requirements_dev.txt
    # pip install -e . is needed in order to use pkg_resources in tests
    $PIP_CMD install ${INSTALL_OPT} -e .
fi

$PIP_CMD list --outdated

set +ex
