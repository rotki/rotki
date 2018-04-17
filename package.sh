#!/usr/bin/env bash

# Use pyinstaller to package the python app
rm -rf build rotkehlchen_py_dist
pyinstaller --noconfirm --clean --distpath rotkehlchen_py_dist rotkehlchen.spec

# Now use electron packager to bundle the entire app together with electron in a dir
./node_modules/.bin/electron-packager . --overwrite \
				      --ignore="rotkehlchen$" \
				      --ignore="rotkehlchen.egg-info" \
				      --ignore="tools$" \
				      --ignore=".*\.sh" \
				      --ignore=".*\.py"
