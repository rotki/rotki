import logging
from pathlib import Path
from typing import TYPE_CHECKING

from rotkehlchen.constants.misc import AIRDROPSDIR_NAME, APPDIR_NAME
from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
    HISTORY_MAPPING_STATE_DECODED,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import Location

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.client import DBCursor
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


@enter_exit_debug_log()
def _add_new_supported_locations(write_cursor: 'DBCursor') -> None:
    write_cursor.execute(
        'INSERT OR IGNORE INTO location(location, seq) VALUES (?, ?)',
        ('p', Location.HTX.value),
    )


@enter_exit_debug_log()
def _remove_coinbasepro_credentials(write_cursor: 'DBCursor') -> None:
    write_cursor.execute(
        'DELETE FROM user_credentials WHERE location=?;',
        (Location.COINBASEPRO.serialize_for_db(),),
    )


@enter_exit_debug_log()
def _remove_old_csv_files(data_dir: Path) -> None:
    """Delete old csv files for airdrops"""
    airdrops_dir = data_dir / APPDIR_NAME / AIRDROPSDIR_NAME
    for csv_file_path in airdrops_dir.glob('*.csv'):
        try:
            csv_file_path.unlink()
        except OSError as e:
            log.error(f'Failed to remove airdrop file {csv_file_path} due to {e}. Skipping it')
        else:
            log.debug(f'Deleted {csv_file_path} as part of the db upgrade')


@enter_exit_debug_log()
def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
    """Reset all decoded evm events except for the customized ones and those in zksync lite."""
    if write_cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0] > 0:
        customized_events = write_cursor.execute(
            'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?',
            (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
        ).fetchone()[0]
        querystr = (
            'DELETE FROM history_events WHERE identifier IN ('
            'SELECT H.identifier from history_events H INNER JOIN evm_events_info E '
            'ON H.identifier=E.identifier AND E.tx_hash IN '
            '(SELECT tx_hash FROM evm_transactions) AND H.location != "o")'  # location 'o' is zksync lite  # noqa: E501
        )
        bindings: tuple = ()
        if customized_events != 0:
            querystr += ' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)'  # noqa: E501
            bindings = (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED)

        write_cursor.execute(querystr, bindings)
        write_cursor.execute(
            'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions) AND value=?',  # noqa: E501
            (HISTORY_MAPPING_STATE_DECODED,),
        )


@enter_exit_debug_log(name='UserDB v42->v43 upgrade')
def upgrade_v42_to_v43(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v42 to v43. This was in v1.34 release.

    - add usd_price to the nfts table
    - change hop protocol counterparty value
    - add new supported location: HTX
    - remove coinbasepro credentials
    - remove CSVs files since they will be replaced by parquet files
    - reset decoded evm events except for zksync lite and custom ones
    """
    progress_handler.set_total_steps(6)
    with db.user_read_write() as write_cursor:
        _add_usd_price_nft_table(write_cursor)
        progress_handler.new_step()
        _change_hop_counterparty_value(write_cursor)
        progress_handler.new_step()
        _add_new_supported_locations(write_cursor)
        progress_handler.new_step()
        _remove_coinbasepro_credentials(write_cursor)
        progress_handler.new_step()
        _remove_old_csv_files(db.user_data_dir.parent.parent)
        progress_handler.new_step()
        _reset_decoded_events(write_cursor)
        progress_handler.new_step()
