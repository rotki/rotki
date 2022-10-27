#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pathlib
from os import environ

from pkg_resources import parse_requirements
from setuptools import find_packages, setup

# Repository root directory for use with reading files
directory = pathlib.Path(__file__).parent

# Load install_requires from requirements.txt.
# https://stackoverflow.com/a/59971236/4651668
requirements = directory.joinpath('requirements.txt').read_text()
requirements = [str(r) for r in parse_requirements(requirements)]

version = '1.26.0'  # Do not edit: this is maintained by bumpversion (see .bumpversion.cfg)

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
        # Data files to package in the Rotki python package wheel. While
        # pyinstaller does not use this list, changes here should be kept in
        # sync with rotkehlchen.spec
        'rotkehlchen': [
            'data/eth_abi.json',
            'data/eth_contracts.json',
            'data/all_assets.json',
            'data/all_assets.meta',
            'data/uniswapv2_lp_tokens.json',
            'data/uniswapv2_lp_tokens.meta',
            'data/global.db',
            'data/globaldb_v2_v3_assets.sql',
            'data/nodes.json',
            'chain/ethereum/modules/dxdaomesa/data/contracts.json',
        ],
    },
    python_requires='>=3.9',
    install_requires=requirements,
    use_scm_version={
        'fallback_version': environ.get('PACKAGE_FALLBACK_VERSION') or version,
    },
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
