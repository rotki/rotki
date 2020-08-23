Rotkehlchen Data Faker Tool
##################################################
.. toctree::
  :maxdepth: 2


Introduction
============

The rotkehlchen data faker tool is used to generate fake data for usage with Rotkhelchen. It creates fake users with fake balance, trade and other data across exchanges. It also runs a fake API server that mocks all exchanges to serve that fake data.

Installation and Usage
======================

To install it make sure to install the extra requirements that it has in the same
venv as the normal rotkehlchen development happens. Use ``tools/data_faker/requirements.txt`` for the extra requirements.

Then to run it run it from inside the ``tools/data_faker/`` directory by doing: ``python -m ``python -m data_faker --user-password 123 --user-name foo_8``, replacing username and password with the desired test username and password.

Once the data generation is finished, the data faker will show that a REST API is running. That is the mock exchanges API.

To use it from the rotkehlchen application edit ``rotkehlchen/constants/misc.py`` to use the mock exchange APIs and also to set the cache seconds in ``rotkehlchen/constants/timing.py`` to ``0``.

