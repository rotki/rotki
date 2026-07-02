import json
import logging
from typing import TYPE_CHECKING

from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_27(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at v1.43.3

    Remove the defunct Loopring module from active modules, queried addresses, cached account id
    mappings, and external service credentials.
    """
    @progress_step(description='Removing loopring module settings')
    def _remove_loopring_module_settings(rotki: 'Rotkehlchen') -> None:
        with rotki.data.db.conn.write_ctx() as write_cursor:
            if (active_modules_result := write_cursor.execute("SELECT value FROM settings WHERE name='active_modules'").fetchone()) is not None:  # noqa: E501
                try:
                    active_modules = json.loads(active_modules_result[0])
                except json.JSONDecodeError:
                    log.error(
                        'During data migration 27 a non-json active_modules entry was found: %s.',
                        active_modules_result[0],
                    )
                else:
                    write_cursor.execute(
                        "UPDATE OR IGNORE settings SET value=? WHERE name='active_modules'",
                        (json.dumps([
                            module for module in active_modules
                            if module != 'loopring'
                        ]),),
                    )

            write_cursor.execute(
                'DELETE FROM multisettings WHERE name=?',
                ('queried_address_loopring',),
            )
            write_cursor.execute(
                'DELETE FROM multisettings WHERE name LIKE ? ESCAPE ?',
                ('loopring\\_%', '\\'),
            )
            write_cursor.execute(
                'DELETE FROM external_service_credentials WHERE name=?',
                ('loopring',),
            )

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=False)
