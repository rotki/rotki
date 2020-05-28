System Requirements and Installation Guide
##################################################
.. toctree::
  :maxdepth: 2


Introduction
*************

The easiest way to start Rotki is to download the packaged binary for your Operating system. Linux, OSX and Windows is supported. To see how to do this go to the :ref:`next section <packaged_binaries>`.


.. _packaged_binaries:

Packaged Binaries
******************

Linux
==========

Go to the `releases <https://github.com/rotki/rotki/releases>`_ page and download the linux-x64 appimage from the `latest release <https://github.com/rotki/rotki/releases/latest>`_. Or the ``tar.xz`` file. Whichever you prefer.

If you got the appimage you have to give it the executable permission. Do :code:`chmod +x rotki-linux_x86_64-vx.x.x.AppImage` replacing the ``x`` with the proper version. And then run it.

If you got the tar, unzip it in a directory of your choice. In the root directory of the unzipped archive there is a ``rotki`` executable. Run it via the terminal to start rotki.

Troubleshooting
------------------

If you get a problem when starting the application or during its usage please open an issue in Github and include all logs that can be found in ``~/.config/rotki/logs``.

OSX
========

Go to the `releases <https://github.com/rotki/rotki/releases>`_ page and download the darwin-x64 dmg package from the `latest release <https://github.com/rotki/rotki/releases/latest>`_.

Click on the dmg installer and when prompted drag the Rotki logo to your Applications. This will install the application and once finished you can select Rotki from your applications folder and launch it.

If your OSX version does not allow you to open the application you will have to go to your OS settings and insert an exception for Rotki to let it run. `Here <https://ccm.net/faq/29619-mac-os-x-run-apps-downloaded-from-unknown-sources>`__ is a guide.

Troubleshooting
----------------

If you get a problem when starting the application or during its usage please open an issue in Github and include all logs that can be found in ``~/Library/Application Support/rotki/logs``.


Windows
==========

Go to the `releases <https://github.com/rotki/rotki/releases>`_ page and download the win32-x64 package from the `latest release <https://github.com/rotki/rotki/releases/latest>`_.

Unzip it in a folder of your choice. In the root directory of the unzipped archive there is a ``rotki`` executable. Double click it to start rotki.

Troubleshooting
---------------

If you get "The python backend crashed" or any other error please run the executable via the Command Prompt. Then provide us with the output that is visible in the prompt and this will help us debug your issue.

You should also include all logs that can be found in ``<WindowsDrive>:\Users\<User>\Roaming\rotki\logs\`` (``%APPDATA%\rotki\logs``).


Build from Source
******************

Linux
=========

Make sure you have `node.js <https://nodejs.org/en/>`_ and `npm <https://www.npmjs.com/>`_. If you don't, use your linux distro's package manager to get them.

Get `sqlcipher <https://www.zetetic.net/sqlcipher/>`_:

- If you're running Archlinux you can install the `package <https://www.archlinux.org/packages/community/x86_64/sqlcipher/>`_ with ``pacman``.

- If you're running Ubuntu you will need to install `libsqlcipher-dev <https://packages.ubuntu.com/trusty/libdevel/libsqlcipher-dev>`_ with ``apt-get`` instead.

Install electron and any other npm dependencies by::

    cd frontend/app
    npm ci

Create a new `virtual environment <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_ to install all the python dependencies. If you don't have ``mkvirtualenv`` then check how to get it depending on your distribution. `Here <http://exponential.io/blog/2015/02/10/install-virtualenv-and-virtualenvwrapper-on-ubuntu/>`__ is a guide for Ubuntu and `here <https://wiki.archlinux.org/index.php/Python/Virtual_environment>`__ is one for ArchLinux::

    mkvirtualenv rotki

Then install all the python requirements by doing::

    pip install -r requirements.txt

If you want to also have the developer requirements in order to develop rotki
then do::

    pip install -r requirements_dev.txt

Since the electron application is located in a different directory you also need to do::

    pip install -e .

