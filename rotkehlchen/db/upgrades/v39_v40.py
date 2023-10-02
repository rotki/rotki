import logging
from typing import TYPE_CHECKING
from uuid import uuid4

from rotkehlchen.constants import ZERO
from rotkehlchen.db.utils import update_table_schema
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import Location

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor, DBConnection
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

PREFIX = 'RE_%'  # hard-coded since this is a migration and prefix may change in the future
LEDGER_ACTIONS_PREFIX = 'MLA_'  # prefix to add to ledger actions migrated to history events id
CHANGES = [  # TO TYPE, TO SUBTYPE, FROM TYPE, FROM SUBTYPE
    (HistoryEventType.DEPOSIT, HistoryEventSubType.NONE, HistoryEventType.DEPOSIT, HistoryEventSubType.SPEND),  # noqa: E501
    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.NONE, HistoryEventType.WITHDRAWAL, HistoryEventSubType.RECEIVE),  # noqa: E501
    (HistoryEventType.RECEIVE, HistoryEventSubType.NONE, HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE),  # noqa: E501

    (HistoryEventType.SPEND, HistoryEventSubType.FEE, HistoryEventType.DEPOSIT, HistoryEventSubType.FEE),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, HistoryEventType.WITHDRAWAL, HistoryEventSubType.FEE),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, HistoryEventType.RECEIVE, HistoryEventSubType.FEE),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, HistoryEventType.STAKING, HistoryEventSubType.FEE),  # noqa: E501
]

DEFAULT_BASE_NODES_AT_V40 = [
    ('base etherscan', '', 0, 1, '0.28', 'BASE'),
    ('base ankr', 'https://rpc.ankr.com/base', 0, 1, '0.18', 'BASE'),
    ('base BlockPi', 'https://base.blockpi.network/v1/rpc/public', 0, 1, '0.18', 'BASE'),
    ('base PublicNode', 'https://base.publicnode.com', 0, 1, '0.18', 'BASE'),
    ('base 1rpc', 'https://1rpc.io/base', 0, 1, '0.18', 'BASE'),
]


LEDGER_ACTION_TYPE_TO_NAME = {
    'A': 'income',
    'B': 'expense',
    'C': 'loss',
    'D': 'dividends income',
    'E': 'donation received',
    'F': 'airdrop',
    'G': 'gift',
    'H': 'grant',
}


def _migrate_rotki_events(write_cursor: 'DBCursor') -> None:
    """
    Migrate rotki events that were broken due to https://github.com/rotki/rotki/issues/6550
    """
    log.debug('Enter _migrate_rotki_events')
    write_cursor.executemany(
        'UPDATE history_events SET type=?, subtype=? WHERE '
        'event_identifier LIKE ? AND type=? AND subtype=?',
        [(
            to_type.serialize(), to_subtype.serialize(), PREFIX,
            from_type.serialize(), from_subtype.serialize(),
        ) for to_type, to_subtype, from_type, from_subtype in CHANGES],
    )
    log.debug('Exit _migrate_rotki_events')


def _upgrade_rotki_events(write_cursor: 'DBCursor') -> None:
    """Upgrade the rotki events schema table to specify location as a type"""
    log.debug('Enter _upgrade_rotki_events')
    update_table_schema(
        write_cursor=write_cursor,
        table_name='history_events',
        schema="""identifier INTEGER NOT NULL PRIMARY KEY,
        entry_type INTEGER NOT NULL,
        event_identifier TEXT NOT NULL,
        sequence_index INTEGER NOT NULL,
        timestamp INTEGER NOT NULL,
        location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
        location_label TEXT,
        asset TEXT NOT NULL,
        amount TEXT NOT NULL,
        usd_value TEXT NOT NULL,
        notes TEXT,
        type TEXT NOT NULL,
        subtype TEXT NOT NULL,
        FOREIGN KEY(asset) REFERENCES assets(identifier) ON UPDATE CASCADE,
        UNIQUE(event_identifier, sequence_index)""",
    )
    log.debug('Exit _upgrade_rotki_events')


def _purge_kraken_events(write_cursor: 'DBCursor') -> None:
    """
    Purge kraken events, after the changes that allows for processing of new assets.
    We may have had missed events so now let's repull. And since we will also
    get https://github.com/rotki/rotki/issues/6582 this resetting should not need to
    happen in the future.

    This just mimics DBHandler::purge_exchange_data
    """
    log.debug('Enter _reset_kraken_events')
    write_cursor.execute(
        'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
        (f'{Location.KRAKEN!s}\\_%', '\\'),
    )
    location = Location.KRAKEN.serialize_for_db()
    for table in ('trades', 'asset_movements', 'history_events'):
        write_cursor.execute(f'DELETE FROM {table} WHERE location = ?;', (location,))

    log.debug('Exit _reset_kraken_events')


def _add_base_chain_data(write_cursor: 'DBCursor') -> None:
    log.debug('Enter _add_base_chain_data')
    write_cursor.execute('INSERT OR IGNORE INTO location(location, seq) VALUES ("j", 42);')
    write_cursor.executemany(
        'INSERT OR IGNORE INTO rpc_nodes(name, endpoint, owned, active, weight, blockchain) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        DEFAULT_BASE_NODES_AT_V40,
    )
    log.debug('Exit _add_base_chain_data')


