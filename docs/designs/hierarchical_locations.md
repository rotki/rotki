# Hierarchical and custom locations

Status: Implemented for rotki 1.45 (user DB v54). Where the implementation differs, section 20 says
how; section 21 records the placement of the built-in locations.

## 1. Summary

Replace the `Location` enum and its one-character database encoding with one canonical,
database-backed location tree. Seed every location shipped by rotki into that tree and let users add
custom nodes to the same tree.

Locations describe **where** assets or events belong. Connectors describe **how** rotki obtains
data. They are separate identities:

- Qonto is a built-in bank location and `qonto` is also the identifier of its connector. The equal
  spelling is incidental; the values belong to separate namespaces.
- FinTS is only a connector. A FinTS connection points at an actual bank location such as ING or
  DKB. FinTS must never appear as an event, balance, snapshot, or report location.
- An exchange connector similarly points at its exchange location. Connector capabilities and
  credentials do not belong in location metadata.
- On-chain protocols are not locations. Their identity remains in the existing `counterparty`
  field. This avoids duplicating Aave, Uniswap, and every other protocol below each chain.

The migration is complete, not additive. The finished system has no legacy location enum, no second
location catalog, and no database character encoding. Temporary compatibility code may exist while
the implementation is in progress, but it is removed before completion.

## 2. Goals

1. Represent locations at arbitrary depth, for example:

   ```text
   Total
   └── Blockchains
       └── EVM Chains
           └── Ethereum Mainnet
   ```

2. Seed all current built-in locations and supported chains into the tree.
3. Let users create, rename, move, archive, and, where safe, delete custom locations.
4. Allow a custom node below any active node, including a built-in leaf. Any location can therefore
   be refined later without changing its type.
5. Make subtree filtering work consistently for history, balances, snapshots, accounting reports,
   and exports.
6. Separate connector implementation identity from location identity for exchanges and banks.
7. Preserve stable event identity and all existing user data through the migration.

## 3. Non-goals

- Users cannot edit, move, archive, or delete nodes shipped by rotki.
- Custom connector code and connector installation are separate projects.
- This work does not remove or replace the on-chain `counterparty` field.
- The tree is not a general tagging or classification system.

## 4. Core model

### 4.1 One type of node

Every node except the root can be assigned directly to data, and every node can have children.

Assigning a broad node simply means the source is not known more specifically. For example:

- a manual balance may be assigned directly to `Banks` when the institution is unknown;
- a transaction may be assigned to `EVM Chains` when the exact chain is unknown;
- a normal on-chain event is assigned to `Ethereum Mainnet`;
- a user may later create a child below an existing custom location.

The root is the only exception. It represents the total aggregate and is not accepted as the direct
location of an event, account, connection, or manual balance.

### 4.2 One canonical parent

The hierarchy is a rooted tree with arbitrary depth and any number of branches. Every node except
`total` has exactly one parent.

“Multiple containment parents” would mean allowing the same node to have more than one parent, for
example placing one `Aave v3` node below both Ethereum and Optimism. That produces a directed
acyclic graph rather than a tree and makes the node appear to occur on both chains. The design does
not support that. Cross-cutting classifications such as “all Aave v3 activity” belong to protocol
counterparty filtering, not location containment.

### 4.3 Built-in and custom nodes

- `is_builtin = 1` means rotki ships and owns the node. It is immutable through the user API.
- `is_builtin = 0` means the user created the node. It can be renamed, moved, archived, and, when it
  has no references or children, deleted.
- Users may add custom children below built-in or custom nodes.
- Built-in status never changes after creation.
- Archived custom nodes remain resolvable for historical data but do not appear in new-entry
  selectors by default.

This flag is the mutability boundary between protected nodes shipped by rotki and nodes created by
the user.

### 4.4 Stable identity and display name

- A location identifier is immutable.
- Existing built-ins keep their current API serialization wherever practical, for example `kraken`,
  `ethereum`, and `arbitrum one`.
- New structural built-ins use stable human-readable identifiers such as `evm chains`.
- Custom nodes use opaque identifiers such as `custom:550e8400-e29b-41d4-a716-446655440000`.
- The display name is editable only for custom nodes.
- Names are never used as foreign keys, cache keys, or event identifiers.
- Names must be unique among siblings using case-insensitive comparison. The same name may occur in
  different branches.

