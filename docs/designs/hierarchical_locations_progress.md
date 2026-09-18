# Hierarchical locations: inventory, decisions and progress

Companion to `hierarchical_locations.md` (the design). This file records the implementation
inventory, the placement decisions taken while implementing, and the state of each section, so
that the work can be resumed by anyone from the repository alone.

## Sections and status

Each section ends in one or more commits. Update the status column in the commit that finishes a
section.

| # | Section | Design workstream | Status |
|---|---------|-------------------|--------|
| 1 | Inventory, catalog, old-to-new mapping, catalog validation tests | A, B (catalog) | done |
| 2 | `locations` schema, v54 upgrade, `DBLocations`, migration fixtures/assertions | A, B | done |
| 3 | Replace the enum with `LocationIdentifier` + constants in all backend consumers | C | done |
| 4 | Exact/subtree filtering and aggregation (history, balances, snapshots, accounting, exports) | C | todo |
| 5 | Custom location API (CRUD, usage, image upload) | B | todo |
| 6 | Connector separation (`integration_connections`, registries, Qonto, FinTS, global v19 mappings) | D | todo |
| 7 | Generic import preflight, aliases, user-data export/import | C, section 12 | todo |
| 8 | Frontend (tree store, selectors, filters, management, bank flow, preflight) | E | todo |
| 9 | Cleanup, performance measurements, docs, full test runs | F, section 17 | todo |

Transitional state (removed by section 6 unless noted):

- FinTS has no location. `rotkehlchen.banks.constants.FINTS_CONNECTOR` ('fints') keys its
  credentials and manifest like an exchange location until connections store connector and
  location separately. `LOCATION_DETAILS` still carries a `fints` entry for the bank setup UI.
  `ExchangeInterface.data_location` is the location a connection's events, balances and snapshots
  use; `Fints.data_location` returns `banks` until section 6 gives each FinTS connection its
  institution location.
- `user_credentials.location` and `user_credentials_mappings.credential_location` hold text but have
  no FK: they are connector identity, replaced by `integration_connections` in section 6. Premium
  credentials keep the `external` location they always had.

Pre-tree character encoding: `rotkehlchen/locations/legacy_chars.py` is the frozen codec every
historical user DB upgrade (v36..v53), the v54 migration and the global v18->v19 conversion use. Old
upgrades no longer call the enum serializers.

## Placement decisions (review these)

The catalog is `rotkehlchen/data/locations.json`; the loader and tree validation are in
`rotkehlchen/locations/`. Identifiers of existing built-ins equal their current API serialization
(`str(Location.X)`), so every string key built from `str(location)` (query ranges, key-value cache,
settings) stays valid without rewriting.

- `TOTAL` -> root `total` ("Total").
- `BLOCKCHAIN` -> `blockchain`, displayed as "Blockchains". The old broad snapshot bucket and the
  new structural node are the same node.
- `BANKS` -> `banks` ("Banks"); same reasoning.
- New structural built-ins: `evm chains` (below `blockchain`), `exchanges` and `other` (below
  `total`).
- EVM Chains: ethereum ("Ethereum Mainnet"), optimism, arbitrum one, base, polygon pos, gnosis,
  scroll, binance sc, hyperliquid (HyperEVM), monad, sonic, robinhood, ink and **avalanche**
  (rotki's Avalanche support is the C-Chain, which is an EVM chain even though the code does not
  treat it as one of `EVM_LOCATIONS`).
- Directly below Blockchains: bitcoin, bitcoin cash, solana, polkadot, kusama, **zksync lite**
  (EVM-like, not EVM) and **loopring** (a shut-down zk-rollup, kept for historical data).
- Exchanges: every exchange location, including dead ones (ftx, ftxus, bittrex, coinbasepro) and
  import-only ones (blockfi, nexo, shapeshift, uphold, bisq, cryptocom, ...). **All are active**:
  users still enter historical data for dead exchanges manually, so hiding them from new-entry
  selectors would be a regression. Only the legacy branch is inactive.
- Banks: qonto. FinTS is not a location.
- Other: external, equities, realestate ("Real estate"), commodities.
- Legacy (conditional, never in the catalog): `legacy locations` ("Legacy locations", inactive,
  below `other`) with `legacy:uniswap`, `legacy:balancer`, `legacy:gitcoin`, `legacy:sushiswap`.
  Defined in `rotkehlchen/locations/legacy_chars.py`.
