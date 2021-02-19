#!/usr/bin/env bash

WORKDIR=$PWD
# cleanup before starting to package stuff
make clean

if [[ -n "${CI-}" ]]; then
  echo "::group::Pip install"
fi

# Perform sanity checks before pip install
pip install packaging  # required for the following script
# We use npm ci. That needs npm >= 5.7.0
npm --version | python -c "import sys;npm_version=sys.stdin.readlines()[0].rstrip('\n');from packaging import version;supported=version.parse(npm_version) >= version.parse('5.7.0');sys.exit(1) if not supported else sys.exit(0);"
if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: The system's npm version is not >= 5.7.0 which is required for npm ci"
    exit 1
fi

# Install the rotki package and pyinstaller. Needed by the pyinstaller
pip install -e .
pip install pyinstaller==3.5

if [[ -n "${CI-}" ]]; then
  echo "::endgroup::"
fi

# Perform sanity checks that need pip install
python -c "import sys;from rotkehlchen.db.dbhandler import detect_sqlcipher_version; version = detect_sqlcipher_version();sys.exit(0) if version == 4 else sys.exit(1)"
if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: The packaging system's sqlcipher version is not >= v4"
    exit 1
fi


# Get the arch
ARCH=$(uname -m)
if [[ "$ARCH" == 'x86_64' ]]; then
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
    export ONEFILE=0
elif [[ "$OSTYPE" == "win32" ]]; then
    PLATFORM='win32'
elif [[ "$OSTYPE" == "freebsd"* ]]; then
    PLATFORM='freebsd'
else
    echo "package.sh - ERROR: Unsupported platform '${OSTYPE}'"
    exit 1
fi

if [[ -n "${CI-}" ]]; then
  echo "::group::PyInstaller"
fi
# Use pyinstaller to package the python app
rm -rf build rotkehlchen_py_dist
pyinstaller --noconfirm --clean --distpath rotkehlchen_py_dist rotkehlchen.spec

if [[ -n "${CI-}" ]]; then
  echo "::endgroup::"
fi

ROTKEHLCHEN_VERSION=$(python setup.py --version)
export ROTKEHLCHEN_VERSION

if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: pyinstaller step failed"
    exit 1
fi



