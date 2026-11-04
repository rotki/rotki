===================
Developer Changelog
===================

This changelog documents API changes, schema modifications, and other developer-relevant changes that may affect integrations with rotki.

Unreleased
==========

Custom Location API
-------------------

* **New Endpoints**: ``GET/POST /api/(version)/locations``, ``PATCH/DELETE /api/(version)/locations/(identifier)``, and ``GET /api/(version)/locations/(identifier)/usage``.

  - List the complete location tree, create custom locations, and rename, move, archive, restore or delete them. Built-in locations remain immutable.
  - A PATCH with ``dry_run: true`` validates the edit and returns the old and new display paths without persisting it. Omitting ``icon`` preserves it; ``icon: null`` removes it.
  - Locations with children or data cannot be deleted. Archiving requires all children to be archived first.

* **New Endpoints**: ``GET/POST/DELETE /api/(version)/locations/(identifier)/image``.

  - Upload, retrieve or remove a custom location image. Uploads accept only multipart image files; client filenames are never used as filesystem paths.
  - Uploaded images are stored per user outside the database and are not included in database backups or premium sync. GET supports conditional requests with ``ETag`` and ``If-None-Match``.

Location Subtrees and CSV Imports
---------------------------------

* **Changed Endpoints**: History-event queries, exports, deletion and group positioning, data-issue queries, and historical-balance queries accept ``location_scope``: ``exact`` (the default) or ``subtree``. The latter includes the selected location and all descendants. A scope without a location is not a filter and cannot authorize bulk event deletion.
* **Changed Endpoint**: ``GET /api/(version)/locations/associated`` now returns ``{"locations": [...], "ancestors": [...]}`` instead of a flat list. ``ancestors`` contains the ancestors not already listed as directly used locations.
* **Changed Output**: Balance snapshots and balance location totals separate blockchains by chain instead of combining them under ``blockchain``. History-event, PnL and snapshot CSV exports include ``location_path``.
* **New Endpoints**: ``GET/PUT/DELETE /api/(version)/locations/aliases`` manage case-insensitive aliases for location values in CSV imports.
* **New Endpoint**: ``PUT/POST /api/(version)/import/preflight`` reports resolved, unresolved and ambiguous location values without importing data.
* **Changed Endpoint**: ``PUT/POST /api/(version)/import`` accepts ``location_mappings`` and returns ``409`` without importing while any location value remains unresolved or ambiguous. Mappings override identifier, alias and unique-name resolution. Empty or whitespace-only CSV locations can be mapped with the empty-string key; multipart uploads encode mappings as JSON.
* **Frontend**: Custom CSV imports run location preflight and ask users to map unknown or ambiguous CSV values before submitting the import. Both browser uploads and packaged file imports pass the selected mappings. Only a boolean success result marks an import as complete.
* **User DB v54**: The unreleased v53-to-v54 upgrade and fresh database schema now include ``location_aliases``. No additional database version is introduced.

Classified User Messages
------------------------

* **Renamed Message**: ``legacy`` is now ``user_message``. Consumers matching the old type name must migrate.
* **Changed Message**: ``user_message``

  - Besides ``verbosity`` and ``value``, ``data`` now always carries ``key`` and ``fields``, and carries ``subject``, which is ``null`` for a message about no single location.
  - ``key`` is why the message happened, one of ``bad_data``, ``network``, ``auth``, ``unknown_asset``, ``local_db``, ``price``, ``unsupported`` or ``internal``.
  - ``fields`` holds the unrendered data of that family, e.g. ``record`` and ``error`` for ``bad_data``. ``value`` keeps the rendered sentence.
  - ``group`` is the message's identity, ``[verbosity, key, subject, ...]`` followed by the fields that family groups by. Messages with the same ``group`` are repeats of one problem.

* **Changed Endpoint**: ``GET /api/(version)/messages``

  - The response is now ``{"messages": [...], "dropped": int}`` instead of ``{"errors": [...], "warnings": [...]}``. Each entry of ``messages`` is the same ``{"type": ..., "data": ...}`` object the websocket sends, instead of a string, plus ``count``, how many times it was sent while held, and ``last_sent``, the timestamp of its last send. ``dropped`` counts the messages discarded to stay within bounds, each of which is written to the backend log.
  - Every message type that could not be delivered over a websocket is now held here, whether the send failed, no client was connected, or the client disconnected before receiving it. Previously each of those three paths applied a different policy. Progress and status types are dropped, except a ``progress_updates`` message carrying a CSV import result. A state message is held only in its latest form per key (e.g. ``refresh_balances`` per chain), and a repeating failure once with a count: a ``user_message`` once per ``group``, keeping its newest ``value``.

