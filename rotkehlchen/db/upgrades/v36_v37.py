import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.constants.assets import A_ETH2
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
            if isinstance(entry[1], str):
                event_identifier = entry[1]
            else:  # is an EVM transaction event
                if location not in EVM_LOCATIONS:
                    # data is somehow wrong. Let's try to fix location
                    chain_id = write_cursor.execute('SELECT chain_id from evm_transactions WHERE tx_hash=?', (entry[1],)).fetchone()  # noqa: E501
                    if chain_id is not None:
                        location = Location.from_chain_id(chain_id)
                    else:  # could not find tx_hash. Let's just default to ethereum
                        location = Location.ETHEREUM

                event_identifier = f'{location.to_chain_id()}{deserialize_evm_tx_hash(entry[1]).hex()}'  # noqa: E501 # pylint: disable=no-member

            if location == Location.KRAKEN or event_identifier.startswith('rotki_events'):  # This is the rule at 1.27.1   # noqa: E501
                entry_type = 0  # Pure history base entry
            else:
                entry_type = 1  # An evm event
            if entry[11] is None:
                new_entries.append([entry[0], entry_type, event_identifier, *entry[2:11], 'none'])  # turn NULL values to text `none`  # noqa: E501
            else:
                new_entries.append([entry[0], entry_type, event_identifier, *entry[2:12]])  # Don't change NON-NULL values  # noqa: E501

            if entry_type == 1:
                extra_evm_info_entries.append((entry[0], entry[1]) + entry[12:])

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


def _fix_kraken_eth2_events(write_cursor: 'DBCursor') -> None:
    """Fix kraken events with negative amounts related to staking ETH after the merge"""
    log.debug('Enter _fix_kraken_eth2_events')
    write_cursor.execute(
        'SELECT identifier, amount, usd_value FROM history_events WHERE location="B" AND '
        'asset=? AND type="staking" AND subtype="reward" AND CAST(amount AS REAL) < 0',
        (A_ETH2.identifier,),
    )
    update_tuples = []
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
    log.debug('Exit _fix_kraken_eth2_events')


def upgrade_v36_to_v37(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v36 to v37. This was in v1.28.0 release.

        - Replace null history event subtype
    """
    log.debug('Entered userdb v36->v37 upgrade')
    progress_handler.set_total_steps(5)
    with db.user_write() as write_cursor:
        _create_new_tables(write_cursor)
        progress_handler.new_step()
        _update_history_events_schema(write_cursor, db.conn)
        progress_handler.new_step()
        _update_ens_mappings_schema(write_cursor)
        progress_handler.new_step()
        _delete_old_tables(write_cursor)
        progress_handler.new_step()
        _fix_kraken_eth2_events(write_cursor)
        progress_handler.new_step()

    log.debug('Finished userdb v36->v36 upgrade')
