lint:
	flake8 rotkehlchen/ tools/data_faker
	mypy rotkehlchen/ tools/data_faker --ignore-missing-imports --warn-unreachable
	pylint --rcfile .pylint.rc rotkehlchen/ tools/data_faker