Separating identifier and name allows a user to rename “ING” without rewriting every event or
breaking saved filters.

### 4.5 Icons

Extend the visual metadata contract already returned by the locations endpoint and rendered by
`LocationIcon`:

- `icon`: an icon name from the rotki UI icon library, such as `lu-landmark`;
- `image`: a packaged image name or a custom uploaded image.

`image` takes precedence over `icon`, matching current frontend behavior. Every built-in catalog
entry declares either `icon` or `image`. A custom location may select an icon-library entry or
upload an image; when neither is supplied the API returns a generic location icon. Icons are not
inherited from ancestors.

Custom image handling extends the existing custom asset-icon machinery: use the same allowed file
types, upload validation, user-data image directory, replacement/deletion behavior, and cache
handling. Store custom location images by immutable location identifier, never by display name.
The API must not accept arbitrary filesystem paths or remote URLs. User-data backup and restore
include uploaded location images.

## 5. Initial tree

The version-controlled built-in catalog initially resembles:

```text
Total
├── Blockchains
│   ├── EVM Chains
│   │   ├── Ethereum Mainnet
│   │   ├── Optimism
│   │   ├── Arbitrum One
│   │   ├── Base
│   │   ├── Polygon PoS
│   │   └── ...
│   ├── Bitcoin
│   ├── Bitcoin Cash
│   ├── Solana
│   ├── Polkadot
│   ├── Kusama
│   └── ...
├── Exchanges
│   ├── Kraken
│   ├── Coinbase
│   ├── Binance
│   ├── inactive historical exchanges
│   └── user-created exchanges
├── Banks
│   ├── Qonto
│   └── user-created institutions used by FinTS or file import
└── Other
    ├── External
    ├── Equities
    ├── Real estate
    └── Commodities
```

`Total`, `Blockchains`, `EVM Chains`, `Exchanges`, `Banks`, and `Other` are immutable built-in nodes.
They are protected by the same `is_builtin` rule as built-in leaf nodes.

The exact placement of every existing enum member is part of the migration mapping and must be
reviewed explicitly. A catalog validation test guarantees that no enum member is forgotten.

## 6. Protocols are not locations

Modern on-chain events already have the correct model:

- location: the chain, such as Ethereum Mainnet;
- counterparty: the protocol, such as `aave-v3` or `uniswap-v3`.

Keep that separation. It avoids:

- duplicating every protocol and version below every supported chain;
- deciding whether a cross-chain protocol has multiple parents;
- changing an event's location whenever protocol classification improves;
- forcing chain-specific code to recover the chain from a protocol leaf;
- conflating source filtering with accounting counterparty rules.

The old enum contains protocol-labelled remnants that require explicit cleanup:

- `UNISWAP`
- `BALANCER`
- `SUSHISWAP`
- `GITCOIN`

Repository history shows that the automatic producers are already gone:

- v34-to-v35 dropped the AMM swaps table and Uniswap, Sushiswap, and Balancer trade query ranges;
- v37-to-v38 dropped the shared AMM events table and the remaining Uniswap and Sushiswap event
  ranges, while v41-to-v42 dropped the Balancer events table;
- Gitcoin-specific ledger actions were deleted by the v31-to-v32 upgrade;
- no source-specific producer currently refers to these constants outside the enum and location
  visual metadata.

Generic history-event, manual-balance, and snapshot schemas nevertheless accept an unrestricted
`LocationField`, so users can still have references to these values. The migration therefore scans
all real location columns for their encoded values before dropping the old location table:

- If none of the four values is referenced, do not create `Legacy locations` or any of its
  children. The four enum entries disappear completely.
- If at least one is referenced, create an inactive immutable `Legacy locations` node below
  `Other`, then create only the referenced children among Uniswap, Balancer, Sushiswap, and Gitcoin.
- Map every reference one-to-one to its corresponding legacy child. Do not infer a chain, add a
  counterparty, merge snapshot rows, or otherwise reinterpret user data.

The compatibility nodes are hidden from all new-entry selectors but remain resolvable in history,
reports, filters, and exports. A later upgrade may remove a child and then the parent once they have
no references. Fresh databases never contain this branch.

## 7. Database schema

### 7.1 Locations

Replace `location(location CHAR(1), seq INTEGER)` with:

```sql
CREATE TABLE locations (
    identifier TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    parent_identifier TEXT REFERENCES locations(identifier),
    is_builtin INTEGER NOT NULL CHECK(is_builtin IN (0, 1)),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    icon TEXT,
    image TEXT,
    CHECK(identifier != ''),
    CHECK(name != ''),
    CHECK(parent_identifier IS NULL OR parent_identifier != identifier)
);

CREATE INDEX idx_locations_parent ON locations(parent_identifier);

CREATE UNIQUE INDEX unique_locations_sibling_name
ON locations(parent_identifier, name COLLATE NOCASE);
```

Field meanings:

- `identifier`: immutable database and API identity;
- `name`: user-facing name, editable for custom nodes;
- `parent_identifier`: the tree edge; `NULL` only for Total;
- `is_builtin`: ownership and mutability boundary;
- `is_active`: supports archiving referenced custom nodes;
- `icon` and `image`: the existing location visual metadata contract.

Application-level validation enforces:

- exactly one node has no parent and its identifier is `total`;
- all other nodes have an existing parent;
- no cycles;
- sibling-name uniqueness, including the root special case;
- only custom nodes can be mutated;
- a node cannot be moved below itself or one of its descendants;
- active nodes cannot be placed below archived nodes;
- the root cannot be assigned directly to user data.

### 7.2 Aliases

Aliases are not needed to separate identifier from name; the `identifier` and `name` columns already
do that. Aliases are an optional import convenience for values such as `CoinbasePro`, `Coinbase
Pro`, or an old name of a renamed custom location.

If alias persistence is included in the first implementation, use the minimal schema:

```sql
CREATE TABLE location_aliases (
    alias TEXT NOT NULL COLLATE NOCASE PRIMARY KEY,
    location_identifier TEXT NOT NULL REFERENCES locations(identifier) ON DELETE CASCADE
);
```

An alias resolves to exactly one location. No `source` column is needed: provenance does not affect
resolution or user behavior. Alias support may be deferred until CSV import preflight without
changing the core location schema.

### 7.3 Location references

Every column that means an actual location becomes a `TEXT` FK to `locations(identifier)`. This
includes at least:

- `history_events.location`
- `history_events_backup.location`
- `timed_location_data.location`
- `manually_tracked_balances.location`
- `margin_positions.location`
- `skipped_external_events.location`
- `bitcoin_transactions.location`
- `event_metrics.location`
- location-bearing data issue fields after checking their current serialization

The implementation inventory searches the entire repository for `Location`, `LocationField`,
`serialize_for_db`, `deserialize_from_db`, and raw location SQL. Every occurrence is classified as
one of:

- real location;
- connector identity;
- connection identity;
- protocol counterparty;
- unrelated use of the English word “location.”

Migration tests fail if a real location reference remains character-encoded.

### 7.4 Total snapshots

The old `TOTAL` location becomes the root `total` node. Existing total rows stay in
`timed_location_data`; no separate snapshot table is required.

The root row is a stored aggregate, while descendant rows are breakdown values. Code reading a root
snapshot uses its stored value and does not add descendants to it. For any other selected node,
subtree aggregation sums that node's direct value and its descendants.

Every non-root snapshot row is a disjoint direct bucket, never a cached subtotal of its children.
Historical `BLOCKCHAIN` and `BANKS` rows remain valid broad buckets at timestamps where no finer
breakdown was stored. New snapshot code writes the most specific available locations and must not
also write a parent subtotal for the same assets. `total` is the deliberate exception: it remains
the independently stored overall aggregate used by current net-worth history.

This preserves the current snapshot representation and avoids a large unrelated snapshot migration.
The API still rejects `total` as the direct location of events, connections, and manual balances.

### 7.5 Built-in catalog

Add a version-controlled catalog such as `rotkehlchen/data/locations.json`. It seeds fresh user
databases and supplies built-in rows to upgrades:

```json
{
  "identifier": "ethereum",
  "name": "Ethereum Mainnet",
  "parent_identifier": "evm chains",
  "image": "ethereum.svg"
}
```

All catalog entries are built-in by definition; the file does not need to repeat `is_builtin`.
Protocol counterparties and connector manifests do not belong in this file.

Catalog tests prove:

- identifiers are unique;
- names are unique among siblings;
- exactly one root exists;
- every parent exists;
- the tree is acyclic;
- every old enum value has an explicit migration rule;
- every supported blockchain has a node;
- every built-in has either a valid icon-library name or image;
- every packaged icon reference exists;
- inactive historical locations remain resolvable.

Adding a built-in location after this change means adding a catalog entry and a user DB upgrade that
inserts it. It does not mean adding an enum member or assigning another character.

## 8. Backend representation

### 8.1 Identifier type

Remove the `Location` enum and its `DBCharEnumMixIn`. Introduce:

```python
LocationIdentifier = NewType('LocationIdentifier', str)
```

Domain objects and database rows store the same stable identifier. Parsing validates basic syntax;
database-facing services validate existence and active status.

Code that intrinsically targets a built-in location may use named `Final` constants such as
`LOCATION_ETHEREUM`. There is no exhaustive enum and no integer/character serialization. Supported
chains come from chain registries, and supported connectors come from connector registries.

### 8.2 Location data access

- `DBLocations` owns location SQL, ancestry/descendant queries, and mutation checks;
- a small location API service owns request-level validation and response serialization;
- callers do not duplicate recursive SQL or mutation rules.

The tree rules need one data-access implementation so a CSV importer, history filter, and bank
setup cannot disagree about what an active descendant of Banks means.

The tree is small and changes rarely. `DBLocations` may cache ancestor/descendant sets if measurement
shows value; caching is not required initially.

### 8.3 Validation fields

Replace the generic enum field with fields that state their constraints:

- any existing active location except Total;
- an existing location below a required built-in ancestor;
- a supported blockchain;
- a connector identifier.

Examples:

- a generic history event or manual balance accepts any active non-root location;
- a Bitcoin event accepts only a supported Bitcoin-family chain;
- FinTS setup accepts a location in the Banks subtree;
- exchange setup validates an exchange connector, not an arbitrary Exchanges descendant.

## 9. Hierarchical filtering and aggregation

Filtering APIs accept an explicit scope:

```json
{
  "location": "blockchains",
  "location_scope": "subtree"
}
```

Scopes are:

- `exact`: only the selected node;
- `subtree`: the selected node and every descendant.

Default to `exact` for API backward compatibility. The tree UI defaults structural selections to
`subtree` and can expose an exact/subtree choice because any non-root node may contain direct data
and children.

`DBLocations` resolves descendants once, then the data query uses an indexed predicate:

```sql
WHERE history_events.location IN (?, ?, ...)
```

Do not recursively join the tree against every history row. Exclusion filters expand subtrees in
the same way.

Associated-location responses include directly used locations and the ancestors needed to display
their paths. An ancestor is not reported as directly used merely because a descendant is used.

## 10. Custom location API

Expose authenticated endpoints:

- `GET /locations`: visible nodes and hierarchy metadata;
- `POST /locations`: create a custom node;
- `PATCH /locations/{identifier}`: rename, move, select an icon-library icon, or archive a custom
  node;
- `POST /locations/{identifier}/image`: upload or replace a custom location image;
- `DELETE /locations/{identifier}/image`: remove its uploaded image and restore its selected or
  generic icon;
- `DELETE /locations/{identifier}`: delete only an unused childless custom node;
- `GET /locations/{identifier}/usage`: references preventing deletion.

Creation payload:

```json
{
  "name": "ING",
  "parent_identifier": "banks"
}
```

The backend generates the identifier. Clients never derive it from the name.

Moving a node changes historical aggregation paths. The API returns its old and new ancestor paths
so the UI can show a precise warning before committing the move.

## 11. Connector and connection separation

### 11.1 Connector identity

Bank and exchange manifests use `connector_identifier`, not `location`. Managers instantiate
connectors from explicit registries keyed by connector identifier; they do not import modules by
formatting a location name.

Connection persistence stores both concepts:

```sql
CREATE TABLE integration_connections (
    identifier TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    connector_identifier TEXT NOT NULL,
    location_identifier TEXT NOT NULL REFERENCES locations(identifier),
    api_key TEXT,
    api_secret TEXT,
    passphrase TEXT,
    UNIQUE(connector_identifier, name)
);
```

`integration_type` is intentionally absent. The connector registry already knows whether a
connector is a bank or exchange; storing it again would create another value that can disagree.

Connection identifiers remain stable through display-name and location-name changes. Sync, edit,
delete, authentication, status, sessions, and cursors use the connection identifier.

Connector-specific settings move from `user_credentials_mappings` to a mapping keyed by connection
identifier. Audit and migrate all other connector-bearing state:

- exchange and bank manager registries;
- session and cursor cache keys;
- used query ranges;
- non-syncing exchange settings;
- exchange-specific symbol and unsupported-asset mappings in the global database;
- API payloads currently identifying connections by `(location, name)`.

Global `location_asset_mappings` should become connector asset mappings. Those rows describe a
provider's symbol namespace, not where an event occurred.

### 11.2 Qonto

- Qonto is an immutable built-in node below Banks.
- The `qonto` connector fixes or defaults the connection location to Qonto.
- Qonto events, balances, and snapshots use the Qonto location.

### 11.3 FinTS

- Remove FinTS from the location enum, catalog, event data, and UI location metadata.
- Register `fints` only as a connector.
- FinTS setup requires an existing active descendant of Banks or offers inline creation.
- Bank code and endpoint are connector credentials, not location identity.
- Multiple connections may point at the same institution location.
- Events use the institution location; `location_label` remains the account/connection label.
- Balances aggregate by institution location, not connector.

Persist the connection identifier and normalized source ID in bank transaction extra data. New bank
event group identifiers use stable institution, account, and source identities, never a mutable
connection name.

## 12. Import and export

Generic CSV import stops silently converting an unknown source to External.

Resolution order:

1. exact location identifier;
2. exact saved alias, if aliases are implemented;
3. unique case-insensitive display-name match;
4. unresolved source returned in import preflight.

Preflight lets the user map an unresolved value to an existing location or create a custom one.
Ambiguous names never resolve silently.

Exports include stable identifiers and display paths where the format permits. User-data export
includes custom nodes before rows that reference them. When custom icons and aliases exist, it also
includes those resources.

## 13. Migration

### 13.1 Version boundary

This change ships as part of the user DB v54 upgrade in rotki 1.45. Replace the unreleased v53-to-v54
location changes with the hierarchical schema and catalog seeding. The final v54 schema, upgrade,
and catalog never insert FinTS as a location; they register it only as a connector. No released user
database can contain the interim FinTS location, so it requires no compatibility mapping.

Qonto is seeded below Banks as both a valid location and the fixed location of the Qonto connector.

### 13.2 Conditional legacy locations

The rows in the old `location` table do not count as usage because that table always contains every
enum member. Before rebuilding location-bearing tables, query their actual reference columns for
the four protocol-labelled characters. Include non-FK location fields discovered by the inventory
in section 7.3 rather than assuming that foreign-key introspection finds every reference.

| Old value | Character | Conditional identifier |
|-----------|-----------|------------------------|
| Uniswap | `Q` | `legacy:uniswap` |
| Balancer | `X` | `legacy:balancer` |
| Gitcoin | `^` | `legacy:gitcoin` |
| Sushiswap | `_` | `legacy:sushiswap` |

If the query finds no matches, omit the entire legacy branch. Otherwise insert the inactive
built-in parent and only the children present in the result, then map those characters one-to-one.
All normal enum characters use a reviewed static old-character-to-identifier mapping; never derive
that mapping from enum order at runtime.

### 13.3 Upgrade algorithm

In one backed-up user DB upgrade:

1. Create the new `locations` table and seed the built-in tree.
2. Create the connector/connection tables and migrate credentials with separate connector and
   location identifiers.
3. Scan actual location references and insert the conditional legacy branch when needed.
4. Rebuild every true location-bearing table with `TEXT` foreign keys while transforming each old
   character through the reviewed mapping.
5. Migrate connector caches, settings, query ranges, and global connector asset mappings.
6. Drop old tables only after row-count and reference checks pass.
7. Run `PRAGMA foreign_key_check`, tree validation, and semantic assertions.
8. Commit and bump the DB version.

Upgrade progress steps separate table rebuilding from credential migration so progress remains
meaningful on large databases.

### 13.4 Migration assertions

- Every old enum value is handled exactly once.
- The legacy branch is absent when none of its children are referenced.
- When legacy values are referenced, only those children exist and their reference counts are
  unchanged.
