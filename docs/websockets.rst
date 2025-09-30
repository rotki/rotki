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
A message having ``total_steps`` and ``current_step`` being ``0`` is sent at the start for the frontend to
switch to the progress screen from the login screen.

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
- ``current_upgrade``: Structure that holds information about currently running upgrade. Contains: ``to_version`` - version of the database upgrade that is currently being applied; ``total_steps`` - total number of steps that currently running upgrade consists of; ``current_step`` - step that the upgrade is at as of this websocket message.
- ``target_version``: The target version of the DB. When this is reached, the upgrade process will have finished.


Data migration status
=========================

The messages sent by rotki when a user is logging in and a db upgrade is happening. The format is the following.
A message having ``total_steps`` and ``current_step`` being ``0`` is sent at the start for the frontend to
switch to the progress screen from the login screen.


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


EVM/EVMLke Accounts Detection
==========================================

If there are new evm / evmlike accounts detected (due to a data migration, user-initiated detection, periodic detection, etc.) then the frontend will be notified of any new EVM accounts that were detected. This is done via the following message.

::

    {
        "type": "evmlike_accounts_detection",
        "data": [
            {
                "address": "0x4bBa290826C253BD854121346c370a9886d1bC26",
                "chain": "optimism"
            },
            {
                "address": "0x4bBa290826C253BD854121346c370a9886d1bC26",
                "chain": "zksync_lite"
            }
        ]
    }


- ``address``: Address of an account.
- ``chain``: Chain of an account.


Token Detection
=======================

While we are processing transactions new tokens may be detected and added to the database. Some of them can be spam tokens. Using this message we can let the frontend know which tokens are detected. Then they can in turn allow the user to see an aggregated list of all detected tokens and using that list, easily mark spam assets if any.

The `seen_tx_hash` and `seen_description` keys are optional, but mutually exclusive. If one exists the other should not. But also both can be missing.

::

    {
        "type": "new_token_detected",
        "data": {
            "token_kind": "evm",
            "token_identifier": "eip155:1/erc20:0x76dc5F01A1977F37b483F2C5b06618ed8FcA898C",
            "seen_tx_hash": "0x06a8b9f758b0471886186c2a48dea189b3044916c7f94ee7f559026fefd91c39"
        }
    }

::

   {
        "type": "new_token_detected",
        "data": {
            "token_kind": "evm",
            "token_identifier": "eip155:1/erc20:0x87Dd56068Af560B0D8472C4EF41CB902FCbF5ebE",
            "seen_description": "Querying curve pools"
        }
    }

