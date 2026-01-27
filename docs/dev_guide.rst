Developer Guide
##################################################
.. toctree::
   :maxdepth: 2


History Events — Automatic Task Timeline
******************************************

This section describes how history events are processed automatically and on user action, covering both the backend task system and the frontend lifecycle.


Backend Tasks
==============

.. list-table::
   :header-rows: 1
   :widths: 25 15 10 50

   * - Task
     - Periodic
     - API
     - WebSocket Messages
   * - Historical Balances
     - Yes (10 min)
     - Yes
     - ``PROGRESS_UPDATES``, ``NEGATIVE_BALANCE_DETECTED``
   * - Asset Movements
     - Yes (configurable)
     - Yes
     - ``UNMATCHED_ASSET_MOVEMENTS``
   * - Custom Events
     - No
     - Yes
     - None


Historical Balances Processing
-------------------------------

Runs every 10 minutes or via API. When history events are mutated, a cache stores the earliest affected timestamp so only necessary recomputation happens.

Sends ``PROGRESS_UPDATES`` during processing. Sends ``NEGATIVE_BALANCE_DETECTED`` if any asset would go negative (indicating missing or incorrect events).

::

    Periodic Scheduler (10 min)              API: POST /api/v1/tasks
             |                                        |
             +----------------+-----------------------+
                              v
                process_historical_balances()
                              |
                              v
             +----------------+----------------+
             v                                 v
      WS: PROGRESS_UPDATES      WS: NEGATIVE_BALANCE_DETECTED


Unmatched Asset Movements
--------------------------

Runs periodically (configurable) or via API. Correlates exchange deposit/withdrawal records with blockchain transactions.

Sends ``UNMATCHED_ASSET_MOVEMENTS`` with count if any remain unmatched, prompting users to manually resolve them.

::

    Periodic Scheduler           API: POST /api/v1/tasks     API: PUT .../match_asset_movements
             |                            |                            |
             +------------+---------------+                            |
                          v                                            |
             process_asset_movements()                                 |
                          |                                            |
                          v                                            |
               match_asset_movements()  <------------------------------+
                          |
                          v
             WS: UNMATCHED_ASSET_MOVEMENTS
                  (if unmatched > 0)


Custom Event Handling
----------------------

API-only (no periodic task). Detects duplicates when a customized event coexists with its re-decoded version.

``GET`` detects duplicate groups (auto-fixable, manual review, or exact). ``POST`` applies fixes. Returns HTTP response only.

::

    GET /api/1/customizedeventduplicatesresource     POST /api/1/customizedeventduplicatesresource
                  |                                               |
                  | (detect)                                      | (fix)
                  +----------------------+------------------------+
                                         v
                    find_customized_event_duplicate_groups()
                                         |
                                         v
                                 HTTP Response only


Frontend Lifecycle
===================

The frontend triggers two heavy tasks via ``triggerTask`` calls:

- ``triggerTask('asset_movement_matching')``
- ``triggerTask('historical_balance_processing')``


Phase 1 — App Startup
-----------------------

Before the user navigates to the History Events page:

- A global watcher monitors the history events processing status.
- When processing finishes, it calls ``triggerTask('asset_movement_matching')``.


Phase 2 — History Events Page Loads
-------------------------------------

A ``watch(loading)`` fires when ``loading`` becomes ``false``, where ``loading`` is ``processing || groupLoading``:

- **processing** — history events processing (querying and decoding).
- **groupLoading** — fetching events from the database (e.g. after editing an event, changing page, or re-fetching the list).

When ``loading`` becomes ``false`` (including after editing an event), the following run in parallel:

- ``refreshUnmatchedAssetMovements()`` — fetches unmatched and ignored movement lists (API query only, no task trigger).
- ``fetchCustomizedEventDuplicates()`` — fetches duplicate group IDs (API query only, no task trigger).

If issues are found, a warning button appears. Alert banners are shown after the user clicks that button.


Phase 3 — User Actions on the History Events Page
---------------------------------------------------

**Unmatched movements:**

- User clicks "Auto Match" -> ``triggerTask('asset_movement_matching')`` -> awaits task -> refreshes list.
- User manually matches a movement -> API call (no task) -> refreshes list.

**Customized event duplicates:**

- User clicks "View" -> navigates to filtered page (no task).
- User clicks "Fix" -> ``fixDuplicates()`` API call (no task) -> refreshes counts.
- There is no automatic fix that runs via a heavy task. All duplicate fixing requires explicit user action.


Phase 4 — Historical Balances Page
------------------------------------

When the user clicks "Get Historical Balances":

- **Source = Archive Node** — triggers an API task (query only).
- **Source = Historical Events** — triggers an API task. If the response has ``processingRequired === true`` (history events still need to be processed before balances can be calculated), it calls ``triggerTask('historical_balance_processing')``.

WebSocket messages update the progress bar and negative balance warnings in real time during processing.


Summary
--------

**triggerTask Calls**

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - ``triggerTask`` Call
     - Fires Automatically (No User Click)
     - Fires by User Action
   * - ``'asset_movement_matching'``
     - History event processing finishes (monitor watcher)
     - User clicks "Auto Match" button
   * - ``'historical_balance_processing'``
     - Never
     - User clicks "Get Historical Balances" and backend says processing is required

**Feature Automation**

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Feature
     - Has Automatic Fix/Trigger?
   * - Historical balances processing
     - No — user must click the button (auto-fetch only if saved filters exist)
   * - Unmatched asset movements
     - Yes — auto-match runs when history event processing finishes
   * - Customized event duplicates
     - No — everything requires explicit user action
