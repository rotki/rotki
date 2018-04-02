#!/usr/bin/env sh

if [[ $TRAVIS_OS_NAME == 'osx' ]]; then
    brew update && brew install sqlcipher
    # Per the `pyenv homebrew recommendations <https://github.com/yyuu/pyenv/wiki#suggested-build-environment>`_.
    brew install openssl readline
    # See https://docs.travis-ci.com/user/osx-ci-environment/#A-note-on-upgrading-packages.
    # I didn't do this above because it works and I'm lazy.
    brew outdated pyenv || brew upgrade pyenv
    # virtualenv doesn't work without pyenv knowledge. venv in Python 3.3
    # doesn't provide Pip by default. So, use `pyenv-virtualenv <https://github.com/yyuu/pyenv-virtualenv/blob/master/README.md>`_.
    brew install pyenv-virtualenv
    pyenv install $PYTHON
    # I would expect something like ``pyenv init; pyenv local $PYTHON`` or
    # ``pyenv shell $PYTHON`` would work, but ``pyenv init`` doesn't seem to
    # modify the Bash environment. ??? So, I hand-set the variables instead.
    export PYENV_VERSION=$PYTHON
    export PATH="/Users/travis/.pyenv/shims:${PATH}"
    pyenv virtualenv $PYTHON venv
    echo `ls`
    pyenv activate venv
    # A manual check that the correct version of Python is running.
    python --version
else
    # Ubuntu
    sudo apt-get install -y libsqlcipher-dev libzmq-dev
fi
