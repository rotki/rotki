lint:
	flake8 rotkehlchen/ tools/data_faker
	mypy rotkehlchen/ tools/data_faker --ignore-missing-imports
	pylint --rcfile .pylint.rc rotkehlchen/ tools/data_faker
