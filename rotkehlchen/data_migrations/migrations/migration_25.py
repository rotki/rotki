import json
from typing import TYPE_CHECKING

from rotkehlchen.logging import enter_exit_debug_log
from rotkehlchen.types import ExternalService
from rotkehlchen.utils.progress import perform_userdb_migration_steps, progress_step

if TYPE_CHECKING:
    from rotkehlchen.data_migrations.progress import MigrationProgressHandler
    from rotkehlchen.rotkehlchen import Rotkehlchen


CRYPTOCOMPARE_ORACLE = 'cryptocompare'
ORACLE_SETTINGS_DEFAULTS = {
    'current_price_oracles': ['defillama', 'coingecko', 'uniswapv2', 'uniswapv3'],
    'historical_price_oracles': ['defillama', 'coingecko', 'uniswapv3', 'uniswapv2'],
}


@enter_exit_debug_log()
def data_migration_25(rotki: 'Rotkehlchen', progress_handler: 'MigrationProgressHandler') -> None:
    """Introduced at v1.43.1
    - Remove cryptocompare from configured price oracles if no API key is set.
    """
    @progress_step(description='Removing cryptocompare oracle without API key')
    def _remove_cryptocompare_without_api_key(rotki: 'Rotkehlchen') -> None:
        with rotki.data.db.conn.write_ctx() as write_cursor:
            if write_cursor.execute(
                'SELECT COUNT(*) FROM external_service_credentials WHERE name=?',
                (ExternalService.CRYPTOCOMPARE.serialize(),),
            ).fetchone()[0] != 0:
                return

            for setting_name, default_oracles in ORACLE_SETTINGS_DEFAULTS.items():
                if (result := write_cursor.execute(
                    'SELECT value FROM settings WHERE name=?',
                    (setting_name,),
                ).fetchone()) is None:
                    continue

                oracles = json.loads(result[0])
                if CRYPTOCOMPARE_ORACLE not in oracles:
                    continue

                new_oracles = [oracle for oracle in oracles if oracle != CRYPTOCOMPARE_ORACLE]
                write_cursor.execute(
                    'UPDATE settings SET value=? WHERE name=?',
                    (
                        json.dumps(new_oracles if len(new_oracles) != 0 else default_oracles),
                        setting_name,
                    ),
                )

    perform_userdb_migration_steps(rotki, progress_handler, should_vacuum=False)
