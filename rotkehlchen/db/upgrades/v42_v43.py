import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def _add_usd_price_nft_table(write_cursor: 'DBCursor') -> None:
    write_cursor.execute(
        'ALTER TABLE nfts ADD COLUMN usd_price REAL NOT NULL DEFAULT 0;',
    )


@enter_exit_debug_log()
def _change_hop_counterparty_value(write_cursor: 'DBCursor') -> None:
    write_cursor.execute(
        'UPDATE evm_events_info SET counterparty=? WHERE counterparty=?',
        ('hop', 'hop-protocol'),
    )


@enter_exit_debug_log(name='UserDB v42->v43 upgrade')
def upgrade_v42_to_v43(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v42 to v43. This was in v1.34 release.

    - add usd_price to the nfts table
    - change hop protocol counterparty value
    """
    progress_handler.set_total_steps(2)
    with db.user_write() as write_cursor:
        _add_usd_price_nft_table(write_cursor)
        progress_handler.new_step()
        _change_hop_counterparty_value(write_cursor)
        progress_handler.new_step()
