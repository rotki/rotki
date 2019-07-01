System Requirements and Installation Guide
##################################################
.. toctree::
  :maxdepth: 2


Introduction
============

The easiest way to start Rotkehlchen is to download the packaged binary for your Operating system. For now only Linux and OSX is supported. To see how to do this go to the :ref:`next section <packaged_binaries>`.


.. _packaged_binaries:

Packaged Binaries
=================

Linux
*****

Go to the `releases <https://github.com/rotkehlchenio/rotkehlchen/releases>`_ page and download the linux-x64 package from the `latest release <https://github.com/rotkehlchenio/rotkehlchen/releases/latest>`_.

Unzip it in a directory of your choice. In the root directory of the unzipped archive there is a ``rotkehlchen`` executable. Run it via the terminal to start rotkehlchen.

OSX
***

Go to the `releases <https://github.com/rotkehlchenio/rotkehlchen/releases>`_ page and download the darwin-x64 package from the `latest release <https://github.com/rotkehlchenio/rotkehlchen/releases/latest>`_.

Unzip it in a directory of your choice. In the root directory of the unzipped archive there is a `rotkehlchen` executable. Run it **from a terminal window** to start rotkehlchen. Clicking on it **will not work**.

Build from Source
=================

Linux
*****

Make sure you have `node.js <https://nodejs.org/en/>`_ and `npm <https://www.npmjs.com/>`_. If you don't, use your linux distro's package manager to get them.

Get `zeromq <http://zeromq.org/>`_ using the package manager of your distro. For example here is the package in `Archlinux <https://www.archlinux.org/packages/community/x86_64/zeromq/>`_ and in `Ubuntu <https://packages.ubuntu.com/source/trusty/libs/zeromq>`_.

Also get `sqlcipher <https://www.zetetic.net/sqlcipher/>`_:

- If you're running Archlinux you can install the `package <https://www.archlinux.org/packages/community/x86_64/sqlcipher/>`_ with ``pacman``.

- If you're running Ubuntu you will need to install `libsqlcipher-dev <https://packages.ubuntu.com/trusty/libdevel/libsqlcipher-dev>`_ with ``apt-get`` instead.

Install electron and any other npm dependencies by::

    npm install
    npm rebuild zeromq --runtime=electron --target=3.0.0

Create a new `virtual environment <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_ to install all the python dependencies. If you don't have ``mkvirtualenv`` then check how to get it depending on your distribution. `Here <http://exponential.io/blog/2015/02/10/install-virtualenv-and-virtualenvwrapper-on-ubuntu/>`_ is a guide for Ubuntu and `here <https://wiki.archlinux.org/index.php/Python/Virtual_environment>`_ is one for ArchLinux::

    mkvirtualenv rotkehlchen

Then install all the python requirements by doing::

    pip install -r requirements.txt

If you want to also have the developer requirements in order to develop rotkehlchen
then do::

    pip install -r requirements_dev.txt

Now to start the application you need to type ``npm start``.

If you get runtime errors about a Node version mismatch, you can try to rebuild the electron
modules like this:::

    ./node_modules/.bin/electron-rebuild

OSX
***

The tl;dr version is:
- install sqlcipher
- use a virtual env with python 3.7.x
- make sure pip installed everything it says it installed
- get your node under control with nvm. It has been tested with 8.9

The following recipe has been tested using `Anaconda <https://conda.io>`_. `VirtualEnv <https://virtualenv.pypa.io>`_ works as well, refer to the documentations of those projects to install and use them.

Rotkehlchen uses an encrypted database called `SQLCipher <https://www.zetetic.net/sqlcipher/>`_. Before we can proceed, we need to install it. Homebrew makes it simple:::

    $ brew update && brew install sqlcipher

Also these are some dependencies that may or may not be properly installed in your system so make sure you have them.::

    $ brew install zmq
    $ brew install gmp

If you wish to use Conda, use the following commands:::

    $ brew cask install caskroom/cask/anaconda
    $ echo "export PATH=$PATH:/usr/local/anaconda3/bin" >> ~/.bash_profile
    $ echo ". /usr/local/anaconda3/etc/profile.d/conda.sh" >> ~/.bash_profile
    $ source ~/.bash_profile
    $ conda create python=3.7 --name rotkehlchen
    $ conda activate rotkehlchen

If you wish to use Virtualenvwrapper use the following::

    $ pip install virtualenv
    $ pip install virtualenvwrapper

And add the following to your shell startup file, assuming virtualenvwrapper was installed in ``/usr/local/bin``::

    export WORKON_HOME=$HOME/.virtualenvs
    export PROJECT_HOME=$HOME/Devel
    source /usr/local/bin/virtualenvwrapper.sh

Before using `pip`, let´s ensure we have the latest version:::

    $ pip install --upgrade pip

Install all the requirements:::

    $ sudo pip install -r requirements.txt

If you want to also have the developer requirements in order to develop rotkehlchen
then do:::

    $ pip install -r requirements_dev.txt

.. NOTE::
   Make sure that pysqlcipher3 is properly installed. If ``$ pip freeze | grep pysqlcipher3`` returns nothing for you then it was not installed. Try to manually install only that dependency with the verbose option to see where it fails. ``$ pip install pysqlcipher3 -v``. If it fails at the stage of finding the library for ``-lsqlcipher`` then ``brew install sqlciper`` did not place the installed lib directory to the ``LIBRARY_PATH`` and you will have to do it manually. For example if ``sqlcipher`` was installed at ``/usr/local/Cellar/sqlcipher/3.4.2/`` then use pip install this way::
     $ LIBRARY_PATH=/usr/local/Cellar/sqlcipher/3.4.2/lib pip install pysqlcipher3.

Rotkehlchen uses electron, we need to install it. To do so you need ``node.js`` and ``npm``. If you don't have it use homebrew to install it::

    $ brew install node

Almost there, we can now install all the NodeJS dependencies. Using a recent NodeJS version such as 8.9.x, it should be smooth. Also since npm uses gyp and gyp requires python 2.7 make sure to set it up appropriately before invoking npm::

    $ npm config set python python2.7
    $ npm install
    $ PYTHON=/usr/bin/python2.7 ./node_modules/.bin/electron-rebuild

You can now start Rotkehlchen:::

    $ npm start
