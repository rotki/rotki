# History Events Implementation Files Summary

## Backend (Python)

### Database Layer

1. **`/Users/banteg/dev/rotki/rotki/rotkehlchen/db/history_events.py`**
   - Main database handler class `DBHistoryEvents`
   - Core methods:
     - `add_history_event()` - Insert single event
     - `add_history_events()` - Insert multiple events
     - `edit_history_event()` - Edit existing event
     - `delete_history_events_by_identifier()` - Delete events
     - `get_history_events()` - Query events with filtering
     - `get_history_events_and_limit_info()` - Query with pagination info
     - `rows_missing_prices_in_base_entries()` - Find events missing USD values
   - Handles serialization/deserialization of different event types
   - Manages customized events tracking

2. **`/Users/banteg/dev/rotki/rotki/rotkehlchen/db/filtering.py`**
   - Filter query classes:
     - `HistoryEventFilterQuery` - Base filter for all history events
     - `EvmEventFilterQuery` - EVM-specific event filtering
     - `EthStakingEventFilterQuery` - ETH staking event filtering
     - `EthDepositEventFilterQuery` - ETH deposit filtering
     - `EthWithdrawalFilterQuery` - ETH withdrawal filtering
   - Filter parameters:
     - Timestamp range (from_ts, to_ts)
     - Assets
     - Event types/subtypes
     - Locations and location labels
     - Transaction hashes
     - Counterparties
     - Products
     - Addresses
     - Custom events only flag
     - Exclude ignored assets flag

3. **`/Users/banteg/dev/rotki/rotki/rotkehlchen/db/schema.py`**
   - Database schema definitions:
     - `history_events` table - Main events table
     - `evm_events_info` table - EVM-specific event data
     - `eth_staking_events_info` table - ETH staking event data
     - `history_events_mappings` table - Event state tracking (customized, etc.)
   - Indexes on:
     - entry_type, timestamp, location, location_label
     - asset, type, subtype, ignored

### API Layer

4. **`/Users/banteg/dev/rotki/rotki/rotkehlchen/api/rest_helpers/history_events.py`**
   - Helper functions for API operations:
     - `edit_grouped_events_with_optional_fee()` - Handle grouped event editing
     - `edit_grouped_evm_swap_events()` - Handle EVM swap event editing

5. **`/Users/banteg/dev/rotki/rotki/rotkehlchen/api/v1/resources.py`**
   - REST API endpoints (methods in resource classes):
     - GET `/api/1/history/events` - Query history events
     - POST `/api/1/history/events` - Add new events
     - PATCH `/api/1/history/events` - Edit existing events
     - DELETE `/api/1/history/events` - Delete events
     - POST `/api/1/history/events/export` - Export events to CSV

6. **`/Users/banteg/dev/rotki/rotki/rotkehlchen/api/v1/schemas.py`**
   - API request/response schemas
   - Validation schemas for history events

### Event Structures

7. **`/Users/banteg/dev/rotki/rotki/rotkehlchen/history/events/structures/`**
   - `base.py` - Base history event classes
   - `evm_event.py` - EVM event structure
   - `eth2.py` - ETH staking event structures
   - `asset_movement.py` - Asset movement events
   - `swap.py` - Swap event structures
   - `types.py` - Event type enums

## Frontend (TypeScript/Vue)

### Components

8. **`/Users/banteg/dev/rotki/rotki/frontend/app/src/components/history/events/`**
   - **`HistoryEventsTable.vue`** - Main table component for displaying events
   - **`HistoryEventsList.vue`** - List view component
   - **`HistoryEventsAction.vue`** - Action buttons for events
   - **`HistoryEventsExport.vue`** - Export functionality
   - **`HistoryEventsQueryStatus.vue`** - Query status display
   - **`HistoryEventsSkippedExternalEvents.vue`** - Skipped events handling

### Composables/API

9. **`/Users/banteg/dev/rotki/rotki/frontend/app/src/composables/history/events/index.ts`**
   - Main composable for history events operations
   - Functions:
     - `fetchHistoryEvents()` - Query events
     - `addHistoryEvent()` - Add new event
     - `editHistoryEvent()` - Edit event
     - `deleteHistoryEvent()` - Delete event

10. **`/Users/banteg/dev/rotki/rotki/frontend/app/src/composables/api/history/events/index.ts`**
    - API layer for history events
    - Direct API calls to backend

### Types

11. **`/Users/banteg/dev/rotki/rotki/frontend/app/src/types/history/events/index.ts`**
    - TypeScript type definitions for history events
    - Interfaces for event structures

12. **`/Users/banteg/dev/rotki/rotki/frontend/app/src/modules/history/events/request-types.ts`**
    - Request payload interfaces:
      - `HistoryEventRequestPayload` - Query parameters
      - `HistoryEventExportPayload` - Export parameters
    - Filter fields:
      - `fromTimestamp`, `toTimestamp`
      - `groupByEventIds`
      - `eventIdentifiers`, `eventTypes`, `eventSubtypes`
      - `locationLabels`, `asset`, `counterparties`
      - `location`, `products`, `entryTypes`
      - `txHashes`, `validatorIndices`
      - `customizedEventsOnly`, `excludeIgnoredAssets`

### Forms

13. **`/Users/banteg/dev/rotki/rotki/frontend/app/src/modules/history/management/forms/`**
    - Various form components for creating/editing different event types
    - `EvmEventForm.vue`, `SwapEventForm.vue`, etc.

## Key Features

1. **Filtering Capabilities**:
   - Time range filtering
   - Asset filtering
   - Event type/subtype filtering
   - Location and address filtering
   - Counterparty and product filtering
   - Custom events filtering
   - Ignored assets exclusion

2. **Event Types Supported**:
   - EVM events (transactions)
   - EVM swap events
   - ETH staking events (deposits, withdrawals, block events)
   - Asset movements
   - Generic history events

3. **Database Optimization**:
   - Multiple indexes for fast querying
   - Separate tables for event-type-specific data
   - Event grouping support
   - Pagination support

4. **User Features**:
   - Add/Edit/Delete events
   - Export to CSV
   - Customized event tracking
   - Query status monitoring
   - Grouped event display
