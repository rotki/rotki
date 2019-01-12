#!/usr/bin/env bash

set -ex


INSTALL_OPT=""
PIP_CMD="pip"
if [[ "${TRAVIS_OS_NAME}" == "osx" ]]; then
    # install into user dir on macos to avoid sudo
    # INSTALL_OPT="--user"
    PIP_CMD="pip"
fi

$PIP_CMD install ${INSTALL_OPT} --upgrade pip wheel
$PIP_CMD install ${INSTALL_OPT} pytest-travis-fold codecov pytest-cov
$PIP_CMD install ${INSTALL_OPT} -r requirements_dev.txt

$PIP_CMD list --outdated

set +ex
