$PYINSTALLER_VERSION = if ($env:PYINSTALLER_VERSION) { $env:PYINSTALLER_VERSION } else { '3.5' }
$SQLCIPHER_VERSION = if ($env:SQLCIPHER_VERSION) { $env:SQLCIPHER_VERSION } else { 'v4.4.0' }
$PYSQLCIPHER3_VERSION = if ($env:PYSQLCIPHER3_VERSION) { $env:PYSQLCIPHER3_VERSION } else { 'c01b3bda144073eb34412ae64702fa2362a778e7' }
$BUILD_DEPENDENCIES = if ($env:BUILD_DEPENDENCIES) { $env:BUILD_DEPENDENCIES } else { 'rotki-build-dependencies' }

# Setup constants
$MINIMUM_NPM_VERSION = "7.6.2"
$TCLTK='tcltk85-8.5.19-17.tcl85.Win10.x86_64'

echo "Starting rotki build process with SQLCipher $SQLCIPHER_VERSION and pysqlcipher3 $PYSQLCIPHER3_VERSION"

$PROJECT_DIR = $PWD

function ExitOnFailure {
    param([string]$ExitMessage)
    if (-not ($LASTEXITCODE -eq 0)) {
        echo "$ExitMessage"
        exit 1;
    }
}

if ($Env:CI) {
    echo "::group::Setup Build dependencies"
}

if ($Env:CI) {
    cd ~\
} else {
    cd ..
}

if (-not (Test-Path $BUILD_DEPENDENCIES -PathType Container)) {
    mkdir $BUILD_DEPENDENCIES
}

cd $BUILD_DEPENDENCIES
$BUILD_DEPS_DIR = $PWD

if (-not (Test-Path $TCLTK -PathType Container)) {
    echo "Setting up TCL/TK $TCLTK"
    curl.exe -L -O "https://bitbucket.org/tombert/tcltk/downloads/$TCLTK.tgz"
    ExitOnFailure("Failed to download tcl/tk")
    tar -xf "$TCLTK.tgz"
    ExitOnFailure("Failed to untar tcl/tk")
}

if ($Env:CI) {
    echo "::addpath::$PWD\$TCLTK\bin"
} else {
    $env:Path += ";$PWD\$TCLTK\bin"
}

if ($Env:CI) {
    echo "::endgroup::"
    echo "::group::Build SQLCipher"
}

if (-not (Test-Path sqlcipher -PathType Container)) {
    echo "Cloning SQLCipher"
    git clone https://github.com/sqlcipher/sqlcipher
    ExitOnFailure("Failed to clone SQLCipher")
}

cd sqlcipher
$SQLCIPHER_DIR = $PWD

$tag = git name-rev --tags --name-only $(git rev-parse HEAD)

if (-not ($tag -match $SQLCIPHER_VERSION)) {
    echo "Checking out SQLCipher $SQLCIPHER_VERSION"
    git checkout $SQLCIPHER_VERSION
    ExitOnFailure("Failed to checkout SQLCipher $SQLCIPHER_VERSION")
}

if (-not (git status --porcelain)) {
    echo "Applying Makefile patch for SQLCipher"
    git apply $PROJECT_DIR\packaging\sqlcipher_win.diff
    ExitOnFailure("Failed to apply the Makefile patch for SQLCipher")
}


$OPENSSL_PATH = (Join-Path ${env:ProgramFiles} "OpenSSL-Win64")

if (-not(Test-Path "$OPENSSL_PATH" -PathType Container))
{
    echo "Installing OpenSSL 1.1.1.8"
    choco install -y openssl --version 1.1.1.800 --no-progress
    ExitOnFailure("Installation of OpenSSL Failed")
}

echo "Setting up Visual Studio Dev Shell"

$BACKUP_ENV = @()
Get-Childitem -Path Env:* | Foreach-Object {
    $BACKUP_ENV += $_
}

$vsPath = &(Join-Path ${env:ProgramFiles(x86)} "\Microsoft Visual Studio\Installer\vswhere.exe") -version '[16.0,)' -property installationpath
Import-Module (Join-Path $vsPath "Common7\Tools\Microsoft.VisualStudio.DevShell.dll")

