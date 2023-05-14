import json
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.base import HistoryBaseEntryType
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.constants.assets import A_ETH2
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
    HISTORY_MAPPING_STATE_DECODED,
)
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EVM_LOCATIONS, Location, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
    """
    Reset all decoded events except the customized ones.
    """
    write_cursor.execute('SELECT tx_hash from evm_transactions')
    tx_hashes = [x[0] for x in write_cursor]
    write_cursor.execute(
        'SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?',
        (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
    )
    customized_event_ids = [x[0] for x in write_cursor]
    length = len(customized_event_ids)
    querystr = 'DELETE FROM history_events WHERE event_identifier=?'
    if length != 0:
        querystr += f' AND identifier NOT IN ({", ".join(["?"] * length)})'
        bindings = [(x, *customized_event_ids) for x in tx_hashes]
    else:
        bindings = [(x,) for x in tx_hashes]
    write_cursor.executemany(querystr, bindings)
    write_cursor.executemany(
        'DELETE from evm_tx_mappings WHERE tx_hash=? AND value=?',
        [(tx_hash, HISTORY_MAPPING_STATE_DECODED) for tx_hash in tx_hashes],
    )


def _move_event_locations(write_cursor: 'DBCursor') -> None:
    """
    Create location ethereum and optimism and move the blockchain events to those locations

    This used to be DB data migration 9 which was added only for when upgrading from 1.27.0 to
    1.27.1. So it only exists in 1.27.1 and has from now on (1.28.0) moved to this DB upgrade

    This should always be at the start of this DB upgrade as it relies on the old schema.
    """
    log.debug('Enter _move_event_locations')
    write_cursor.execute('INSERT OR IGNORE INTO location(location, seq) VALUES ("f", 38);')
    write_cursor.execute('INSERT OR IGNORE INTO location(location, seq) VALUES ("g", 39);')

    write_cursor.execute(
        'SELECT chain_id, tx_hash FROM evm_transactions WHERE '
        'tx_hash IN (SELECT event_identifier FROM history_events)',
    )
    update_tuples = []
    for chain_id, tx_hash in write_cursor:
        if chain_id == 1:
            location = 'f'  # ethereum
        elif chain_id == 10:
            location = 'g'  # optimism
        else:  # unexpected -- skip entry from editing
            log.error(f'Found unexpected chain id {chain_id} in the DB for transaction {tx_hash}')
            continue

        update_tuples.append((location, tx_hash))

    write_cursor.executemany(
        'UPDATE history_events SET location=? WHERE event_identifier=?', update_tuples,
    )
    write_cursor.execute('DELETE FROM history_events_mappings WHERE name="chain_id"')
    log.debug('Exit _move_event_locations')


def _update_history_events_schema(write_cursor: 'DBCursor', conn: 'DBConnection') -> None:
    """
    1. Reset all decoded events
    2. Rewrite the DB schema of the history events to have subtype as non Optional
    3. Delete counterparty and extra_data fields
    4. Add `entry_type` column that helps determine types of events.
    5. Turn event_identifier to a string

    Also turn all null subtype entries to have subtype none
    """
    log.debug('Enter _update_history_events_schema')

    _reset_decoded_events(write_cursor)
    write_cursor.execute("""CREATE TABLE IF NOT EXISTS history_events_copy (
    identifier INTEGER NOT NULL PRIMARY KEY,
    entry_type INTEGER NOT NULL,
    event_identifier TEXT NOT NULL,
    sequence_index INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    location TEXT NOT NULL,
    location_label TEXT,
    asset TEXT NOT NULL,
    amount TEXT NOT NULL,
    usd_value TEXT NOT NULL,
    notes TEXT,
    type TEXT NOT NULL,
    subtype TEXT NOT NULL,
    FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
    UNIQUE(event_identifier, sequence_index)
    );""")
    new_entries = []
    extra_evm_info_entries = []
    with conn.read_ctx() as read_cursor:
        read_cursor.execute('SELECT * from history_events')
        for entry in read_cursor:
            location = Location.deserialize_from_db(entry[4])
            db_event_identifier = entry[1]
            if location in EVM_LOCATIONS:
                event_identifier = f'{location.to_chain_id()}{deserialize_evm_tx_hash(db_event_identifier).hex()}'  # noqa: E501 # pylint: disable=no-member
            elif location == Location.KRAKEN or db_event_identifier.startswith(b'rotki_events'):
                # kraken is the only location with basic history event entry type that doesn't
                # start with 'rotki_events'
                event_identifier = db_event_identifier.decode()
            else:
                # this shouldn't happen, leaving it here to avoid failing during the upgrade
                # _move_event_locations should have moved already all the events that are related
                # to evm transactions with the wrong location
                log.critical(f'Unexpected event {entry=} found. Skipping')
                continue

            if location == Location.KRAKEN or event_identifier.startswith('rotki_events'):  # This is the rule at 1.27.1   # noqa: E501
                entry_type = HistoryBaseEntryType.HISTORY_EVENT.serialize_for_db()
            else:
                entry_type = HistoryBaseEntryType.EVM_EVENT.serialize_for_db()
                extra_evm_info_entries.append((entry[0], entry[1]) + entry[12:])

            if entry[11] is None:
                new_entries.append([entry[0], entry_type, event_identifier, *entry[2:11], 'none'])  # turn NULL values to text `none`  # noqa: E501
            else:
                new_entries.append([entry[0], entry_type, event_identifier, *entry[2:12]])  # Don't change NON-NULL values  # noqa: E501

    # add all non-evm entries to the new table (no data lost)
    write_cursor.executemany('INSERT INTO history_events_copy VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', new_entries)  # noqa: E501
    for entry in extra_evm_info_entries:
        write_cursor.execute(
            'INSERT INTO evm_events_info VALUES(?, ?, ?, ?, ?, ?)',
            (entry[0], entry[1], entry[2], None, None, entry[3]),
        )

    write_cursor.switch_foreign_keys('OFF')  # need FK off or history_events_mappings get deleted
    write_cursor.execute('DROP TABLE history_events')
    write_cursor.execute('ALTER TABLE history_events_copy RENAME TO history_events')
    write_cursor.switch_foreign_keys('ON')

    log.debug('Exit _update_history_events_schema')


def _create_new_tables(write_cursor: 'DBCursor') -> None:
    """Create new tables

    Data is not migrated to the evm_events_info as it will be done when redecoding.
    Still left to do: delete all data except customized events and figure out what to do
    with the custom events.
    """
    log.debug('Enter _create_new_tables')
    write_cursor.execute("""
        CREATE TABLE IF NOT EXISTS evm_events_info(
            identifier INTEGER PRIMARY KEY,
            tx_hash BLOB NOT NULL,
            counterparty TEXT,
            product TEXT,
            address TEXT,
            extra_data TEXT,
            FOREIGN KEY(identifier) REFERENCES history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE
        );
    """)  # noqa: E501
    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS eth_staking_events_info(
        identifier INTEGER PRIMARY KEY,
        validator_index INTEGER NOT NULL,
        is_exit_or_blocknumber INTEGER NOT NULL,
        FOREIGN KEY(identifier) REFERENCES history_events(identifier) ON UPDATE CASCADE ON DELETE CASCADE
    );
    """)  # noqa: E501

    log.debug('Exit _create_new_tables')


def _delete_old_tables(write_cursor: 'DBCursor') -> None:
    """Deletes old tables that are now unused along with related data
    """
    log.debug('Enter _delete_old_tables')
    write_cursor.execute('DROP TABLE IF EXISTS eth2_deposits')
    write_cursor.execute(
        'DELETE FROM used_query_ranges WHERE name LIKE ?',
        ('eth2_deposits%',),
    )

    log.debug('Exit _delete_old_tables')


def _update_ens_mappings_schema(write_cursor: 'DBCursor') -> None:
    log.debug('Enter _update_ens_mappings_schema')
    write_cursor.execute("""CREATE TABLE ens_mappings_copy (
        address TEXT NOT NULL PRIMARY KEY,
        ens_name TEXT UNIQUE,
        last_update INTEGER NOT NULL,
        last_avatar_update INTEGER NOT NULL DEFAULT 0
    )""")
    write_cursor.execute(
        'INSERT INTO ens_mappings_copy(address, ens_name, last_update) '
        'SELECT address, ens_name, last_update FROM ens_mappings',
    )
    write_cursor.execute('DROP TABLE ens_mappings')
    write_cursor.execute('ALTER TABLE ens_mappings_copy RENAME TO ens_mappings')
    log.debug('Exit _update_ens_mappings_schema')


def _fix_kraken_events(write_cursor: 'DBCursor') -> None:
    """
    Fix kraken events with negative amounts related to:
    - staking ETH after the merge
    - trades not having subtypes and having negative amounts
    - withdrawals use positive amounts
    - instant swaps
    Needs to be executed after _update_history_events_schema
    """
    log.debug('Enter _fix_kraken_events. Fixing kraken eth2 related tuples')
    update_tuples: list[Any] = []
    write_cursor.execute(
        'SELECT identifier, amount, usd_value FROM history_events WHERE location="B" AND '
        'asset=? AND type="staking" AND subtype="reward" AND CAST(amount AS REAL) < 0',
        (A_ETH2.identifier,),
    )
    for event_row in write_cursor:
        update_tuples.append(
            (
                HistoryEventType.INFORMATIONAL.serialize(),
                HistoryEventSubType.NONE.serialize(),
                str(-FVal(event_row[1])),
                str(-FVal(event_row[2])),
                'Automatic virtual conversion of staked ETH rewards to ETH',
                event_row[0],
            ),
        )
    if len(update_tuples) != 0:
        write_cursor.executemany(
            'UPDATE history_events SET type=?, subtype=?, amount=?, usd_value=?, notes=? WHERE identifier=?',  # noqa: E501
            update_tuples,
        )

    log.debug('Fixing kraken trades')
    update_tuples = []
    write_cursor.execute(
        'SELECT identifier, amount, usd_value FROM history_events WHERE location="B" AND '
        'type="trade" AND subtype="none"',
    )

    trade_db_type = HistoryEventType.TRADE.serialize()
    for event_row in write_cursor:
        asset_amount = FVal(event_row[1])
        usd_value = FVal(event_row[2])
        if asset_amount < ZERO:
            event_subtype = HistoryEventSubType.SPEND
            asset_amount = -asset_amount
            usd_value = -usd_value
        else:
            event_subtype = HistoryEventSubType.RECEIVE

        update_tuples.append(
            (
                trade_db_type,
                event_subtype.serialize(),
                str(asset_amount),
                str(usd_value),
                event_row[0],
            ),
        )

    if len(update_tuples) != 0:
        write_cursor.executemany(
            'UPDATE history_events SET type=?, subtype=?, amount=?, usd_value=? WHERE identifier=?',  # noqa: E501
            update_tuples,
        )

    log.debug('Fixing kraken withdrawals')  # deposits are all positive amount already
    update_tuples = []
    write_cursor.execute(
        'SELECT identifier, amount, usd_value FROM history_events WHERE location="B" AND '
        'type="withdrawal"',
    )
    for event_row in write_cursor:
        update_tuples.append(
            (
                str(-FVal(event_row[1])),
                str(-FVal(event_row[2])),
                event_row[0],
            ),
        )
    if len(update_tuples) != 0:
        write_cursor.executemany(
            'UPDATE history_events SET amount=?, usd_value=? WHERE identifier=?',
            update_tuples,
        )

    log.debug('Fixing kraken instant swaps')
    update_tuples = []
    grouped_events: dict[str, list[Any]] = defaultdict(list)
    write_cursor.execute(
        'SELECT identifier, event_identifier, type, amount, usd_value FROM history_events '
        'WHERE location="B" AND type IN ("spend", "receive") AND subtype="none"',
    )
    for row in write_cursor:
        grouped_events[row[1]].append(row)

    for events in grouped_events.values():
        if len(events) != 2:
            # we are looking for instant swaps that are always pairs of spend/receive
            # with the same event identifier
            continue

        for event in events:
            if event[2] == 'spend':
                event_subtype = HistoryEventSubType.SPEND
                asset_amount = FVal(event[3])
                asset_amount_str = str(-asset_amount) if asset_amount != ZERO else str(asset_amount)  # noqa: E501
                usd_value_str = str(-FVal(event[4]))
            else:
                event_subtype = HistoryEventSubType.RECEIVE
                asset_amount_str = event[3]
                usd_value_str = event[4]

            update_tuples.append(
                (
                    trade_db_type,
                    event_subtype.serialize(),
                    asset_amount_str,
                    usd_value_str,
                    event[0],
                ),
            )
    if len(update_tuples) != 0:
        write_cursor.executemany(
            'UPDATE history_events SET type=?, subtype=?, amount=?, usd_value=? WHERE identifier=?',  # noqa: E501
            update_tuples,
        )

    log.debug('Exit _fix_kraken_events')


def _trim_daily_stats(write_cursor: 'DBCursor') -> None:
    """Decreases the amount of data in the daily stats table"""
    log.debug('Enter _trim_daily_stats')
    table_exists = write_cursor.execute(
        'SELECT COUNT(*) FROM sqlite_master '
        'WHERE type="table" AND name="eth2_daily_staking_details"',
    ).fetchone()[0] == 1
    table_to_create = 'eth2_daily_staking_details'
    if table_exists is True:
        table_to_create += '_new'
    write_cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_to_create} (
        validator_index INTEGER NOT NULL,
        timestamp INTEGER NOT NULL,
        pnl TEXT NOT NULL,
        FOREIGN KEY(validator_index) REFERENCES eth2_validators(validator_index) ON UPDATE CASCADE ON DELETE CASCADE,
        PRIMARY KEY (validator_index, timestamp)
    );""")  # noqa: E501
    if table_exists is True:
        write_cursor.execute(
            'INSERT INTO eth2_daily_staking_details_new SELECT validator_index, timestamp, pnl '
            'FROM eth2_daily_staking_details',
        )
        write_cursor.execute('DROP TABLE eth2_daily_staking_details')
        write_cursor.execute(
            'ALTER TABLE eth2_daily_staking_details_new RENAME TO eth2_daily_staking_details',
        )
    log.debug('Exit _trim_daily_stats')