Now to start the application you need to change to the ``frontend/app`` directory and type ``npm run electron:serve``.

OSX
=====

The tl;dr version is:
- install sqlcipher
- use a virtual env with python 3.7.x
- make sure pip installed everything it says it installed
- get your node under control with nvm. It has been tested with 8.9

The following recipe has been tested using `Anaconda <https://conda.io>`_. `VirtualEnv <https://virtualenv.pypa.io>`_ works as well, refer to the documentations of those projects to install and use them.

Rotki uses an encrypted database called `SQLCipher <https://www.zetetic.net/sqlcipher/>`_. Before we can proceed, we need to install it. Homebrew makes it simple::

    $ brew update && brew install sqlcipher

Also these are some dependencies that may or may not be properly installed in your system so make sure you have them. ::

    $ brew install gmp

If you wish to use Conda, use the following commands::

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

Before using `pip`, let´s ensure we have the latest version::

    $ pip install --upgrade pip

Install all the requirements::

    $ sudo pip install -r requirements.txt

If you want to also have the developer requirements in order to develop rotki
then do::

    $ pip install -r requirements_dev.txt

.. NOTE::
   Make sure that pysqlcipher3 is properly installed. If ``$ pip freeze | grep pysqlcipher3`` returns nothing for you then it was not installed. Try to manually install only that dependency with the verbose option to see where it fails. ``$ pip install pysqlcipher3 -v``. If it fails at the stage of finding the library for ``-lsqlcipher`` then ``brew install sqlciper`` did not place the installed lib directory to the ``LIBRARY_PATH`` and you will have to do it manually. For example if ``sqlcipher`` was installed at ``/usr/local/Cellar/sqlcipher/3.4.2/`` then use pip install this way:
     ``$ LIBRARY_PATH=/usr/local/Cellar/sqlcipher/3.4.2/lib pip install pysqlcipher3``.

Since the electron application is located in a different directory you also need to do::

    pip install -e .

Rotki uses electron, we need to install it. To do so you need ``node.js`` and ``npm``. If you don't have it use homebrew to install it::

    $ brew install node

Almost there, we can now install all the NodeJS dependencies. Using a recent NodeJS version such as 8.9.x, it should be smooth. Also since npm uses gyp and gyp requires python 2.7 make sure to set it up appropriately before invoking npm::

    $ npm ci

You can now go to the ``frontend/app`` directory and start Rotki::

    $ npm run electron:serve

Windows
==========

This is a guide on how to set up a rotki development environment in Windows from source.

Dependencies
-------------

Node & npm
^^^^^^^^^^^^^^^^^^^^
Install `node (includes npm) <https://nodejs.org/en/download/>`_.

Python
^^^^^^^^^^^^^^^^^^^^

1. Get `python 3.7 <https://www.python.org/downloads/release/python-374/>`_ (3.7 is required due to some rotki dependencies). Make sure to download the 64-bit version of python if your version of Windows is 64-bit! If you're unsure of what Windows version you have, you can check in Control Panel -> System and Security -> System.
2. For some reason python does not always install to the Path variable in Windows. To ensure you have the necessary python directories referenced, go to Control Panel -> System -> Advanced system settings -> Advanced (tab) -> Environment Variables... In the Environment Variables... dialog under "System Varaiables" open the "Path" variable and ensure that both the root python directory as well as the ``\Scripts\`` subdirectory are included. If they are not, add them one by one by clicking "New" and then "Browse" and locating the correct directories. NOTE: By default the Windows MSI installer place python in the ``C:\Users\<username>\AppData\Local\Programs\`` directory.
3. To test if you have entered python correctly into the Path variable, open a command prompt and type in ``python`` then hit Enter. The python cli should run and you should see the python version you installed depicted above the prompt. Press CTRL+Z, then Enter to exit.

    .. NOTE::
        For some reason in newer versions of Windows typing "python" will actually open the Windows Store -- you can fix this by opening "App execution aliases" (search for it via the Windows Search) and toggling off the aliases for python.exe and python3.exe.