* **Changed Message**: ``exchange_unknown_asset``

  - Now also sent for unknown assets in bit2me balances, deposits/withdrawals and trades, cryptocom deposits/withdrawals and trades, and kraken ledger events. These previously arrived as ``user_message`` errors.

No Available Indexers Websocket Message
---------------------------------------

* **Changed Message**: ``no_available_indexers``
* **Change**: The ``data`` object gained an optional ``reason`` key. When it is ``etherscan_paid_key_required`` the chain was refused by etherscan for the configured key and a paid etherscan API key is needed to query it.

Frontend Settings Moved To Their Own Resource
---------------------------------------------

``frontend_settings`` is now read and written on its own resource, as JSON, and only ever merged, so a client no longer deletes keys it does not know.

* **New Endpoint**: ``GET /api/(version)/settings/frontend``

  - Returns the frontend settings as a JSON object. A stored blob that is absent, empty, or not a JSON object reads as ``{}``.

* **New Endpoint**: ``PATCH /api/(version)/settings/frontend``

  - Takes ``patch`` (keys to set) and ``remove`` (keys to delete) and applies them server-side, leaving other keys untouched. A key is replaced wholesale, not merged recursively. Key names must match ``[A-Za-z_][A-Za-z0-9_]*``.
  - Answers ``true``. Read the result back with the GET above.

* **Changed Endpoint**: ``GET /api/(version)/settings``

  - ``frontend_settings`` is **no longer part of the response**. The same applies to the settings carried by ``PUT /settings``, by login and by account creation. Callers must read it from ``GET /settings/frontend``.

* **Changed Endpoint**: ``PUT /api/(version)/settings``

  - ``frontend_settings`` is **no longer accepted** and is rejected as an unknown field. ``PATCH /settings/frontend`` is the only way to write it.

Asset Search NFT Handling
-------------------------

* **Changed Endpoint**: ``POST /api/(version)/assets/search/levenshtein``

  - The boolean ``search_nfts`` is replaced by ``nft_handling``, which takes ``'exclude'`` (the default, matching ``search_nfts: false``), ``'include'`` (matching ``search_nfts: true``) and the new ``'show_only'``. Callers sending ``search_nfts`` must migrate; the field is no longer accepted.
  - ``'show_only'`` searches nfts alone. It cannot be reproduced by filtering an ``'include'`` response: assets and nfts are searched by separate queries whose results are merged and truncated to ``limit`` together, so the nfts can be cut off entirely when enough assets sort ahead of them.

Session Cookie Authentication (Docker)
--------------------------------------

When rotki is set up with the ``ROTKI_SESSION_KEY`` environment variable (the Docker/web deployment), the API enforces a single active session backed by an ``HttpOnly`` cookie. Requests without a valid session cookie are rejected with ``401`` and the websocket handshake is refused. Logging in a user establishes the session and revokes any previous one, so only one frontend is served at a time.

* **New Endpoint**: ``POST /api/(version)/users/(name)/authenticate``

  - Accepts the account ``password`` and issues the session cookie before the asynchronous unlock, so the gated task poll and websocket handshake are authorized.
  - Has no effect when ``ROTKI_SESSION_KEY`` is unset (desktop/Electron deployment), where the API stays session-less as before.

* **New Environment Variable**: ``ROTKI_SESSION_COOKIE_SECURE``

  - Opts the session cookie into the ``Secure`` attribute, which stays off by default because the image serves plain http on loopback or a LAN, where the flag would stop the cookie being sent at all. ``1``/``true`` always sets it; ``forwarded`` derives it per request from ``X-Forwarded-Proto``; an unrecognised value warns and is treated as off.
  - Starling now normalises ``X-Forwarded-Proto`` on every proxied request, keeping an inbound value only when the peer is a trusted hop (the ``--trusted-proxy`` set the access log already uses) and overwriting it with ``http`` otherwise. Previously the header was passed through untouched, so it must not be trusted by anything reading it on an older build. core cannot judge the hop itself, since it sits on loopback behind starling.

* **New Endpoint**: ``POST /api/(version)/mcp/token``

  - Issues an MCP-only bearer linked to the authenticated active session for the streamable HTTP transport exposed by Docker at ``/mcp``. It cannot be used as a REST API session cookie.
  - The MCP server validates the bearer token before protocol handling and checks the durable active-session record, so logout and session takeover revoke MCP access.

