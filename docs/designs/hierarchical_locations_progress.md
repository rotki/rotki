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
| 4 | Exact/subtree filtering and aggregation (history, balances, snapshots, accounting, exports) | C | done |
| 5 | Custom location API (CRUD, usage, image upload) | B | done |
| 6 | Connector separation (`integration_connections`, registries, Qonto, FinTS, global v19 mappings) | D | done |
| 7 | Generic import preflight, aliases, user-data export/import | C, section 12 | done |
| 8 | Frontend (tree store, selectors, filters, management, bank flow, preflight) | E | todo |
| 9 | Cleanup, performance measurements, docs, full test runs | F, section 17 | todo |

Transitional state: none left from sections 1-5. Section 6 gave FinTS connections their own
location and replaced `user_credentials` (bar the premium row) and `user_credentials_mappings`
with `integration_connections`.

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

## Section 4 notes

- `LocationScope` (`exact`, `subtree`) in `rotkehlchen/locations/types.py`. The API field is
  `location_scope`, default `exact`, on every endpoint with a location filter: history events
  (query, export, deletion, group position), data issues, and the three historical balance
  endpoints (event metrics).
- `DBLocationFilter(location, scope, exclude, column)` in `db/filtering.py` is the only location
  filter. The subtree scope is an uncorrelated `location IN (<recursive CTE>)` subquery built by
  `db.locations.subtree_query`, so filters need no cursor. SQLite evaluates it once and probes
  `idx_history_events_location` with the result
  (`tests/db/test_location_filtering.py::test_subtree_filter_uses_location_index` asserts the
  plan). This departs from the design's literal `IN (?, ?, ...)` only in where the descendant set
  is resolved; the query shape and index use are the same. The subtree of `total` adds no
  predicate. `excluded_locations` (internal only, no API) expands with the same scope.
- Balance snapshots now write the most specific location: every chain is its own
  `timed_location_data` bucket (`BlockchainBalances.totals_per_chain` +
  `locations.chains.location_of_chain_balances`, where beacon chain validators count as
  `ethereum` and Kusama, Polkadot and Avalanche map to their catalog nodes). NFTs go to their
  chain (`evm chains` if unknown). Each location's value is net of the liabilities held there
  (chain liabilities to their chain, manual liabilities to their own location), so the values add
  up to the net value; previously every liability was subtracted from the one `blockchain`
  bucket. `/balances` `location` stats change the same way (per chain instead of `blockchain`).
  Old `blockchain` rows stay valid broad buckets and `total` stays the stored aggregate.
- There is no backend endpoint reading a per-location snapshot history for a selected node, so
  read-side subtree aggregation of snapshots (sum direct + descendants, root read directly) belongs
  to the frontend tree store in section 8, using `/statistics/value_distribution` rows.
- `/locations/associated` returns `{"locations": [...], "ancestors": [...]}`: directly used
  locations, and the further ancestors needed for their paths (`DBLocations.ancestor_identifiers`).
  Credential rows whose connector is not a location (FinTS) are left out. The frontend reads
  `locations` only for now.
- Exports: history events CSV adds `location_path` after `location`; the PnL CSV adds it as the
  last column so the formula column letters do not move; the human-readable snapshot location CSV
  adds it too (the import CSV is unchanged). Paths come from `DBLocations.display_paths`
  (`Blockchains > EVM Chains > Ethereum Mainnet`, root left out).
- Fixed section 3 leftovers found by the scoped test run: three API error messages still called
  `.name` on the location (Bitcoin asset check, exchange secret/passphrase checks) and a stale
  auto-notes expectation. The frontend backend-icons extractor now also scans
  `rotkehlchen/data/locations.json`, otherwise regenerating dropped `lu-book-text` (External).
- More pre-existing failures in this sandbox, identical on HEAD:
  `test_history_events_export.py::test_history_export_download_path_traversal`,
  `test_exchanges.py::test_setup_exchange` (live exchanges, skipped in CI).

## Section 5 notes

- Endpoints (documented in `docs/api.rst`, "Location tree"): `GET/POST /locations`,
  `PATCH/DELETE /locations/<identifier>`, `GET /locations/<identifier>/usage`,
  `GET/POST/DELETE /locations/<identifier>/image`. `LocationsService`
  (`api/services/locations.py`) owns request handling; the tree rules stay in `DBLocations`.
  `/locations/all` (flat `LOCATION_DETAILS`) stays until the frontend moves to the tree in
  section 8.
- `PATCH` changes only the given fields. `icon: null` removes the icon (in `edit_custom` the
  `...` default means unchanged). `dry_run` checks the edit without saving; every edit returns
  `old_path` and `new_path` (display names from the root) for the move warning.
- Status codes: unknown location 404; tree rule violations and edits of built-ins 400; deleting a
  used, parent or built-in location 409 (with `usage` explaining why).
- Images reuse the asset icon machinery: `ALLOWED_ICON_EXTENSIONS`, `FileField` validation and
  the image/etag responses of `rotkehlchen/icons.py`. Only multipart uploads are accepted, no
  backend paths or URLs (the asset icon PUT with a path is deliberately not mirrored). Files live
  per user in `<user dir>/images/locations/`, named `<quoted identifier>_<md5 prefix><ext>`; the
  `image` column holds that name, so the name changes with the content and clients can cache by
  it. The old file is removed only after the DB points at the new one; deleting a location or
  its image removes the file. Built-in `image` values are packaged frontend names and are never
  served by the backend, so a client tells the two apart by `is_builtin`.
- User-data backup and restore of the images belongs to section 7.

## Section 6 notes

