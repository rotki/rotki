===================
Developer Changelog
===================

This changelog documents API changes, schema modifications, and other developer-relevant changes that may affect integrations with rotki.

Unreleased
==========

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

  - Required ``asset_movement`` parameter specifying the DB identifier of the asset movement to unlink from its corresponding matched event.
  - Unlinks the asset movement from its matched event. This asset movement will now appear in the list of unmatched movements again.

* **Modified Endpoint**: ``POST /api/(version)/history/events``

  - New optional ``actual_group_identifier`` field in the response, containing the actual group identifier of the event as stored in the DB.
  - This change preserves the actual group identifier when asset movements are combined with the group of their matched event for display as a single unit in the frontend.

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

Historical balance data is now computed via a periodic task and stored in the ``event_metrics`` table.

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



