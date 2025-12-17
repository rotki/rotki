import logging
from typing import TYPE_CHECKING

from rotkehlchen.exchanges.coinbase import ECDSA_KEY_RE
from rotkehlchen.logging import RotkehlchenLogsAdapter, enter_exit_debug_log
from rotkehlchen.types import Location
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


@enter_exit_debug_log()
def data_migration_22(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at v1.41.3
    Removes any Coinbase exchanges with legacy api keys.
    """
    @progress_step(description='Removing legacy Coinbase api keys')
    def _remove_legacy_coinbase_keys(rotki: 'Rotkehlchen') -> None:
        with rotki.data.db.conn.read_ctx() as cursor:
            creds = rotki.data.db.get_exchange_credentials(
                cursor=cursor,
                location=Location.COINBASE,
            )[Location.COINBASE]

        success = True
        for cred in creds:
            if (
                ECDSA_KEY_RE.match(cred.api_key) or
                (len(cred.api_key) == 36 and cred.api_key.count('-') == 4)
            ):  # skip any valid ECDSA or ED25519 keys
                continue

            # Use delete_exchange to remove both from the DB and the list of connected exchanges.
            success, msg = rotki.exchange_manager.delete_exchange(
                name=cred.name,
                location=cred.location,
            )
            if not success:
                log.error(f'Failed to remove legacy coinbase credentials for {cred.name}: {msg}')

        if not success:
            rotki.msg_aggregator.add_error('Failed to remove legacy coinbase credentials. See logs for details.')  # noqa: E501

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=False)