- A connection is one configured account of a connector: `integration_connections(identifier,
  name, connector_identifier, location_identifier, api_key, api_secret, passphrase)` with a
  uuid4 identifier and `UNIQUE(connector_identifier, name)`. Connector specific settings (kraken
  account type, binance markets, kraken futures keys, ...) are rows of
  `integration_connection_settings`, deleted with the connection. `DBConnections`
  (`db/connections.py`) is the only code reading or writing either table.
- Everything that tracks a connection's progress is keyed by its identifier, so it survives
  renames: query ranges `{identifier}_{kind}` (`connection_range_name`), and the
  `DBCacheDynamic` templates starting with `{connection}` (cursors, bank sessions, per-account
  last query ts/id, binance per-pair ids). `LAST_QUERY_TS`/`LAST_BLOCK_ID` stay location keyed
  for chains. Deleting a connection deletes all of it (`DBConnections.delete_progress`). A
  rename rewrites only the `location_label` of the connection's events, which holds the name.
- Connectors come from explicit registries (`EXCHANGE_CONNECTOR_CLASSES`,
  `BANK_CONNECTOR_CLASSES`) instead of importing a module named after a location. An exchange
  connector's location is `exchange_location(connector)` (the same name). A bank manifest carries
  `connector_identifier` and `fixed_location`: Qonto fixes `qonto`, FinTS has none, so each FinTS
  connection names a location in the Banks subtree (validated on add). Bank events get
  `connection_identifier` and the provider `source_id` in extra data, and the group identifier
  hashes location, account and source id.
- API: `/exchanges` and `/banks` take the connection `identifier` on edit, delete, auth and sync;
  add takes `connector` (plus `location` for a bank connector without a fixed one) and returns
  the new identifier. `GET /exchanges/supported` replaces the exchange details of
  `/locations/all`, `/banks/supported` the bank details. `non_syncing_exchanges` is a list of
  identifiers. `/history/events/query/exchange` takes an identifier or a location;
  `/exchanges/binance/pairs/<identifier>`.
- v53->v54 (`_move_credentials_to_connections`, after `_finish_location_tree`): one connection
  per old credential row with a fresh uuid, mappings to settings, range names and caches rekeyed
  through frozen tail regexes (bank caches were `{connector}_{hex(name)}_...`), non-syncing
  entries mapped and unknown ones dropped, then the old non-premium rows and the mappings table
  are dropped and `integration_connections` is FK-checked.
- Frontend: exchanges and banks are addressed by identifier everywhere (store, API clients,
  refresh flows, pages). The bank form picks a connector and, for FinTS, a bank location from
  `GET /locations` limited to the Banks subtree (`bank-locations.ts`). Bank locations are the
  locations of the bank connections (`useBankConnectionsStore().bankLocations`); `isBank` and the
  exchange details of the flat location map are gone.
- Global DB: `location_asset_mappings` became `connector_asset_mappings(connector, exchange_symbol,
  local_id)` and `binance_pairs.location` became `connector`, in the unreleased v18->v19 upgrade
  (after the character conversion), the fresh schema and the packaged `global.db`. The names are
  already the connector identifiers. The setting `binance_pairs_queried_at_{connector}` kept its
  key. The API is `/assets/connectormappings` with `connector` and `connector_symbol`
  (`ConnectorAssetMapping*` entries and `ConnectorAssetMappingsFilterQuery`).
- The data repo contract is unchanged: the update type stays `location_asset_mappings` (so the
  updater method keeps the `update_location_asset_mappings` name the type selects), and its
  entries keep `location`/`location_symbol`, which the updater renames on the way in.
- The frontend cex mapping module still calls the connector its location; its API client
  translates. Renaming that UI vocabulary belongs with the connector/location split of section 8.

## Section 7 notes

- `location_aliases(alias COLLATE NOCASE PRIMARY KEY, location_identifier ON DELETE CASCADE)`
  is created by the unreleased v53->v54 upgrade and the fresh schema. `DBLocations` owns it:
  `get_aliases`, `set_alias` (the target must be assignable: not the total, not archived),
  `delete_alias`. Aliases do not count as usage; deleting a location deletes its aliases. No
  alias is created automatically, not even the old name on a rename, because an alias
  resolves before names and would shadow a later location of that name.
- `DBLocations.resolve(cursor, value)` returns a `LocationResolution` (`resolved`,
  `ambiguous` with the candidates, `unresolved`) in the design's order: identifier (built-ins
  case-insensitive, as `deserialize_location_identifier`), alias, then a unique
  case-insensitive name. Only assignable locations match, so `total` and archived locations
  never do.
- Generic CSV import (`rotki_events`, `rotki_trades`, the `SOURCES_WITH_LOCATION_COLUMN`) no
  longer falls back to External. `resolve_csv_locations` resolves every distinct `Location`
  value; user `location_mappings` win. `PUT/POST /import/preflight` reports the resolutions;
  `/import` takes `location_mappings` and answers 409 with the same `locations` list, importing
  nothing, while a value is unresolved or ambiguous. Aliases are saved separately through
  `/locations/aliases` (GET/PUT/DELETE). Third party formats (cointracking, blockpit,
  bitcoin_tax, coinledger) keep mapping their own venue names and falling back to External:
  their venue columns name platforms of those tools, not the user's locations.
- User data: custom locations and aliases live in the user DB, so DB backups and premium sync
  carry them with the rows that reference them. Decision (user, 2026-09-21): uploaded custom
  location images stay files in the user data directory and are NOT part of backups or sync; a
  restored or synced DB shows the icon or generic fallback until the image is uploaded again.
  This departs from the design's "backup and restore include uploaded location images".
  Snapshot CSV import already takes identifiers and rejects unknown locations; history event
  exports carry identifiers and paths (section 4).
- Until section 8 adds the preflight UI, a generic import with an unknown location value fails
  in the frontend with the 409 message instead of landing at External.

