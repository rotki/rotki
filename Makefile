lint:
	flake8 rotkehlchen/ tools/data_faker
	mypy rotkehlchen/ tools/data_faker --install-types --non-interactive
	pylint --rcfile .pylint.rc rotkehlchen/ tools/data_faker

clean:
	rm -rf build/ rotkehlchen_py_dist/ htmlcov/ rotkehlchen.egg-info/ *.dmg frontend/app/dist/

docker-image:
	packaging/docker-image.sh
