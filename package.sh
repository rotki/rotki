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
    npm install
else
    npm install
    npm rebuild zeromq --runtime=electron --target=3.0.0
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

npm run build

ELECTRON_PACKAGER_EXTRA_ARGS=
if [[ $PLATFORM == "darwin" ]]; then
    ELECTRON_PACKAGER_EXTRA_ARGS="--icon=ui/images/rotki.icns"
elif [[ $PLATFORM == "linux" ||  $PLATFORM == "freebsd" ]]; then
    ELECTRON_PACKAGER_EXTRA_ARGS="--icon=ui/images/rotki_1024x1024.png"
fi
./node_modules/.bin/electron-packager . --overwrite \
				      --ignore="rotkehlchen$" \
				      --ignore="rotkehlchen.egg-info" \
				      --ignore="^/tools$" \
				      --ignore="^/docs$" \
				      --ignore="^/build$" \
				      --ignore="appveyor*" \
				      --ignore="^/.eggs" \
				      --ignore="^/.github" \
				      --ignore="^/.gitignore" \
				      --ignore="^/.ignore" \
				      --ignore=".nvmrc" \
				      --ignore="^/package-lock.json" \
				      --ignore="requirements*" \
				      --ignore="^/rotki_config.json" \
				      --ignore="^/rotkehlchen.spec" \
				      --ignore="setup.cfg" \
				      --ignore="^/stubs" \
				      --ignore="^/.mypy_cache" \
				      --ignore=".travis*" \
				      --ignore="tsconfig*" \
				      --ignore="tsfmt.json" \
				      --ignore="tslint.json" \
				      --ignore="^/.bumpversion.cfg" \
				      --ignore="^/.mypy_cache/" \
				      --ignore="^/.coveragerc" \
				      --ignore="^/.coverage" \
				      --ignore="^/.env" \
				      --ignore="^/README.md" \
				      --ignore="rotkehlchen.log" \
				      --ignore=".*\.sh" \
				      --ignore=".*\.py" \
				      --ignore=".*\.bat" \
				      --ignore="^/CONTRIBUTING.md" \
				      --ignore="^/Makefile" $ELECTRON_PACKAGER_EXTRA_ARGS

if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: electron-packager step failed"
    exit 1
fi

ROTKEHLCHEN_VERSION=$(python setup.py --version)
if [[ $ROTKEHLCHEN_VERSION == *".dev"* ]]; then
    # It's not a tagged release. Returned version
    # looks similar to 0.6.1.dev12+ga5ed53d
    DATE=$(date +%Y-%m-%dT%H-%M-%S)
    export ARCHIVE_NAME="rotki-${PLATFORM}-${ARCH}-v${ROTKEHLCHEN_VERSION}"
    EXEC_NAME="rotki-${DATE}-v${ROTKEHLCHEN_VERSION}"
else
    export ARCHIVE_NAME="rotki-${PLATFORM}-${ARCH}-v${ROTKEHLCHEN_VERSION}"
    EXEC_NAME="rotki-v${ROTKEHLCHEN_VERSION}"
fi

GENERATED_ARCHIVE_NAME="rotki-${PLATFORM}-${ARCH}"

if [[ $PLATFORM == "linux" ]]; then
    mv $GENERATED_ARCHIVE_NAME/rotki $GENERATED_ARCHIVE_NAME/unwrapped_executable
fi

cp tools/scripts/wrapper_script.sh $GENERATED_ARCHIVE_NAME/$EXEC_NAME


if [[ $PLATFORM == "darwin" ]]; then
    # For OSX create a dmg
    ./node_modules/.bin/electron-installer-dmg $GENERATED_ARCHIVE_NAME/rotki.app $ARCHIVE_NAME --icon=ui/images/rotki.icns --title=Rotki

    rm -rf $GENERATED_ARCHIVE_NAME
else
    # Now try to zip the created bundle
    mv $GENERATED_ARCHIVE_NAME $ARCHIVE_NAME
    zip -r $ARCHIVE_NAME.zip "$ARCHIVE_NAME/"
    if [[ $? -ne 0 ]]; then
	echo "package.sh - ERROR: zipping of final bundle failed"
	exit 1
    fi

    rm -rf $ARCHIVE_NAME
fi