def _remove_ftx_data(write_cursor: 'DBCursor') -> None:
    """Removes FTX-related settings from the DB"""
    log.debug('Enter _remove_ftx_data')
    write_cursor.execute(
        'DELETE FROM user_credentials WHERE location IN (?, ?)',
        (Location.FTX.serialize_for_db(), Location.FTXUS.serialize_for_db()),
    )
    write_cursor.execute(
        'DELETE FROM user_credentials_mappings WHERE credential_location IN (?, ?)',
        (Location.FTX.serialize_for_db(), Location.FTXUS.serialize_for_db()),
    )
    write_cursor.execute(
        'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
        (f'{Location.FTX!s}\\_%', '\\'),
    )
    write_cursor.execute(
        'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
        (f'{Location.FTXUS!s}\\_%', '\\'),
    )
    non_syncing_exchanges_in_db = write_cursor.execute(
        'SELECT value FROM settings WHERE name="non_syncing_exchanges"',
    ).fetchone()
    if non_syncing_exchanges_in_db is not None:
        non_syncing_exchanges = json.loads(non_syncing_exchanges_in_db[0])
        new_values = []
        for entry in non_syncing_exchanges:
            if entry['location'] not in (Location.FTX.serialize(), Location.FTXUS.serialize()):
                new_values.append(entry)

        write_cursor.execute(
            'UPDATE settings SET value=? WHERE name="non_syncing_exchanges"',
            (json.dumps(new_values),),
        )
    log.debug('Exit _remove_ftx_data')