def _migrate_ledger_actions(write_cursor: 'DBCursor', conn: 'DBConnection') -> None:
    """
    Migrate all ledger actions to history events, so that we can get rid of the
    deprecated ledger action structure.

    Part of https://github.com/rotki/rotki/issues/6096
    """
    log.debug('Enter _migrate_ledger_actions')
    history_events = []
    with conn.read_ctx() as cursor:
        cursor.execute('SELECT timestamp, type, location, amount, asset, rate, rate_asset, link, notes FROM ledger_actions')  # noqa: E501
        for entry in cursor:
            location = entry[2]
            try:
                val = ord(location)  # can raise TypeError
                if val < 65 or val > 106:  # not between A and j
                    raise TypeError
            except TypeError:
                log.error(f'Skipped a ledger action from migration to history event due to invalid location {location}')  # noqa: E501
                continue

            usd_value = ZERO  # try to use a rate asset if given only if it's against USD. Unfortunately this means we can lose data here but there is no way to translate this to a single history event  # noqa: E501
            if entry[5] is not None and entry[6] is not None and entry[6] == 'USD':
                try:
                    amount = deserialize_fval(entry[3], 'amount', 'ledger actions migration')
                    rate = deserialize_fval(entry[5], 'rate', 'ledger actions migration')
                except DeserializationError as e:
                    log.error(f'Skipped a ledger action from migration to history event due {e}')  # noqa: E501
                    continue

                usd_value = amount * rate

            ledger_action_type = entry[1]
            notes = f'Migrated from a ledger action of {LEDGER_ACTION_TYPE_TO_NAME[ledger_action_type]} type'  # due to DB consistency there should be no key errors # noqa: E501
            if entry[8] is not None:
                notes = f'{entry[8]}. {notes}'
            if entry[7] is not None:
                notes = f'{notes}. {entry[7]}'

            # map the types. Making sure to have the as default/valid combinations
            if ledger_action_type in ('A', 'D', 'G', 'H'):  # income, dividends income, gift, grant action type  # noqa: E501
                event_type = 'receive'
                event_subtype = 'none'
            elif ledger_action_type in ('B', 'C'):  # expense, loss action type
                event_type = 'spend'
                event_subtype = 'none'
            elif ledger_action_type == 'E':
                event_type = 'receive'
                event_subtype = 'donate'
            elif ledger_action_type == 'F':
                event_type = 'receive'
                event_subtype = 'airdrop'
            else:
                raise AssertionError('Should never happen. Guaranteed by DB consistency')

            history_events.append((
                1,  # entry_type -> HISTORY_EVENT
                f'{LEDGER_ACTIONS_PREFIX}{uuid4().hex}',  # event_identifier
                0,  # sequence_index
                entry[0] * 1000,  # timestamp
                location,
                None,  # location_label
                entry[4],  # asset
                entry[3],  # amount
                str(usd_value),  # usd_value
                notes,
                event_type,
                event_subtype,
            ))

    write_cursor.executemany("""INSERT OR IGNORE INTO history_events(
    entry_type,
    event_identifier,
    sequence_index,
    timestamp,
    location,
    location_label,
    asset,
    amount,
    usd_value,
    notes,
    type,
    subtype) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", history_events)
    write_cursor.execute('DROP TABLE IF EXISTS ledger_actions;')
    write_cursor.execute('DROP TABLE IF EXISTS ledger_action_type;')

    log.debug('Exit _migrate_ledger_actions')


def _add_new_tables(write_cursor: 'DBCursor') -> None:
    """
    Add new tables for this upgrade
    """
    log.debug('Entered _add_new_tables')
    write_cursor.execute("""CREATE TABLE IF NOT EXISTS skipped_external_events (
    identifier INTEGER NOT NULL PRIMARY KEY,
    data TEXT NOT NULL,
    location CHAR(1) NOT NULL DEFAULT('A') REFERENCES location(location),
    extra_data TEXT
    );""")
    log.debug('Exit _add_new_tables')


def upgrade_v39_to_v40(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v39 to v40. This was in v1.31.0 release.

        - Migrate rotki events that were broken due to https://github.com/rotki/rotki/issues/6550
        - Purge kraken events
        - Create new tables
    """
    log.debug('Entered userdb v39->v40 upgrade')
    progress_handler.set_total_steps(7)
    with db.user_write() as write_cursor:
        _migrate_rotki_events(write_cursor)
        progress_handler.new_step()
        _purge_kraken_events(write_cursor)
        progress_handler.new_step()
        _add_base_chain_data(write_cursor)
        progress_handler.new_step()
        _upgrade_rotki_events(write_cursor)
        progress_handler.new_step()
        _migrate_ledger_actions(write_cursor, db.conn)
        progress_handler.new_step()
        _add_new_tables(write_cursor)
        progress_handler.new_step()

    db.conn.execute('VACUUM;')
    progress_handler.new_step()

    log.debug('Finished userdb v39->v40 upgrade')
