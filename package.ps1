$SQLCIPHER_VERSION = if ($env:SQLCIPHER_VERSION) { $env:SQLCIPHER_VERSION } else { 'v4.4.0' } 
$PYSQLCIPHER3_VERSION = if ($env:PYSQLCIPHER3_VERSION) { $env:PYSQLCIPHER3_VERSION } else { 'fd1b547407bcb7198107fe3c458105286a060b0d' }
$BUILD_DEPENDENCIES = if ($env:BUILD_DEPENDENCIES) { $env:BUILD_DEPENDENCIES } else { 'rotki-build-dependencies' }

# Setup constants
$MINIMUM_NPM_VERSION = "5.7.0"
$TCLTK='tcltk85-8.5.19.19.tcl85.Win10.x86_64'

echo "Starting rotki build process with SQLCipher $SQLCIPHER_VERSION and pysqlcipher3 $PYSQLCIPHER3_VERSION"

$PROJECT_DIR = $PWD

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
    tar -xf "$TCLTK.tgz"    
}

if ($Env:CI) { 
    echo "::addpath::$PWD\$TCLTK\bin"
} else {
    $env:Path += ";$PWD\$TCLTK\bin"
}


if (-not (Test-Path sqlcipher -PathType Container)) {
    echo "Cloning SQLCipher"
    git clone https://github.com/sqlcipher/sqlcipher
}

cd sqlcipher
$SQLCIPHER_DIR = $PWD

$tag = git name-rev --tags --name-only $(git rev-parse HEAD)

if (-not ($tag -match $SQLCIPHER_VERSION)) {
    echo "Checking out $SQLCIPHER_VERSION"
    git checkout $SQLCIPHER_VERSION
}

if (-not (git status --porcelain)) {
    echo "Applying Makefile patch"
    git apply $PROJECT_DIR\packaging\sqlcipher_win.diff
}

if (-not (Test-Path sqlcipher.dll -PathType Leaf))
{
    echo "Setting up Visual Studio Dev Shell"

    $vsPath = &(Join-Path ${env:ProgramFiles(x86)} "\Microsoft Visual Studio\Installer\vswhere.exe") -property installationpath
    Import-Module (Join-Path $vsPath "Common7\Tools\Microsoft.VisualStudio.DevShell.dll")

    $arch = 64
    $vc_env = "vcvars$arch.bat"
    echo "Load MSVC environment $vc_env"
    $build = (Join-Path $vsPath "VC\Auxiliary\Build")
    $env:Path += ";$build"

    if (-not(Test-Path (Join-Path ${env:ProgramFiles} "OpenSSL-Win64") -PathType Container))
    {
        echo "Installing OpenSSL 1.1.1.8"
        choco install -y openssl --version 1.1.1.800 --no-progress
    }

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

    cd $SQLCIPHER_DIR
    nmake /f Makefile.msc

    if (-not ($LASTEXITCODE -eq 0)) {
        echo "SQLCipher build failed"
        exit 1;
    }
}

$env:Path += ";$SQLCIPHER_DIR"

cd $BUILD_DEPS_DIR

if (-not (Test-Path pysqlcipher3 -PathType Container)) {
    echo "Cloning pysqlcipher3"
    git clone https://github.com/rigglemania/pysqlcipher3.git
}

cd pysqlcipher3
$PYSQLCIPHER3_DIR = $PWD

git checkout $PYSQLCIPHER3_VERSION

if (-not (git status --porcelain)) {
    echo "Applying setup patch"
    git apply $PROJECT_DIR\packaging\pysqlcipher3_win.diff
}

cd $BUILD_DEPS_DIR

if ((-not (Test-Path .venv -PathType Container)) -and (-not ($Env:CI))) {
    echo "Creating rotki .venv"
    python virtualenv .venv
}

cd $PROJECT_DIR
if (-not ($Env:CI)) {
    & $BUILD_DEPS_DIR\.venv\Scripts\activate.ps1    
}


#TODO: Check if already in venv and skip activation

$NPM_VERSION = (npm --version) | Out-String  
 
if ([version]$NPM_VERSION -lt [version]$MINIMUM_NPM_VERSION) {
    echo "Please make sure you have npm version 5.7.0 or newer installed"
    exit 1;
}

# If vctools are not installed building some native python dependenceis will fail with
# Microsoft Visual C++ 14.0 is required
if ($Env:CI) {
    choco install visualstudio2019-workload-vctools --no-progress
}

pip install -r requirements.txt
pip install -e .
pip install pyinstaller==3.5

cd $PYSQLCIPHER3_DIR
python setup.py build
python setup.py install

cd $PROJECT_DIR

python -c "import sys;from rotkehlchen.db.dbhandler import detect_sqlcipher_version; version = detect_sqlcipher_version();sys.exit(0) if version == 4 else sys.exit(1)"

if (-not ($LASTEXITCODE -eq 0)) {
    echo "SQLCipher version verification failed"
    exit 1;
}

$SETUP_VERSION = (python setup.py --version) | Out-String

if (Test-Path build -PathType Container) {
    Remove-Item -Recurse -Force build
}

if (Test-Path rotkehlchen_py_dist -PathType Container) {
    Remove-Item -Recurse -Force rotkehlchen_py_dist
}

pyinstaller --noconfirm --clean --distpath rotkehlchen_py_dist rotkehlchen.spec

if (-not ($LASTEXITCODE -eq 0)) {
    echo "PyInstaller execution was not sucessful"
    exit 1;
}

$BACKEND_BINARY = @(Get-ChildItem -Path $PWD\rotkehlchen_py_dist -Filter *.exe -Recurse -File -Name)[0]

if (-not ($BACKEND_BINARY)) {
    echo "The backend binary was not found"
    exit 1
}

Invoke-Expression "$PWD\rotkehlchen_py_dist\$BACKEND_BINARY version" | Out-String

if (-not ($LASTEXITCODE -eq 0)) {
    echo "Backend test start failed"
    exit 1;
}

echo "Packaging the electron application"

cd frontend\app
npm ci
if (-not ($LASTEXITCODE -eq 0)) {
    echo "Restoring the node dependencies with npm ci failed"
    exit 1;
}

npm run electron:build
if (-not ($LASTEXITCODE -eq 0)) {
    echo "The build step failed"
    exit 1;
}

$BINARY_NAME = @(Get-ChildItem -Path $PWD\dist -Filter *.exe -Recurse -File -Name)[0]

if (-not ($BINARY_NAME)) {
    echo "The app binary was not found"
    exit 1
}

cd dist

$APP_BINARY = "$PWD\$BINARY_NAME"
$APP_CHECKSUM = "$PWD\$BINARY_NAME.sha512"

Get-FileHash $APP_BINARY -Algorithm SHA512 | Select-Object Hash | foreach {$_.Hash} | Out-File -FilePath $APP_CHECKSUM

if ($Env:CI) {
    echo "::set-output name=binary::$($APP_BINARY)"
    echo "::set-output name=checksum::$($APP_CHECKSUM)"
}

echo "Rotki $SETUP_VERSION was build successfully"
