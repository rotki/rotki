import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.constants import (
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_upgrade_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.db.upgrade_manager import DBUpgradeProgressHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log(name='UserDB v44->v45 upgrade')
def upgrade_v44_to_v45(db: 'DBHandler', progress_handler: 'DBUpgradeProgressHandler') -> None:
    """Upgrades the DB from v44 to v45. This was in v1.36 release.

    - Add coinbase prime location
    - reset decoded events
    """
    @progress_step(description='Adding new locations to the DB.')
    def _add_new_locations(write_cursor: 'DBCursor') -> None:
        write_cursor.executescript("""
        /* Coinbase Prime */
        INSERT OR IGNORE INTO location(location, seq) VALUES ('u', 53);
        """)

    @progress_step(description='Resetting decoded events.')
    def _reset_decoded_events(write_cursor: 'DBCursor') -> None:
        """Reset all decoded evm events except for the customized ones and those in zksync lite.
        Code taken from previous upgrade
        """
        if write_cursor.execute('SELECT COUNT(*) FROM evm_transactions').fetchone()[0] > 0:
            customized_events = write_cursor.execute(
                'SELECT COUNT(*) FROM history_events_mappings WHERE name=? AND value=?',
                (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED),
            ).fetchone()[0]
            querystr = (
                "DELETE FROM history_events WHERE identifier IN ("
                "SELECT H.identifier from history_events H INNER JOIN evm_events_info E "
                "ON H.identifier=E.identifier AND E.tx_hash IN "
                "(SELECT tx_hash FROM evm_transactions) AND H.location != 'o')"  # location 'o' is zksync lite  # noqa: E501
            )
            bindings: tuple = ()
            if customized_events != 0:
                querystr += ' AND identifier NOT IN (SELECT parent_identifier FROM history_events_mappings WHERE name=? AND value=?)'  # noqa: E501
                bindings = (HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED)

            write_cursor.execute(querystr, bindings)
            write_cursor.execute(
                'DELETE from evm_tx_mappings WHERE tx_id IN (SELECT identifier FROM evm_transactions) AND value=?',  # noqa: E501
                (0,),  # decoded tx state
            )

    perform_userdb_upgrade_steps(db=db, progress_handler=progress_handler, should_vacuum=True)
