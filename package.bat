Rem Perform sanity checks before pip install
pip install packaging
Rem We use npm ci. That needs npm >= 5.7.0
npm --version | python -c "import sys;npm_version=sys.stdin.readlines()[0].rstrip('\n');from packaging import version;supported=version.parse(npm_version) >= version.parse('5.7.0');sys.exit(1) if not supported else sys.exit(0);"
if %errorlevel% neq 0 (
   echo "package.bat - ERROR: The system's npm version is not >= 5.7.0 which is required for npm ci"
   exit /b %errorlevel%
)
Rem uninstall packaging package since it's no longer required
pip uninstall -y packaging

Rem Install the rotkehlchen package and pyinstaller. Needed by the pyinstaller
pip install -e .
pip install pyinstaller==3.5
if %errorlevel% neq 0 (
   echo "package.bat - ERROR - Pip install step failed"
   exit /b %errorlevel%
)
Rem also for Windows we expect a pysqlcipher3 project to exist to properly
Rem build and install that into the venv since pip install pysqlcipher3 without
Rem having manually compiled sqlcipher will not work.
Rem Reference: https://rotki.readthedocs.io/en/latest/installation_guide.html#sqlcipher-and-pysqlcipher3
cd ../pysqlcipher3
python setup.py build
python setup.py install
cd ../rotkehlchen

Rem Perform sanity checks that need pip install
python -c "import sys;from rotkehlchen.db.dbhandler import detect_sqlcipher_version; version = detect_sqlcipher_version();sys.exit(0) if version == 4 else sys.exit(1)"
if %errorlevel% neq 0 (
   echo "package.bat - ERROR: The packaging system's sqlcipher version is not >= v4"
   exit /b %errorlevel%
)

for /f %%i in ('python setup.py --version') do set ROTKEHLCHEN_VERSION=%%i

Rem Use pyinstaller to package the python app
IF EXIST build rmdir build /s /Q
IF EXIST rotkehlchen_py_dist rmdir rotkehlchen_py_dist /s /Q
pyinstaller --noconfirm --clean --distpath rotkehlchen_py_dist rotkehlchen.spec
if %errorlevel% neq 0 (
   echo "package.bat - ERROR - pyinstaller step failed"
   exit /b %errorlevel%
)

Rem Sanity check that the generated python executable works
FOR %%F IN (rotkehlchen_py_dist/*.exe) DO (
 set PYINSTALLER_GENERATED_EXECUTABLE=%%F
 goto found
)
:found
echo "%PYINSTALLER_GENERATED_EXECUTABLE%"

call rotkehlchen_py_dist\%PYINSTALLER_GENERATED_EXECUTABLE% version
if %errorlevel% neq 0 (
   echo "package.bat - ERROR - The generated python executable does not work properly"
   exit /b %errorlevel%
)

CD electron-app/

Rem npm stuff
call npm ci
if %errorlevel% neq 0 (
   echo "package.bat - ERROR - npm ci step failed"
   exit /b %errorlevel%
)

call npm run electron:build
if %errorlevel% neq 0 (
   echo "ERROR - npm build step failed"
   exit /b %errorlevel%
)

echo "SUCCESS - rotkehlchen is now packaged for windows!"