echo 'Checking binary'
if [[ "$PLATFORM" == "darwin" ]]; then
  PYINSTALLER_GENERATED_EXECUTABLE=$(find ./rotkehlchen_py_dist/rotkehlchen -name "rotkehlchen-*-macos")
  ./rotkehlchen_py_dist/rotkehlchen/${PYINSTALLER_GENERATED_EXECUTABLE##*/} version
else
  # Sanity check that the generated python executable works
  PYINSTALLER_GENERATED_EXECUTABLE=$(ls rotkehlchen_py_dist | head -n 1)
  ./rotkehlchen_py_dist/$PYINSTALLER_GENERATED_EXECUTABLE version
fi


if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: The generated python executable does not work properly"
    exit 1
fi

if [[ -n "${CI-}" ]] && [[ "$PLATFORM" == "darwin" ]] && [[ -n "${$CERTIFICATE_OSX_APPLICATION-}" ]]; then
  echo "Preparing to sign backend binary for macos"
  KEY_CHAIN=rotki-build.keychain
  CSC_LINK=/tmp/certificate.p12
  export CSC_LINK
  # Recreate the certificate from the secure environment variable
  echo $CERTIFICATE_OSX_APPLICATION | base64 --decode > $CSC_LINK
  #create a keychain
  security create-keychain -p actions $KEY_CHAIN
  # Make the keychain the default so identities are found
  security default-keychain -s $KEY_CHAIN
  # Unlock the keychains
  security unlock-keychain -p actions $KEY_CHAIN
  security import $CSC_LINK -k $KEY_CHAIN -P $CSC_KEY_PASSWORD -T /usr/bin/codesign;
  security set-key-partition-list -S apple-tool:,apple: -s -k actions $KEY_CHAIN

  echo "::group::Preparing to sign"
  files=(`find ./rotkehlchen_py_dist -type f -exec ls -dl \{\} \; | awk '{ print $9 }'`)
  for i in "${files[@]}"
  do
    echo "Signing $i"
    codesign --force --options runtime --entitlements ./packaging/entitlements.plist --sign $IDENTITY $i --timestamp || exit 1
    codesign --verify --verbose $i || exit 1
  done
  echo "::endgroup::"
fi


# From here and on we go into the frontend/app directory
cd frontend/app || exit 1

if [[ -n "${CI-}" ]]; then
  echo "::group::npm ci"
fi
# Let's make sure all npm dependencies are installed.
echo "Installing node dependencies"
npm ci
if [[ $? -ne 0 ]]; then
    echo "Verifying npm cache"
    npm cache verify
    echo "Attempting node installation again"
    npm ci
    if [[ $? -ne 0 ]]; then
      echo "package.sh - ERROR: npm ci step failed"
      exit 1
    fi
fi

if [[ -n "${CI-}" ]]; then
  echo "::endgroup::"
fi

if [[ -n "${CI-}" ]]; then
  echo "::group::electron:build"
fi
# Finally run the packaging
echo "Packaging Rotki ${ROTKEHLCHEN_VERSION}"
npm run electron:build
if [[ $? -ne 0 ]]; then
    echo "package.sh - ERROR: electron builder step failed"
    exit 1
fi

if [[ -n "${CI-}" ]]; then
  echo "::endgroup::"
fi

if [[ -n "${CI-}" ]] && [[ "$OSTYPE" == "darwin"* ]]; then
  # remove certs
  rm -fr /tmp/*.p12
fi

echo "Packaging finished for Rotki ${ROTKEHLCHEN_VERSION}"

# Go back to root directory
cd "$WORKDIR" || exit 1

function generate_checksum() {

    local platform
    local filter
    local file
    local checksum_file

    platform=$1
    filter=$2
    file=$(find ./ -name "$filter" | sed 's|^./||' | sed 's|^/||');
    checksum_file="$file.sha512"
    echo "Generating sha512 sum for $file"

    if [[ "$platform" == "linux" ]]; then
      sha512sum "$file" > "$checksum_file"
    elif [[ "$platform" == "darwin" ]]; then
      shasum -a 512 "$file" > "$checksum_file"
    else
      echo "$platform not supported"
      exit 1;
    fi

    eval "$3='$(pwd)/$checksum_file'"
}

cd frontend/app/dist || exit 1

if [[ "$PLATFORM" == "linux" ]]; then
  GENERATED_APPIMAGE=$(find "$(pwd)" -name "rotki-linux*.AppImage"  | head -n 1)
  generate_checksum "$PLATFORM" "rotki-linux*.AppImage" APPIMAGE_CHECKSUM
  generate_checksum "$PLATFORM" "rotki-linux*.tar.xz" TAR_CHECKSUM
  generate_checksum "$PLATFORM" "rotki-linux*.deb" DEB_CHECKSUM

  if [[ -n "${CI-}" ]]; then
    echo "::set-output name=binary::$GENERATED_APPIMAGE"
    echo "::set-output name=binary_name::${GENERATED_APPIMAGE##*/}"
    echo "::set-output name=binary_checksum::$APPIMAGE_CHECKSUM"
    echo "::set-output name=binary_checksum_name::${APPIMAGE_CHECKSUM##*/}"
    echo "::set-output name=archive_checksum::$TAR_CHECKSUM"
    echo "::set-output name=archive_checksum_name::${TAR_CHECKSUM##*/}"
    echo "::set-output name=deb_checksum::$DEB_CHECKSUM"
    echo "::set-output name=deb_checksum_name::${DEB_CHECKSUM##*/}"
  fi

  export APPIMAGE_CHECKSUM
  export TAR_CHECKSUM
elif [[ "$PLATFORM" == "darwin" ]]; then
  DMG=$(find "$(pwd)" -name "rotki-darwin*.dmg"  | head -n 1)
  generate_checksum "$PLATFORM" "rotki-darwin*.dmg" DMG_CHECKSUM
  generate_checksum "$PLATFORM" "rotki-darwin*.zip" ZIP_CHECKSUM

  if [[ -n "${CI-}" ]]; then
    echo "::set-output name=binary::$DMG"
    echo "::set-output name=binary_name::${DMG##*/}"
    echo "::set-output name=binary_checksum::$DMG_CHECKSUM"
    echo "::set-output name=binary_checksum_name::${DMG_CHECKSUM##*/}"
    echo "::set-output name=archive_checksum::$ZIP_CHECKSUM"
    echo "::set-output name=archive_checksum_name::${ZIP_CHECKSUM##*/}"
  fi

  export DMG_CHECKSUM
  export ZIP_CHECKSUM
fi
