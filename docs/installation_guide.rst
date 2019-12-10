System Requirements and Installation Guide
##################################################
.. toctree::
  :maxdepth: 2


Introduction
*************

The easiest way to start Rotki is to download the packaged binary for your Operating system. For now only Linux and OSX is supported. To see how to do this go to the :ref:`next section <packaged_binaries>`.


.. _packaged_binaries:

Packaged Binaries
******************

Linux
==========

Go to the `releases <https://github.com/rotki/rotki/releases>`_ page and download the linux-x64 package from the `latest release <https://github.com/rotki/rotki/releases/latest>`_.

Unzip it in a directory of your choice. In the root directory of the unzipped archive there is a ``rotki`` executable. Run it via the terminal to start rotki.

Troubleshooting
------------------

If you get a problem when starting the application or during its usage please open an issue in Github and include all logs that can be found in `~/.config/rotkehlchen/`.

OSX
========

Go to the `releases <https://github.com/rotki/rotki/releases>`_ page and download the darwin-x64 package from the `latest release <https://github.com/rotki/rotki/releases/latest>`_.

Click on the dmg installer and when prompted drag the Rotki logo to your Applications. This will install the application and once finished you can select Rotki from your applications folder and launch it.

Troubleshooting
----------------

If you get a problem when starting the application or during its usage please open an issue in Github and include all logs that can be found in `~/Library/Logs/rotkehlchen`.


Windows
==========

Go to the `releases <https://github.com/rotki/rotki/releases>`_ page and download the win32-x64 package from the `latest release <https://github.com/rotki/rotki/releases/latest>`_.

Unzip it in a folder of your choice. In the root directory of the unzipped archive there is a ``rotki`` executable. Double click it to start rotki.

Troubleshooting
---------------

If you get "The python backend crushed" or any other error please run the executable via the Command Prompt. Then provide us with the output that is visible in the prompt and this will help us debug your issue.

You should also include all logs that can be found in `%APPDATA%/rotki/`.


Build from Source
******************

Linux
=========

Make sure you have `node.js <https://nodejs.org/en/>`_ and `npm <https://www.npmjs.com/>`_. If you don't, use your linux distro's package manager to get them.

Get `zeromq <http://zeromq.org/>`_ using the package manager of your distro. For example here is the package in `Archlinux <https://www.archlinux.org/packages/community/x86_64/zeromq/>`_ and in `Ubuntu <https://packages.ubuntu.com/source/trusty/libs/zeromq>`_.

Also get `sqlcipher <https://www.zetetic.net/sqlcipher/>`_:

- If you're running Archlinux you can install the `package <https://www.archlinux.org/packages/community/x86_64/sqlcipher/>`_ with ``pacman``.

- If you're running Ubuntu you will need to install `libsqlcipher-dev <https://packages.ubuntu.com/trusty/libdevel/libsqlcipher-dev>`_ with ``apt-get`` instead.

Install electron and any other npm dependencies by::

    npm ci
    npm rebuild zeromq --runtime=electron --target=3.0.0

Create a new `virtual environment <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_ to install all the python dependencies. If you don't have ``mkvirtualenv`` then check how to get it depending on your distribution. `Here <http://exponential.io/blog/2015/02/10/install-virtualenv-and-virtualenvwrapper-on-ubuntu/>`_ is a guide for Ubuntu and `here <https://wiki.archlinux.org/index.php/Python/Virtual_environment>`__ is one for ArchLinux::

    mkvirtualenv rotki

Then install all the python requirements by doing::

    pip install -r requirements.txt

If you want to also have the developer requirements in order to develop rotki
then do::

    pip install -r requirements_dev.txt

Now to start the application you need to type ``npm start``.

If you get runtime errors about a Node version mismatch, you can try to rebuild the electron
modules like this:::

    ./node_modules/.bin/electron-rebuild

OSX
=====

