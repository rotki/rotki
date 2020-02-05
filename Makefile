lint:
	flake8 rotkehlchen/ tools/data_faker
	mypy rotkehlchen/ tools/data_faker
	pylint --rcfile .pylint.rc rotkehlchen/ tools/data_faker

clean:
	rm -rf build/ rotkehlchen_py_dist/ htmlcov/ rotkehlchen.egg-info/ *.dmg electron-app/dist/