4. Make sure you have `pip installed <https://pip.pypa.io/en/stable/installing/#do-i-need-to-install-pip>`_. If your Path environment variable is correctly set up, you can type ``pip -V`` into a command prompt to check (it should return the version of the installed pip).
5. Make sure you have the latest version of pip installed by executing::

    pip install --upgrade pip

6. Using pip, install virtualenvironment and the virtualenvwrapper-win. `See instructions here for installing them on Windows <http://timmyreilly.azurewebsites.net/python-pip-virtualenv-installation-on-windows/>`_. You can choose to follow the rest of the guide as an example or just read the instructions.
7. Lastly, make sure you have the Microsoft Visual Studio build tools. Check the troubleshooting guide's relevant section :ref:`microsoft_visual_studio_build_tools_required`.

Git
^^^^^^^^^^^^^^^^^^^^
Get `latest git <https://gitforwindows.org/>`_.

OpenSSL, Sqlcipher and pysqlcipher3
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to build rotki on Windows, you will need to have installed and built pysqlcipher3 (instructions on this further down) which needs sqlcipher which needs OpenSSL.

1. The guide requires you to get ``OpenSSL``. You can do that from `here <https://slproweb.com/products/Win32OpenSSL.html>`__.

    .. NOTE::
        a) Because of some pysqlcipher3 dependencies, and because it most closely matches the version used in the sqlcipher build guide, you should get OpenSSL 1.0.2 and not 1.1.1 (the naming of libs and dlls has changed between versions and the building of some dependencies will fail).

        b) Get the version of OpenSSL that matches the architecture of your Windows and python installs (i.e. 32- or 64-bit)

        c) When prompted for an install directory for OpenSSL, choose one that does not have spaces in it (i.e. avoid \Program Files\) as installing it in a directory with spaces will cause you numerous headaches when trying to edit the Makefile mentioned in the sqlcipher build instructions.

        d) Verify that the ``<OpenSSL Install Dir>\bin`` directory is on your path after installation, pysqlcipher3 will not build/install correctly if it is missing

2. As no pre-compiled Windows binaries and dlls are readily available for sqlcipher, you will need to build it from source. `Here <https://github.com/sqlitebrowser/sqlitebrowser/wiki/Win64-setup-%E2%80%94-Compiling-SQLCipher>`__ is a good guide on how to compile SQLCipher for Windows.

    .. NOTE::
        a) Follow the instructions in the sqlcipher build guide regarding changes to ``Makefile.msc`` very closely, ensuring that variables that point to the directory where you have actually installed OpenSSL.


3. Once you have completed up to and including Step 6 in the sqlcipher build guide (you can ignore Step 7), you will have compiled sqlcipher and built the necessary headers and libraries that pysqlcipher3 depends on. In the directory you should now see ``sqlcipher.dll``, copy and paste this file to your ``<Windows>\System32`` directory. These files will be used later; you can now move on to setting up your rotki dev environment.

Set up rotki dev environment
----------------------------

Downloading source and installing python dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This guide will assume that you want to use git to clone the project into a development directory; if you wish to just download the source from Github as a zip you can do that instead (the zip file has everything in a folder in the format of ``<project>-<branch>``, so if you download rotki/develop you will get a folder ``rotki-develop``; you can of course rename this). If you download the source as a zip you can skip to Step 4 below.

1. Fork the relevant rotki branch into your own account in github.

2. Open a terminal (command prompt / PowerShell prompt / etc.) in your root development directory (the parent directory of where you will place your rotki development directory).

3. Clone your forked project into the local directory where you want to build rotki (e.g. if you forked the rokti/develop branch you might clone into ``c:\dev\rotki-develop``).

At this point in your local rotki development directory you should have all the same files as they appear in the github page for the rotki branch you chose to download/clone.

Going back to your open terminal, it's time to set up your python virtual environment (virtualenv).

