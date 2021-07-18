lint:
	flake8 rotkehlchen/ tools/data_faker
	yes | mypy rotkehlchen/ tools/data_faker --install-types || true
	mypy rotkehlchen/ tools/data_faker
	pylint --rcfile .pylint.rc rotkehlchen/ tools/data_faker

clean:
	rm -rf build/ rotkehlchen_py_dist/ htmlcov/ rotkehlchen.egg-info/ *.dmg frontend/app/dist/

docker-image:
	packaging/docker-image.sh
