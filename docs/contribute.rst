Rotki Contribution Guide
##############################

Rotki is an opensource project so help is really appreciated.

.. _bug_reporting:

Bug Reporting
*****************

Before reporting an issue, make sure to check the issue tracker for similar ones. If this is a new issue then use the `proper template <https://github.com/rotki/rotki/issues/new?template=bug_report.md>`_ providing a detailed description about:

- **Problem**: what happened and what you were expecting to happen instead.
- **Logs**: run Rotki in debug mode, replicate the issue and attach the logs (see the section `Run Rotki in debug mode <#run-rotki-in-debug-mode>`_).
- **Environment**: the operating system and the Rotki version.

Run Rotki in debug mode
=========================

For running Rotki in debug mode, you can do it either via a config file or the app UI:

- **Config file**: see the section :ref:`set-the-backend-s-arguments`.
- **App UI**: before log in, click the cog wheel at the bottom right corner and select "Debug" (image below). Then log in as usual.

.. image:: images/rotki_debug_mode_set.png
   :alt: Run Rotki in debug mode via app UI
   :align: center

You can find the app logs location by going to "Help" menu at the top and then choosing "Logs Directory".

Feature Requests
******************

Use the `feature request <https://github.com/rotki/rotki/issues/new?template=feature_request.md>`_ template.

Describe exactly what it is that you would like to see added to rotki and why that would provide additional value.

Please note that feature requests are just that. Requests. There is no guarantee that they will be worked on in the near future.

Contributing as a Developer
*****************************

Being an opensource project, we welcome contributions in the form of source code. To do that you will have to work on an issue and open a Pull Request for it.