- No event, balance, credential, or snapshot row is unintentionally dropped.
- Event identifiers and group identifiers remain unchanged.
- Asset, amount, timestamp, type, subtype, notes, and counterparty remain unchanged.
- Every migrated location resolves to a built-in or custom node.
- Credential counts and credential bytes remain unchanged.
- Snapshot totals before and after migration are equal.
- Re-running a connector does not duplicate migrated events.

## 14. Frontend

Replace the flat location-details record with a normalized store:

```ts
interface LocationNode {
  readonly identifier: string;
  readonly name: string;
  readonly parentIdentifier: string | null;
  readonly isBuiltin: boolean;
  readonly isActive: boolean;
  readonly icon?: string;
  readonly image?: string;
}
```

The store computes children, ancestors, and paths. It extends the current image resolver so
packaged location images and uploaded custom images both feed the existing `LocationIcon`
component. Connector manifests remain in exchange/bank stores rather than location entries.

Required UI work:

- reusable tree autocomplete with breadcrumb search results;
- exact/subtree-aware history and report filters;
- custom location create, rename, move, archive, and delete controls;
- the existing icon-library picker plus custom image upload, replacement, and removal;
- a usage dialog explaining why a node cannot be deleted;
- generic event and manual balance forms using all active non-root nodes;
- import preflight mapping and creation flow;
- bank setup that chooses connector and institution separately;
- bank balances grouped by institution;
- connection rows displaying institution and connector independently;
- archived historical nodes visible on old records but absent from creation selectors.

A custom node below Exchanges is a valid source for imports and manual data. It does not become a
supported API connector merely because of its parent.

## 15. Implementation plan

This may be implemented in one large PR. The following are dependency-ordered workstreams and
suggested commit boundaries, not required separate PRs.

### A. Inventory and fixtures

- Classify every current location use as location, connector, connection, or counterparty.
- Create the explicit old-to-new mapping.
- Add upgrade fixtures covering every enum member and every referencing table.
- Add fixtures with no legacy references, each legacy value individually, and all four together.
- Add a large synthetic migration fixture and measurement script.

### B. Catalog and schema migration

- Add and validate the built-in catalog.
- Add `LocationIdentifier` and built-in constants.
- Replace the character table with `locations`.
- Rebuild true location-bearing tables with text foreign keys.
- Preserve Total snapshot rows at the root.
- Implement `DBLocations` and custom location CRUD.
- Extend the existing icon manager and upload validation for custom location images.

### C. Backend consumers and filtering

- Replace enum serialization/deserialization throughout backend domain models.
- Implement exact and subtree filters.
- Update balances, snapshots, accounting, exports, and generic imports.
- Create the inactive legacy branch only for referenced protocol-labelled enum values.
- Keep on-chain events at chain locations and retain counterparties unchanged.

### D. Connector separation

- Introduce connector registries and stable integration connections.
- Migrate exchange and bank credentials plus connector-specific state.
- Refactor Qonto to connector plus fixed Qonto location.
- Refactor FinTS to connector plus selected/custom bank location.
- Rename global connector asset mapping concepts.

### E. Frontend

- Replace the flat store and selectors with the location tree.
- Add location management and subtree filters.
- Reuse the current location icon/image rendering and add custom image management.
- Add import preflight.
- Separate connector selection from location selection in connection flows.
- Add component and composable tests.

### F. Cleanup and verification

- Remove the old enum, character serializer, compatibility code, and obsolete tests.
- Run the complete migration, backend, frontend, and end-to-end suites.
- Record migration and filter performance comparisons.
- Update API documentation and user-facing migration notes.

Completion requires every workstream even if they share one PR.

## 16. Test plan

### 16.1 Tree and CRUD

- built-in catalog validity and full migration-map coverage;
- arbitrary depth;
- cycle and self-parent rejection;
- sibling-name collision rejection;
- all built-in mutation rejection;
- custom children below built-in and custom locations;
- archive versus hard-delete behavior;
- moving a node changes ancestry correctly;
- user-data export/import round trip.

### 16.2 Filtering and aggregation

- exact filtering at broad and specific nodes;
- subtree filtering at Total, Blockchains, EVM Chains, Ethereum Mainnet, Exchanges, and Banks;
- exclusions expand like inclusions;
- direct parent values and descendant values are handled without double counting;
- stored Total snapshot rows are returned directly;
- associated locations include required ancestor paths;
- archived locations remain queryable;
- accounting and CSV exports show correct paths.