The tl;dr version is:
- install sqlcipher
- use a virtual env with python 3.7.x
- make sure pip installed everything it says it installed
- get your node under control with nvm. It has been tested with 8.9

The following recipe has been tested using `Anaconda <https://conda.io>`_. `VirtualEnv <https://virtualenv.pypa.io>`_ works as well, refer to the documentations of those projects to install and use them.

Rotki uses an encrypted database called `SQLCipher <https://www.zetetic.net/sqlcipher/>`_. Before we can proceed, we need to install it. Homebrew makes it simple:::

    $ brew update && brew install sqlcipher

Also these are some dependencies that may or may not be properly installed in your system so make sure you have them.::

    $ brew install zmq
    $ brew install gmp

If you wish to use Conda, use the following commands:::

    $ brew cask install caskroom/cask/anaconda
    $ echo "export PATH=$PATH:/usr/local/anaconda3/bin" >> ~/.bash_profile
    $ echo ". /usr/local/anaconda3/etc/profile.d/conda.sh" >> ~/.bash_profile
    $ source ~/.bash_profile
    $ conda create python=3.7 --name rotki
    $ conda activate rotki

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

If you want to also have the developer requirements in order to develop rotki
then do:::

    $ pip install -r requirements_dev.txt

.. NOTE::
   Make sure that pysqlcipher3 is properly installed. If ``$ pip freeze | grep pysqlcipher3`` returns nothing for you then it was not installed. Try to manually install only that dependency with the verbose option to see where it fails. ``$ pip install pysqlcipher3 -v``. If it fails at the stage of finding the library for ``-lsqlcipher`` then ``brew install sqlciper`` did not place the installed lib directory to the ``LIBRARY_PATH`` and you will have to do it manually. For example if ``sqlcipher`` was installed at ``/usr/local/Cellar/sqlcipher/3.4.2/`` then use pip install this way::
     $ LIBRARY_PATH=/usr/local/Cellar/sqlcipher/3.4.2/lib pip install pysqlcipher3.

Rotki uses electron, we need to install it. To do so you need ``node.js`` and ``npm``. If you don't have it use homebrew to install it::

    $ brew install node

Almost there, we can now install all the NodeJS dependencies. Using a recent NodeJS version such as 8.9.x, it should be smooth. Also since npm uses gyp and gyp requires python 2.7 make sure to set it up appropriately before invoking npm::

    $ npm config set python python2.7
    $ npm ci
    $ PYTHON=/usr/bin/python2.7 ./node_modules/.bin/electron-rebuild

You can now start Rotki:::

    $ npm start

Windows
==========

This is the guide on how to manually build rotki binaries in Windows from source.

Dependencies
-------------

Python and git
^^^^^^^^^^^^^^^^^^^^

Get `python 3.7 <https://www.python.org/downloads/release/python-374/>`_.

Make sure it's 64 bit if you are in 64-bit windows!!!!!

If it's not in the Path `add both directories to the path <https://docs.alfresco.com/4.2/tasks/fot-addpath.html>`_:

``C:\Users\lefteris\AppData\Local\Programs\Python\Python37;C:\Users\lefteris\AppData\Local\Programs\Python\Python37\Scripts``

Get `latest git <https://gitforwindows.org/>`_.

Setup a python virtualenvironment. If you don't know how to do it in windows `here <http://timmyreilly.azurewebsites.net/python-pip-virtualenv-installation-on-windows/>`__ is a good guide.

Make sure you have `pip installed <https://pip.pypa.io/en/stable/installing/#do-i-need-to-install-pip>`_.

Also make sure you have the Microsoft visual studio build tools. Check the troubleshooting guide's relevant section :ref:`microsoft_visual_studio_build_tools_required`.


Sqlcipher and pysqlcipher3
^^^^^^^^^^^^^^^^^^^^^^^^^^

`Here <https://github.com/sqlitebrowser/sqlitebrowser/wiki/Win64-setup-%E2%80%94-Compiling-SQLCipher>`_ is a good guide on how to compile SQLCipher for windows.

