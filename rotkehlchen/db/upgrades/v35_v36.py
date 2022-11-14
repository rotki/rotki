import json
import logging
from typing import TYPE_CHECKING, List, Literal, Sequence, Tuple, Type

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.assets.spam_assets import update_spam_assets
from rotkehlchen.constants.resolver import (
    ETHEREUM_DIRECTIVE,
    ETHEREUM_DIRECTIVE_LENGTH,
    ChainID,
    evm_address_to_identifier,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.globaldb.upgrades.v2_v3 import OTHER_EVM_CHAINS_ASSETS
from rotkehlchen.history.types import DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER, HistoricalPriceOracle
from rotkehlchen.inquirer import DEFAULT_CURRENT_PRICE_ORACLES_ORDER, CurrentPriceOracle
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import EvmTokenKind, OracleSource, SupportedBlockchain
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _rename_eth_to_evm_add_chainid(write_cursor: 'DBCursor'):
    pass


def _upgrade_history_events_mappings(write_cursor: 'DBCursor'):
    pass
    # with db.conn.read_ctx() as read_cursor:
    #     read_cursor.execute('SELECT * from history_events_mappings')
    #     for entry in read_cursor:
    #         write_cursor.execute(
    #             'INSERT OR IGNORE INTO evm_tx_mappings(tx_hash, chain_id, value) VALUES(?, ?, ?)',  # noqa: E501
    #             (entry),
    #         )


def upgrade_v35_to_v36(db: 'DBHandler') -> None:
    """Upgrades the DB from v35 to v36
    - Rename all ethereum transaction tables and add chainid to them
    - Upgrade history_events_mappings to the new format
    """
    log.debug('Entered userdb v35->v36 upgrade')
    with db.user_write() as write_cursor:
        _rename_eth_to_evm_add_chainid(write_cursor)

    log.debug('Finished userdb v35->v36 upgrade')
