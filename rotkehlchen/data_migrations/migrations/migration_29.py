import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.constants import ZERO_32_BYTES_HEX
from rotkehlchen.db.constants import HISTORY_MAPPING_KEY_STATE, HistoryMappingState
from rotkehlchen.history.events.utils import create_group_identifier_from_unique_id
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import Location
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_29(rotki: Rotkehlchen, progress_handler: MigrationProgressHandler) -> None:
    """Introduced at v1.44.2

    Hyperliquid Core history used to be paged backwards while the API returns the oldest
    entries of a range first, so only the first page of each queried range was saved.
    Remove the query ranges of the Hyperliquid Core history so that the next sync queries
    it all again. The events already saved are kept and querying them again is harmless.

    Funding payments were also identified by their hash, which is the zero hash for all of
    them, so they all got the same group identifier and only the first one ever queried
    was saved. Remove that event, since it is saved again under its own group identifier
    by the next sync, unless it was customized.
    """
    @progress_step(description='Resetting Hyperliquid Core history query ranges')
    def _reset_hyperliquid_core_history_ranges(rotki: Rotkehlchen) -> None:
        with rotki.data.db.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?',
                ('hyperliquid\\_core\\_history\\_%', '\\'),
            )

    @progress_step(description='Removing the Hyperliquid funding event with the zero hash')
    def _remove_zero_hash_funding_event(rotki: Rotkehlchen) -> None:
        with rotki.data.db.user_write() as write_cursor:
            write_cursor.execute(
                'DELETE FROM history_events WHERE group_identifier=? AND location=? AND '
                'NOT EXISTS(SELECT 1 FROM history_events_mappings WHERE '
                'parent_identifier=history_events.identifier AND name=? AND value=?)',
                (
                    create_group_identifier_from_unique_id(
                        location=Location.HYPERLIQUID,
                        unique_id=ZERO_32_BYTES_HEX,
                    ),
                    Location.HYPERLIQUID.serialize_for_db(),
                    HISTORY_MAPPING_KEY_STATE,
                    HistoryMappingState.CUSTOMIZED.serialize_for_db(),
                ),
            )

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=False)
