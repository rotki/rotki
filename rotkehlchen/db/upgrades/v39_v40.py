import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

PREFIX = 'RE_%'  # hard-coded since this is a migration and prefix may change in the future
CHANGES = [  # TO TYPE, TO SUBTYPE, FROM TYPE, FROM SUBTYPE
    (HistoryEventType.DEPOSIT, HistoryEventSubType.NONE, HistoryEventType.DEPOSIT, HistoryEventSubType.SPEND),  # noqa: E501
    (HistoryEventType.WITHDRAWAL, HistoryEventSubType.NONE, HistoryEventType.WITHDRAWAL, HistoryEventSubType.RECEIVE),  # noqa: E501
    (HistoryEventType.RECEIVE, HistoryEventSubType.NONE, HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE),  # noqa: E501

    (HistoryEventType.SPEND, HistoryEventSubType.FEE, HistoryEventType.DEPOSIT, HistoryEventSubType.FEE),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, HistoryEventType.WITHDRAWAL, HistoryEventSubType.FEE),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, HistoryEventType.RECEIVE, HistoryEventSubType.FEE),  # noqa: E501
    (HistoryEventType.SPEND, HistoryEventSubType.FEE, HistoryEventType.STAKING, HistoryEventSubType.FEE),  # noqa: E501
]


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
    for table in ('trades', 'asset_movements', 'ledger_actions', 'history_events'):
        write_cursor.execute(f'DELETE FROM {table} WHERE location = ?;', (location,))

    log.debug('Exit _reset_kraken_events')


def upgrade_v39_to_v40(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v39 to v40. This was in v1.31.0 release.
        - Migrate rotki events that were broken due to https://github.com/rotki/rotki/issues/6550
    """
    log.debug('Entered userdb v39->v40 upgrade')
    progress_handler.set_total_steps(3)
    with db.user_write() as write_cursor:
        _migrate_rotki_events(write_cursor)
        progress_handler.new_step()
        _purge_kraken_events(write_cursor)
        progress_handler.new_step()

    db.conn.execute('VACUUM;')
    progress_handler.new_step()

    log.debug('Finished userdb v39->v40 upgrade')
