import logging
import shutil
from typing import TYPE_CHECKING

from rotkehlchen.constants import APPDIR_NAME
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
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

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=True)