* **Changed Endpoint**: ``GET /api/(version)/info``

  - Gains ``session_auth``, ``true`` when the backend was given ``ROTKI_SESSION_KEY``. It is reported separately from the acknowledgement below: one says the operator acknowledged an unauthenticated API, the other says there is none. The frontend shows its Docker warning only when neither holds.
  - ``accept_docker_risk`` is replaced by ``accept_unauthenticated_api``, driven by the new ``ROTKI_ACCEPT_UNAUTHENTICATED_API`` environment variable. ``ROTKI_ACCEPT_DOCKER_RISK`` is no longer read at all. It acknowledged a generic "you are running in docker" warning, so honouring it would leave every operator who set it silently unaware that session authentication now exists. Anyone still relying on it sees the new warning once and can then set ``ROTKI_SESSION_KEY`` or the new variable.

* **New Endpoint**: ``GET /api/(version)/session/validate``

  - Returns ``true`` when the caller holds a valid, currently active session **cookie**, and ``401`` otherwise. Intended as an authorization subrequest: the Docker proxy forwards a caller's cookie here and only then dispatches a control operation, since core alone knows whether a newer login has retired that session.
  - An internal MCP bearer is rejected here even though it authorizes ordinary data routes, so MCP access never confers backend control.

Docker Control Endpoint
-----------------------

The Docker deployment gains ``/_control``, served by the starling proxy on the published port. It lets the frontend restart the backend, start or stop the MCP server, and choose whether MCP comes up with the backend tree, none of which had any path outside the desktop app (closes ``#2807``).

* **New Endpoint**: ``GET /_control``

  - Returns ``{"available": true, "methods": [...]}`` when the endpoint is mounted, and ``404`` when it is not. Unauthenticated, so the frontend can decide whether to offer the controls before a user has logged in.
  - Mounted **only** in Docker with ``ROTKI_SESSION_KEY`` set. A deployment with no session authentication serves no control surface at all.

* **New Endpoint**: ``POST /_control``

  - JSON-RPC 2.0, carrying ``status``, ``restart``, ``startService``, ``stopService`` and ``setServiceAutostart``. ``start`` and ``stop`` are refused: ``stop`` would exit PID 1 and take the container with it.
  - Authorized per request by forwarding the caller's session cookie to ``GET /api/1/session/validate``. ``401`` when core refuses, ``503`` when core cannot be reached.
  - ``restart`` accepts ``loglevel`` and nothing else. A caller-chosen ``data_directory``/``log_directory`` is refused rather than ignored, since in a container those are fixed mounts.
  - ``startService``/``stopService`` only address services that allow manual control, which today means ``mcp`` alone; core and colibri are not independently stoppable.
  - ``setServiceAutostart`` takes ``{"service": "mcp", "autostart": <bool>}`` and records whether MCP comes up with the backend tree from the next start on. It starts and stops nothing, and is refused for any other service. The preference is stored in ``<data_dir>/app.config.json`` as ``{"mcpAutoStart": <bool>}``, the same file name and key the desktop app uses, so it survives a container recreate; with no file MCP stays down, the same default the desktop app ships. Each service's current preference is reported as ``autostart`` in the ``status`` reply.

  A validation core granted within the last two minutes is honoured if core later becomes unreachable, so a ``restart`` whose bring-up fails can still be retried from the UI. It is dropped immediately on a ``401``, and never overrides a core that is answering.

Spam Token Endpoint Renamed
----------------------------

The spam token endpoint now supports both EVM and Solana tokens and has been renamed accordingly.

* **Renamed Endpoint**: ``/api/(version)/assets/evm/spam/`` is now ``/api/(version)/assets/spam/``

  - ``POST`` and ``DELETE`` methods now accept both EVM and Solana token identifiers.


:releasetag:`1.42.0`
====================

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
  - Added ``state_markers`` list parameter that accepts any combination of marker values: ``"customized"``, ``"profit adjustment"``, ``"matched"``, ``"imported from csv"``.
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
  - Optional ``matched_events`` parameter specifying the list of DB identifiers of events to match with the asset movement. The asset movement is marked as having no match if this parameter is omitted or an empty list.
  - Example: ``{"asset_movement": 123, "matched_events": [124]}``

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
  - Replaced the ``customized`` flag with a ``states`` list. Valid states are ``customized``, ``profit adjustment``, ``matched``, ``imported from csv``.

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