4. Recalling the instructions above on how to set up the virtualenv, set one up for rotki (you don't have to use the name ``rotki-develop``)::

    mkvirtualenv rotki-develop

5. Ensure that you're in the directory where you downloaded/cloned the rotki source and bind the virtualenv to the directory::

    setprojectdir .

If at any time you want to dissasociate with the virtual env, you can use the command ``deactivate``. Whenever you open a new terminal you can now use ``workon rotki-develop`` (if you named your virtualenv something else then use that instead of ``rotki-develop``) and it should establish the link to the python virtualenv you created and set your working directory to the directory you were in in Step 5. Following the example above, if you open a brand new terminal and type in ``workon rotki-develop`` your terminal prompt should look something like::

    (rotki-develop) c:\dev\rotki-develop>

6. Now it's time to install all the python requirements. In the open terminal with your virtualenv activated, execute::

    pip install -r requirements_dev.txt

Pay close attention to the results of the command. Sometimes modules are reported as successfully installed but in reality the build has failed. You should carefully scroll through the buffer to ensure everything has been built & installed correct.

At this point, it's likely that pysqlcipher3 has not been built and installed correctly, and you will need to install it manually. If pysqlcipher3 installed successfully, you can skip Steps 7 - 9 and move on to the next section.

Since the electron application is located in a different directory you also need to do (NOTE: execute this only after pysqlcipher3 has successfully installed)::

    pip install -e .

7. Go back to your development directory and download / clone (if you want to use git but don't want to clone the whole project, check out `degit <https://www.npmjs.com/package/degit>`_) the source for `pysqlcipher3 <https://github.com/rigglemania/pysqlcipher3>`_.

8. With your code editor of choice, edit the ``setup.py`` file in ``\pysqlcipher3\``, make the following changes and save the file::

    Lines 165 - 169 Before
            ext_modules=[Extension(
            name=PACKAGE_NAME + EXTENSION_MODULE_NAME,
            sources=sources,
            define_macros=define_macros)
        ],
    Lines 165 ... AFTER
            ext_modules=[Extension(
            name=PACKAGE_NAME + EXTENSION_MODULE_NAME,
            sources=sources,
            library_dirs=[r'<DIRECTORY WHERE YOU BUILT SQLCIPHER TO (i.e. where the compiled sqlcipher.exe and sqlcipher.dll are)>'],
            include_dirs=[r'<THE PARENT DIRECTORY OF THE ABOVE DIRECTORY>'],
            define_macros=define_macros)
        ],

9. Going back to the open terminal that you have, and ensuring that you are still in the rotki virtualenv that you created, navigate to the directory where you have downloaded the ``pysqlcipher3`` source.

In the terminal execute the two following commands in succession::

    python setup.py build
    python setup.py install

If all went well, pysqlcipher3 should have successfuly built and installed. If it didn't, try going back and ensuring that you have properly built sqlcipher and pointed to the right directories in the setup.py file, or consult the troubleshooting section.

Installing Electron and Running Rotki
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. In your terminal, navigate to your rotki development directory and enter the following commands to install electron and its dependencies::

    cd frontend\app
    npm ci

2. At this point, your terminal's cwd should be ``<rotki development directory>\frontend\app\`` and the rotki virtualenv should be activated. You should now be able to start rotki in development mode by executing::

    npm run electron:serve

After the app is built, if everything went well you should see the below text in your terminal and a new electron window that has opened with the rotki app running. ::

    INFO  Starting development server...
    ...
    INFO  Launching Electron...
    2020-XX-XXXX:XX:XX.XXXX: The Python sub-process started on port: XXXX (PID: YYYY)

If you get any errors about missing dependencies, try to install them via npm and run again; consult the troubleshooting section for other errors.

3. Alternatively, you can also choose to build the application. In order to do so, navigate to your rotki development directory and execute the ``package.bat`` file.
NOTE: You will need to edit the directories in the batch file to point to where you built pysqlcipher3 and your rotki development directory (`see here <https://github.com/rotki/rotki/blob/5f55522efc8faa1992b64e8b27c96ce8c844d70c/package.bat#L27-L30>`_).

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
