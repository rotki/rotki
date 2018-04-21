#!/usr/bin/env bash

# Install the rotkehlchen package and pyinstaller. Needed by the pyinstaller
pip install -e .
pip install pyinstaller

# Get the arch
ARCH=`uname -m`
if [ ${ARCH} == 'x86_64' ]; then
    ARCH='x64'
else
    echo "package.sh - ERROR: Unsupported architecture '${ARCH}'"
    exit 1
fi

# Get the platform
if [[ "$OSTYPE" == "linux-gnu" ]]; then
    PLATFORM='linux'
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM='darwin'
elif [[ "$OSTYPE" == "win32" ]]; then
    PLATFORM='win32'
elif [[ "$OSTYPE" == "freebsd"* ]]; then
    PLATFORM='freebsd'
else
    echo "package.sh - ERROR: Unsupported platform '${OSTYPE}'"
    exit 1
fi

# Use pyinstaller to package the python app
rm -rf build rotkehlchen_py_dist
pyinstaller --noconfirm --clean --distpath rotkehlchen_py_dist rotkehlchen.spec

if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: pyinstaller step failed"
    exit 1
fi


# Now use electron packager to bundle the entire app together with electron in a dir
rm -rf ./node_modules
npm config set python python2.7
npm install
if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: npm install step failed"
    exit 1
fi

PYTHON=/usr/bin/python2.7 ./node_modules/.bin/electron-rebuild
if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: electron-rebuild step failed"
    exit 1
fi

./node_modules/.bin/electron-packager . --overwrite \
				      --ignore="rotkehlchen$" \
				      --ignore="rotkehlchen.egg-info" \
				      --ignore="tools$" \
				      --ignore=".*\.sh" \
				      --ignore=".*\.py"

if [[ $? -ne 0 ]]; then
    echo "test.sh - ERROR: electron-packager step failed"
    exit 1
fi

# Now try to zip the created bundle
NAME="rotkehlchen-${PLATFORM}-${ARCH}"
zip -r $NAME "$NAME/"
if [[ $? -ne 0 ]]; then
    echo "test.sh - ERROR: zipping of final bundle failed"
    exit 1
fi

rm -rf $NAME
