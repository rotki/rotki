from typing import TYPE_CHECKING

from rotkehlchen.exchanges.coinbase import ECDSA_KEY_RE
from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.types import ExchangeApiCredentials, Location
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen


@enter_exit_debug_log()
def data_migration_22(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at v1.41.3
    Removes legacy Coinbase api keys from the user db.
    """
    @progress_step(description='Removing legacy Coinbase api keys')
    def _remove_legacy_coinbase_keys(rotki: 'Rotkehlchen') -> None:
        with rotki.data.db.conn.read_ctx() as cursor:
            creds = rotki.data.db.get_exchange_credentials(
                cursor=cursor,
                location=Location.COINBASE,
            )[Location.COINBASE]

        creds_to_remove: list[ExchangeApiCredentials] = []
        for cred in creds:
            if (
                ECDSA_KEY_RE.match(cred.api_key) or
                (len(cred.api_key) == 36 and cred.api_key.count('-') == 4)
            ):  # skip any valid ECDSA or ED25519 keys
                continue

            creds_to_remove.append(cred)

        with rotki.data.db.conn.write_ctx() as write_cursor:
            write_cursor.executemany(
                'DELETE FROM user_credentials WHERE name=? AND location=?',
                [(cred.name, cred.location.serialize_for_db()) for cred in creds_to_remove],
            )

    perform_userdb_migration_steps(rotki, progress_handler)
