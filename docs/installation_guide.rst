System Requirements and Installation Guide
##################################################
.. toctree::
  :maxdepth: 2


Introduction
============

The easiest way to start Rotkehlchen is to download the packaged binary for your Operating system. For now only Linux and OSX is supported. To see how to do this go to the :ref:`next section <_packaged_binaries>`.


.. _packaged_binaries:

Packaged Binaries
=================

Linux
*****

Go to the `releases <https://github.com/rotkehlchenio/rotkehlchen/releases>`_ page and download the linux-x64 package from the `latest release <https://github.com/rotkehlchenio/rotkehlchen/releases/latest>`_.

Unzip it in a directory of your choice. In the root directory of the unzipped archive there is a ``rotkehlchen`` executable. Run it to start rotkehlchen.

OSX
***

Go to the `releases <https://github.com/rotkehlchenio/rotkehlchen/releases>`_ page and download the darwin-x64 package from the `latest release <https://github.com/rotkehlchenio/rotkehlchen/releases/latest>`_.

Unzip it in a directory of your choice. In the root directory of the unzipped archive there is a `rotkehlchen` executable. Run it to start rotkehlchen.

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

    npm install --runtime=electron --target=1.8.4

