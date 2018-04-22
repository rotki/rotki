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

# Let's make sure all npm dependencies are installed. Since we added electron tests
# maybe this does not need to happen here?
rm -rf ./node_modules
npm config set python python2.7
if [[ $PLATFORM == "darwin" ]]; then
  # If we add the specific electron runtime compile in OSX fails with an error
  # that looks like this: https://www.npmjs.com/package/nan#compiling-against-nodejs-012-on-osx
  # - npm install --runtime=electron --target=1.8.4
    npm install
else
    npm install --runtime=electron --target=1.8.4
fi

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
    echo "package.sh - ERROR: electron-packager step failed"
    exit 1
fi

NAME="rotkehlchen-${PLATFORM}-${ARCH}"
# Ugly hack to include zmq lib in the distribution. TODO: Is there a better solution?
# Step 1: Copy the library in the directory
# Step 2: Create a wrapper script executable for both distros which points
#         the LD_LIBRARY_PATH to the current directory
if [[ $PLATFORM == "darwin" ]]; then
    ZMQLIBPATH=`otool -l ./rotkehlchen-darwin-x64/rotkehlchen.app/Contents/Resources/app/node_modules/zmq/bin/darwin-x64-57/zmq.node | grep zmq | awk '/ / { print $2 }'`
    cp $ZMQLIBPATH $NAME/
    if [[ $? -ne 0 ]]; then
	echo "package.sh - ERROR: copying libzmq step failed"
	exit 1
    fi
else
    ZMQLIBPATH=`ldd ./rotkehlchen-linux-x64/resources/app/node_modules/zmq/bin/*/zmq.node | grep libzmq | awk '/ => / { print $3 }'`
    cp $ZMQLIBPATH $NAME/
    if [[ $? -ne 0 ]]; then
	echo "package.sh - ERROR: copying libzmq step failed"
	exit 1
    fi
    PGMLIBPATH=`ldd $ZMQLIBPATH | grep libpgm | awk '/ => / { print $3 }'`
    cp $PGMLIBPATH $NAME/
    if [[ $? -ne 0 ]]; then
	echo "package.sh - ERROR: copying libpgm step failed"
	exit 1
    fi

    mv $NAME/rotkehlchen $NAME/unwrapped_executable
fi
    cp tools/scripts/wrapper_script.sh $NAME/rotkehlchen


# Now try to zip the created bundle
zip -r $NAME "$NAME/"
if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: zipping of final bundle failed"
    exit 1
fi

rm -rf $NAME