- Icons of structural nodes: total `lu-wallet`, blockchain `lu-link`, evm chains `lu-layers`,
  exchanges `lu-arrow-left-right`, other `lu-ellipsis`, legacy `lu-archive`. All are icons the
  frontend already uses.

The reviewed old-character mapping is `V53_LOCATION_CHAR_TO_IDENTIFIER` in
`rotkehlchen/locations/legacy_chars.py`. It covers the 57 characters a v53 database can hold apart
from the four legacy ones. Sonic, Robinhood, Ink, Qonto and FinTS were only introduced by the
unreleased v53->v54 upgrade, so no released database contains their characters.
`rotkehlchen/tests/unit/test_location_catalog.py` checks that every enum value is handled exactly
once.

Deferred per user decision (2026-09-18): the `location_aliases` table is built in section 7
together with import preflight, not earlier. It is still required.

## Inventory

### Storage: real locations (become TEXT FKs to `locations(identifier)`)

User DB, all currently `CHAR(1)` via `Location.serialize_for_db()`:

| Table.column | Notes |
|--------------|-------|
| `history_events.location` | indexed (`idx_history_events_location`) |
| `history_events_backup.location` | same DDL as history_events (`DB_CREATE_HISTORY_EVENTS_BACKUP`) |
| `timed_location_data.location` | PK part; holds the `total` aggregate rows |
| `manually_tracked_balances.location` | |
| `margin_positions.location` | |
| `skipped_external_events.location` | in UNIQUE(data, location) |
| `bitcoin_transactions.location` | bitcoin / bitcoin cash; indexed |
| `event_metrics.location` | no FK today; indexed in `idx_event_metrics_balances_latest` |
| `data_issues.location` | `TEXT`, no FK, but stores the DB character (`tasks/data_issues.py` deserializes it with `deserialize_from_db`); in unique indexes |

Not locations: `user_notes.location` (UI page name), every `location_label` column (account or
address label).

### Storage: connector / connection identity (section 6)

| Place | Current key | Target |
|-------|-------------|--------|
| `user_credentials(name, location)` | location char + name | `integration_connections` (connector id + location id + stable connection id) |
| `user_credentials_mappings(credential_name, credential_location, ...)` | char + name | keyed by connection identifier |
| `used_query_ranges.name` | `{location}_{history_events|margins|lending_history}_{name}`, `{location}_lending_history_{name}` | connection identifier |
| `key_value_cache.name` | `{location}_{name}_...` (coinbase, bitstamp, binance, banks) | connection identifier |
| setting `non_syncing_exchanges` | JSON list of `ExchangeLocationID` | connection identifiers |
| global setting `binance_pairs_queried_at_{location}` | connector (binance / binanceus) | connector identifier |
| global `binance_pairs.location` | char | connector identifier |
| global `location_asset_mappings.location` | char, NULL = any | connector identifier (rename concept to connector asset mappings) |

Global DB v18->v19 is unreleased (1.45), so these global changes fold into it. Section 2 already
converted `location_asset_mappings.location` and `binance_pairs.location` from characters to text
names in that upgrade and in the packaged `rotkehlchen/data/global.db` (only those rows changed; for
exchanges the name is also the connector identifier). Remote asset-mapping updates from the data
repo already use names (`Location.deserialize(raw_location)` in `db/updates.py`), so the data repo
needs no change.

### Code classification (backend, 147 non-test files, ~960 references)

- **Real location** (event, balance or snapshot `location`): `history/events/**`, `chain/**` (chain
  location of on-chain events), `db/history_events.py`, `db/filtering.py`, `db/dbhandler.py`
  (snapshots, manual balances, margin positions), `balances/**`, `accounting/**`,
  `tasks/historical_balances.py`, `tasks/data_issues.py`, `history/data_issues/**`,
  `data_import/importers/*` (event location of imported rows), `serialization/`, `api/v1/schemas.py`
  (`LocationField`), `api/services/*`, `mcp/*`, `externalapis/*` (event locations).
- **Connector identity** (which implementation fetches data): `exchanges/manager.py`
  (`_get_exchange_module_name` imports modules by location name), `exchanges/constants.py`
  (`SUPPORTED_EXCHANGES` and so on), `constants/location_details.py` (exchange and bank details
  mixed into location metadata), `banks/manager.py` (`import_module(f'rotkehlchen.banks.{location}')`),
  `banks/manifests.py` (`BankManifest.location`), `globaldb/binance.py`,
  `globaldb/handler.py` (location asset mappings), `assets/converters.py`.
