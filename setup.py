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
requirements = [str(r) for r in parse_requirements(requirements)]

version = '1.19.0'  # Do not edit: this is maintained by bumpversion (see .bumpversion.cfg)

setup(
    name='rotkehlchen',
    author='Rotki Solutions GmbH',
    author_email='info@rotki.com',
    description='Acccounting, asset management and tax report helper for cryptocurrencies',
    license='AGPL-3',
    keywords='accounting tax-report portfolio asset-management cryptocurrencies',
    url='https://github.com/rotki/rotki',
    packages=find_packages('.'),
    package_data={
        # TODO: Investigate if it's needed. rotkehlchen.spec is where files seem to be copied
        'rotkehlchen': ['data/*.json', 'data/*.meta', 'data/*.db'],
    },
    python_requires='>=3.6',
    install_requires=requirements,
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
