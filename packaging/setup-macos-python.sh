#!/usr/bin/env bash
# code parts picked up from
# https://github.com/matthew-brett/multibuild/
MACPYTHON_URL=https://www.python.org/ftp/python
MACPYTHON_PY_PREFIX=/Library/Frameworks/Python.framework/Versions
DOWNLOADS_SDIR=~/

function lex_ver {
    # Echoes dot-separated version string padded with zeros
    # Thus:
    # 3.2.1 -> 003002001
    # 3     -> 003000000
    echo "$1" | awk -F "." '{printf "%03d%03d%03d", $1, $2, $3}'
}

function unlex_ver {
    # Reverses lex_ver to produce major.minor.micro
    # Thus:
    # 003002001 -> 3.2.1
    # 003000000 -> 3.0.0
    echo "$((10#${1:0:3}+0)).$((10#${1:3:3}+0)).$((10#${1:6:3}+0))"
}

function strip_ver_suffix {
    echo $(unlex_ver $(lex_ver $1))
}


function install_mac_cpython {
    local py_version

    local py_osx_ver=$2
    local py_stripped
    local py_inst
    py_version="$1"
    py_stripped=$(strip_ver_suffix "$py_version")

    local postfix
    if [[ ${py_osx_ver} == 11 ]]; then
      postfix="macos"
    else
      postfix="macosx"
    fi

    py_inst=python-${py_version}-${postfix}${py_osx_ver}.pkg
    local inst_path=$DOWNLOADS_SDIR$py_inst
    mkdir -p "$DOWNLOADS_SDIR"
    DOWNLOAD_URL=$MACPYTHON_URL/"$py_stripped"/"${py_inst}"
    if [[ ! -f $inst_path ]]; then
      echo downloading "$DOWNLOAD_URL"
      curl "$DOWNLOAD_URL" > "$inst_path"
    else
      echo "Using cached $inst_path"
    fi
    sudo installer -pkg "$inst_path" -target /
    local py_mm=${py_version:0:4}
    export PYTHON_EXE=$MACPYTHON_PY_PREFIX/$py_mm/bin/python$py_mm
    export PYTHON_DIR=$MACPYTHON_PY_PREFIX/$py_mm
    # Install certificates for Python 3.6
    local inst_cmd="/Applications/Python ${py_mm}/Install Certificates.command"
    if [ -e "$inst_cmd" ]; then
        sh "$inst_cmd"
    fi
    # If the signature is not removed from Python the PyInstaller will fail
    codesign --remove-signature "$PYTHON_DIR/Python"
}

install_mac_cpython "$1" "$2"
echo "PATH=$PYTHON_DIR:$PYTHON_DIR/bin:$PATH" >> $GITHUB_ENV