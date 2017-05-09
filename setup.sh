#!/usr/bin/env bash

# env
export npm_config_target=1.4.15 # electron version
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

# run
./node_modules/.bin/electron .
