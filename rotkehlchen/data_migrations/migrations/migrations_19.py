import logging
import shutil
from typing import TYPE_CHECKING

from rotkehlchen.chain.gnosis.constants import BRIDGE_QUERIED_ADDRESS_PREFIX
from rotkehlchen.constants import APPDIR_NAME
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import SupportedBlockchain
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_19(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """
    Introduced at v1.36.1

    - Clean incorrectly created folder `app` in the users/{username} folder
    """
    @progress_step(description="Cleaning up rotki's directory tree.")
    def _delete_bad_folder(rotki: 'Rotkehlchen') -> None:
        bad_folder = rotki.user_directory / APPDIR_NAME
        if bad_folder.exists():
            log.info(f'Deleting folder {bad_folder} created by mistake')
            shutil.rmtree(bad_folder)

    @progress_step(description='Cleaning unused gnosis bridge logs.')
    def _delete_old_gnosis_bridge_ranges(rotki: 'Rotkehlchen') -> None:
        """Delete query ranges for accounts that were deleted"""
        db = rotki.data.db
        with db.conn.read_ctx() as cursor:
            addresses = db.get_single_blockchain_addresses(
                cursor=cursor,
                blockchain=SupportedBlockchain.GNOSIS,
            )
            db_query_ranges: list[str] = [row[0] for row in cursor.execute(
                'SELECT name FROM used_query_ranges WHERE name LIKE ?',
                (f'{BRIDGE_QUERIED_ADDRESS_PREFIX}%',),
            )]

        expected_ranges = {f'{BRIDGE_QUERIED_ADDRESS_PREFIX}{address}' for address in addresses}
        with db.user_write() as write_cursor:
            for entry_name in db_query_ranges:
                if entry_name not in expected_ranges:
                    write_cursor.execute(
                        'DELETE FROM used_query_ranges where name=?',
                        (entry_name,),
                    )

    @progress_step(description='Refresh coinbase queries')
    def _refresh_coinbase_queries(rotki: 'Rotkehlchen') -> None:
        with rotki.data.db.user_write() as write_cursor:
            write_cursor.execute('DELETE FROM key_value_cache WHERE name LIKE ? ESCAPE ?', ('coinbase\\_%\\_last\\_query\\_ts', '\\'))  # noqa: E501

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=True)
