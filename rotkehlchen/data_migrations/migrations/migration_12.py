import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

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


def data_migration_12(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """
    Migrate rotki events that were broken due to https://github.com/rotki/rotki/issues/6550

    May be introduced at v1.30.2. In any case will be removed when DB upgrade 39 -> 40 happens
    as it will move to that DB upgrade.
    """
    log.debug('Enter data_migration_12')
    progress_handler.set_total_steps(1)
    progress_handler.new_step('Migrating custom rotki events')

    with rotki.data.db.conn.write_ctx() as write_cursor:
        write_cursor.executemany(
            'UPDATE history_events SET type=?, subtype=? WHERE '
            'event_identifier LIKE ? AND type=? AND subtype=?',
            [(
                to_type.serialize(), to_subtype.serialize(), PREFIX,
                from_type.serialize(), from_subtype.serialize(),
            ) for to_type, to_subtype, from_type, from_subtype in CHANGES],
        )

    log.debug('Exit data_migration_12')