::

   {
        "type": "new_token_detected",
        "data": {
            "token_kind": "solana",
            "token_identifier": "solana/token:EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        }
    }


- ``token_kind`` Indicates what kind of token was detected. Either `evm` or `solana`.
- ``seen_tx_hash``: A transaction hash in the same chain as the token in which the token was first seen.
- ``seen_description``: A description of the action in which the token was first seen and added to the DB. For example, querying curve pools, querying yearn pools etc.
- ``is_ignored`` (Optional): If it is set the backend has marked automatically the asset as ignored for the user.


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


Query transactions
=========================

While querying transactions the backend sends ws messages giving status updates. There are different schemas depending on the type of transactions being queried. This is specified by the `subtype` key which can have a value of either `evm` or `bitcoin`.

For EVM transactions:

::

    {
        "type": "transaction_status",
        "data": {
            "address": "0x123...",
            "chain": "optimism",
            "subtype": "evm",
            "period": [1600000000, 1700000000],
            "status": "querying_transactions"
        }
    }


- ``address``: The EVM address being queried for transactions.
- ``chain``: The EVM chain for which transactions are being queried.
- ``subtype``: Labels which type of transaction status message this is. Will be `evm` for EVM transactions.
- ``period``: The time range that is being queried.
- ``status``: Either `querying_transactions_started`, `querying_transactions`, `querying_internal_transactions`, `querying_evm_tokens_transactions`, or `querying_transactions_finished`.

For Bitcoin transactions:

::

    {
        "type": "transaction_status",
        "data": {
            "addresses": ["bc1q...", "bc1q..."],
            "chain": "btc",
            "subtype": "bitcoin",
            "status": "querying_transactions_started"
        }
    }


- ``addresses``: The list of Bitcoin addresses being queried for transactions.
- ``chain``: The chain for which transactions are being queried. Will be `btc` for Bitcoin transactions.
- ``subtype``: Labels which type of transaction status message this is. Will be `bitcoin` for Bitcoin transactions.
- ``status``: Either `querying_transactions_started`, `querying_transactions_finished`, `decoding_transactions_started`, or `decoding_transactions_finished`.


Query new history events
=========================

In addition to history from evm transactions we need to query events from exchanges, eth staking events etc. The backend will emit a ws message as the following when such a query starts.

::

    {
        "type": "history_events_status",
        "data": {
            "status": "querying_events_started",
            "location": "kraken",
            "event_type": "history_query",
            "name": "My kraken exchange"
        }
    }


- ``status``: Can be either `querying_events_started`, `querying_events_finished`, `querying_events_status_update`. Each pair of events is triggered per exchange instance if the location is an exchange.
- ``event_type``: Labels the type of events being queried. Valid values are: ``history_query``.
- ``location`` (Optional): When the same ``event_type`` can be queried in multiple locations this helps to differentiate them.
- ``name`` (Optional): If multiple appearances of the same location are possible it will differentiate each one of them.

Finally the backend provides more granular information to know what interval of time is getting queried for certain locations.

::

    {
        "type": "history_events_status",
        "data": {
            "status": "querying_events_status_update",
            "location": "kraken",
            "event_type": "history_query",
            "name": "My kraken exchange",
            "period": [0, 1682100570]
        }
    }


- ``event_type``: Labels the type of events being queried. Valid values are: ``history_query``.
- ``location``(Optional): When the same ``event_type`` can be queried in multiple locations this helps to differentiate them.
- ``name`` (Optional): If multiple appearances of the same location are possible it will differentiate each one of them.
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


Premium Database Upload Progress
========================================

When the backend uploads a premium user DB messages of this type are sent to notify the frontend of the progress.

::

    {
        "type": "database_upload_progress",
        "data": {
            "type": "uploading",
            "current_chunk": 1,
            "total_chunks": 4,
        }
    }


- ``type``: Which part of the upload process is currently in progress. Valid values are: ``compressing``, ``encrypting``, and ``uploading``. Only ``uploading`` has any other data included.
- ``current_chunk``: The index of the current chunk being uploaded.
- ``total_chunks``: The total number of chunks to be uploaded.


Premium Database Upload result
========================================

Whenever the backend attempts to upload a premium user DB there can be various reasons it did not upload. Either errors (non-actionable) or safety limits (actionable -- can be force pushed).  We use this websocket message to communicate to the frontend.

::

    {
        "type": "database_upload_result",
        "data": {
            "uploaded": False,
            "actionable": True,
            "message": "Remote database bigger than the local one"
        }
    }


- ``uploaded``: A boolean, denoting if the premium database upload happened or not.
- ``actionable``: If ``uploaded`` is false, then this explains if the reason it did not upload is something actionable that could be solved by force pushing. If True, then
  that means it failed to upload for something like remote database being more recent than local or bigger than local etc. If false it's a bad error like "could not contact the server" in which case force pushing won't help.
- ``message``: If ``uploaded`` is false, then this is a user facing message to explain why. IF ``uploaded`` is true this will be ``null``.


New accounting rule conflict
============================

When we pull new rules from the remote repository and there are conflicts in the accounting rules we emit one ws message per conflict with

::

    {
        "type":"accounting_rule_conflict",
        "data":{"num_of_conflicts": 1}
    }


- ``num_of_conflicts``: Number of conflicts found during the processing of accounting rules.


Transaction decoding process
============================

When the endpoint to start the task for decoding undecoded transactions is queried we send ws messages to inform about the progress.

::

    {
        "type": "progress_updates",
        "data": {chain":"ethereum", "total":2, "processed":0, "subtype":"undecoded_transactions"}
    }


- ``subtype``: Set to "undecoded_transactions" to identify transaction decoding progress
- ``chain``: Chain where the task is decoding transactions.
- ``total``: Total number of transactions that will be decoded.
- ``processed``: The total number of transactions that have already been decoded.

The backend will send a ws message at the beginning before decoding any transaction and another at the end of the task. Every 10 decoded transactions it will also update the status.


Calendar reminders
============================

When a reminder for a calendar event is processed we emit a message with the following format. The reminder is then deleted.

::

    {
        "data":{
            "identifier":2,
            "name":"CRV unlock",
            "description":"Unlock date for CRV",
            "timestamp":1713621899,
        },
        "type":"calendar_reminder"
    }


- ``data``: Contains the information of the calendar event, that is: identifier, name, description, timestamp, address, blockchain, counterparty and color.


Protocol cache updates
============================

Whenever a protocol cache is being updated for protocols like Curve, Convex, Gearbox, [Velo/Aero]drome, etc., Messages are emitted every 5 seconds to notify the progress of it.

::

    {
        "data": {
            "subtype":"protocol_cache_updates",
            "protocol":"curve",
            "chain":"ethereum",
            "processed": 324,
            "total":3042,
        },
        "type":"progress_updates"
    }


- ``subtype``: Set to "protocol_cache_updates" to identify protocol cache update progress
- ``protocol``: The protocol being updated (e.g., "curve", "convex", "gearbox")
- ``chain``: The blockchain on which the protocol cache is being updated
- ``processed``: Number of items processed so far
- ``total``: Total number of items to process


Unknown asset on exchange
============================

If an unknown asset is encountered on an exchange we emit a message with the following format.

::

    {
        "type": "exchange_unknown_asset",
        "data": {
            "location": "bybit",
            "name": "Bybit 1",
            "identifier": "ENA",
            "details": "balance query",
        }
    }


- ``location``: Exchange where the asset was found.
- ``name``: Differentiates between multiple instances of the same exchange.
- ``identifier``: Asset identifier of the unknown asset.
- ``details``: Details about what type of event was being processed when the unknown asset was encountered.


CSV Import Results
=======================

When importing CSV data from various sources, progress updates are sent to inform about the import status and any issues encountered. The format is as follows:

::

    {
        "type": "progress_updates",
        "data": {
            "source_name": "Cointracking",
            "subtype": "csv_import_result",
            "total": 12,
            "processed": 7,
            "messages": [
                {
                    "msg": "Not importing ETH Transactions from Cointracking.",
                    "rows": [1, 2],
                    "is_error": true
                },
                {
                    "msg": "Unknown asset ADS.",
                    "rows": [9],
                    "is_error": true
                }
            ]
        }
    }


- ``subtype``: Set to "csv_import_result" to identify CSV import progress
- ``source_name``: Name of the source from which the CSV is being imported
- ``total``: Total number of rows to be processed in the CSV
- ``processed``: Number of rows that have been processed so far
- ``messages``: Array of message objects containing:
  - ``msg``: Description of the import status or error
  - ``rows``: Array of row numbers affected by this message
  - ``is_error``: Boolean indicating if this message represents an error condition


Historical Price Query Status
=================================

During historical price queries, progress updates are sent to track the status of the price data retrieval. The format is:

::

    {
        "type": "progress_updates",
        "data": {
            "total": 100,
            "processed": 45,
            "subtype": "historical_price_query_status"
        }
    }


- ``total``: Total number of time intervals to query
- ``processed``: Number of intervals that have been processed so far
- ``subtype``: Set to "historical_price_query_status" to identify historical price query progress


Liquity staking status
=======================

Liquity staking has several products whose price needs to be remotely queried. The progress of these queries can be followed by

::

    {
        "type": "progress_updates",
        "data": {
            "total": 4,
            "processed": 1,
            "subtype": "liquity_staking_query"
        }
    }


- ``total``: Total number of products that the staking logic has to check.
- ``processed``: Number of products queried.
- ``subtype``: Set to "liquity_staking_query" to identify liquity staking queries.


Async prices queries
======================

Kraken and Liquity query prices for historical events and they report the status using the following structure sent after processing some number of events:

::

    {
        "type": "progress_updates",
        "data": {
            "total": 220,
            "processed": 190,
            "subtype": "stats_price_query"
        }
    }


- ``total``: Total number of history events that need their price queried.
- ``processed``: Number of events processed.
- ``subtype``: Set to "stats_price_query" to identify prices queries for statistics.


Multiple timestamp price queries
=================================

Track the progress for when we need to query prices at multiple timestamps.

::

    {
        "type": "progress_updates",
        "data": {
            "total": 6,
            "processed": 5,
            "subtype": "multiple_prices_query_status"
        }
    }


- ``total``: Total number of combinations asset-price that will be queried.
- ``processed``: Number of prices queried.
- ``subtype``: Set to "multiple_prices_query_status" to identify prices queries.


Solana Tokens Manual Migration
=================================

Solana tokens that require manual migration by the user.

::

    {
        "type": "progress_updates",
        "data": {
            "identifiers": ['HODL', 'TRUMP']
        }
    }


- ``identifiers``: Asset identifiers that need to manually migrated to solana tokens.


Binance Missing Market Pairs
=================================

Trades were queried from a binance exchange, but no market pairs are selected to query.

::

    {
        "type": "binance_pairs_missing",
        "data": {
            "location": "binance",
            "name": "Binance 1"
        }
    }


- ``location``: Location of the binance exchange. Either ``binance`` or ``binanceus``
- ``name``: Name of the exchange.