- **Connection identity** (one configured account): `ExchangeLocationID(name, location)`,
  `ExchangeInterface.location_id()`, `db/dbhandler.py` credential and rename code, bank
  `pending_setups`/`sync_status`, API payloads identifying connections by `(location, name)`.
  Exchange modules use `self.location` for all three meanings; section 6 splits them.
- **Protocol counterparty**: none left in code. `UNISWAP`, `BALANCER`, `SUSHISWAP`, `GITCOIN` are
  referenced only by the enum and `constants/location_details.py`.
- **Historical upgrades and migrations** (`db/upgrades/*`, `data_migrations/*`): they operate on old
  schemas. Freeze them with literal characters or string identifiers when the enum goes (section 3).

## Section 2 notes

- Schema: `locations` table + `idx_locations_parent` + `unique_locations_sibling_name`; every real
  location column is `TEXT NOT NULL REFERENCES locations(identifier)` (no default). Fresh DBs seed
  built-ins through `DBLocations.seed_builtin_locations` right after the create script.
- `rotkehlchen/db/locations.py` (`DBLocations`): catalog seeding, get/get_all, recursive
  `descendants` and `ancestors`, `path_names`, `validate_tree`, `validate_assignable` (rejects root
  and archived), `usage`, custom `add_custom`/`edit_custom`/`delete_custom` with all mutation rules.
  `LOCATION_REFERENCES` lists every real location column.
- v53->v54 upgrade: the five old "add location" steps are gone; new steps create/seed the tree, add
  the conditional legacy branch, rebuild the 11 location-bearing tables through a temporary
  `location_char_mapping` table (derived tables `event_metrics`/`data_issues` may drop unknown rows,
  all others abort), recreate their indexes, drop `location`, then run a scoped
  `foreign_key_check` and tree validation.
- Tests: `tests/db/test_db_upgrades.py::test_upgrade_db_53_to_54_locations` (every character in
  history events, every table, legacy none/each/all-in-every-table), `..._unknown_location_restores_backup`,
  `tests/db/test_db_locations.py`, `tests/unit/test_location_catalog.py`, global
  `test_upgrade_v18_v19`.
- Known pre-existing failures on develop in this sandbox (not ours): `test_inquirer.py::test_switching_to_backup_api`,
  `test_bitcoin.py::test_bitcoin_balance_api_resolver`, `test_bitcoin.py::test_local_bitcoin_mempool_api`,
  `accounting/test_settings.py::test_eth_withdrawal_not_taxable`. VCR tests error in parallel runs
  here because `git merge-base bugfixes develop` fails in the sandbox.

## Section 3 notes

- The `Location` enum is gone. `LocationIdentifier` (`rotkehlchen/locations/types.py`) is the
  only location type; `LOCATION_<NAME>` constants for every built-in are in
  `rotkehlchen/locations/constants.py` (a test checks they match the catalog).
- `rotkehlchen/locations/chains.py` is the chain registry: `EVM_LOCATIONS`, `EVMLIKE_LOCATIONS`,
  `EVM_EVMLIKE_LOCATIONS`, `BITCOIN_LOCATIONS`, `BLOCKCHAIN_LOCATIONS`, `location_from_chain_id`,
  `location_to_chain_id`, `location_from_chain`, `location_to_chain` and the `is_*_location`
  predicates. The Literal location types were dropped; annotations use `LocationIdentifier`.
- Parsing: `deserialize_location_identifier` checks syntax only (built-in names are
  case-insensitive and accept underscores; prefixed ids like `custom:<uuid>` are verbatim).
  `deserialize_builtin_location` (catalog.py) keeps the old "must be a location rotki knows"
  semantics for CSV importers, remote asset-mapping updates, bridge extra data and the MCP
  taxonomy. The generic CSV importer therefore still falls back to External for anything that is
  not a built-in until section 7 adds preflight.
- Existence checks happen where user data is written: manual balance add/edit and history event
  add/edit call `DBLocations.validate_assignable` (edits accept archived locations). API
  `LocationField` only checks syntax and `limit_to`.
- `LOCATION_DETAILS` (/locations/all) is derived from the catalog: every built-in (Total and the
  structural nodes included), the four legacy locations and the transitional fints entry, each
  with an explicit `label`. Display names now come from the catalog, e.g. `cryptocom` is
  "Crypto.com" and `ethereum` "Ethereum Mainnet"; `get_formatted_location_name` returns the
  identifier for anything without details.
- Tests: `tests/utils/locations.py` freezes the v53 enum order so migration tests keep an
  independent source; `try_get_first_exchange` takes the expected exchange class instead of
  location-literal overloads.
