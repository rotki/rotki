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


install_requirements = list(set(
    requirement.strip() for requirement in open('requirements.txt')
    if not requirement.lstrip().startswith('#')
))

version = '0.1.0'  # Do not edit: this is maintained by bumpversion (see .bumpversion.cfg)
def read_version_from_git():
    try:
        import shlex
        git_version, _ = subprocess.Popen(
            shlex.split('git describe --tags --abbrev=8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        ).communicate()
        # Popen returns bytes
        git_version = git_version.decode()

        if git_version.startswith('v'):
            git_version = git_version[1:]

        git_version = git_version.strip()
        # if this is has commits after the tag, it's a prerelease:
        if git_version.count('-') == 2:
            _, _, commit = git_version.split('-')
            if commit.startswith('g'):
                commit = commit[1:]
            return '{}+git.r{}'.format(version, commit)
        elif git_version.count('.') == 2:
            return git_version
        else:
            return version
    except BaseException as e:
        print('could not read version from git: {}'.format(e))
        return version

setup(
    name='rotkehlchen',
    version=read_version_from_git(),
    author='Lefteris Karapetsas',
    author_email='lefteris@refu.co',
    description=('Acccounting, asset management and tax report helper for cryptocurrencies'),
    license='BSD-3',
    keywords='accounting tax-report portfolio asset-management cryptocurrencies',
    url='https://github.com/rotkehlchenio/rotkehlchen',
    packages=['rotkehlchen'],
    install_requires=install_requirements,
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
