===================
Developer Changelog
===================

This changelog documents API changes, schema modifications, and other developer-relevant changes that may affect integrations with rotki.

Unreleased
==========

Event Group Position Endpoint
-----------------------------

A new endpoint to get the 0-based position of a history event group in the filtered and sorted list of groups. This is useful for navigating to a specific event in paginated views.

* **New Endpoint**: ``GET /api/(version)/history/events/position``

  - Required ``group_identifier`` parameter specifying the group identifier to find the position of.
  - Returns the 0-based position of the group in the filtered and sorted (timestamp DESC) list of groups.
  - Returns null if the group is not found.

ETH2 Staking Events Refetch Endpoint
------------------------------------

A new endpoint to refetch ETH2 staking events and return a breakdown of newly added events.

* **New Endpoint**: ``POST /api/(version)/blockchains/eth2/events/refetch``

  - Required ``entry_type`` parameter specifying which type of staking events to refetch. Valid values are ``"block_productions"`` and ``"eth_withdrawals"``.
  - Optional ``from_timestamp`` and ``to_timestamp`` parameters to restrict the time range of events to refetch.
  - Optional ``validator_indices`` parameter, a list of validator indices to refetch events for.
  - Optional ``addresses`` parameter, a list of EVM addresses (fee recipients for block productions, withdrawal addresses for withdrawals) to refetch events for.
  - ``validator_indices`` and ``addresses`` cannot both be specified in the same request. If neither is provided, events for all tracked validators are refetched.
  - Supports ``async_query`` for background execution.
  - ``result`` returns an object with ``total``, ``per_validator``, and ``per_address`` breakdowns of newly added event counts.
  - ``per_address`` maps fee recipient addresses for block productions or withdrawal addresses for withdrawals.

History Events Filter State Markers Parameter
---------------------------------------------

The history events filter now uses a ``state_markers`` list parameter instead of the ``customized_events_only`` boolean flag for filtering by event states.

* **Modified Endpoint**: ``POST /api/(version)/history/events``

  - Removed ``customized_events_only`` boolean parameter.
  - Added ``state_markers`` list parameter that accepts any combination of marker values: ``"customized"``, ``"profit adjustment"``, ``"auto matched"``, ``"imported from csv"``.
  - Events matching any of the specified markers are returned (OR logic).
  - If ``state_markers`` is not provided or is empty, no marker filtering is applied.
  - Example: ``{"state_markers": ["customized", "imported from csv"]}`` returns events with either marker.

CSV Import Marker for History Events
------------------------------------

All history events imported via CSV now have the ``imported_from_csv`` state marker automatically applied. This allows the frontend and API consumers to identify which events originated from CSV imports.

Changes on historical balances queries
---------------------------------------

Historical balances queries (ERC20 balanecOf and native token balances) are now cached in the db for future retrieval. `get_historical_balance` is now deleted from chain/evm/manager.py

Use now:

- `evm_manager.node_inquirer.get_historical_native_balance`
- `evm_manager.node_inquirer.get_historical_token_balance`

Mass Delete History Events by Filter
-------------------------------------

The history events DELETE endpoint now supports deleting events using filter parameters in addition to specific identifiers.

* **Modified Endpoint**: ``DELETE /api/(version)/history/events``

  - Now accepts filter parameters (asset, from_timestamp, to_timestamp, event_types, location, etc.) to delete matching events.
  - All provided filters are combined (intersection) to determine which events to delete.
  - At least one filter parameter must be provided to prevent accidental mass deletion.
  - The ``identifiers`` parameter is now optional when other filter parameters are provided.

Trigger Async Task
------------------

Bypasses the normal background task scheduling and runs a task immediately. Only supports triggering the historical balance processing and the asset movement matching tasks currently.

* **New Endpoint**: ``POST /api/(version)/tasks/trigger``

  - Required ``task`` parameter specifying which task to run. Valid values are ``historical_balance_processing`` and ``asset_movement_matching``.

Scheduler Control
-----------------

Enables or disables the periodic task scheduler. This should be called by the frontend once initial data loading is complete (transaction decoding, balances fetch, asset movement matching, historical balance processing). This ensures background tasks that require exclusive database write access (like backup sync) don't run during DB upgrades, migrations, and asset updates.

* **New Endpoint**: ``PUT /api/(version)/tasks/scheduler``

  - Required ``enabled`` parameter (boolean) specifying whether to enable or disable the scheduler.
  - Example: ``{"enabled": true}``

Matching Asset Movements With Onchain Events
--------------------------------------------

Exchange asset movement events may now be manually matched with specific onchain events via the API.

