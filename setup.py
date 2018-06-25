#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


install_requires_replacements = {
    (
        'git+https://github.com/ethereum/eth-typing.git'
        '@a4eba0cd42c34e051ac8818177c8eb95ac67f5b5#egg=eth-typing'
    ): 'eth-typing',
}

install_requirements = list(set(
    install_requires_replacements.get(requirement.strip(), requirement.strip())
    for requirement in open('requirements.txt')
    if not requirement.lstrip().startswith('#')
))

version = '0.3.1'  # Do not edit: this is maintained by bumpversion (see .bumpversion.cfg)

setup(
    name='rotkehlchen',
    author='Lefteris Karapetsas',
    author_email='lefteris@refu.co',
    description=('Acccounting, asset management and tax report helper for cryptocurrencies'),
    license='BSD-3',
    keywords='accounting tax-report portfolio asset-management cryptocurrencies',
    url='https://github.com/rotkehlchenio/rotkehlchen',
    packages=['rotkehlchen'],
    install_requires=install_requirements,
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    long_description=read('README.md'),
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
