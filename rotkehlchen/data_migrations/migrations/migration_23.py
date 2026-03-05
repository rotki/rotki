import logging
from typing import TYPE_CHECKING

from rotkehlchen.db.constants import EXTRAINTERNALTXPREFIX, TX_INTERNALS_QUERIED
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.utils.hexbytes import hexstring_to_bytes
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_23(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at v1.42.1
    - Move extrainternaltx dynamic cache entries to evm_tx_mappings(TX_INTERNALS_QUERIED)
    """
    @progress_step(description='Migrating internal transaction query cache to tx mappings')
    def _migrate_internal_tx_cache_to_mappings(rotki: 'Rotkehlchen') -> None:
        with rotki.data.db.conn.write_ctx() as write_cursor:
            rows = write_cursor.execute(
                'SELECT name FROM key_value_cache WHERE name LIKE ? ESCAPE ?',
                (f'{EXTRAINTERNALTXPREFIX}\\_%', '\\'),
            )
            mapping_tuples: list[tuple[int, bytes, int]] = []
            for cache_key, in rows:
                split_key = cache_key.split('_', 3)
                if len(split_key) != 4:
                    log.error(f'Skipping malformed {EXTRAINTERNALTXPREFIX} cache key: {cache_key}')
                    continue

                _, raw_chain_id, _, raw_tx_hash = split_key
                try:
                    mapping_tuples.append((
                        TX_INTERNALS_QUERIED,
                        hexstring_to_bytes(raw_tx_hash),
                        int(raw_chain_id),
                    ))
                except (ValueError, DeserializationError) as e:
                    log.error(
                        f'Failed to parse {EXTRAINTERNALTXPREFIX} cache key {cache_key} due to {e!s}',  # noqa: E501
                    )

            if len(mapping_tuples) != 0:
                write_cursor.executemany(
                    'INSERT OR IGNORE INTO evm_tx_mappings(tx_id, value) '
                    'SELECT identifier, ? FROM evm_transactions WHERE tx_hash=? AND chain_id=?',
                    mapping_tuples,
                )

            # Cleanup after migration. Runtime no longer reads these keys.
            write_cursor.execute(
                'DELETE FROM key_value_cache WHERE name LIKE ? ESCAPE ?',
                (f'{EXTRAINTERNALTXPREFIX}\\_%', '\\'),
            )

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=False)
