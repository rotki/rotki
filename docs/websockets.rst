rotki Websockets API
##################################################
.. toctree::
  :maxdepth: 2


Introduction
*************

When the rotki backend runs it exposes a websockets API that can be easily subscribed to. Through that API rotki backend pushes data to the subscribed clients (mainly the rotki frontend) in a continuous manner and as soon as they are available.


Subscribe
***********

In order to subscribe to the websockets api open a socket to the host/port combination that you have set for websockets in the backend and send an empty message.

Messages Format
*****************

All messages sent by the backend via websockets are stringified json and they have the following format.

::

    {
        "type": "legacy",
        "data": "{"some": 1, "data": 2}"
    }


The ``"type"`` attribute determines what kind of message it is and what to expect in ``"data"``.

Messages
************


Legacy messages
====================

The messages sent by rotki via the ``MessagesAggregator`` can be found in this type. The format is


::

    {
        "type": "legacy",
        "data": "{"verbosity": "warning", "value": "A warning"}"
    }


- ``verbosity``: The verbosity of the message. Can be one of ``"warning"`` or ``"error"``.
- ``value``: A string with the contents of the message.


Balance snapshot errors
=========================

The messages sent by rotki when there is a snapshot balance error. There can be multiple of these errors for one balance snapshot. The format is the following.


::

    {
        "type": "balance_snapshot_error",
        "data": "{"location": "poloniex", "error": "Could not connect to poloniex"}"
    }


- ``location``: An approximate location name for where in the balance snapshot the error happened.
- ``error``: A string with details of the error


DB Upgrade status
=========================

The messages sent by rotki when a user is logging in and a db upgrade is happening. The format is the following.


::

    {
        "type": "db_upgrade_status",
	"data": {
	    "start_version": 26,
	    "target_version": 35,
	    "current_upgrade": {
		"to_version": 30,
		"total_steps": 8,
		"current_step": 5
	    }
	}
    }


- ``start_version``: DB version that user's database had before any upgrades began. This is the version of the DB when rotki first starts.
- ``current_upgrade``: Structure that holds information about currently running upgrade. Contains: ``to_version`` - version of the the database upgrade that is currently being applied; ``total_steps`` - total number of steps that currently running upgrade consists of; ``current_step`` - step that the upgrade is at as of this websocket message. 
- ``target_version``: The target version of the DB. When this is reached, the upgrade process will have finished.


Data migration status
=========================

The messages sent by rotki when a user is logging in and a db upgrade is happening. The format is the following.


::

    {
        "type": "data_migration_status",
        "data": {
	    "start_version": 1,
	    "target_version": 8,
	    "current_migration": {
		"version": 8,
		"total_steps": 20,
		"current_step": 3,
		"description": "Checking 0xbd96cDCc6Ae1ffB73ace84E16601E1CF909D5749 EVM chain activity"
	    }
	}
    }


- ``start_version``: Last data migration version when the migration process started
- ``current_migration``: Structure that holds information about currently running migration. Contains: ``version`` - The migration that is being applied; ``total_steps`` - total number of steps that currently running migration consists of; ``current_step`` - step that the migration is at as of this websocket message; ``description`` - An optional string (can be null) that explains what is the migration doing at this step.
- ``target_version``: The target migration version. When this will have been reached and finished, the migrations will end.


EVM Addresses Migrations
============================

At the user DB migrations when a new evm chain is introduced rotki will do a migration that will add any addresses used in mainnet to the new evm chain. At the same time it needs to notify the frontend that new evm chain/ evm address combination was added at migration so the frontend can do extra actions such as detecting tokens. The message is simple and just contains the list of migrated addresses if any.

::

    {
        "type": "evm_address_migration",
        "data": [{
	    "evm_chain": "optimism",
	    "address": "0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12"
	}, {
	    "evm_chain": "optimism",
	    "address": "0xFeebabE6b0418eC13b30aAdF129F5DcDd4f70CeA"
	}]
    }


EVM Token Detection
=======================

While we are processing EVM transactions new tokens may be detected and added to the database. Some of them can be spam tokens. Using this message we can let the frontend know which tokens are detected. Then they can in turn allow the user to see an aggregated list of all detected tokens and using that list, easily mark spam assets if any.

This also contains two optional, mutually excluse keys. If one exists the other shold not. But also both can be missing.

- ``"seen_tx_hash"``: A transaction hash in the same chain as the token in which the token was first seen.
- ``"seen_description"``: A description of the action in which the token was first seen and added to the DB. For example, querying curve pools, querying yearn pools etc.

::

    {
        "type": "new_evm_token_detected",
        "data": {
            "token_identifier": "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "seen_tx_hash": "0x06a8b9f758b0471886186c2a48dea189b3044916c7f94ee7f559026fefd91c39"
        }
    }

::

   {
        "type": "new_evm_token_detected",
        "data": {
            "token_identifier": "eip155:1/erc20:0x87Dd56068Af560B0D8472C4EF41CB902FCbF5ebE",
            "seen_description": "Querying curve pools"
        }
    }
