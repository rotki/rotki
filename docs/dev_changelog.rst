===================
Developer Changelog
===================

This changelog documents API changes, schema modifications, and other developer-relevant changes that may affect integrations with rotki.

Unreleased
==========

Event/Group Identifier Renaming
-------------------------------

The common identifier for groups of events (i.e. all events from a given EVM tx) is renamed from ``event_identifier`` to ``group_identifier``.

* **Modified Endpoints**:

  - ``POST``, ``PUT``, and ``PATCH`` on ``/api/(version)/history/events`` - Renamed ``event_identifier`` to ``group_identifier``.
  - ``PUT /api/(version)/history/events/export`` - Renamed ``event_identifiers`` to ``group_identifiers``.
  - ``POST /api/(version)/history/debug`` - Renamed ``event_identifier`` to ``group_identifier``.
  - ``POST /api/(version)/balances/historical/asset`` - Renamed ``last_event_identifier`` to ``last_group_identifier``.
  - ``POST /api/(version)/balances/historical/netvalue`` - Renamed ``last_event_identifier`` to ``last_group_identifier``.


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



