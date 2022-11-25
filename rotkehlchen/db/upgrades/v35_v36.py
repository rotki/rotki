import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _rename_eth_to_evm_add_chainid(write_cursor: 'DBCursor') -> None:
    write_cursor.execute('/*IMPLEMENT ME*/')


def _upgrade_events_mappings(write_cursor: 'DBCursor') -> None:
    """TODO: Upgrade both evm_tx_mappings and history_events_mappings"""
    write_cursor.execute('/*IMPLEMENT ME*/')


def _remove_adex(write_cursor: 'DBCursor') -> None:
    """TODO: Remove all adex related tables, events, data in other tables.
    Check removal commit to see all data that should go
    """
    write_cursor.execute('/*IMPLEMENT ME*/')


def upgrade_v35_to_v36(db: 'DBHandler') -> None:
    """Upgrades the DB from v35 to v36
    - Rename all ethereum transaction tables and add chainid to them
    - Upgrade history_events_mappings to the new format
    """
    log.debug('Entered userdb v35->v36 upgrade')
    with db.user_write() as write_cursor:
        _rename_eth_to_evm_add_chainid(write_cursor)

    log.debug('Finished userdb v35->v36 upgrade')
