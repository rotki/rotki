import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


install_requirements = [
    # Should be same as requirements.txt
    'zerorpc',
    'matplotlib'
]

setup(
    name='Rotkelchen',
    version='0.0.1',
    author='Lefteris Karapetsas',
    author_email='lefteris@refu.co',
    description=('Acccounting, trading and portfolio helper for cryptocurrencies'),
    license='Private',
    keywords='accounting trading portfolio cryptocurrencies',
    url='http://packages.python.org/an_example_pypi_project',
    packages=['rotkelchen', 'tests'],
    install_requires=install_requirements,
    long_description=read('README.md'),
    classifiers=[
        'Development Status :: 1 - Planning',
        'Topic :: Utilities',
    ],
)
