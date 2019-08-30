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
$PIP_CMD install ${INSTALL_OPT} pytest-travis-fold codecov pytest-cov
$PIP_CMD install ${INSTALL_OPT} -r requirements_dev.txt
$PIP_CMD install ${INSTALL_OPT} -e .

$PIP_CMD list --outdated

set +ex
