#!/usr/bin/env bash

set -ex


INSTALL_OPT=""
if [[ "${TRAVIS_OS_NAME}" == "osx" ]]; then
    # install into user dir on macos to avoid sudo
    INSTALL_OPT="--user"
fi

pip install ${INSTALL_OPT} --upgrade pip wheel
pip install ${INSTALL_OPT} pytest-travis-fold codecov pytest-cov
pip install ${INSTALL_OPT} -r requirements_dev.txt

pip list --outdated

set +ex