$arch = 64
$vc_env = "vcvars$arch.bat"
echo "Load MSVC environment $vc_env"
$build = (Join-Path $vsPath "VC\Auxiliary\Build")
$env:Path += ";$build"

Enter-VsDevShell -VsInstallPath $vsPath -DevCmdArguments -arch=x64
if (Get-Command "$vc_env" -errorAction SilentlyContinue)
{
    ## Store the output of cmd.exe. We also ask cmd.exe to output
    ## the environment table after the batch file completes
    ## Go through the environment variables in the temp file.
    ## For each of them, set the variable in our local environment.
    cmd /Q /c "$vc_env && set" 2>&1 | Foreach-Object {
        if ($_ -match "^(.*?)=(.*)$")
        {
            Set-Content "env:\$( $matches[1] )" $matches[2]
        }
    }

    echo "Environment successfully set"
}

if (-not (Test-Path sqlcipher.dll -PathType Leaf))
{
    cd $SQLCIPHER_DIR
    nmake /f Makefile.msc
    ExitOnFailure("Failed to build SQLCipher")

}

# Reset the environment **
Get-Childitem -Path Env:* | Foreach-Object {
    Remove-Item "env:\$($_.Name)"
}

$BACKUP_ENV | Foreach-Object {
    Set-Content "env:\$($_.Name)" $_.Value
}

$env:Path += ";$SQLCIPHER_DIR"

if ($Env:CI) {
    echo "::endgroup::"
    echo "::group::Setup PySQLCipher"
}

cd $BUILD_DEPS_DIR

if (-not (Test-Path pysqlcipher3 -PathType Container)) {
    echo "Cloning pysqlcipher3"
    git clone https://github.com/rigglemania/pysqlcipher3.git
    ExitOnFailure("Failed to clone pysqlcipher3")
}

cd pysqlcipher3
$PYSQLCIPHER3_DIR = $PWD

if (-not (git rev-parse HEAD) -match $PYSQLCIPHER3_VERSION) {
    git checkout $PYSQLCIPHER3_VERSION
    ExitOnFailure("Failed to checkout pysqlcipher3 $PYSQLCIPHER3_VERSION")
}

if (-not (git status --porcelain)) {
    echo "Applying setup patch"
    git apply $PROJECT_DIR\packaging\pysqlcipher3_win.diff
    ExitOnFailure("Failed to apply pysqlcipher3 patch")
}

if ($Env:CI) {
    echo "::endgroup::"
}

if ((-not ($env:VIRTUAL_ENV)) -and (-not ($Env:CI))) {
    if ((-not (Test-Path "$BUILD_DEPS_DIR\.venv" -PathType Container))) {
        cd $BUILD_DEPS_DIR
        pip install virtualenv --user
        echo "Creating rotki .venv"
        python -m virtualenv .venv
        ExitOnFailure("Failed to create rotki VirtualEnv")
    }

    cd $PROJECT_DIR

    echo "Activating rotki .venv"
    & $BUILD_DEPS_DIR\.venv\Scripts\activate.ps1
    ExitOnFailure("Failed to activate rotki VirtualEnv")
}

cd $PROJECT_DIR
$NPM_VERSION = (npm --version) | Out-String

if ([version]$NPM_VERSION -lt [version]$MINIMUM_NPM_VERSION) {
    echo "Please make sure you have npm version $MINIMUM_NPM_VERSION or newer installed"
    exit 1;
}

if (-not (Test-Path sqlcipher.dll -PathType Leaf)) {
    echo "Copying sqlcipher.dll to project directory"
    Copy-Item "$SQLCIPHER_DIR\sqlcipher.dll" .\
}

if (-not (Test-Path libcrypto-1_1-x64.dll -PathType Leaf)) {
    echo "Copying libcrypto-1_1-x64.dll to project directory"
    Copy-Item "$OPENSSL_PATH\bin\libcrypto-1_1-x64.dll" .\
}

if ($Env:CI) {
    echo "::group::pip install"
}

pip install pyinstaller==$PYINSTALLER_VERSION
pip install -r requirements.txt
pip install -e.