* **New Endpoint**: ``PUT /api/(version)/history/events/match/asset_movements``

  - Match asset movements with corresponding events or mark asset movements as having no match.
  - Required ``asset_movement`` parameter specifying the DB identifier of the asset movement.
  - Optional ``matched_event`` parameter specifying the DB identifier of the event to match with the asset movement. If this parameter is omitted or set to null, the asset movement is marked as having no match.
  - Example: ``{"asset_movement": 123, "matched_event": 124}``

* **New Endpoint**: ``POST /api/(version)/history/events/match/asset_movements``

  - Finds possible matches for a given asset movement within the specified time range.
  - Required ``asset_movement`` parameter specifying the group identifier to find matches for.
  - Required ``time_range`` parameter specifying the time range in seconds to include.
  - Optional ``only_expected_assets`` parameter indicating whether to limit the possible matches to only events with assets in the same collection as the asset movement's asset. True by default.
  - Example: ``{"asset_movement": "ef2...69f", "time_range": 7200, "only_expected_assets": true}``

* **New Endpoint**: ``GET /api/(version)/history/events/match/asset_movements``

  - Optional ``only_ignored`` flag indicating whether to return a list of the movements that are marked as having no match, or the list of all movements that have not been matched or ignored yet.

* **New Endpoint**: ``DELETE /api/(version)/history/events/match/asset_movements``

  - Required ``identifier`` parameter specifying the DB identifier of an asset movement or an event matched with an asset movement to unlink.
  - Unlinks the asset movement from its matched event. This asset movement will now appear in the list of unmatched movements again.

* **Modified Endpoint**: ``POST /api/(version)/history/events``

  - New optional ``actual_group_identifier`` field in the response, containing the actual group identifier of the event as stored in the DB.
    This preserves the actual group identifier when asset movements are combined with the group of their matched event for display as a single unit in the frontend.
  - Replaced the ``customized`` flag with a ``states`` list. Valid states are ``customized``, ``profit_adjustment``, ``auto_matched``, ``imported_from_csv``.

* **New Settings** (new fields in both ``PUT`` and ``POST`` on ``/api/(version)/settings``)
  - ``asset_movement_amount_tolerance`` The tolerance value used when matching asset movement amounts with onchain events. Must be a positive decimal number. Default is ``"0.000001"``.
  - ``asset_movement_time_range`` The time range before/after the asset movement (depending on if its a deposit/withdrawal) in which to check for possible matching events. Default is 54000 (15 hours). Note: there is also a 1 hour tolerance on the other side of the asset movement, since some exchanges do not provide accurate timestamps.
  - ``suppress_missing_key_msg_services`` A list of services for which the missing api key WS message should be suppressed. Empty list by default.

Event/Group Identifier Renaming
-------------------------------

The common identifier for groups of events (i.e. all events from a given EVM tx) is renamed from ``event_identifier`` to ``group_identifier``.

* **Modified Endpoints**:

  - ``POST``, ``PUT``, and ``PATCH`` on ``/api/(version)/history/events`` - Renamed ``event_identifier`` to ``group_identifier``.
  - ``PUT /api/(version)/history/events/export`` - Renamed ``event_identifiers`` to ``group_identifiers``.
  - ``POST /api/(version)/history/debug`` - Renamed ``event_identifier`` to ``group_identifier``.
  - ``POST /api/(version)/balances/historical/asset`` - Renamed ``last_event_identifier`` to ``last_group_identifier``.
  - ``POST /api/(version)/balances/historical/netvalue`` - Renamed ``last_event_identifier`` to ``last_group_identifier``.

Historical Balance Metrics
--------------------------

Historical balance data is now computed via an API task and stored in the ``event_metrics`` table.

* **Modified Endpoint**: ``POST /api/(version)/balances/historical/asset``

  - Removed ``last_group_identifier`` from response. Negative balance detection is now handled by the periodic task.


:releasetag:`1.41.1`
====================

Runtime Log Level Modification
------------------------------

The backend log level may now be modified at runtime without restarting.

* **Modified Endpoint**: ``GET /api/(version)/settings/configuration``

  - Now includes a ``loglevel`` field in response
  - Example: ``{"loglevel": {"value": "DEBUG", "is_default": true}, ...}``

* **New Endpoint**: ``PUT /api/(version)/settings/configuration``

  - Currently only supports the ``loglevel`` parameter
  - Accepted values: ``TRACE``, ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``
  - Returns the same format as the GET endpoint.

ERC-721 (NFT) Token IDs
----------------------------------------

ERC-721 token IDs may now be set when adding/editing assets.

* **Modified Endpoint**: ``PUT /api/(version)/assets/all``

  - Supports a new ``collectible_id`` field. Only valid when token_kind is ``"erc721"``.

* **Modified Endpoint**: ``GET /api/(version)/assets/all``

  - Now includes a ``collectible_id`` field in the response when token_kind is ``"erc721"``.