def _adjust_user_settings(write_cursor: 'DBCursor') -> None:
    """Adjust user settings, renaming a key that misbehaves in frontend transformation"""
    log.debug('Enter _adjust_user_settings')
    write_cursor.execute(
        'UPDATE settings SET name="ssf_graph_multiplier" WHERE name="ssf_0graph_multiplier"')
    log.debug('Exit _adjust_user_settings')


def upgrade_v36_to_v37(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v36 to v37. This was in v1.28.0 release.

        - Replace null history event subtype
    """
    log.debug('Entered userdb v36->v37 upgrade')
    progress_handler.set_total_steps(9)
    with db.user_write() as write_cursor:
        _move_event_locations(write_cursor)
        progress_handler.new_step()
        _create_new_tables(write_cursor)
        progress_handler.new_step()
        _update_history_events_schema(write_cursor, db.conn)
        progress_handler.new_step()
        _update_ens_mappings_schema(write_cursor)
        progress_handler.new_step()
        _delete_old_tables(write_cursor)
        progress_handler.new_step()
        _fix_kraken_events(write_cursor)
        progress_handler.new_step()
        _trim_daily_stats(write_cursor)
        progress_handler.new_step()
        _remove_ftx_data(write_cursor)
        progress_handler.new_step()
        _adjust_user_settings(write_cursor)
        progress_handler.new_step()

    log.debug('Finished userdb v36->v36 upgrade')
