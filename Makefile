COMMON_LINT_PATHS = rotkehlchen/ rotkehlchen_mock/ package.py docs/conf.py
TOOLS_LINT_PATH = tools/
ALL_LINT_PATHS = $(COMMON_LINT_PATHS) $(TOOLS_LINT_PATH)

lint:
	ruff check $(ALL_LINT_PATHS)
	double-indent --dry-run $(ALL_LINT_PATHS)
	./tools/find-duplicate-constants/run.sh
	mypy $(COMMON_LINT_PATHS) --install-types --non-interactive
	@set -e; \
	(PYRIGHT_PYTHON_IGNORE_WARNINGS=1 pyright $(COMMON_LINT_PATHS)) & pyright_pid=$$!; \
	(pylint --rcfile .pylint.rc $(ALL_LINT_PATHS)) & pylint_pid=$$!; \
	pyright_status=0; pylint_status=0; \
	wait $$pyright_pid || pyright_status=$$?; \
	wait $$pylint_pid || pylint_status=$$?; \
	if [ $$pyright_status -ne 0 ] || [ $$pylint_status -ne 0 ]; then exit 1; fi
	python tools/lint_checksum_addresses.py
	python tools/lint_new_logging_fstrings.py


format:
	ruff check $(ALL_LINT_PATHS) --fix
	double-indent $(ALL_LINT_PATHS)
	python tools/lint_checksum_addresses.py --fix


clean:
	rm -rf build/ dist/ rotkehlchen_py_dist/ htmlcov/ rotkehlchen.egg-info/ *.dmg frontend/app/dist/ frontend/app/build/


docker-image:
	packaging/build-docker.sh


test-assets:
	uv run pytest -m asset_test rotkehlchen/tests

create-cassettes:
	RECORD_CASSETTES=true uv run pytest -m vcr rotkehlchen/tests

create-cassette:
	RECORD_CASSETTES=true uv run pytest -m vcr $(filter-out $@,$(MAKECMDGOALS))



# A macro to catch extra makefile arguments and use them elsewhere
# https://stackoverflow.com/a/6273809/110395
%:
	@:
