import json
import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from eth_utils import to_checksum_address

from rotkehlchen.constants import ZERO
from rotkehlchen.constants.misc import AIRDROPSDIR_NAME, APPDIR_NAME
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.oracles.structures import CurrentPriceOracle
from rotkehlchen.types import Location
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _merge_onto_canonical_identifier(
        write_cursor: DBCursor,
        child_columns: list[tuple[str, str]],
        merges: list[tuple[str, str]],
) -> None:
    """Collapse each non canonical evm identifier onto the canonical one already in assets.

    A rename is not possible for these since the row they would become exists, so every row
    referencing the non canonical identifier is moved instead, and whatever collides with a
    row the canonical identifier already has is dropped.

    timed_balances is summed rather than moved: a row of each identifier can share a
    (timestamp, category), and dropping one of those would silently take that amount out of
    the netvalue graph. The summation is done here instead of in sqlite because amount and
    usd_value are TEXT columns holding arbitrary precision values that SUM() would coerce to
    floats. Same reasoning as DBHandler.replace_asset_identifier.
    """
    log.debug('Merging %s non canonical evm asset identifiers onto their canonical row', len(merges))  # noqa: E501
    merged: dict[tuple[str, int, str], list[FVal]] = defaultdict(lambda: [ZERO, ZERO])
    for new_identifier, identifier in merges:
        for category, timestamp, amount, usd_value in write_cursor.execute(
                'SELECT category, timestamp, amount, usd_value FROM timed_balances '
                'WHERE currency IN (?, ?)',
                (identifier, new_identifier),
        ).fetchall():
            totals = merged[category, timestamp, new_identifier]
            totals[0] += FVal(amount)
            totals[1] += FVal(usd_value)

    write_cursor.executemany('DELETE FROM timed_balances WHERE currency IN (?, ?)', merges)
    write_cursor.executemany(
        'INSERT INTO timed_balances(category, timestamp, currency, amount, usd_value) '
        'VALUES(?, ?, ?, ?, ?)',
        [
            (category, timestamp, currency, str(amount), str(usd_value))
            for (category, timestamp, currency), (amount, usd_value) in merged.items()
        ],
    )
    stale = [(identifier,) for _, identifier in merges]
    for table, column in child_columns:
        if table == 'timed_balances':
            continue  # summed above, since moving it can only drop one of the two amounts

        write_cursor.executemany(
            f'UPDATE OR IGNORE {table} SET {column}=? WHERE {column}=?',
            merges,
        )
        write_cursor.executemany(  # whatever stayed behind collides with a row the canonical
            f'DELETE FROM {table} WHERE {column}=?',  # identifier already has
            stale,
        )

    write_cursor.executemany(
        "UPDATE OR IGNORE multisettings SET value=? WHERE value=? AND name='ignored_asset'",
        merges,
    )
    write_cursor.executemany(
        "DELETE FROM multisettings WHERE value=? AND name='ignored_asset'",
        stale,
    )
    write_cursor.executemany(  # last, nothing references it anymore
        'DELETE FROM assets WHERE identifier=?',
        stale,
    )