### 16.3 Migration

- fresh database schema;
- upgrade from the oldest supported DB;
- every legacy enum value;
- no legacy references, proving that the legacy branch is omitted;
- each protocol-labelled legacy value in every table where it can occur;
- only referenced legacy children are created and all values remain unchanged;
- interrupted upgrade rollback;
- foreign key and tree validation;
- before/after snapshot totals;
- before/after event and credential counts;
- no connector resync duplicates.

### 16.4 Connectors

- Qonto connector writes Qonto location data;
- two FinTS institutions produce distinct locations, balances, and events;
- two connections at the same bank aggregate below that institution;
- filtering Banks returns Qonto and all FinTS-backed institutions;
- no event, balance, snapshot, or report returns FinTS as a location;
- connection rename leaves sessions, cursors, and event identity intact;
- a custom exchange location does not appear as a supported exchange connector.

### 16.5 Frontend

- tree rendering and breadcrumb search;
- exact/subtree selection;
- custom CRUD and validation errors;
- immutable controls for every built-in node;
- icon-library, packaged-image, custom-image, and generic fallback rendering;
- custom location image upload, replacement, removal, backup, and restore;
- archived location display;
- unknown import-location mapping;
- bank connector/location separation.

## 17. Performance validation

The history location index is important on large databases. Before merging:

1. Generate databases with at least 400,000 and 2,000,000 history events.
2. Measure exact location filters before and after migration.
3. Measure subtree filters at small and large branches.
4. Compare database and index sizes for character and text identifiers.
5. Run `EXPLAIN QUERY PLAN` and confirm the history location index is used after subtree expansion.
6. Measure migration wall time and peak temporary disk usage.

The intended query resolves the small descendant set once and uses an indexed `IN` predicate. If
text identifiers cause a material regression, use integer surrogate foreign keys behind
`DBLocations` before release. Do not retain the character encoding as the optimization.

Commit the comparison script and results with the implementation. Judge the result on a large user
scenario, not an empty development database.

## 18. Acceptance scenario

The feature is complete when:

1. The built-in path is Total → Blockchains → EVM Chains → Ethereum Mainnet.
2. A user creates ING and DKB below Banks.
3. They configure one FinTS connection for each and a Qonto connection.
4. Sync produces ING, DKB, and Qonto balances and history; no FinTS location exists.
5. Filtering ING exactly returns only ING.
6. Filtering the Banks subtree returns all three institutions.
7. The user creates `My old exchange` below Exchanges and imports a generic CSV into it.
8. The import appears under that source instead of External.
9. An Ethereum Aave v3 event remains located at Ethereum Mainnet and has counterparty `aave-v3`.
10. Renaming a custom location or connection does not alter event identity.
11. Archiving a used custom location preserves all history and reports.
12. Total snapshot history remains unchanged through migration.
13. Exporting and importing user data recreates custom nodes before dependent rows.
14. A custom location can use an icon-library icon or an uploaded image.

## 19. Decisions fixed by this design

- One database-backed location tree completely replaces the enum schema.
- Total is the immutable root and remains the stored snapshot aggregate.
- Blockchains contains EVM Chains, which contains Ethereum Mainnet and the other EVM chains.
- Every non-root node can be assigned directly and can gain children.
- All nodes shipped by rotki are immutable; all user-created nodes are editable subject to usage
  constraints.
- The tree has arbitrary depth and one canonical parent per node.
- Protocols are counterparties, not locations.
- Legacy protocol-labelled nodes exist only when referenced and remain inactive compatibility
  locations without reinterpretation.
- Connector identity is a separate namespace and persistence concept.
- FinTS is a connector and is never a location.
- Qonto is both a location and a connector identifier in separate namespaces.
- Stable identifiers are immutable; display names are editable for custom nodes.
- Alias support is optional import functionality and needs no provenance field.
- Location visuals extend the existing icon/image contract and support custom uploads.
- The work may ship in one large PR, but all dependency-ordered workstreams remain required.

## 20. Deviations from this design