In order for your Pull Request to be considered it will need to pass the automated CI tests and you will also need to sign the CLA (Contributor's license agreement).

Committing Rules
==================

For an exhaustive guide read `this <http://chris.beams.io/posts/git-commit/>`_ guide. It's all really good advice. Some rules that you should always follow though are:

1. Commits should be just to the point, not too long and not too short.
2. Commit title not exceed 50 characters.
3. Give a description of what the commit does in a short title. If more information is needed then add a blank line and afterward elaborate with as much information as needed.
4. Commits should do one thing, if two commits both do the same thing, that's a good sign they should be combined.
5. **Never** merge master on the branch, always rebase on master. To delete/amend/edit/combine commits follow `this tutorial <https://robots.thoughtbot.com/git-interactive-rebase-squash-amend-rewriting-history>`_.

When pushing on a PR the tags ``[skip ci]`` or ``[ci skip]`` can be used a part of the commit message to skip the run of all the CI jobs (lint, test etc).

Adding new assets to Rotki
============================

To add new assets to rotki you need to edit `all assets file <https://github.com/rotki/rotki/blob/239552b843cd8ad99d02855ff95393d6032dbc57/rotkehlchen/data/all_assets.json>`__.

::

    "CRC": {
        "coingecko": "crycash",
        "cryptocompare": "CRYC",
        "ethereum_address": "0xF41e5Fbc2F6Aac200Dd8619E121CE1f05D150077",
        "ethereum_token_decimals": 18,
        "name": "CryCash",
        "started": 1524526765,
        "symbol": "CRC",
        "type": "ethereum token"
    },

As an example look above. The key should be unique as it's the unique identifier for each asset. Then the possible keys are:

- ``coingecko``: The CoinGecko identifier for the asset. It's used to pull CoinGecko logo and prices. If not supported by CoinGecko it should be an empty string. To see how to get the CoinGecko identifier go to :ref:`get CoinGecko asset identifier <get_coingecko_asset_identifier>`.
- ``cryptocompare``: The CryptoCompare identifier for the asset. It's used to pull historical prices. This is an optional entry. If missing, the identifier is considered the same as as the asset key. If not supported by CryptoCompare it should be an empty string. To see how to get the CryptoCompare identifier go to :ref:`get CryptoCompare asset identifier <get_cryptocompare_asset_identifier>`.
- ``ethereum_address``: If this is an ethereum token give the checksummed ethereum address here. See :ref:`here <helpful_asset_commands>` for help on deriving the checksummed address.
- ``ethereum_token_decimal``: If this is an ethereum token give the ERC20 decimals here.
- ``name``: Give the name of the asset here.
- ``started``: The UNIX timestamp (in seconds) where data for the assets should first be available. Use the appropriate blockchain explorer for getting the date of the token deployment or the launch of the chain. In case of a leveraged token (e.g. "BCHDOWN") either use the date when CryptoCompare/CoinGecko started to track it or when the exchange opened its trade. Please, in case of `converting a date to a UNIX timestamp <https://www.epochconverter.com/>`__ make sure the date is in UTC/GMT.
- ``symbol``: The token symbol. Does not need to be unique (identifier should be).
- ``type``: The type of the asset. Standalone chain, ethereum token etc. For possible values for this field check `here <https://github.com/rotki/rotki/blob/239552b843cd8ad99d02855ff95393d6032dbc57/rotkehlchen/assets/resolver.py#L12>`__.
- ``forked``: This is an optional field. Given to specify if an asset is a fork of another asset. For example ``ETC`` should have ``ETH`` here.
- ``swapped_for``: This is an optional field. Given to specify if an asset is swapped for another asset. For example ``LEND`` should have ``AAVE`` here.

Once an asset is added and both CoinGecko and CryptoCompare identifiers have been validated (if existing), the md5sum of the file should be regenerated and added to the `meta file <https://github.com/rotki/rotki/blob/239552b843cd8ad99d02855ff95393d6032dbc57/rotkehlchen/data/all_assets.meta>`__. And the version in the meta file should also be bumped. The same changes should be done in the unit test that checks exactly for the md5 sum of the assets file.

You can find some helpful commands :ref:`here <helpful_asset_commands>` if your need.

.. _get_coingecko_asset_identifier:

Get CoinGecko asset identifier
--------------------------------

In most cases the CoinGecko asset identifier matches the URL one, for example "weth" for `WETH <https://www.coingecko.com/en/coins/weth>`__. However, sometimes it doesn't, for example "sharering" for `SHR <https://www.coingecko.com/en/coins/sharetoken>`__ ("sharetoken" in the URL).

This identifiers mismatch can be detected by running the `this test <https://github.com/rotki/rotki/blob/develop/rotkehlchen/tests/unit/test_assets.py#L91>`__:

::

    python pytestgeventwrapper.py -xs rotkehlchen/tests/unit/test_assets.py::test_coingecko_identifiers_are_reachable

The test warns each mismatch suggesting the potential identifier (e.g. *Suggestion: id:sharering name:ShareToken symbol:shr*). This identifier can be checked via the **GET coins by id endpoint** on the `CryptoCompare API explorer <https://www.coingecko.com/en/api#explore-api>`__.

The test also warns about any asset delisted from CoinGecko. In that case, add the delisted asset identifier in the `coins_delisted_from_coingecko list <https://github.com/rotki/rotki/blob/80893e93a9b2e74287a5949c5fb742b5a068cecc/rotkehlchen/tests/unit/test_assets.py#L72>`__.

.. _get_cryptocompare_asset_identifier:

Get CryptoCompare asset identifier
------------------------------------

One important gotcha is to check for CryptoCompare asset prices. Unfortunately you need to to check the page of each asset in CryptoCompare. For example for `$BASED <https://www.cryptocompare.com/coins/based/overview>`__ you would need to check the page and then try to see the api call for USD price to see `if it exists <https://min-api.cryptocompare.com/data/pricehistorical?fsym=$BASED&tsyms=USD&ts=1611915600>`__. If this returns something like:

::

   {"Response":"Error","Message":"There is no data for any of the toSymbols USD .","HasWarning":true,"Type":2,"RateLimit":{},"Data":{},"Warning":"There is no data for the toSymbol/s USD ","ParamWithError":"tsyms"}

Then that means you have to check the CryptoCompare page and compare directly with the asset they have listed there. Like `so <https://min-api.cryptocompare.com/data/pricehistorical?fsym=$BASED&tsyms=WETH&ts=1611915600>`__ and see that it works. Then you need to edit the CryptoCompare mappings in the code to add that special mapping `here <https://github.com/rotki/rotki/blob/239552b843cd8ad99d02855ff95393d6032dbc57/rotkehlchen/externalapis/cryptocompare.py#L45>`__.
If you don't find your asset on CryptoCompare just put an empty string for the cryptocompare key. Like ``cryptocompare: ""``.

Hopefully this situation with CryptoCompare is temporary and they will remove the need for these special mappings soon.


.. _helpful_asset_commands:

Helpful commands
------------------------------------

- To get the checksummed ethereum address, you can get from the Python console using our code simply by doing::

    >>> from eth_utils.address import to_checksum_address
    >>> to_checksum_address("0x9c78ee466d6cb57a4d01fd887d2b5dfb2d46288f")
    '0x9C78EE466D6Cb57A4d01Fd887D2b5dFb2D46288f'

- To get the md5sm of the assets file, you can do (from the root directory):

    - on Linux: ``md5sum rotkehlchen/data/all_assets.json``
    - on MacOS: ``md5 rotkehlchen/data/all_assets.json``

Code Testing
**************

Python
========

In order to run the python test suite, first make sure the virtual environment is activated, the developer requirements are installed, and then do:

::

    python pytestgeventwrapper.py -xs rotkehlchen/tests

We require this wrapper as a drop-in replacement of pytest due to quirks of gevent and monkeypatching.

For running the tests with a more specific usage and invocation, please refer to the `pytest <https://docs.pytest.org/en/stable/usage.html>`__ documentation.


Linting
--------

Before each commit you should run the linting checks. They run ``flake8``, ``mypy`` and ``pylint`` in order.

Do that by invoking ``make lint`` from the root directory of the project.

Alternative Linting and Static Analysis Tools
----------------------------------------------

There is some alternative linting tools that we don't run in the CI since they have a lot of false positives. It's good to run them from time to time so they are listed here.

 - **vulture**: Source and docs `here <https://github.com/jendrikseipp/vulture>`__. Just get via ``pip install vulture``. If you simply run it from the root directory you will get a list of possibly unused code that you can remove. You will have to go through a lot of false positives.
 - **bandit** Source and docs `here <https://github.com/PyCQA/bandit>`__. Just get via ``pip install bandit``. If you run it you will get a lot of potential issues in the code. You will have to go through a lot of false positives.

Manual Testing
***********************

In order to make sure that the final executable works as a complete package (including the UI) a bit of manual testing with the final binaries is required.

This should eventually be reduced when we manage to have a more complete E2E test suite. Everything below that can be E2E tested should be.

If time allows test the below on the binaries for all OSes. If not just on one.

Startup
=========

New User
----------

- Create a new user and see that it works. Both with and without a premium key. With a premium key make sure that you can verify that pulling data from the server works.

- Provide mismatching passwords and see it's handled properly.

- Provide wrong premium keys and see it's handled properly

Sign in existing user
----------------------

- Sign in an existing user with a wrong password and see it's handled.

- Sign in a non-existing user and see it's handled

- Sing in an existing user and see it works

External Trades
================

- Add an external trade and see it's added in the table
- Edit an external trade from the table and see it's altered
- Delete an external trade from the table and see it's removed
- Expand the details on a trade and see they are shown properly

Data Importing
===============

- Import some data from cointracking.info and see that works properly

Exchanges
===========

- Add an invalid exchange API key and see it's handled properly
- Add a valid exchange API key and see it works. See that dashboard balances are also updated.
- Remove an exchange and see that it works and that the dasboard balances are updated.

External Services
==================

- Add an API key for all external services
- Remove an API key for all external services

Application and Accounting Settings
====================================

- Change all application settings one by one and see the changes are reflected.
- Same as above but for invalid values (if possible) and see they are handled.
- Change the profit currency and see it works
- Change all accounting settings one by one and see the changes are reflected.
- Same as above but for invalid values (if possible) and see they are handled.

Accounts and Balances
========================

Fiat
-----

- Add a fiat balance and see it works
- Remove a fiat balance and see it works
- See that adding non number or negative is handled

Ethereum Accounts
-------------------

- Add an ethereum account and see it works
- Add an invalid ethereum account and see it is handled properly
- Remove an ethereum account and see it works
- After adding tokens to an account that has it expand the account and see all tokens owned by it are shown.

Ethereum Tokens
-------------------

- Track an ethereum token and see it works. Works is defined as being added:
    - In the dashboard
    - In the owned tokens
    - In total blockchain balances
    - In the expanded asset details of ETH accounts that own it.
- Remove an ethereum token and see it works. Works means being removed from all the above.

Bitcoin accounts
----------------

- Add a bitcoin account and see it works
- Add an invalid bitcoin account and see it is handled properly
- Remove a bitcoin account and see it works

Tax Report
===========

- Check that invalid input in the date range are handled properly
- Create a big tax report over many exchanges for a long period of time and see that it's correct and no unexpected problems occur.
- Create a CSV export of the report and see it works

Premium Analytics
===================

- Check they work for a premium account
- Modify the range of the netvalue graph and see it works properly
- Change the asset and modify the range of the graph of amount and value of an asset and see it works properly
- Check the netvalue distribution by location works properly
- Check the netvalue distribution by asset works properly and that you can modify the number of assets shown in the graph