@enter_exit_debug_log(name='UserDB v52->v53 upgrade')
def upgrade_v52_to_v53(db: DBHandler, progress_handler: DBUpgradeProgressHandler) -> None:
    """Upgrades the DB from v52 to v53. This happened in 1.44."""

    @progress_step(description='Create event metrics table and indexes.')
    def _create_event_metrics_table(write_cursor: DBCursor) -> None:
        # Hardcoded schema/indexes to prevent future schema changes from affecting this upgrade.
        write_cursor.execute("""
CREATE TABLE IF NOT EXISTS event_metrics (
    id INTEGER NOT NULL PRIMARY KEY,
    event_identifier INTEGER NOT NULL REFERENCES history_events(identifier) ON DELETE CASCADE,
    location CHAR(1) NOT NULL,
    location_label TEXT,
    protocol TEXT,
    metric_key TEXT NOT NULL,
    metric_value TEXT NOT NULL,
    asset TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    sequence_index INTEGER NOT NULL,
    sort_key INTEGER NOT NULL,
    UNIQUE(event_identifier, location_label, protocol, metric_key, asset)
);
""")
        write_cursor.executescript("""
CREATE INDEX IF NOT EXISTS idx_event_metrics_event ON event_metrics(event_identifier);
CREATE INDEX IF NOT EXISTS idx_event_metrics_location_label ON event_metrics(location_label);
CREATE INDEX IF NOT EXISTS idx_event_metrics_protocol ON event_metrics(protocol);
CREATE INDEX IF NOT EXISTS idx_event_metrics_metric_key ON event_metrics(metric_key);
CREATE INDEX IF NOT EXISTS idx_event_metrics_metric_key_timestamp ON event_metrics(metric_key, timestamp);
CREATE INDEX IF NOT EXISTS idx_event_metrics_metric_key_asset_sort_key ON event_metrics(metric_key, asset, sort_key);
CREATE INDEX IF NOT EXISTS idx_event_metrics_asset ON event_metrics(asset);
CREATE INDEX IF NOT EXISTS idx_event_metrics_balances_latest ON event_metrics(metric_key, location, location_label, protocol, asset, timestamp, sort_key, metric_value);
""")  # noqa: E501

    @progress_step(description='Create data issues table and indexes.')
    def _create_data_issues_table(write_cursor: DBCursor) -> None:
        # Hardcoded schema/indexes to prevent future schema changes from affecting this upgrade.
        write_cursor.execute("""
CREATE TABLE IF NOT EXISTS data_issues (
    id INTEGER NOT NULL PRIMARY KEY,
    kind TEXT NOT NULL,
    location TEXT NOT NULL,
    location_label TEXT NOT NULL DEFAULT '',
    protocol TEXT NOT NULL DEFAULT '',
    asset TEXT NOT NULL DEFAULT '',
    event_identifier INTEGER,
    ts_start INTEGER NOT NULL,
    ts_end INTEGER NOT NULL,
    severity TEXT NOT NULL,
    state TEXT NOT NULL,
    auto_remediation_attempts_json TEXT NOT NULL DEFAULT '[]',
    payload_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    resolved_at INTEGER
);
""")
        write_cursor.executescript("""
CREATE INDEX IF NOT EXISTS idx_data_issues_state ON data_issues(state);
CREATE INDEX IF NOT EXISTS idx_data_issues_kind_state ON data_issues(kind, state);
CREATE INDEX IF NOT EXISTS idx_data_issues_location_label_asset ON data_issues(location, location_label, asset);
-- `event_identifier` is nullable because some issues are scoped to an event while others are
-- scoped to a bucket. SQLite treats NULL values as distinct in normal UNIQUE constraints, so
-- partial unique indexes are required to enforce one natural key row for both scopes.
CREATE UNIQUE INDEX IF NOT EXISTS unique_data_issues_event_scope ON data_issues(kind, location, location_label, protocol, asset, event_identifier) WHERE event_identifier IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS unique_data_issues_bucket_scope ON data_issues(kind, location, location_label, protocol, asset) WHERE event_identifier IS NULL;
""")  # noqa: E501

    @progress_step(description='Add Gate location.')
    def _add_gate_location(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            "INSERT OR IGNORE INTO location(location, seq) VALUES ('{', 59);",
        )

    @progress_step(description='Add Bit2me location.')
    def _add_bit2me_location(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            "INSERT OR IGNORE INTO location(location, seq) VALUES ('|', 60);",
        )

    @progress_step(description='Add CoinEx location.')
    def _add_coinex_location(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            "INSERT OR IGNORE INTO location(location, seq) VALUES ('}', 61);",
        )

    @progress_step(description='Add Sonic location.')
    def _add_sonic_location(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            "INSERT OR IGNORE INTO location(location, seq) VALUES ('~', 62);",
        )

    @progress_step(description='Normalize exchange history event location labels.')
    def _normalize_exchange_event_location_labels(write_cursor: DBCursor) -> None:
        """Normalize exchange labels used as accounting bucket keys.

        If a user has exactly one API key for an exchange and the existing non-NULL event labels
        for that exchange don't indicate mixed keys, NULL labels on that exchange's events can be
        updated to that key name. Existing non-NULL labels are left untouched since they may come
        from CSV imports or removed/dead exchange credentials. Locations with multiple keys are
        intentionally left untouched since assigning old NULL events to a specific key would be
        ambiguous.
        """
        exchange_locations = tuple(location.serialize_for_db() for location in (
            Location.BINANCE,
            Location.BINANCEUS,
            Location.BISQ,
            Location.BITCOINDE,
            Location.BITFINEX,
            Location.BITMEX,
            Location.BITPANDA,
            Location.BITSTAMP,
            Location.BITTREX,
            Location.BLOCKFI,
            Location.BYBIT,
            Location.COINBASE,
            Location.COINBASEPRIME,
            Location.COINBASEPRO,
            Location.CRYPTOCOM,
            Location.FTX,
            Location.FTXUS,
            Location.GEMINI,
            # GATE is omitted because it is first added in this upgrade/release.
            Location.HTX,
            Location.ICONOMI,
            Location.INDEPENDENTRESERVE,
            Location.KRAKEN,
            Location.KUCOIN,
            Location.NEXO,
            Location.OKX,
            Location.POLONIEX,
            Location.SHAPESHIFT,
            Location.UPHOLD,
            Location.WOO,
        ))
        placeholders = ','.join('?' * len(exchange_locations))
        write_cursor.execute(
            'CREATE TEMP TABLE IF NOT EXISTS _exchange_label_fill AS SELECT '
            'user_credentials.location AS location, user_credentials.name AS name FROM '
            'user_credentials WHERE '
            f'user_credentials.location IN ({placeholders}) GROUP BY user_credentials.location '
            'HAVING COUNT(*)=1 AND (SELECT COUNT(DISTINCT history_events.location_label) '
            'FROM history_events WHERE history_events.location=user_credentials.location AND '
            'history_events.location_label IS NOT NULL)<=1',
            exchange_locations,
        )
        write_cursor.execute(
            'UPDATE history_events SET location_label=(SELECT name FROM _exchange_label_fill '
            'WHERE location=history_events.location) WHERE location IN (SELECT location FROM '
            '_exchange_label_fill) AND location_label IS NULL',
        )
        write_cursor.execute('DROP TABLE IF EXISTS _exchange_label_fill')

    @progress_step(description='Persist indexer source for internal transactions.')
    def _add_internal_tx_source(write_cursor: DBCursor) -> None:
        # Track which indexer produced each internal tx row. DEFAULT 0 backfills all
        # existing rows as legacy since source tracking only starts from this upgrade.
        if 'source' not in {
            row[1] for row in write_cursor.execute(
                'PRAGMA table_info(evm_internal_transactions)',
            )
        }:
            write_cursor.execute(
                'ALTER TABLE evm_internal_transactions '
                'ADD COLUMN source INTEGER NOT NULL DEFAULT 0',
            )

    @progress_step(description='Add naming system source to ens mappings.')
    def _add_source_to_ens_mappings(write_cursor: DBCursor) -> None:
        """Store one name per naming system (ENS, GNS, ...) for an address in the
        ens_mappings cache, so that name priority can be applied at read time.
        Existing rows are backfilled as ENS names since that was the only system."""
        if 'source' in {
            row[1] for row in write_cursor.execute('PRAGMA table_info(ens_mappings)')
        }:
            return

        write_cursor.executescript("""
ALTER TABLE ens_mappings RENAME TO ens_mappings_old;
CREATE TABLE ens_mappings (
    address TEXT NOT NULL,
    ens_name TEXT UNIQUE,
    last_update INTEGER NOT NULL,
    last_avatar_update INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'ens',
    PRIMARY KEY(address, source)
);
INSERT INTO ens_mappings(address, ens_name, last_update, last_avatar_update)
SELECT address, ens_name, last_update, last_avatar_update FROM ens_mappings_old;
DROP TABLE ens_mappings_old;
""")

    @progress_step(description='Add GNS after ENS in address name priority.')
    def _add_gns_to_address_name_priority(write_cursor: DBCursor) -> None:
        if (data := write_cursor.execute(
            "SELECT value FROM settings WHERE name='address_name_priority'",
        ).fetchone()) is None:
            return  # A missing setting uses the defaults, which already have GNS after ENS.

        try:
            priority = json.loads(data[0])
        except json.JSONDecodeError as e:
            log.error('Failed to read address name priority from user db due to %s', e)
            return

        if not isinstance(priority, list):
            return

        priority = [source for source in priority if source != 'gns_names']
        if 'ens_names' in priority:
            priority.insert(priority.index('ens_names') + 1, 'gns_names')
        else:
            priority.append('gns_names')

        write_cursor.execute(
            "UPDATE settings SET value=? WHERE name='address_name_priority'",
            (json.dumps(priority),),
        )

    @progress_step(description='Add Kraken as the first current price oracle.')
    def _add_kraken_current_price_oracle(write_cursor: DBCursor) -> None:
        if (data := write_cursor.execute(
            "SELECT value FROM settings WHERE name='current_price_oracles'",
        ).fetchone()) is None:
            return  # A missing setting uses the defaults, which already have Kraken first.

        try:
            oracles: list[str] = json.loads(data[0])
        except json.JSONDecodeError as e:
            log.error('Failed to read current price oracles from user db due to %s', e)
            return

        kraken = CurrentPriceOracle.KRAKEN.serialize()
        write_cursor.execute(
            'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
            (
                'current_price_oracles',
                json.dumps([
                    kraken,
                    *(oracle for oracle in oracles if oracle != kraken),
                ]),
            ),
        )

    @progress_step(description='Removing orphaned history event backups.')
    def _remove_orphaned_event_backups(write_cursor: DBCursor) -> None:
        """Remove backup rows whose event no longer exists. Such backups can never be
        legitimately restored (restore flows find their targets via history_event_links,
        which cascade away with the event), but identifiers (rowids) get reused after
        deletion and save_history_event_backup keeps the earliest row per identifier,
        so a stale backup could later be restored over an unrelated event.
        """
        write_cursor.execute(
            'DELETE FROM history_events_backup WHERE identifier NOT IN '
            '(SELECT identifier FROM history_events)',
        )

    @progress_step(description='Marking exchange adjustment events as synthetic.')
    def _mark_exchange_adjustments_synthetic(write_cursor: DBCursor) -> None:
        """Stamp the auto-created exchange adjustment events with the new SYNTHETIC
        mapping state (5) so they are shown as events manufactured by rotki.

        Scoped to adjustments carrying the MATCHED state (3), which only the asset
        movement matching machinery sets — user-created events of the same type are
        left alone. Hardcoded values to keep the upgrade immune to future changes.
        """
        write_cursor.execute(
            "INSERT OR IGNORE INTO history_events_mappings(parent_identifier, name, value) "
            "SELECT M.parent_identifier, 'state', 5 FROM history_events_mappings M "
            "INNER JOIN history_events H ON H.identifier=M.parent_identifier "
            "WHERE M.name='state' AND M.value=3 AND H.type='exchange adjustment'",
        )

    @progress_step(description='Create bitcoin transaction tables.')
    def _create_bitcoin_transaction_tables(write_cursor: DBCursor) -> None:
        """Bitcoin transactions used to be decoded into history events and then thrown away,
        on the assumption that a chain without protocols would never need decoding again.
        Correcting a decoding mistake does need it though, and so does a transaction whose
        events changed because another of its addresses started being tracked. Save them so
        that both can be done without querying the explorers again.

        Hardcoded schema/indexes to prevent future schema changes from affecting this upgrade.
        """
        write_cursor.execute("""
CREATE TABLE IF NOT EXISTS bitcoin_transactions (
    identifier INTEGER NOT NULL PRIMARY KEY,
    location CHAR(1) NOT NULL REFERENCES location(location),
    tx_id TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    block_height INTEGER NOT NULL,
    fee INTEGER NOT NULL,
    vin_count INTEGER,
    vout_count INTEGER,
    UNIQUE(location, tx_id)
);""")
        write_cursor.execute("""
CREATE TABLE IF NOT EXISTS bitcoin_tx_io (
    tx_id INTEGER NOT NULL,
    direction INTEGER NOT NULL CHECK(direction IN (1, 2)),
    io_index INTEGER NOT NULL,
    value INTEGER NOT NULL,
    address TEXT,
    script BLOB,
    PRIMARY KEY(tx_id, direction, io_index),
    FOREIGN KEY(tx_id) REFERENCES bitcoin_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE
) WITHOUT ROWID;""")  # noqa: E501
        write_cursor.execute("""
CREATE TABLE IF NOT EXISTS bitcointx_address_mappings (
    tx_id INTEGER NOT NULL,
    address TEXT NOT NULL,
    PRIMARY KEY(tx_id, address),
    FOREIGN KEY(tx_id) REFERENCES bitcoin_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE
) WITHOUT ROWID;""")  # noqa: E501
        write_cursor.execute("""
CREATE TABLE IF NOT EXISTS bitcoin_tx_mappings (
    tx_id INTEGER NOT NULL,
    value INTEGER NOT NULL,
    PRIMARY KEY(tx_id, value),
    FOREIGN KEY(tx_id) REFERENCES bitcoin_transactions(identifier) ON DELETE CASCADE ON UPDATE CASCADE
) WITHOUT ROWID;""")  # noqa: E501
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_bitcoin_tx_io_address ON bitcoin_tx_io(address);',
        )

    @progress_step(description='Index raw transaction timestamps and address mappings.')
    def _create_transaction_timestamp_indexes(write_cursor: DBCursor) -> None:
        write_cursor.executescript("""
CREATE INDEX IF NOT EXISTS idx_evm_transactions_chain_timestamp
ON evm_transactions(chain_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_evmtx_address_mappings_address
ON evmtx_address_mappings(address, tx_id);
CREATE INDEX IF NOT EXISTS idx_zksynclite_transactions_from_timestamp
ON zksynclite_transactions(from_address, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_zksynclite_transactions_to_timestamp
ON zksynclite_transactions(to_address, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_solana_transactions_block_time
ON solana_transactions(block_time DESC);
CREATE INDEX IF NOT EXISTS idx_solanatx_address_mappings_address
ON solanatx_address_mappings(address, tx_id);
CREATE INDEX IF NOT EXISTS idx_bitcoin_transactions_location_timestamp
ON bitcoin_transactions(location, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_bitcointx_address_mappings_address
ON bitcointx_address_mappings(address, tx_id);
""")

    @progress_step(description='Turn bitcoin events into chain events.')
    def _migrate_bitcoin_events(write_cursor: DBCursor) -> None:
        """Bitcoin events were plain history events that identified their transaction only by
        the prefix of their group identifier, so every query that goes from a transaction to
        its events needed a bitcoin-specific branch. Turn them into chain events like every
        other chain, with the transaction id in chain_events_info.tx_ref.

        Only events whose group identifier is a prefixed 64 character transaction id are
        converted; anything else at a bitcoin location was created by the user and stays a
        plain history event. Hardcoded values to keep the upgrade immune to future changes.

        The backup copies kept for edited/matched events are migrated the same way. A restore
        replaces the live row (INSERT OR REPLACE), which cascades its chain_events_info away
        and puts the backup's own chain info back, so a backup left as a plain event would
        silently undo this migration and leave an event that no transaction filter, deletion
        or redecode could find any more.
        """
        for table, chain_table in (
            ('history_events', 'chain_events_info'),
            ('history_events_backup', 'chain_events_info_backup'),
        ):
            migrated: list[tuple[int, bytes]] = []
            for location, prefix in (('q', 'btc_'), ('r', 'bch_')):
                for identifier, group_identifier in write_cursor.execute(
                    f'SELECT identifier, group_identifier FROM {table} '
                    'WHERE location=? AND entry_type=1 AND group_identifier LIKE ?',  # 1 is HistoryBaseEntryType.HISTORY_EVENT  # noqa: E501
                    (location, f'{prefix}%'),
                ).fetchall():  # materialized since the writes below reuse the cursor
                    try:
                        tx_ref = bytes.fromhex(group_identifier.removeprefix(prefix))
                    except ValueError:
                        continue  # a user created event that only looks like a transaction

                    if len(tx_ref) == 32:
                        migrated.append((identifier, tx_ref))

            write_cursor.executemany(
                f'INSERT OR IGNORE INTO {chain_table}(identifier, tx_ref, counterparty, address) '
                'VALUES(?, ?, NULL, NULL)',
                migrated,
            )
            write_cursor.executemany(  # 11 is HistoryBaseEntryType.BITCOIN_EVENT
                f'UPDATE {table} SET entry_type=11 WHERE identifier=?',
                [(identifier,) for identifier, _ in migrated],
            )

    @progress_step(description='Resetting decoded events.')
    def _reset_decoded_events(write_cursor: DBCursor) -> None:
        """Reset all decoded evm, solana and bitcoin events.

        If any event in a transaction is customized, all events in that transaction are
        preserved along with its decoded status. Bitcoin transactions are not present in the
        newly created transaction tables yet, so their migrated chain events are selected by
        location and will be refetched after the query range reset below.
        """
        has_bitcoin_events = write_cursor.execute(
            "SELECT COUNT(*) FROM history_events WHERE location IN ('q', 'r') AND entry_type=11",
        ).fetchone()[0] > 0
        if not (
            write_cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0] > 0 or
            write_cursor.execute('SELECT COUNT(*) FROM solana_transactions').fetchone()[0] > 0 or
            has_bitcoin_events
        ):
            return

        querystr = (
            "DELETE FROM history_events WHERE identifier IN ("
            "SELECT H.identifier FROM history_events H INNER JOIN chain_events_info C "
            "ON H.identifier=C.identifier AND (C.tx_ref IN "
            "(SELECT tx_hash FROM evm_transactions) OR C.tx_ref IN "
            "(SELECT signature FROM solana_transactions) OR H.location IN ('q', 'r')) "
            "AND H.location != 'o')"  # location 'o' is zksync lite
        )
        bindings: tuple = ()
        has_customized = write_cursor.execute(
            'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?',
            (customized_events_bindings := (
                HISTORY_MAPPING_KEY_STATE,
                HistoryMappingState.CUSTOMIZED.serialize_for_db(),
            )),
        ).fetchone()[0] != 0
        if has_customized:
            querystr += (
                ' AND group_identifier NOT IN ('
                'SELECT H2.group_identifier FROM history_events H2 '
                'INNER JOIN history_events_mappings M ON H2.identifier = M.parent_identifier '
                'WHERE M.name=? AND M.value=?)'
            )
            bindings = customized_events_bindings

        write_cursor.execute(querystr, bindings)
        # A deleted event cannot be restored through any supported flow. Remove its backup too,
        # otherwise a reused history-event identifier could restore stale Bitcoin metadata.
        write_cursor.execute(
            'DELETE FROM history_events_backup WHERE identifier NOT IN '
            '(SELECT identifier FROM history_events)',
        )

        for table, tx_table, tx_id_col in (
            ('evm_tx_mappings', 'evm_transactions', 'tx_hash'),
            ('solana_tx_mappings', 'solana_transactions', 'signature'),
        ):
            tx_querystr = (
                f'DELETE FROM {table} WHERE tx_id IN '
                f'(SELECT identifier FROM {tx_table}) AND value=?'
            )
            tx_bindings: tuple = (0,)  # decoded tx state
            if has_customized:
                tx_querystr += (
                    f' AND tx_id NOT IN ('
                    f'SELECT DISTINCT T.identifier FROM {tx_table} T '
                    f'INNER JOIN chain_events_info C ON T.{tx_id_col} = C.tx_ref '
                    'INNER JOIN history_events_mappings M ON C.identifier = M.parent_identifier '
                    'WHERE M.name=? AND M.value=?)'
                )
                tx_bindings += customized_events_bindings
            write_cursor.execute(tx_querystr, tx_bindings)

    @progress_step(description='Reset bitcoin transaction query range.')
    def _reset_bitcoin_query_range(write_cursor: DBCursor) -> None:
        """Bitcoin transactions with a change output were decoded as a spend of the entire
        input plus a receive of the change, inventing a disposal and an acquisition that
        never happened and corrupting cost basis. Transfers between owned addresses were
        also never credited to the receiving address in historical balances.

        There is nothing saved locally to redecode from yet, since the transaction tables
        this same upgrade creates are only filled from now on. Instead reset the per-address
        last queried block, so the next transaction query refetches the full history from the
        explorers and decodes it with the corrected logic. That query also fills the new
        tables, which is what makes any future correction a local redecode instead of this.

        The decoded Bitcoin events are reset by the preceding upgrade step. The next query
        therefore refetches the full history and writes events decoded with the corrected logic.
        """
        write_cursor.execute(
            "DELETE FROM key_value_cache WHERE "
            "name LIKE 'last\\_btc\\_tx\\_block\\_%' ESCAPE '\\' OR "
            "name LIKE 'last\\_bch\\_tx\\_block\\_%' ESCAPE '\\'",
        )

    @progress_step(description='Remove obsolete airdrop parquet files.')
    def _remove_airdrop_parquet_files(write_cursor: DBCursor) -> None:
        """Remove parquet airdrop files left behind now that airdrops use compressed CSV files."""
        for parquet_file_path in (
            db.user_data_dir.parent.parent / APPDIR_NAME / AIRDROPSDIR_NAME
        ).glob('*.parquet'):
            try:
                parquet_file_path.unlink()
            except OSError as e:
                log.error(
                    'Failed to remove airdrop file %s due to %s. Skipping it',
                    parquet_file_path,
                    e,
                )

    @progress_step(description='Adding blockscout to the gnosis indexer order.')
    def _add_blockscout_to_gnosis_indexers(write_cursor: DBCursor) -> None:
        """Etherscan now only serves gnosis to paid api keys, so blockscout became the primary
        gnosis indexer. Users who never customized the order pick that up from the defaults, but
        an explicitly saved gnosis order overrides them and would keep querying an endpoint the
        user probably has no access to. Put blockscout first for those, keeping whatever else
        they had chosen as the fallback. Hardcoded strings to keep the upgrade immune to future
        changes of the setting's serialization.
        """
        if (result := write_cursor.execute(
            "SELECT value FROM settings WHERE name='evm_indexers_order'",
        ).fetchone()) is None:
            return  # never customized, the new default applies

        try:
            orders = json.loads(result[0])
        except json.JSONDecodeError as e:
            log.error('During v52->v53 found a non-json evm_indexers_order entry. %s', e)
            return

        if (
            not isinstance(orders, dict) or
            not isinstance(gnosis_order := orders.get('gnosis'), list) or
            'blockscout' in gnosis_order
        ):
            return  # no explicit gnosis order, or blockscout is already among the choices

        orders['gnosis'] = ['blockscout', *gnosis_order]
        write_cursor.execute(
            "UPDATE settings SET value=? WHERE name='evm_indexers_order'",
            (json.dumps(orders),),
        )

    @progress_step(description='Canonicalize evm asset identifiers that were not checksummed.')
    def _checksum_evm_asset_identifiers(write_cursor: DBCursor) -> None:
        """Rewrite the evm asset identifiers whose address was never checksummed.

        The globaldb upgrade running before this one canonicalizes the same identifiers there.
        The transformation is the same on both sides and depends on nothing but the identifier
        itself, so the two need no coordination, and this pass only has to find the identifiers
        this db mirrored while they were still non canonical.

        An address that was never checksummed is uniformly cased, so the keccak behind
        to_checksum_address is only paid for a handful of the mirrored identifiers.
        """
        identifiers = {identifier for (identifier,) in write_cursor.execute(
            "SELECT identifier FROM assets WHERE identifier LIKE 'eip155:%'",
        )}
        renames: list[tuple[str, str]] = []
        merges: list[tuple[str, str]] = []
        for identifier in sorted(identifiers):  # a snapshot, identifiers is added to below
            if len(parts := identifier.split(':')) != 3:
                continue

            # an erc721 identifier appends /<collectible id> after the address
            if (body := (address := parts[2].split('/')[0])[2:]) != body.lower() and body != body.upper():  # noqa: E501
                continue

            try:
                checksummed = to_checksum_address(address)
            except ValueError:
                log.error('Skipping asset %s with an invalid evm address %s', identifier, address)
                continue

            if checksummed == address:
                continue

            # unlike the globaldb's, this table's identifier is case sensitive, so both casings
            # can sit in it: the mirror of the globaldb inserts the identifier as the globaldb
            # spelled it, while an asset built straight from a checksummed address inserts its
            # own. A rename would hit the primary key here and be ignored, leaving the two
            # apart, which is what this step exists to end, so those are merged instead.
            if (new_identifier := identifier.replace(address, checksummed)) in identifiers:
                merges.append((new_identifier, identifier))
            else:
                renames.append((new_identifier, identifier))
                identifiers.add(new_identifier)  # so a second casing of it merges onto this

        if len(renames) == 0 and len(merges) == 0:
            return

        log.debug('Canonicalizing %s evm asset identifiers', len(renames) + len(merges))
        # assets.identifier is the parent of an ON UPDATE CASCADE foreign key from every asset
        # column, but foreign keys are not guaranteed to be on during an upgrade, so each
        # column is written explicitly instead of relying on the cascade. Which ones those are
        # is asked of the db rather than listed here, so a column cannot be missed. The only
        # asset columns with no foreign key are data_issues and event_metrics, both of which
        # this same upgrade creates, and multisettings, handled below.
        child_columns: list[tuple[str, str]] = []
        for (table,) in write_cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'",
        ).fetchall():
            child_columns.extend(
                (table, fk_entry[3])
                for fk_entry in write_cursor.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()  # noqa: E501
                if fk_entry[2] == 'assets' and fk_entry[4] == 'identifier'
            )

        for table, column in (('assets', 'identifier'), *child_columns):
            write_cursor.executemany(
                f'UPDATE OR IGNORE {table} SET {column}=? WHERE {column}=?',
                renames,
            )

        write_cursor.executemany(  # the ignored assets are kept in here, without a foreign key
            "UPDATE OR IGNORE multisettings SET value=? WHERE value=? AND name='ignored_asset'",
            renames,
        )
        if len(merges) != 0:
            _merge_onto_canonical_identifier(
                write_cursor=write_cursor,
                child_columns=child_columns,
                merges=merges,
            )

    @progress_step(description='Create timed balances netvalue index.')
    def _create_timed_balances_netvalue_index(write_cursor: DBCursor) -> None:
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS '
            'idx_timed_balances_currency_timestamp_category_value '
            'ON timed_balances(currency, timestamp, category, usd_value)',
        )

    @progress_step(description='Create and migrate EVM account proxy mappings.')
    def _create_evm_account_proxies_table(write_cursor: DBCursor) -> None:
        # `proxies` was stored as `<proxy_type>:<proxy_address>` in evm_accounts_details.
        # Keep this upgrade self-contained so later schema changes cannot affect it.
        write_cursor.execute("""
CREATE TABLE IF NOT EXISTS evm_account_proxies (
    account VARCHAR[42] NOT NULL,
    chain_id INTEGER NOT NULL,
    proxy_type TEXT NOT NULL,
    proxy_address VARCHAR[42] NOT NULL,
    PRIMARY KEY (account, chain_id, proxy_type, proxy_address)
);
""")
        write_cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_evm_account_proxies_chain_account '
            'ON evm_account_proxies(chain_id, account)',
        )
        write_cursor.execute("""
INSERT OR IGNORE INTO evm_account_proxies(account, chain_id, proxy_type, proxy_address)
SELECT
    account,
    chain_id,
    substr(value, 1, instr(value, ':') - 1),
    substr(value, instr(value, ':') + 1)
FROM evm_accounts_details
WHERE key = 'proxies' AND instr(value, ':') > 1;
""")
        write_cursor.execute("DELETE FROM evm_accounts_details WHERE key = 'proxies';")

    @progress_step(description='Remove obsolete unsupported-assets update setting.')
    def _remove_obsolete_setting(write_cursor: DBCursor) -> None:
        """Remove the cursor for the retired exchange unsupported-asset blocklist."""
        write_cursor.execute(
            "DELETE FROM settings WHERE name='location_unsupported_assets_version'",
        )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler)
