#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pathlib

from pkg_resources import parse_requirements
from setuptools import find_packages, setup

# Repository root directory for use with reading files
directory = pathlib.Path(__file__).parent

# Load install_requires from requirements.txt.
# https://stackoverflow.com/a/59971236/4651668
requirements = directory.joinpath('requirements.txt').read_text()
requirements = [x for x in requirements.split('\n') if not x.startswith('git+')]
requirements = [str(r) for r in parse_requirements(requirements)]
requirements.append('flask-restful')
dependency_links = [
    'git+git://github.com/flask-restful/flask-restful@fc9b34c39472284a57c50d94fec5b51fe8d71e14#egg=flask-restful'  # noqa: E501
]

version = '1.16.2'  # Do not edit: this is maintained by bumpversion (see .bumpversion.cfg)

setup(
    name='rotkehlchen',
    author='Rotki Solutions GmbH',
    author_email='info@rotki.com',
    description='Acccounting, asset management and tax report helper for cryptocurrencies',
    license='BSD-3',
    keywords='accounting tax-report portfolio asset-management cryptocurrencies',
    url='https://github.com/rotki/rotki',
    packages=find_packages('.'),
    package_data={
        # TODO: Investigate if it's needed. rotkehlchen.spec is where files seem to be copied
        'rotkehlchen': ['data/*.json', 'data/*.meta', 'data/*.db'],
    },
    python_requires='>=3.6',
    install_requires=requirements,
    dependency_links=dependency_links,
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    long_description=directory.joinpath('README.md').read_text(),
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Topic :: Utilities',
    ],
    entry_points={
        'console_scripts': [
            'rotkehlchen = rotkehlchen.__main__:main',
        ],
    },
)