- **Subtree query.** Filters do not resolve the descendants in Python and bind a literal
  `IN (?, ?, ...)` list. `DBLocationFilter` emits an uncorrelated `location IN (<recursive CTE>)`
  subquery (`db.locations.subtree_query`), which SQLite evaluates once before probing the location
  index. Measurements at 400,000 and 2,000,000 history events showed it as fast as a literal list,
  with the same plan. The subtree of `total` adds no predicate.
- **Scope in the UI.** History location filters always use the subtree scope. There is no
  exact/subtree choice; exact scope is available through the API only. The frontend has no report
  (PnL) location filters, so there was nothing there to make subtree aware.
- **Icons of custom locations.** A custom location picks from a fixed list of icons
  (`LOCATION_ICONS` in the frontend), not from the whole icon library: the app only registers
  icon names that appear in its source. An unknown icon falls back to `lu-map-pin`.
- **Images and backups.** Uploaded custom location images are files in the user data directory
  (`images/locations/`). They are not part of DB backups or premium sync; a restored or synced DB
  shows the icon or the generic fallback until the image is uploaded again. Custom locations and
  aliases live in the user DB and travel with it.
- **Third-party CSV formats.** Only rotki's own formats (`rotki_events`, `rotki_trades` and the
  sources with a location column) go through import preflight. The cointracking, blockpit,
  bitcoin_tax and coinledger importers keep mapping their own venue names and fall back to
  External, because those names are platforms of those tools rather than the user's locations.
- **Aliases.** No alias is created automatically, not even the old name on a rename: an alias
  resolves before names and would shadow a later location of that name.
- **Performance validation.** The comparison script and its results were not committed; they are
  in the PR description. Text identifiers stayed within about 3% of the character encoding, so
  there are no integer surrogate keys. At 2,000,000 events the upgrade takes about 190 s, with peak
  disk use of about 3.3 times the database (database, backup copy and WAL) and peak memory of about
  1.2 times the database size.

## 21. Placement of the built-in locations

The catalog is `rotkehlchen/data/locations.json`. Identifiers of locations that existed before
equal their old API serialization, so string keys built from them (query ranges, key-value cache,
settings) stay valid.

- `total` ("Total") is the root. `blockchain` is displayed as "Blockchains" and `banks` as "Banks":
  the old broad snapshot buckets and the new structural nodes are the same nodes.
- Structural built-ins: `evm chains` below `blockchain`, and `exchanges` and `other` below `total`.
- EVM Chains: ethereum ("Ethereum Mainnet"), optimism, arbitrum one, base, polygon pos, gnosis,
  scroll, binance sc, hyperliquid (HyperEVM), monad, sonic, robinhood, ink and avalanche. rotki's
  Avalanche support is the C-Chain, an EVM chain, even though the code does not count it among
  `EVM_LOCATIONS`.
- Directly below Blockchains: bitcoin, bitcoin cash, solana, polkadot, kusama, zksync lite
  (EVM-like, not EVM) and loopring (a shut-down zk-rollup kept for historical data).
- Exchanges: every exchange location, including dead ones (ftx, ftxus, bittrex, coinbasepro) and
  import-only ones (blockfi, nexo, shapeshift, uphold, bisq, cryptocom, ...). All of them are
  active, because users still enter historical data for dead exchanges by hand.
- Banks: qonto. Other: external, equities, realestate ("Real estate") and commodities.
- Legacy: `legacy locations` (inactive, below `other`) with `legacy:uniswap`, `legacy:balancer`,
  `legacy:gitcoin` and `legacy:sushiswap`, created only when data references them. They are
  defined in `rotkehlchen/locations/legacy_chars.py`, never in the catalog.
- Icons of the structural nodes: total `lu-wallet`, blockchain `lu-link`, evm chains `lu-layers`,
  exchanges `lu-arrow-left-right`, other `lu-ellipsis`, legacy `lu-archive`.

The reviewed old-character mapping is `V53_LOCATION_CHAR_TO_IDENTIFIER` in
`rotkehlchen/locations/legacy_chars.py`, the frozen codec that the historical upgrades
(v36..v53), the v54 upgrade and the global v18->v19 conversion use. It covers the 57 characters a
v53 database can hold besides the four legacy ones; Sonic, Robinhood, Ink, Qonto and FinTS were
only introduced by the unreleased v53->v54 upgrade, so no released database contains their
characters. `rotkehlchen/tests/unit/test_location_catalog.py` checks that every old value is
handled exactly once.
