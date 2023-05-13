Rotki Websockets API
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


EVM Accounts Detection
=======================

If there are new evm accounts detected (due to a data migration, user-initiated detection, periodic detection, etc.) then the frontend will be notified of any new EVM accounts that were detected. This is done via the following message.

::

    {
        "type": "evm_accounts_detection",
        "data": [
            {
                "address": "0x4bBa290826C253BD854121346c370a9886d1bC26",
                "evm_chain": "optimism"
            },
            {
                "address": "0x4bBa290826C253BD854121346c370a9886d1bC26",
                "evm_chain": "avalanche"
            }
        ]
    }


- ``address``: Address of an account.
- ``evm_chain``: Chain of an account.


EVM Token Detection
=======================

While we are processing EVM transactions new tokens may be detected and added to the database. Some of them can be spam tokens. Using this message we can let the frontend know which tokens are detected. Then they can in turn allow the user to see an aggregated list of all detected tokens and using that list, easily mark spam assets if any.

This also contains two optional, mutually excluded keys. If one exists the other should not. But also both can be missing.

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


- ``seen_tx_hash``: A transaction hash in the same chain as the token in which the token was first seen.
- ``seen_description``: A description of the action in which the token was first seen and added to the DB. For example, querying curve pools, querying yearn pools etc.


Missing API Key
=======================

Having API keys for some services (such as etherscan) is crucial for rotki to work. So sometimes we might specifically prompt the user to add an API key for a service. In that case we send a websocket message to the frontend.

::

    {
        "type": "missing_api_key",
        "data": {
            "service": "etherscan",
            "location": "optimism"
        }
    }


- ``service``: Service for which an API key is needed.
- ``location``: For services like etherscan that require different API keys for different locations this is the location for which the API key is needed. If a service does not require a location then this key will be missing.


Query new history events
=========================

In addition to history from evm transactions we need to query events from exchanges, eth staking events etc. The backend will emit a ws message as the following when such a query starts.

::

    {
        "type": "querying_events_status",
        "data": {
            "status": "querying_events_started",
            "location": "kraken",
            "event_type": "history_query",
            "name": "My kraken exchange"
        }
    }


- ``status``: Can be either `querying_events_started`, `querying_events_finished`, `querying_events_status_update`. Each pair of events is triggered per exchange instance if the location is an exchange.
- ``event_type``: Labels the type of events being queried. Valid values are: ``history_query``.
- ``location``(Optional): When the same ``event_type`` can be queried in multiple locations this helps to differentiate them.
- ``name``(Optional): If multiple appearances of the same location are possible it will differentiate each one of them.

Finally the backend provides more granular information to know what interval of time is getting queried for certain locations.

::

    {
        "type": "querying_events_status",
        "data": {
            "status": "history_event_status",
            "location": "kraken",
            "event_type": "history_query",
            "name": "My kraken exchange",
            'period': [0, 1682100570]
        }
    }


- ``event_type``: Labels the type of events being queried. Valid values are: ``history_query``.
- ``location``(Optional): When the same ``event_type`` can be queried in multiple locations this helps to differentiate them.
- ``name``(Optional): If multiple appearances of the same location are possible it will differentiate each one of them.
- ``period``: Time range that is being queried.


Request a refresh of balances
=============================

If at some point backend detects that balances need to be refreshed, it will send this message to the frontend.

::

    {
        "type": "refresh_balances",
        "data": {
            "type": "blockchain_balances",
            "blockchain": "optimism"
        }
    }


- ``type``: Balances section that needs a refresh. Valid values are: ``blockchain_balances``.
- ``blockchain``: Returned only for section: ``blockchain_balances``. The blockchain for which balances need to be refreshed. Valid values are: ``optimism``, ``eth``.