cd $PYSQLCIPHER3_DIR
python setup.py build
python setup.py install

cd $PROJECT_DIR

python -c "import sys;from rotkehlchen.db.dbhandler import detect_sqlcipher_version; version = detect_sqlcipher_version();sys.exit(0) if version == 4 else sys.exit(1)"
ExitOnFailure("SQLCipher version verification failed")

$SETUP_VERSION = (python setup.py --version) | Out-String

if ($Env:CI) {
    echo "::endgroup::"
}

if (Test-Path build -PathType Container) {
    Remove-Item -Recurse -Force build
}

if (Test-Path rotkehlchen_py_dist -PathType Container) {
    Remove-Item -Recurse -Force rotkehlchen_py_dist
}

if ($Env:CI) {
    echo "::group::PyInstaller"
}

pyinstaller --noconfirm --clean --distpath rotkehlchen_py_dist rotkehlchen.spec
ExitOnFailure("PyInstaller execution was not sucessful")

$BACKEND_BINARY = @(Get-ChildItem -Path $PWD\rotkehlchen_py_dist -Filter *.exe -Recurse -File -Name)[0]
ExitOnFailure("The backend binary was not found")

Invoke-Expression "$PWD\rotkehlchen_py_dist\$BACKEND_BINARY version" | Out-String
ExitOnFailure("The backend test start failed")

if ($Env:CI) {
    echo "::endgroup::"
}

echo "Packaging the electron application"

if ($Env:CI) {
    echo "::group::npm ci"
}

cd frontend\app
npm ci
ExitOnFailure("Restoring the node dependencies with npm ci failed")

if ($Env:CI) {
    echo "::endgroup::"
    echo "::group::electron build"
}

npm run electron:build
ExitOnFailure("Building the electron app failed")

if ($Env:CI) {
    echo "::endgroup::"
}

$BINARY_NAME = @(Get-ChildItem -Path $PWD\dist -Filter *.exe -Recurse -File -Name)[0]

if (-not ($BINARY_NAME)) {
    echo "The app binary was not found"
    exit 1
}

cd dist
$CHECKSUM_NAME = "$BINARY_NAME.sha512"
$APP_BINARY = "$PWD\$BINARY_NAME"
$APP_CHECKSUM = "$PWD\$CHECKSUM_NAME"

Get-FileHash $APP_BINARY -Algorithm SHA512 | Select-Object Hash | foreach {$_.Hash} | Out-File -FilePath $APP_CHECKSUM

echo "Preparing backend binary for publishing"

$BACKEND_DIST = "$PROJECT_DIR\rotkehlchen_py_dist"
cd $BACKEND_DIST
$BACKEND_BINARY_FILE = "$BACKEND_DIST\$BACKEND_BINARY"
$BACKEND_BINARY_CHECKSUM_NAME = "$BACKEND_BINARY.sha512"
$BACKEND_BINARY_CHECKSUM = "$BACKEND_DIST\$BACKEND_BINARY_CHECKSUM_NAME"
Get-FileHash $BACKEND_BINARY_FILE -Algorithm SHA512 | Select-Object Hash | foreach {$_.Hash} | Out-File -FilePath $BACKEND_BINARY_CHECKSUM_NAME

if ($Env:CI) {
    echo "::set-output name=binary::$($APP_BINARY)"
    echo "::set-output name=binary_name::$($BINARY_NAME)"
    echo "::set-output name=binary_checksum::$($APP_CHECKSUM)"
    echo "::set-output name=binary_checksum_name::$($CHECKSUM_NAME)"
    echo "::set-output name=backend_binary::$($BACKEND_BINARY_FILE)"
    echo "::set-output name=backend_binary_name::$($BACKEND_BINARY)"
    echo "::set-output name=backend_binary_checksum::$($BACKEND_BINARY_CHECKSUM)"
    echo "::set-output name=backend_binary_checksum_name::$($BACKEND_BINARY_CHECKSUM_NAME)"
}

echo "rotki $SETUP_VERSION was build successfully"

if (($env:VIRTUAL_ENV) -and (-not ($Env:CI))) {
    deactivate
    cd $PROJECT_DIR
}
