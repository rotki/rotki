#!/usr/bin/env bash

if [ -z "$1" ]; then
  echo "usage: $0 [minor|major|patch]"
  exit 1
fi

if [ "$1" != 'minor' ] && [ "$1" != 'major' ] && [ "$1" != 'patch' ]; then
  echo "usage: $0 [minor|major|patch]"
  exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo 'Git working directory is not clean:'
  git status
  exit 1
fi

echo "Preparing $1 release"

ROOT_DIR=$PWD
cd ../ || exit 1

if [ -d 'scripts' ]; then
  cd .. || exit 1
  ROOT_DIR=$PWD
else
  cd "$ROOT_DIR" || exit 1
fi

cd frontend/app || exit 1

npm version --no-git-tag-version "$1"
git add package.json
git add package-lock.json

cd "$ROOT_DIR" || exit 1

bump2version --allow-dirty --config-file .bumpversion.cfg "$1"