#!/usr/bin/env bash

REVISION=$(git rev-parse HEAD)
ROTKI_VERSION=$(cat .bumpversion.cfg | grep 'current_version = ' | sed -n -e 's/current_version = //p')
POSTFIX=$(if git describe --tags --exact-match "$REVISION" &>/dev/null; then echo ''; else echo '-dev'; fi)
ROTKI_VERSION=${ROTKI_VERSION}${POSTFIX}

docker build --pull --no-cache -t rotki . --build-arg REVISION="$REVISION" --build-arg ROTKI_VERSION="$ROTKI_VERSION"