The guide also requires you to get ``OpenSSL``. You can do that from `here <https://slproweb.com/products/Win32OpenSSL.html>`__.
Make sure it's for the same architecture as the rest. 32/64 bit. At the installer change the location to the bin directory as the tutorial says. Make sure that ``-IC:\dev\OpenSSL-Win64\include`` and all other relevant options point to the actual location where openssl was installed. Also pay attention to the rest of the stuff in the tutorial warns to change in ``Makefile.msc``.


Then you can go to ``pysqlcipher3`` and edit the ``setup.py`` file to include the location of the headers and the libraries you just compiled. Add the following to the extension that is being built.::


    library_dirs=[r'C:\Users\yourusername\w\sqlcipher'],
    include_dirs=[r'C:\Users\yourusername\w'],

Obviously replace ``yourusername`` with whatever you are using. And then do ``python setup.py build`` and ``python setup.py install``.


Nodejs
^^^^^^^^

Get node.js from `here <https://nodejs.org/en/download/>`__.

Installation
------------

Inside rotki install normally like you would in linux  ... but you got to either copy ``slqcipher.dll`` in the rotki directory or put it in the directory where windows searches for DLLs.

Troubleshooting
---------------

anyapi-ms-win-crt-runtime missing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you get ``anyapi-ms-win-crt-runtime-l1-1-0.dll is missing`` error when running python follow `this <https://www.ghacks.net/2017/06/06/the-program-cant-start-because-api-ms-win-crt-runtime-l1-1-0-dll-is-missing/>`__ guide to resolve it.

.. _microsoft_visual_studio_build_tools_required:

Microsoft Visual C++ 14.0 is required
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you get::

    building 'gevent.libev.corecext' extension                                                                                                                                                                                                                            
    error: Microsoft Visual C++ 14.0 is required. Get it with "Microsoft Visual C++ Build Tools": https://visualstudio.microsoft.com/downloads/                 


Then go `here <https://visualstudio.microsoft.com/downloads/>`__ and get the microsoft visual studio build tools and install them. The specific parts of the tools that need to be installed can be seen in `this SO answer <https://stackoverflow.com/questions/29846087/microsoft-visual-c-14-0-is-required-unable-to-find-vcvarsall-bat/49986365#49986365>`__.

You also need to add them to the path. The tools were probably installed here: ``C:\Program Files (x86)\Microsoft Visual Studio\2017\BuildTools\Common7\Tools``
Environment variable should be: ``VS140COMNTOOLS``


Alternative dependencies with sqlciper amalgamation
-------------------------------------------------------------

This is a not so well tested way but some work has been done by cryptomental in `this <https://github.com/rotki/rotki/issues/28>`__ issue for it. With the amalgamation you can obtain all sqlcipher dependencies precompiled and amalgamated in one big blog. But ... it's tricky, hense not so well tested.

Read the issue for a lot of details and also the ``appveyor.yml`` for what needs to be done to build sqlcipher and keep the following in mind:

1. Replace ``robocopy`` with ``copy -r`` and make sure to copy into python system include and not the venv one.
2. If while building the amalgamation you get: ``"Fatal error: OpenSSL could not be detected!"`` try `this SO answer <https://stackoverflow.com/a/38969408>`__. and make sure to add ``OPENSSL_CONF`` to the environment variables pointing to the location of ``openssl.conf``.
3. In addition copy the amalgamation dir's ssl include folder to the python include folder::

       $ cp -r sqlcipher-amalgamation-3020001/openssl-include/openssl/ /c/Users/lefteris/AppData/Local/Programs/Python/Python37-32/include/openssl

4. Copy the amalgamation dir's ssl libraries to the python lib folder::

       $ cp sqlcipher-amalgamation-3020001/OpenSSL-Win32/* /c/Users/lefteris/AppData/Local/Programs/Python/Python37-32/libs/

   Note it has to be the OpenSSL-Win32 part.
