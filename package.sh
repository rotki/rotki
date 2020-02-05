#!/usr/bin/env bash

# cleanup before starting to package stuff
make clean

# Perform sanity checks before pip install
pip install packaging  # required for the following script
# We use npm ci. That needs npm >= 5.7.0
npm --version | python -c "import sys;npm_version=sys.stdin.readlines()[0].rstrip('\n');from packaging import version;supported=version.parse(npm_version) >= version.parse('5.7.0');sys.exit(1) if not supported else sys.exit(0);"
if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: The system's npm version is not >= 5.7.0 which is required for npm ci"
    exit 1
fi
# uninstall packaging package since it's no longer required
pip uninstall -y packaging

# Install the rotki package and pyinstaller. Needed by the pyinstaller
pip install -e .
pip install pyinstaller==3.5

# Perform sanity checks that need pip install
python -c "import sys;from rotkehlchen.db.dbhandler import detect_sqlcipher_version; version = detect_sqlcipher_version();sys.exit(0) if version == 4 else sys.exit(1)"
if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: The packaging system's sqlcipher version is not >= v4"
    exit 1
fi


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

export ROTKEHLCHEN_VERSION=$(python setup.py --version)

if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: pyinstaller step failed"
    exit 1
fi

# Sanity check that the generated python executable works
PYINSTALLER_GENERATED_EXECUTABLE=$(ls rotkehlchen_py_dist | head -n 1)
./rotkehlchen_py_dist/$PYINSTALLER_GENERATED_EXECUTABLE version
if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: The generated python executable does not work properly"
    exit 1
fi


# From here and on we go into the electron-app directory
cd electron-app

# Let's make sure all npm dependencies are installed.
npm ci
if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: npm ci step failed"
    exit 1
fi

# Finally run the packaging
echo "Packaging Rotki ${ROTKEHLCHEN_VERSION}"
npm run electron:build
if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: electron builder step failed"
    exit 1
fi
echo "Packaging finished for Rotki ${ROTKEHLCHEN_VERSION}"

# Now if in linux make the AppImage executable
if [[ "$PLATFORM" == "linux" ]]; then
    # Go back to root directory
    cd ..
    # Find the appImage, make it executable and remember its filename so
    # travis can do the publishing
    # They don't do it automatically. Long discussion here:
    # https://github.com/electron-userland/electron-builder/issues/893
    export GENERATED_APPIMAGE=$(ls electron-app/dist/*AppImage | head -n 1)
    chmod +x $GENERATED_APPIMAGE
fi
