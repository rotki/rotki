COMMON_LINT_PATHS = rotkehlchen/ rotkehlchen_mock/ package.py docs/conf.py packaging/docker/entrypoint.py
TOOLS_LINT_PATH = tools/
ALL_LINT_PATHS = $(COMMON_LINT_PATHS) $(TOOLS_LINT_PATH)

lint:
	ruff check $(ALL_LINT_PATHS)
	double-indent --dry-run $(ALL_LINT_PATHS)
	./tools/find-duplicate-constants/run.sh
	mypy $(COMMON_LINT_PATHS) --install-types --non-interactive
	PYRIGHT_PYTHON_IGNORE_WARNINGS=1 pyright $(COMMON_LINT_PATHS)
	pylint --rcfile .pylint.rc $(ALL_LINT_PATHS)
	python tools/lint_checksum_addresses.py


format:
	ruff check $(ALL_LINT_PATHS) --fix
	double-indent $(ALL_LINT_PATHS)
	python tools/lint_checksum_addresses.py --fix


clean:
	rm -rf build/ dist/ rotkehlchen_py_dist/ htmlcov/ rotkehlchen.egg-info/ *.dmg frontend/app/dist/ frontend/app/build/


docker-image:
	packaging/docker-image.sh


test-assets:
	uv run pytestgeventwrapper.py -m asset_test rotkehlchen/tests

create-cassettes:
	RECORD_CASSETTES=true uv run pytestgeventwrapper.py -m vcr rotkehlchen/tests

create-cassette:
	RECORD_CASSETTES=true uv run pytestgeventwrapper.py -m vcr $(filter-out $@,$(MAKECMDGOALS))



# A macro to catch extra makefile arguments and use them elsewhere
# https://stackoverflow.com/a/6273809/110395
%:
	@:
