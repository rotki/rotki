#!/usr/bin/env bash
# code parts picked up from
# https://github.com/matthew-brett/multibuild/
MACPYTHON_URL=https://www.python.org/ftp/python
MACPYTHON_PY_PREFIX=/Library/Frameworks/PythonT.framework/Versions
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
    local choice_changes
    local installer_result
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
    local py_mm=${py_version:0:4}
    choice_changes=$(mktemp)
    cat > "$choice_changes" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<array>
    <dict>
        <key>attributeSetting</key>
        <integer>1</integer>
        <key>choiceAttribute</key>
        <string>selected</string>
        <key>choiceIdentifier</key>
        <string>org.python.Python.PythonTFramework-${py_mm}</string>
    </dict>
</array>
</plist>
EOF
    sudo installer -pkg "$inst_path" -applyChoiceChangesXML "$choice_changes" -target /
    installer_result=$?
    rm "$choice_changes"
    if [[ $installer_result -ne 0 ]]; then
        return "$installer_result"
    fi

    export PYTHON_EXE=$MACPYTHON_PY_PREFIX/$py_mm/bin/python${py_mm}t
    export PYTHON_DIR=$MACPYTHON_PY_PREFIX/$py_mm
    # The free-threaded framework shares certificates with the regular framework.
    local inst_cmd="/Applications/Python ${py_mm}/Install Certificates.command"
    if [ -e "$inst_cmd" ]; then
        sh "$inst_cmd"
    fi
}

install_mac_cpython "$1" "$2" || exit 1
"$PYTHON_EXE" -c 'import sys, sysconfig; assert sysconfig.get_config_var("Py_GIL_DISABLED") == 1; assert not sys._is_gil_enabled()'
echo "PATH=$PYTHON_DIR:$PYTHON_DIR/bin:$PATH" >> "$GITHUB_ENV"
echo "UV_PYTHON=$PYTHON_EXE" >> "$GITHUB_ENV"
