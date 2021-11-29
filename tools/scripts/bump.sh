#!/usr/bin/env bash

source tools/scripts/check_unmerged.sh force

vercomp () {
    if [[ $1 == $2 ]]
    then
        return 0
    fi
    local IFS=.
    local i ver1=($1) ver2=($2)
    # fill empty fields in ver1 with zeros
    for ((i=${#ver1[@]}; i<${#ver2[@]}; i++))
    do
        ver1[i]=0
    done
    for ((i=0; i<${#ver1[@]}; i++))
    do
        if [[ -z ${ver2[i]} ]]
        then
            # fill empty fields in ver2 with zeros
            ver2[i]=0
        fi
        if ((10#${ver1[i]} > 10#${ver2[i]}))
        then
            return 1
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]}))
        then
            return 2
        fi
    done
    return 0
}

if [ -z "$1" ]; then
  echo "usage: $0 [minor|major|patch]"
  exit 1
fi

if [ "$1" != 'minor' ] && [ "$1" != 'major' ] && [ "$1" != 'patch' ]; then
  echo "usage: $0 [minor|major|patch]"
  exit 1
fi

NPM_VERSION="$(npm -v)"
vercomp $NPM_VERSION "7.0.0"
if [ "$?" == '2' ]; then
    echo 'npm version should be > 7.0.0'
    exit 1
fi

if [ "$(git diff --shortstat 2> /dev/null | tail -n1)" != "" ]; then
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

cd frontend || exit 1

npm version --no-git-tag-version "$1" -w rotki
node bump.js
git add app/package.json
git add package-lock.json

cd "$ROOT_DIR" || exit 1

bump2version --allow-dirty --config-file .bumpversion.cfg "$1"
