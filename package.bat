Rem Install the rotkehlchen package and pyinstaller. Needed by the pyinstaller
pip install -e .
pip install pyinstaller
if %errorlevel% neq 0 (
   echo "ERROR - Pip install step failed"
   exit /b %errorlevel%
)

Rem Use pyinstaller to package the python app
IF EXIST build rmdir build /s /Q
IF EXIST rotkehlchen_py_dist rmdir rotkehlchen_py_dist /s /Q
 pyinstaller --noconfirm --clean --distpath rotkehlchen_py_dist rotkehlchen.spec
if %errorlevel% neq 0 (
   echo "ERROR - pyinstaller step failed"
   exit /b %errorlevel%
)

Rem npm stuff
IF EXIST node_modules rmdir node_modules /s /Q
call npm config set python python2.7
call npm install
call npm rebuild zeromq --runtime=electron --target=3.0.0
if %errorlevel% neq 0 (
   echo "ERROR - npm install step failed"
   exit /b %errorlevel%
)

call node_modules/.bin/electron-rebuild
if %errorlevel% neq 0 (
   echo "ERROR - electron rebuild step failed"
   exit /b %errorlevel%
)

call npm run build
if %errorlevel% neq 0 (
   echo "ERROR - npm build step failed"
   exit /b %errorlevel%
)

call node_modules/.bin/electron-packager . --overwrite ^
                                      --ignore="rotkehlchen$" ^
				      --ignore="rotkehlchen.egg-info" ^
				      --ignore="^/tools$" ^
				      --ignore="^/docs$" ^
				      --ignore="^/build$" ^
				      --ignore="appveyor*" ^
				      --ignore="^/.eggs" ^
				      --ignore="^/.github" ^
				      --ignore="^/.coverage" ^
				      --ignore="^/.gitignore" ^
				      --ignore="^/.ignore" ^
				      --ignore=".nvmrc" ^
				      --ignore="^/package-lock.json" ^
				      --ignore="requirements*" ^
				      --ignore="^/rotki_config.json" ^
				      --ignore="^/rotkehlchen.spec" ^
				      --ignore="setup.cfg" ^
				      --ignore="^/stubs" ^
				      --ignore="^/.mypy_cache" ^
				      --ignore=".travis*" ^
				      --ignore="tsconfig*" ^
				      --ignore="tsfmt.json" ^
				      --ignore="tslint.json" ^
				      --ignore="^/.bumpversion.cfg" ^
				      --ignore="^/.mypy_cache/" ^
				      --ignore="^/.coveragerc" ^
				      --ignore="^/.coverage" ^
				      --ignore="^/.env" ^
				      --ignore="^/README.md" ^
				      --ignore="rotkehlchen.log" ^
				      --ignore=".*\.sh" ^
				      --ignore=".*\.py" ^
				      --ignore=".*\.bat" ^
				      --ignore="^/CONTRIBUTING.md" ^
				      --ignore="^/Makefile"

if %errorlevel% neq 0 (
   echo "ERROR - electron-packager step failed"
   exit /b %errorlevel%
)

echo "SUCCESS - rotkehlchen is now packaged for windows!"
