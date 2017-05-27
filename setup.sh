#!/usr/bin/env bash

# env
# This needs to be the same electron version as we have in package.json
export npm_config_target=1.6.10
export npm_config_arch=x64
export npm_config_target_arch=x64
export npm_config_disturl=https://atom.io/download/electron
export npm_config_runtime=electron
export npm_config_build_from_source=true
npm config ls

# clean caches, very important!!!!!
rm -rf ~/.node-gyp
rm -rf ~/.electron-gyp
rm -rf ./node_modules


# install everything based on the package.json
npm install

# If when running you get a different node.js version error
# just like here: https://github.com/fyears/electron-python-example/issues/9
# then do the following as seen in SO: http://stackoverflow.com/questions/42616008/node-module-version-conflict-when-installing-modules-for-electron/42616189#42616189
./node_modules/.bin/electron-rebuild

# run
./node_modules/.bin/electron .
